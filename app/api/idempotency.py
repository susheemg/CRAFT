"""Idempotency for mutating requests.

The API accepted an ``Idempotency-Key`` header and did nothing with it, which is
worse than not offering it: a client that retried a timed-out ``POST /v1/risks``
believing itself protected got a second risk on the register. Mobile clients
retry, load balancers retry, and people double-click.

The guarantee: within the retention window, the same key and the same body on
the same endpoint returns the original response without re-running the handler.
The same key with a *different* body is refused, because that means the key is
being reused for something else and replaying the old answer would be a lie.

It is implemented as middleware rather than a per-endpoint dependency so that
every mutating route is covered by construction — a new endpoint cannot forget
to opt in.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import SessionLocal, identity_lookup, set_session_context
from app.models.audit import IdempotencyKey
from app.models.base import utcnow
from app.models.iam import ApiToken
from app.security.auth import TokenInvalid, decode_token
from app.security.crypto import sha256_hex

log = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
RETENTION = timedelta(hours=24)
MAX_STORED_BODY = 64_000


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("Idempotency-Key")
        if not key or request.method not in MUTATING_METHODS:
            return await call_next(request)
        if len(key) > 80:
            return _error(
                400,
                "idempotency_key_too_long",
                "An Idempotency-Key may be at most 80 characters.",
                request,
            )

        body = await request.body()
        endpoint = f"{request.method} {request.url.path}"
        digest = sha256_hex(body.decode("utf-8", "replace"))

        # The tenant must be known before the store can be consulted, and that
        # happens before the route resolves the principal. Resolving it from
        # the credential here is cheap and keeps one tenant from ever replaying
        # another's response by guessing a key.
        tenant_id = _tenant_from_credentials(request)
        if tenant_id is None:
            # Unauthenticated or unreadable credential: let the request through
            # and let the normal 401 happen rather than inventing a scope.
            return await call_next(request)

        db = SessionLocal()
        try:
            set_session_context(db, tenant_id, "system:idempotency")
            existing = db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id,
                    IdempotencyKey.key == key,
                    IdempotencyKey.endpoint == endpoint,
                )
            ).scalar_one_or_none()

            if existing is not None:
                if existing.request_digest != digest:
                    return _error(
                        422,
                        "idempotency_key_reused",
                        "This Idempotency-Key was already used for a different "
                        "request body on this endpoint. Use a new key.",
                        request,
                    )
                if existing.response_body is None:
                    # A request with this key is still in flight. Returning the
                    # half-finished state would be worse than saying so.
                    return _error(
                        409,
                        "idempotency_in_progress",
                        "A request with this Idempotency-Key is still being "
                        "processed. Retry shortly.",
                        request,
                    )
                log.info("Replayed idempotent %s (key %s)", endpoint, key[:12])
                return JSONResponse(
                    status_code=existing.status_code,
                    content=existing.response_body,
                    headers={"Idempotent-Replay": "true"},
                )

            # Claim the key before running the handler. The unique constraint is
            # what makes two simultaneous identical requests safe: one inserts,
            # the other loses the race and is told the work is in flight.
            db.add(
                IdempotencyKey(
                    tenant_id=tenant_id,
                    key=key,
                    endpoint=endpoint,
                    request_digest=digest,
                    response_body=None,
                    status_code=0,
                    created_at=utcnow(),
                )
            )
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return _error(
                    409,
                    "idempotency_in_progress",
                    "A request with this Idempotency-Key is already being "
                    "processed. Retry shortly.",
                    request,
                )
        finally:
            db.close()

        response = await call_next(request)
        captured, payload = await _capture(response)
        _finalise(tenant_id, key, endpoint, captured.status_code, payload)
        return captured


def _finalise(tenant_id, key: str, endpoint: str, status_code: int, payload) -> None:
    """Store the response for replay, or release the claim so a retry can work.

    A failed request does not hold its key. If a call returns 500, the client
    should be able to retry with the same key and have it actually run.
    """
    db = SessionLocal()
    try:
        set_session_context(db, tenant_id, "system:idempotency")
        row = db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.key == key,
                IdempotencyKey.endpoint == endpoint,
            )
        ).scalar_one_or_none()
        if row is None:
            return
        if 200 <= status_code < 300 and payload is not None:
            row.response_body = payload
            row.status_code = status_code
        else:
            db.delete(row)
        db.commit()
    except Exception:  # noqa: BLE001 - never fail the request over bookkeeping
        db.rollback()
        log.exception("Could not record idempotency result for %s", endpoint)
    finally:
        db.close()


async def _capture(response):
    """Read a streaming response so its body can be stored and still returned."""
    chunks = [chunk async for chunk in response.body_iterator]
    body = b"".join(chunks)
    rebuilt = JSONResponse(
        content=None, status_code=response.status_code, headers=dict(response.headers)
    )
    rebuilt.body = body
    rebuilt.headers["content-length"] = str(len(body))

    payload = None
    if len(body) <= MAX_STORED_BODY and response.headers.get("content-type", "").startswith(
        "application/json"
    ):
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
    return rebuilt, payload


def _tenant_from_credentials(request: Request) -> uuid.UUID | None:
    raw = None
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        raw = authorization[7:]
    else:
        raw = request.cookies.get("craft_session")
    if not raw:
        return None

    if raw.startswith("craft_"):
        db = SessionLocal()
        try:
            with identity_lookup(db):
                token = db.execute(
                    select(ApiToken).where(ApiToken.token_hash == sha256_hex(raw))
                ).scalar_one_or_none()
            return token.tenant_id if token else None
        except Exception:  # noqa: BLE001
            return None
        finally:
            db.close()

    try:
        claims = decode_token(raw)
    except TokenInvalid:
        return None
    try:
        return uuid.UUID(claims["tid"])
    except (KeyError, ValueError):
        return None


def _error(status: int, code: str, message: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def sweep_expired(db) -> int:
    """Drop keys past the retention window. Called by the relay's idle cycle."""
    from sqlalchemy import delete

    result = db.execute(
        delete(IdempotencyKey).where(IdempotencyKey.created_at < utcnow() - RETENTION)
    )
    return result.rowcount or 0
