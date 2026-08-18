"""Immutable audit, the event outbox, and external integration (schemas
``audit`` and ``integ``).

``audit.audit_log`` is append-only and hash-chained per tenant:

    row_hash = SHA-256( prev_hash || canonical_json(row_without_hashes) )

A database trigger blocks UPDATE and DELETE on the table for every role, so
immutability does not depend on the application behaving. A verifier
recomputes the chain and reports the first sequence number at which it breaks.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    func,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ActorType, Base, TimestampMixin, pg_enum, uuid_pk


class AuditLog(Base):
    """One row per action. Never updated, never deleted."""

    __tablename__ = "audit_log"
    __table_args__ = (
        UniqueConstraint("tenant_id", "seq", name="uq_audit_log_tenant_seq"),
        Index("ix_audit_log_time", "tenant_id", "created_at"),
        Index("ix_audit_log_entity", "entity", "entity_id"),
        Index("ix_audit_log_actor", "actor_ref"),
        Index("ix_audit_log_action", "action"),
        {"schema": "audit"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(pg_enum(ActorType, "actor_type"), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    on_behalf_of: Mapped[str | None] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    # AI lineage
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    sources: Mapped[dict | None] = mapped_column(JSONB)
    # Request context
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(300))
    # Chain
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditChainCheck(Base):
    """Result of a chain verification pass — itself audit evidence."""

    __tablename__ = "chain_check"
    __table_args__ = {"schema": "audit"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    from_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    to_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_intact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_broken_seq: Mapped[int | None] = mapped_column(BigInteger)
    head_hash: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSONB)


class OutboxEvent(Base):
    """Transactional outbox — the state change and its event commit together."""

    __tablename__ = "outbox_event"
    __table_args__ = (
        Index("ix_outbox_undelivered", "delivered_at"),
        {"schema": "audit"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    # Per-event backoff, so one failing subscriber cannot starve the queue
    # behind it, and a claim marker so concurrent relays cannot take the same
    # event twice.
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(Text)


class WebhookSubscription(Base, TimestampMixin):
    __tablename__ = "webhook_subscription"
    __table_args__ = {"schema": "integ"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Distinct from last_delivery_at: an endpoint that has been attempted every
    # minute for a week but last succeeded in March is the interesting case.
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WebhookDelivery(Base):
    __tablename__ = "webhook_delivery"
    __table_args__ = (
        Index("ix_webhook_delivery_sub", "subscription_id", "created_at"),
        {"schema": "integ"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("integ.webhook_subscription.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalConnection(Base, TimestampMixin):
    """An outbound system CRAFT exchanges records with — Brata, an ITSM, a SIEM.

    ``kind='brata'`` drives the dedicated Brata adapter; ``rest_generic`` and
    ``mcp_generic`` cover anything else that speaks JSON over HTTPS or MCP.
    """

    __tablename__ = "external_connection"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_external_connection_name"),
        {"schema": "integ"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="brata")
    transport: Mapped[str] = mapped_column(String(20), nullable=False, default="rest")  # rest | mcp
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_scheme: Mapped[str] = mapped_column(String(30), nullable=False, default="bearer")
    # bearer | api_key_header | oauth2_client_credentials | none
    auth_header_name: Mapped[str | None] = mapped_column(String(60))
    credential_ciphertext: Mapped[str | None] = mapped_column(Text)
    credential_vault_ref: Mapped[str | None] = mapped_column(Text)
    oauth_token_url: Mapped[str | None] = mapped_column(Text)
    oauth_scope: Mapped[str | None] = mapped_column(String(200))
    verify_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timeout_seconds: Mapped[float] = mapped_column(nullable=False, default=30.0)
    # Which record types flow which way.
    sync_config: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_health_detail: Mapped[str | None] = mapped_column(Text)


class SyncLog(Base):
    """Every exchange with an external system, for reconciliation and dispute."""

    __tablename__ = "sync_log"
    __table_args__ = (
        Index("ix_sync_log_conn_time", "connection_id", "created_at"),
        {"schema": "integ"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("integ.external_connection.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound | outbound
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(60))
    local_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    remote_id: Mapped[str | None] = mapped_column(String(120))
    status_code: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    request_digest: Mapped[str | None] = mapped_column(String(64))
    response_digest: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyKey(Base):
    """Makes retries and double-clicks safe on every create/action endpoint."""

    __tablename__ = "idempotency_key"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", "endpoint", name="uq_idempotency"),
        {"schema": "integ"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(160), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_body: Mapped[dict | None] = mapped_column(JSONB)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
