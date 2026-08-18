"""The audit log, webhook subscriptions and outbound integrations."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, requires
from app.api.schemas import ConnectionCreate, ConnectionOut, McpToolCall, SyncRequest, WebhookCreate
from app.models.audit import (
    AuditChainCheck,
    AuditLog,
    ExternalConnection,
    OutboxEvent,
    SyncLog,
    WebhookSubscription,
)
from app.models.base import utcnow
from app.security.crypto import seal
from app.services import audit as audit_service
from app.services import brata as brata_service
from app.services import outbox as outbox_service
from app.services.brata import IntegrationError

# ==========================================================================
# Audit
# ==========================================================================
audit_router = APIRouter(prefix="/audit", tags=["Audit"])


@audit_router.get("/log", summary="Query the immutable log")
def query_log(
    db: DbSession,
    principal=Depends(requires("sec.auditlog.read")),
    action: Optional[str] = None,
    entity: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    actor_ref: Optional[str] = None,
    outcome: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=500),
    cursor: Optional[int] = Query(default=None, description="Return entries below this seq"),
) -> dict:
    stmt = select(AuditLog).where(AuditLog.tenant_id == principal.tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_ref:
        stmt = stmt.where(AuditLog.actor_ref.like(f"%{actor_ref}%"))
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until:
        stmt = stmt.where(AuditLog.created_at <= until)
    if cursor:
        stmt = stmt.where(AuditLog.seq < cursor)

    rows = db.execute(stmt.order_by(AuditLog.seq.desc()).limit(limit)).scalars().all()
    return {
        "data": [
            {
                "seq": r.seq,
                "occurred_at": r.created_at.isoformat(),
                "action": r.action,
                "outcome": r.outcome,
                "actor_ref": r.actor_ref,
                "actor_type": r.actor_type.value,
                "entity": r.entity,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "before_state": r.before_state,
                "after_state": r.after_state,
                "detail": r.detail,
                "model": r.model,
                "prompt_version": r.prompt_version,
                "sources": r.sources,
                "request_id": r.request_id,
                "row_hash": r.row_hash[:16],
                "prev_hash": r.prev_hash[:16] if r.prev_hash else None,
            }
            for r in rows
        ],
        "next_cursor": rows[-1].seq if len(rows) == limit else None,
    }


@audit_router.get("/verify", summary="Verify the hash chain end to end")
def verify(
    db: DbSession,
    principal=Depends(requires("sec.auditlog.read")),
    persist: bool = Query(default=False, description="Record the result as a check"),
) -> dict:
    """Recomputes every row hash and confirms each links to its predecessor.

    An intact result means no entry has been altered, deleted or spliced in
    since it was written. A break reports the exact sequence number, which is
    where an investigation starts.
    """
    report = audit_service.verify_chain(db, principal.tenant_id, persist=persist)
    if persist:
        db.commit()
    return {
        "intact": report.is_intact,
        "rows_checked": report.rows_checked,
        "first_broken_seq": report.first_broken_seq,
        "reason": report.reason,
        "head_seq": report.to_seq,
        "head_hash": report.head_hash,
        "checked_at": utcnow().isoformat(),
        "interpretation": (
            "Every entry hashes to its recorded value and links to the one before it."
            if report.is_intact
            else (
                f"The chain breaks at sequence {report.first_broken_seq}. "
                "Treat every entry from that point on as unverified and "
                "investigate database-level access."
            )
        ),
    }


@audit_router.get("/checks", summary="History of chain verifications")
def verification_history(
    db: DbSession, principal=Depends(requires("sec.auditlog.read"))
) -> dict:
    rows = db.execute(
        select(AuditChainCheck)
        .where(AuditChainCheck.tenant_id == principal.tenant_id)
        .order_by(AuditChainCheck.checked_at.desc())
        .limit(100)
    ).scalars().all()
    return {
        "data": [
            {
                "checked_at": c.checked_at.isoformat(),
                "is_intact": c.is_intact,
                "rows_checked": c.rows_checked,
                "first_broken_seq": c.first_broken_seq,
                "detail": c.detail,
            }
            for c in rows
        ]
    }


@audit_router.get("/summary", summary="Activity summary")
def summary(
    db: DbSession,
    days: int = Query(default=7, ge=1, le=90),
    principal=Depends(requires("sec.auditlog.read")),
) -> dict:
    since = utcnow() - timedelta(days=days)
    by_action = db.execute(
        select(AuditLog.action, func.count(AuditLog.seq))
        .where(AuditLog.tenant_id == principal.tenant_id, AuditLog.created_at >= since)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.seq).desc())
        .limit(25)
    ).all()
    failures = db.execute(
        select(func.count(AuditLog.seq)).where(
            AuditLog.tenant_id == principal.tenant_id,
            AuditLog.created_at >= since,
            AuditLog.outcome == "failure",
        )
    ).scalar_one()
    seq, head_hash = audit_service.head(db, principal.tenant_id)
    return {
        "window_days": days,
        "head_seq": seq,
        "head_hash": head_hash[:16] if head_hash else None,
        "failures": failures,
        "by_action": [{"action": a, "count": c} for a, c in by_action],
    }


# ==========================================================================
# Integrations
# ==========================================================================
integ_router = APIRouter(prefix="/integrations", tags=["Integrations"])


@integ_router.get("/connections", summary="List outbound connections")
def list_connections(
    db: DbSession, principal=Depends(requires("integration.manage"))
) -> dict:
    rows = db.execute(
        select(ExternalConnection).where(ExternalConnection.tenant_id == principal.tenant_id)
    ).scalars().all()
    return {
        "data": [
            ConnectionOut(
                id=c.id,
                name=c.name,
                kind=c.kind,
                transport=c.transport,
                base_url=c.base_url,
                auth_scheme=c.auth_scheme,
                is_active=c.is_active,
                verify_tls=c.verify_tls,
                last_sync_at=c.last_sync_at,
                last_health_ok=c.last_health_ok,
                last_health_detail=c.last_health_detail,
            ).model_dump(mode="json")
            for c in rows
        ]
    }


@integ_router.post("/connections", status_code=201, summary="Connect an external system")
def create_connection(
    payload: ConnectionCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("integration.manage")),
) -> dict:
    """Endpoint paths and field names live in ``sync_config``, not in code.

    Brata's exact contract was not in the design dossier, so the adapter ships
    with conventional defaults that can be overridden entirely from here — a
    configuration change rather than a release.
    """
    if not payload.base_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "invalid_url",
                    "message": "The base URL must include a scheme.",
                }
            },
        )
    if payload.base_url.startswith("http://") and payload.verify_tls:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "insecure_url",
                    "message": (
                        "Plain HTTP would send credentials and register data in the "
                        "clear. Use HTTPS, or set verify_tls=false deliberately for a "
                        "local test endpoint."
                    ),
                }
            },
        )
    connection = ExternalConnection(
        tenant_id=principal.tenant_id,
        name=payload.name,
        kind=payload.kind,
        transport=payload.transport,
        base_url=payload.base_url.rstrip("/"),
        auth_scheme=payload.auth_scheme,
        auth_header_name=payload.auth_header_name,
        credential_ciphertext=seal(payload.credential) if payload.credential else None,
        credential_vault_ref=payload.vault_ref,
        oauth_token_url=payload.oauth_token_url,
        oauth_scope=payload.oauth_scope,
        verify_tls=payload.verify_tls,
        timeout_seconds=payload.timeout_seconds,
        sync_config=payload.sync_config or {},
        is_active=True,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(connection)
    db.flush()
    audit_service.record(
        db,
        tenant_id=principal.tenant_id,
        action="integration.connection_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="external_connection",
        entity_id=connection.id,
        after_state={
            "name": connection.name,
            "kind": connection.kind,
            "transport": connection.transport,
            "base_url": connection.base_url,
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(connection.id), "name": connection.name, "transport": connection.transport}


@integ_router.post("/connections/{connection_id}:health", summary="Check a connection")
async def connection_health(
    connection_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("integration.manage")),
) -> dict:
    connection = _connection(db, principal.tenant_id, connection_id)
    ok, detail = await brata_service.check_health(db, connection)
    db.commit()
    return {"ok": ok, "detail": detail, "transport": connection.transport}


@integ_router.post("/connections/{connection_id}:sync", summary="Run a sync")
async def run_sync(
    connection_id: uuid.UUID,
    payload: SyncRequest,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("integration.manage")),
) -> dict:
    """Pulled risks are deduplicated by lineage, so re-running a pull updates
    what is already here rather than creating a second copy of it."""
    connection = _connection(db, principal.tenant_id, connection_id)
    try:
        if payload.operation == "push_risks":
            outcome = await brata_service.push_risks(
                db, connection, limit=payload.limit, actor_ref=principal.actor_ref
            )
        else:
            outcome = await brata_service.pull_risks(
                db, connection, limit=payload.limit, actor_ref=principal.actor_ref
            )
    except IntegrationError as exc:
        db.commit()  # keep the sync_log entry recording the failure
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "integration_failed", "message": str(exc)}},
        ) from exc

    audit_service.record(
        db,
        tenant_id=principal.tenant_id,
        action=f"integration.{payload.operation}",
        outcome="success" if outcome.ok else "failure",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="external_connection",
        entity_id=connection.id,
        detail={
            "created": outcome.created,
            "updated": outcome.updated,
            "skipped": outcome.skipped,
            "failed": outcome.failed,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "operation": payload.operation,
        "ok": outcome.ok,
        "created": outcome.created,
        "updated": outcome.updated,
        "skipped": outcome.skipped,
        "failed": outcome.failed,
        "messages": outcome.messages[:20],
    }


@integ_router.post("/connections/{connection_id}/mcp:call", summary="Call a remote MCP tool")
async def mcp_call(
    connection_id: uuid.UUID,
    payload: McpToolCall,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("integration.manage")),
) -> dict:
    connection = _connection(db, principal.tenant_id, connection_id)
    if connection.transport != "mcp":
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "wrong_transport",
                    "message": f"'{connection.name}' is configured as a {connection.transport} connection.",
                }
            },
        )
    client = brata_service.BrataMcpClient(connection)
    try:
        result = await client.call_tool(payload.tool, payload.arguments)
    except IntegrationError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "mcp_call_failed", "message": str(exc)}},
        ) from exc
    audit_service.record(
        db,
        tenant_id=principal.tenant_id,
        action="integration.mcp_tool_called",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="external_connection",
        entity_id=connection.id,
        detail={"tool": payload.tool},
        request_id=request_id,
    )
    db.commit()
    return {"tool": payload.tool, "result": result}


@integ_router.get("/connections/{connection_id}/mcp/tools", summary="List remote MCP tools")
async def mcp_tools(
    connection_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("integration.manage")),
) -> dict:
    connection = _connection(db, principal.tenant_id, connection_id)
    client = brata_service.BrataMcpClient(connection)
    try:
        tools = await client.list_tools()
    except IntegrationError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "mcp_list_failed", "message": str(exc)}},
        ) from exc
    return {"data": tools}


@integ_router.get("/syncs", summary="Sync history")
def sync_history(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    principal=Depends(requires("integration.manage")),
) -> dict:
    rows = db.execute(
        select(SyncLog)
        .where(SyncLog.tenant_id == principal.tenant_id)
        .order_by(SyncLog.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(row.id),
                "connection_id": str(row.connection_id),
                "direction": row.direction,
                "operation": row.operation,
                "entity": row.entity,
                "outcome": row.outcome,
                "status_code": row.status_code,
                "latency_ms": row.latency_ms,
                "remote_id": row.remote_id,
                "local_id": str(row.local_id) if row.local_id else None,
                "error": row.error,
                "occurred_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


# --------------------------------------------------------------------------
# Webhooks
# --------------------------------------------------------------------------
@integ_router.get("/webhooks", summary="List webhook subscriptions")
def list_webhooks(db: DbSession, principal=Depends(requires("admin.tenant.manage"))) -> dict:
    rows = db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.tenant_id == principal.tenant_id
        )
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(w.id),
                "name": w.name,
                "url": w.url,
                "topics": w.topics,
                "is_active": w.is_active,
                "consecutive_failures": w.consecutive_failures,
                "suspended": w.consecutive_failures >= 10,
                "last_success_at": w.last_success_at.isoformat()
                if w.last_success_at
                else None,
            }
            for w in rows
        ],
        "available_topics": list(outbox_service.TOPICS),
    }


@integ_router.post("/webhooks", status_code=201, summary="Subscribe to events")
def create_webhook(
    payload: WebhookCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.tenant.manage")),
) -> dict:
    """Deliveries are signed with HMAC-SHA256 over the raw body.

    Verify the signature before trusting a payload; without that check an
    endpoint accepts anything that knows its URL.
    """
    unknown = set(payload.topics) - set(outbox_service.TOPICS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "unknown_topic",
                    "message": f"Not published by this platform: {', '.join(sorted(unknown))}",
                }
            },
        )
    if not payload.url.startswith("https://"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "insecure_url",
                    "message": "Webhook endpoints must be HTTPS.",
                }
            },
        )
    secret = payload.secret or secrets.token_urlsafe(32)
    subscription = WebhookSubscription(
        tenant_id=principal.tenant_id,
        name=payload.name,
        url=payload.url,
        topics=payload.topics,
        secret_ciphertext=seal(secret),
        is_active=True,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(subscription)
    db.flush()
    audit_service.record(
        db,
        tenant_id=principal.tenant_id,
        action="integration.webhook_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="webhook_subscription",
        entity_id=subscription.id,
        after_state={"name": payload.name, "url": payload.url, "topics": payload.topics},
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(subscription.id),
        "secret": secret,
        "signature_header": "X-Craft-Signature",
        "note": (
            "This secret is shown once. Verify each delivery by computing "
            "HMAC-SHA256 over the raw request body and comparing it in constant "
            "time with the signature header."
        ),
    }


@integ_router.get("/outbox", summary="Outbox state and dead letters")
def outbox_state(db: DbSession, principal=Depends(requires("integration.manage"))) -> dict:
    now = utcnow()
    pending = db.execute(
        select(func.count(OutboxEvent.id)).where(
            OutboxEvent.tenant_id == principal.tenant_id,
            OutboxEvent.delivered_at.is_(None),
            OutboxEvent.attempts < outbox_service.MAX_ATTEMPTS,
        )
    ).scalar_one()
    # Queued but not yet due: these are backing off after a failure, which is
    # a different situation from a queue that is not moving at all.
    waiting = db.execute(
        select(func.count(OutboxEvent.id)).where(
            OutboxEvent.tenant_id == principal.tenant_id,
            OutboxEvent.delivered_at.is_(None),
            OutboxEvent.attempts < outbox_service.MAX_ATTEMPTS,
            OutboxEvent.next_attempt_at > now,
        )
    ).scalar_one()
    in_flight = db.execute(
        select(func.count(OutboxEvent.id)).where(
            OutboxEvent.tenant_id == principal.tenant_id,
            OutboxEvent.delivered_at.is_(None),
            OutboxEvent.claimed_at.isnot(None),
        )
    ).scalar_one()
    oldest = db.execute(
        select(func.min(OutboxEvent.occurred_at)).where(
            OutboxEvent.tenant_id == principal.tenant_id,
            OutboxEvent.delivered_at.is_(None),
            OutboxEvent.attempts < outbox_service.MAX_ATTEMPTS,
        )
    ).scalar()
    dead = outbox_service.dead_letters(db, principal.tenant_id)
    return {
        "pending": pending,
        "waiting_on_backoff": waiting,
        "in_flight": in_flight,
        "oldest_pending_age_seconds": (
            round((now - oldest).total_seconds()) if oldest else 0
        ),
        "dead_letter_count": len(dead),
        "dead_letters": [
            {
                "id": str(e.id),
                "topic": e.topic,
                "attempts": e.attempts,
                "last_error": e.last_error,
                "occurred_at": e.occurred_at.isoformat(),
                "next_attempt_at": e.next_attempt_at.isoformat(),
            }
            for e in dead
        ],
    }


@integ_router.post("/outbox/{event_id}:replay", summary="Replay a failed event")
def replay_event(
    event_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("integration.manage")),
) -> dict:
    event = db.get(OutboxEvent, event_id)
    if event is None or event.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such event."}}
        )
    outbox_service.replay(db, event_id)
    db.commit()
    return {"id": str(event_id), "status": "pending", "attempts_reset": True}


def _connection(db, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> ExternalConnection:
    connection = db.get(ExternalConnection, connection_id)
    if connection is None or connection.tenant_id != tenant_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "No such connection."}},
        )
    return connection
