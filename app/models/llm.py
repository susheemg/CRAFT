"""LLM configuration and the model-invocation ledger (schema ``config``).

The configuration separates six concerns, so an administrator can change any
one without touching the others:

    provider   who serves the model, and which sealed credential to use
    model      a specific served model, its capability and its economics
    route      which model serves a given task class
    fallback   what to try when the primary fails or a cap is hit
    policy     rate, token budget, cost cap, alert threshold, kill switch
    version    an approved snapshot that can be activated or rolled back

The credential column holds ciphertext produced by the envelope-encryption
helper, or an external vault reference. Plaintext keys are never persisted and
never returned by the API.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class LlmProvider(Base, TimestampMixin):
    __tablename__ = "llm_provider"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_llm_provider_name"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    # anthropic | openai | azure_openai | bedrock | google | mistral
    # | openai_compatible | ollama
    base_url: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(40))
    api_version: Mapped[str | None] = mapped_column(String(40))
    # Exactly one of these carries the credential:
    credential_ciphertext: Mapped[str | None] = mapped_column(Text)  # sealed locally
    credential_vault_ref: Mapped[str | None] = mapped_column(Text)  # external KMS/vault pointer
    credential_hint: Mapped[str | None] = mapped_column(String(12))  # last 4 chars, for recognition
    credential_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_headers: Mapped[dict | None] = mapped_column(JSONB)
    supports_prompt_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_health_detail: Mapped[str | None] = mapped_column(Text)

    models: Mapped[list["LlmModel"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class LlmModel(Base, TimestampMixin):
    __tablename__ = "llm_model"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_key", name="uq_llm_model_key"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("config.llm_provider.id", ondelete="CASCADE"), nullable=False
    )
    model_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160))
    capability: Mapped[str] = mapped_column(String(20), nullable=False, default="chat")
    # chat | embedding | classify | vision
    context_window: Mapped[int | None] = mapped_column(Integer)
    max_output: Mapped[int | None] = mapped_column(Integer)
    in_cost_per_1k: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    out_cost_per_1k: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    cache_write_cost_per_1k: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    cache_read_cost_per_1k: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    supports_native_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    provider: Mapped[LlmProvider] = relationship(back_populates="models")


class LlmRoute(Base, TimestampMixin):
    """Task class → primary model, with an ordered fallback chain."""

    __tablename__ = "llm_route"
    __table_args__ = (
        UniqueConstraint("tenant_id", "task_class", "environment", name="uq_llm_route_task"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    task_class: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("config.llm_model.id", ondelete="RESTRICT"), nullable=False
    )
    fallback_model_ids: Mapped[list | None] = mapped_column(JSONB)
    min_tier: Mapped[str | None] = mapped_column(String(4))
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="production")
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.0)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=86400)
    guardrail_profile: Mapped[str] = mapped_column(String(60), nullable=False, default="default")
    system_prompt: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    model: Mapped[LlmModel] = relationship()


class LlmPolicy(Base, TimestampMixin):
    """Rate, budget and cost governance, scoped globally or to a provider/route."""

    __tablename__ = "llm_policy"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scope", "scope_ref", name="uq_llm_policy_scope"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="global")
    # global | provider | route
    scope_ref: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    rate_rpm: Mapped[int | None] = mapped_column(Integer)
    token_budget_daily: Mapped[int | None] = mapped_column(BigInteger)
    cost_cap_monthly: Mapped[float | None] = mapped_column(Numeric(12, 2))
    alert_threshold: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.8)
    kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kill_switch_reason: Mapped[str | None] = mapped_column(Text)
    kill_switch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LlmConfigVersion(Base):
    """An immutable snapshot of the whole LLM configuration.

    Production activation requires a second approver; the previous version is
    retained so any change rolls back in one action.
    """

    __tablename__ = "llm_config_version"
    __table_args__ = (
        Index("ix_llm_config_version_tenant", "tenant_id", "version_no"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # draft | pending_approval | active | superseded | rolled_back
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    proposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PromptTemplate(Base, TimestampMixin):
    """Change-controlled prompt, versioned.

    ``cache_prefix`` is the stable, reusable head of the prompt — standards
    text, control catalogues, policy extracts. Keeping it stable and putting it
    first is what makes provider-side prompt caching effective.
    """

    __tablename__ = "prompt_template"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", "version", name="uq_prompt_template_version"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    task_class: Mapped[str] = mapped_column(String(60), nullable=False)
    cache_prefix: Mapped[str | None] = mapped_column(Text)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PromptCacheEntry(Base):
    """Exact-match response cache.

    Keyed on a SHA-256 of (model, system prefix, rendered prompt, parameters).
    A hit returns the stored completion without a provider call at all — the
    cheapest possible token, which is the one never sent.
    """

    __tablename__ = "prompt_cache_entry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cache_key", name="uq_prompt_cache_key"),
        Index("ix_prompt_cache_expiry", "expires_at"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_class: Mapped[str] = mapped_column(String(60), nullable=False)
    model_key: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_meta: Mapped[dict | None] = mapped_column(JSONB)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved_cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelInvocation(Base):
    """Lineage and FinOps ledger — one row per attempted model call."""

    __tablename__ = "model_invocation"
    __table_args__ = (
        Index("ix_model_invocation_time", "tenant_id", "created_at"),
        Index("ix_model_invocation_run", "run_id"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
    activity_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.activity_run.id", ondelete="SET NULL")
    )
    task_class: Mapped[str] = mapped_column(String(60), nullable=False)
    provider_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    model_key: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_name: Mapped[str | None] = mapped_column(String(80))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    prompt_digest: Mapped[str | None] = mapped_column(String(64))
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False, default="system")
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_status: Mapped[str] = mapped_column(String(20), nullable=False, default="miss")
    # miss | local_hit | provider_hit | bypass
    cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    cost_saved: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    # The model's own stated confidence in its output, where the task asked for
    # one. Needed by two controls: PR-AIG-02 escalates below the agent's floor,
    # and PR-AIG-03 baselines it per task class to detect drift when a provider
    # silently changes a model underneath us. Null for deterministic calls that
    # were never asked to express confidence.
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    # ok | error | blocked | capped
    error: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
