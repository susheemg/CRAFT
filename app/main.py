"""Application entrypoint.

On start-up the service migrates the schema, seeds reference data and starts the
outbox relay — in that order, and all of it idempotent, so a Render deploy or a
container restart converges on the right state without an operator running
anything by hand.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.idempotency import IdempotencyMiddleware
from app.api.v1 import (
    admin_llm, admin_rbac, appsec, auth, compliance, operations, platform, processes,
    risks,
)
from app.config import get_settings
from app.db import engine, session_scope
from app.mcp import server as mcp_server
from app.migrate import run as run_migrations
from app.security.rbac import AuthorizationError
from app.services import outbox
from app.web import router as web_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger("craft")
settings = get_settings()

DESCRIPTION = """
An AI-native governance, risk and compliance platform.

**How to use this API.** Sign in at `POST /v1/auth/login`, or present a bearer
token issued by `POST /v1/auth/tokens`. Every endpoint declares the permission
it needs; the token carries no more authority than the principal behind it.

**Three properties worth knowing before you build against it.**

*The audit log cannot be edited.* Entries are hash-chained and the database
refuses `UPDATE` and `DELETE`. `GET /v1/audit/verify` recomputes the chain and
names the exact sequence number of any break.

*Approvals belong to people.* Agent principals cannot hold approval authority.
An action that needs a decision returns `202` with a gate identifier rather
than proceeding.

*Model calls are governed.* Provider, routing, budget and caching are
administered through `/v1/admin/llm`. Credentials are sealed on receipt and
never returned.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("CRAFT %s starting in %s", settings.version, settings.environment)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        # Re-raising the driver exception alone produces a two-hundred line
        # SQLAlchemy traceback whose first useful word is on the last line. The
        # operator needs to know which host was tried and which variable chose
        # it, so that goes first and the traceback follows.
        from urllib.parse import urlsplit

        parsed = urlsplit(settings.database_url)
        target = f"{parsed.hostname or 'unknown'}:{parsed.port or 5432}"
        log.error(
            "Cannot reach the database at %s (from CRAFT_DATABASE_URL). "
            "The service will not start without it.",
            target,
        )
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            log.error(
                "That host is the local development default, which means "
                "CRAFT_DATABASE_URL is not reaching this container. On Render, "
                "check that the service was created from render.yaml and that "
                "the fromDatabase link to craft-db is still present."
            )
        log.error("Underlying error: %s", exc)
        raise

    if settings.auto_migrate:
        applied = run_migrations()
        log.info("Migrations: %s", f"{len(applied)} applied" if applied else "already current")

    if settings.auto_seed:
        from app.seed import run as run_seed

        with session_scope(bypass_rls=True) as db:
            summary = run_seed(db)
        log.info(
            "Seed complete: %s permissions, %s roles, %s controls",
            summary["permissions"],
            summary["roles"],
            summary["controls"],
        )
        if summary.get("generated_password"):
            # Printed once, at first boot only, because there is otherwise no
            # way into a fresh deployment.
            log.warning(
                "\n%s\nBootstrap administrator: %s\nPassword: %s\n"
                "Sign in and change this now. It will not be shown again.\n%s",
                "=" * 68,
                summary["admin_email"],
                summary["generated_password"],
                "=" * 68,
            )

    stop = asyncio.Event()
    relay = None
    if settings.enable_outbox_relay:
        relay = asyncio.create_task(outbox.relay_loop(stop))
        log.info("Outbox relay started")

    yield

    stop.set()
    if relay:
        relay.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relay
    log.info("CRAFT stopped")


app = FastAPI(
    title="CRAFT",
    description=DESCRIPTION,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "persistAuthorization": True},
)


# --------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "Unhandled error on %s %s (request_id=%s)",
            request.method,
            request.url.path,
            request_id,
        )
        raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    # Modest hardening: the UI is server-rendered and loads no third-party assets.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if elapsed_ms > 3000:
        log.warning("Slow request: %s %s took %sms", request.method, request.url.path, elapsed_ms)
    return response


app.add_middleware(IdempotencyMiddleware)

if settings.cors_origins:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )


# --------------------------------------------------------------------------
# Error handling — one envelope shape everywhere
# --------------------------------------------------------------------------
@app.exception_handler(AuthorizationError)
async def authorization_error(request: Request, exc: AuthorizationError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    """Normalise every raised HTTPException into the documented envelope.

    Handlers raise with either a bare string or an already-shaped error body;
    without this, callers would have to parse two different formats depending
    on which layer refused them.
    """
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        body = detail
        body["error"].setdefault("request_id", request_id)
    else:
        body = {
            "error": {
                "code": _CODE_FOR_STATUS.get(exc.status_code, "error"),
                "message": detail if isinstance(detail, str) else "Request refused.",
                "request_id": request_id,
            }
        }
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


_CODE_FOR_STATUS = {
    400: "bad_request",
    401: "unauthenticated",
    403: "permission_denied",
    404: "not_found",
    409: "conflict",
    422: "validation_failed",
    429: "rate_limited",
    503: "unavailable",
}


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_failed",
                "message": "The request did not match the expected shape.",
                "details": [
                    {
                        "field": ".".join(str(p) for p in err["loc"][1:]) or None,
                        "issue": err["msg"],
                    }
                    for err in exc.errors()
                ],
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    log.exception("Unhandled %s (request_id=%s)", type(exc).__name__, request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                # Never leak internals to the caller; the detail is in the log.
                "message": "Something went wrong. Quote the request id when reporting it.",
                "request_id": request_id,
            }
        },
    )


# --------------------------------------------------------------------------
# Routers
# --------------------------------------------------------------------------
v1 = APIRouter(prefix="/v1")
v1.include_router(auth.router)
v1.include_router(risks.router)
v1.include_router(compliance.router)
v1.include_router(operations.router)
v1.include_router(admin_llm.router)
v1.include_router(admin_rbac.router)
v1.include_router(platform.audit_router)
v1.include_router(platform.integ_router)
v1.include_router(processes.router)
v1.include_router(processes.agent_router)
v1.include_router(processes.oversight_router)
v1.include_router(appsec.router)
v1.include_router(appsec.ai_router)
app.include_router(v1)
app.include_router(mcp_server.router)
app.include_router(web_router)

_STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"
if not _STATIC_DIR.is_dir():  # pragma: no cover - packaging fault
    raise RuntimeError(
        f"Static assets are missing from {_STATIC_DIR}. The console would render "
        "unstyled, so this is a packaging fault rather than something to ignore."
    )
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------
@app.get("/healthz", tags=["Health"], summary="Liveness")
def healthz() -> dict:
    return {"status": "ok", "version": settings.version, "environment": settings.environment}


@app.get("/readyz", tags=["Health"], summary="Readiness")
def readyz() -> JSONResponse:
    """Ready means the database answers and the schema is present.

    A process that is up but cannot reach its database should not receive
    traffic, so this checks rather than assumes.
    """
    checks: dict[str, object] = {}
    ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            tables = conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema IN "
                    "('iam','ref','core','domain','compliance','config','audit','integ')"
                )
            ).scalar_one()
        checks["database"] = "ok"
        checks["tables"] = tables
        if tables < 40:
            ok = False
            checks["schema"] = f"only {tables} tables present; migrations may not have run"
    except Exception as exc:
        ok = False
        checks["database"] = f"unreachable: {type(exc).__name__}"
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": jsonable_encoder(checks)},
    )
