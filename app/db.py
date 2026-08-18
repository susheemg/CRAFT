"""Database engine and session management.

Two things happen here that matter for control design:

1.  Every session sets ``app.tenant_id`` and ``app.actor_ref`` as PostgreSQL
    session variables. Row-level security policies read ``app.tenant_id`` so
    tenant isolation is enforced by the database, not by application queries.
2.  Sessions are opened with a statement timeout so a runaway query cannot
    exhaust a connection indefinitely.
"""

from __future__ import annotations

import contextlib
import uuid
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_connection_defaults(dbapi_conn, _record):  # pragma: no cover - driver hook
    with dbapi_conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = {_settings.db_statement_timeout_ms}")
        cur.execute("SET TIME ZONE 'UTC'")


@event.listens_for(engine, "checkin")
def _scrub_connection(dbapi_conn, _record):  # pragma: no cover - driver hook
    """Clear the tenant binding before a connection returns to the pool.

    Without this, session-scoped settings would outlive the request that set
    them and the next borrower would inherit someone else's tenant. That would
    be a cross-tenant read caused by connection reuse — the worst class of bug
    this system could have — so it is cleared unconditionally.
    """
    try:
        with dbapi_conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.tenant_id', '', false), "
                "set_config('app.actor_ref', '', false), "
                "set_config('app.bypass_rls', 'off', false)"
            )
        dbapi_conn.commit()
    except Exception:  # a broken connection is discarded by the pool anyway
        pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def set_session_context(
    db: Session, tenant_id: Optional[uuid.UUID], actor_ref: str = "system"
) -> None:
    """Bind the RLS tenant and the acting principal to this database session.

    Binding also clears any bypass left over from identity resolution, so a
    request cannot carry cross-tenant reach past the point where its tenant is
    known. The settings are transaction-local, so they cannot leak to the next
    borrower of a pooled connection.
    """
    # The context is remembered on the Session, not just pushed to the current
    # connection. Committing ends a transaction and releases the connection back
    # to the pool, which scrubs it; without the memory, everything after the
    # first commit in a request would run unbound and a fail-closed policy would
    # return nothing. The after_begin listener re-applies it to each new
    # transaction.
    db.info["craft_context"] = {
        "tenant": str(tenant_id) if tenant_id else "",
        "actor": actor_ref,
        "bypass": "off",
    }
    _apply_context(db)


_CONTEXT_SQL = text(
    "SELECT set_config('app.tenant_id', :tenant, false), "
    "set_config('app.actor_ref', :actor, false), "
    "set_config('app.bypass_rls', :bypass, false)"
)


def _apply_context(db: Session) -> None:
    ctx = db.info.get("craft_context")
    if ctx:
        db.execute(_CONTEXT_SQL, ctx)


@event.listens_for(Session, "after_begin")
def _rebind_context(session, _transaction, connection):  # pragma: no cover - ORM hook
    """Re-apply the tenant binding whenever a new transaction starts.

    This runs on the connection the transaction just took, not through the
    Session, because the Session is mid-checkout at this point.
    """
    ctx = session.info.get("craft_context")
    if ctx:
        connection.execute(_CONTEXT_SQL, ctx)


def set_rls_bypass(db: Session, enabled: bool) -> None:
    """Turn tenant isolation off for this transaction.

    There are exactly two legitimate reasons to do this, and both are
    unavoidably cross-tenant:

      * migrations and seeding, which operate on the whole database
      * identity resolution, where a bearer token or an email address must be
        matched before the tenant it belongs to is known

    Everything else binds a tenant first. If a third caller ever appears here,
    treat it as a design error rather than a new exception.
    """
    ctx = db.info.setdefault(
        "craft_context", {"tenant": "", "actor": "system", "bypass": "off"}
    )
    ctx["bypass"] = "on" if enabled else "off"
    _apply_context(db)


@contextlib.contextmanager
def identity_lookup(db: Session) -> Iterator[Session]:
    """Cross-tenant window for resolving who is calling. Closes on exit."""
    set_rls_bypass(db, True)
    try:
        yield db
    finally:
        set_rls_bypass(db, False)


@contextlib.contextmanager
def session_scope(
    tenant_id: Optional[uuid.UUID] = None,
    actor_ref: str = "system",
    bypass_rls: bool = False,
) -> Iterator[Session]:
    """Transactional scope for background work and scripts.

    ``bypass_rls`` exists for the seeder and migrations, which legitimately span
    tenants. Application code should pass a tenant instead.
    """
    db = SessionLocal()
    try:
        set_session_context(db, tenant_id, actor_ref)
        if bypass_rls:
            set_rls_bypass(db, True)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextlib.contextmanager
def owner_session_scope() -> Iterator[Session]:
    """Transactional scope on the schema-owning credential.

    Reference data in ``ref`` is versioned with the code, not edited by users,
    so the serving credential holds SELECT on it and nothing more. The seeder
    therefore cannot write the catalogue on the request-serving connection —
    it needs the same credential that runs migrations. Where the deployment has
    only one credential (managed Postgres), this resolves to the same URL and
    costs a second short-lived engine at boot.
    """
    owner_engine = create_engine(
        _settings.owner_database_url, pool_pre_ping=True, future=True
    )
    factory = sessionmaker(bind=owner_engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        owner_engine.dispose()


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Tenant context is applied by the auth dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
