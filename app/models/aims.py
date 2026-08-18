"""AI management system model — ISO/IEC 42001:2023.

Four registers and one charter table.

``domain.ai_system``
    The inventory. Built by discovery from the live model gateway rather than by
    hand, because an AI register maintained by memory is stale within two
    quarters and worthless in an audit.

``domain.ai_system_resource``
    A.4.2 to A.4.6 require data, tooling, compute and human resources to be
    documented. One shape with a discriminator, not four near-identical tables.

``domain.ai_impact_assessment``
    A.5. The three impact dimensions — individual, group, societal — are
    separate columns on purpose. One merged "impact" field lets an assessor
    answer two of three and appear finished.

``domain.ai_data_provenance``
    A.7.3 to A.7.6: where the data came from, on what basis, at what quality,
    prepared how.

``config.agent_charter``
    The bounded mandate under which an agent operates. The existing registry
    describes agents in code; this makes the mandate a record an auditor can
    read and a budget the runtime enforces.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    VersionedMixin,
    uuid_pk,
)


def _tenant() -> Mapped[uuid.UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )


class AiSystem(Base, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """An AI system the organisation develops, provides, uses or deploys."""

    __tablename__ = "ai_system"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_ai_system_code"),
        CheckConstraint(
            "lifecycle_stage IN ('inception','design','development','verification',"
            "'deployment','operation','monitoring','retirement','decommissioned')",
            name="ck_ai_system_lifecycle",
        ),
        CheckConstraint(
            "autonomy_level IN ('assistive','advisory','supervised_autonomy','high_autonomy')",
            name="ck_ai_system_autonomy",
        ),
        CheckConstraint(
            "status IN ('proposed','active','suspended','retired')", name="ck_ai_system_status"
        ),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.application.id", ondelete="SET NULL")
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="SET NULL")
    )
    # An organisation is frequently more than one of developer, provider, user,
    # deployer and partner for the same system, so this is a set, not a column.
    org_roles: Mapped[list[str]] = mapped_column(ARRAY(String(30)), nullable=False, default=list)
    lifecycle_stage: Mapped[str] = mapped_column(String(30), nullable=False, default="inception")
    autonomy_level: Mapped[str] = mapped_column(String(30), nullable=False, default="assistive")
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    prohibited_use: Mapped[str | None] = mapped_column(Text)
    affected_parties: Mapped[list[str]] = mapped_column(
        ARRAY(String(60)), nullable=False, default=list
    )
    is_high_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_criteria: Mapped[str | None] = mapped_column(Text)
    deployment_plan_ref: Mapped[str | None] = mapped_column(String(200))
    # A.6.2.8: at minimum while the system is in use.
    event_logging_stages: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    technical_doc_ref: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    resources: Mapped[list["AiSystemResource"]] = relationship(
        back_populates="ai_system", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["AiImpactAssessment"]] = relationship(
        back_populates="ai_system",
        cascade="all, delete-orphan",
        order_by="AiImpactAssessment.version",
    )


class AiSystemResource(Base, TimestampMixin):
    """A data, tooling, compute or human resource an AI system depends on."""

    __tablename__ = "ai_system_resource"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('data','tooling','system_compute','human')",
            name="ck_ai_resource_type",
        ),
        Index("ix_ai_resource_system", "ai_system_id"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.ai_system.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    descriptor: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lifecycle_stages: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.supplier.id", ondelete="SET NULL")
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("config.llm_model.id", ondelete="SET NULL")
    )
    competence_requirements: Mapped[str | None] = mapped_column(Text)
    documented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ai_system: Mapped[AiSystem] = relationship(back_populates="resources")


class AiImpactAssessment(Base, TimestampMixin):
    """An AI system impact assessment (clause 6.1.4, controls A.5.2 to A.5.5).

    A model may assemble the inputs and draft the text. It may not approve the
    result: ``ck_ai_impact_human_approval`` in migration 0006 refuses an
    approved row that names no human approver.
    """

    __tablename__ = "ai_impact_assessment"
    __table_args__ = (
        UniqueConstraint("ai_system_id", "version", name="uq_ai_impact_version"),
        CheckConstraint(
            "trigger_reason IN ('initial','material_change','periodic','incident',"
            "'regulatory_change')",
            name="ck_ai_impact_trigger",
        ),
        CheckConstraint(
            "residual_rating IS NULL OR residual_rating IN ('low','medium','high','unacceptable')",
            name="ck_ai_impact_residual",
        ),
        CheckConstraint(
            "draft_provenance IN ('human_attested','ai_generated','ai_assisted')",
            name="ck_ai_impact_provenance",
        ),
        CheckConstraint(
            "status IN ('draft','in_review','approved','superseded')", name="ck_ai_impact_status"
        ),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.ai_system.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger_reason: Mapped[str] = mapped_column(String(30), nullable=False, default="initial")
    lifecycle_stage: Mapped[str] = mapped_column(String(30), nullable=False, default="design")
    individual_impacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    group_impacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    societal_impacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    benefits: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mitigations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    residual_rating: Mapped[str | None] = mapped_column(String(20))
    drafted_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.agent_identity.id", ondelete="SET NULL")
    )
    draft_provenance: Mapped[str] = mapped_column(
        String(20), nullable=False, default="human_attested"
    )
    assessed_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A.5.3 asks for retention for a defined period, so the period is a column
    # rather than a policy sentence nobody can query.
    retain_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    ai_system: Mapped[AiSystem] = relationship(back_populates="assessments")


class AiDataProvenance(Base, TimestampMixin):
    """Origin, basis, quality and preparation of a dataset an AI system uses."""

    __tablename__ = "ai_data_provenance"
    __table_args__ = (
        Index("ix_ai_provenance_system", "ai_system_id"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.ai_system.id", ondelete="CASCADE"), nullable=False
    )
    dataset_label: Mapped[str] = mapped_column(String(200), nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    acquisition_basis: Mapped[str | None] = mapped_column(Text)
    lawful_basis: Mapped[str | None] = mapped_column(String(120))
    licence_terms: Mapped[str | None] = mapped_column(Text)
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_record_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.processing_record.id", ondelete="SET NULL")
    )
    quality_criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    quality_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    preparation_method: Mapped[str | None] = mapped_column(Text)
    lineage_hash: Mapped[str | None] = mapped_column(String(80))
    recorded_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.agent_identity.id", ondelete="SET NULL")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiThirdParty(Base, TimestampMixin):
    """Responsibility allocation across the AI supply chain (A.10).

    Joins the existing supplier register rather than creating a second one; a
    second supplier list is how two answers to the same question arise.
    """

    __tablename__ = "ai_third_party"
    __table_args__ = (
        CheckConstraint(
            "party_role IN ('supplier','partner','customer','deployer','data_provider',"
            "'model_provider')",
            name="ck_ai_third_party_role",
        ),
        CheckConstraint(
            "assurance_status IN ('not_assessed','in_progress','assured','deficient')",
            name="ck_ai_third_party_assurance",
        ),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.ai_system.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.supplier.id", ondelete="SET NULL")
    )
    party_role: Mapped[str] = mapped_column(String(30), nullable=False)
    lifecycle_stages: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    allocated_responsibilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    contractual_ref: Mapped[str | None] = mapped_column(String(200))
    assurance_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_assessed"
    )
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiIncidentLink(Base):
    """Links an incident to the AI system involved, so A.8.4 reuses the
    incident engine instead of forking it."""

    __tablename__ = "ai_incident_link"
    __table_args__ = (
        CheckConstraint(
            "harm_type IN ('individual','group','societal','environmental','operational',"
            "'security')",
            name="ck_ai_incident_harm",
        ),
        {"schema": "domain"},
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("domain.incident.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ai_system_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("domain.ai_system.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = _tenant()
    harm_type: Mapped[str] = mapped_column(String(20), nullable=False)
    externally_reported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentCharter(Base, TimestampMixin):
    """The bounded mandate an agent operates under.

    ``enabled`` is the kill switch. The runtime must read it before every tool
    call, not once at agent start: a long-running loop must not outlive the
    decision to stop it.
    """

    __tablename__ = "agent_charter"
    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_code", "version", name="uq_agent_charter_version"),
        CheckConstraint(
            "autonomy_tier IN ('T0_observe','T1_draft','T2_propose','T3_bounded_act',"
            "'T4_deterministic')",
            name="ck_agent_charter_tier",
        ),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.agent_identity.id", ondelete="CASCADE")
    )
    agent_code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    autonomy_tier: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    permitted_frameworks: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    prohibited_actions: Mapped[list[str]] = mapped_column(
        ARRAY(String(300)), nullable=False, default=list
    )
    escalation_gate_code: Mapped[str | None] = mapped_column(String(60))
    max_risk_severity: Mapped[str | None] = mapped_column(String(20))
    daily_token_budget: Mapped[int | None] = mapped_column(BigInteger)
    daily_action_budget: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    disabled_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    grants: Mapped[list["AgentToolGrant"]] = relationship(
        back_populates="charter", cascade="all, delete-orphan"
    )


class AgentToolGrant(Base):
    """One tool an agent may call, at one operation, filtered to one scope.

    The resource filter is what makes separation of duties survive a prompt
    injection: an agent granted ``asc_evidence/write`` filtered to
    ``kind=activity`` cannot write a measurement however it is instructed.
    """

    __tablename__ = "agent_tool_grant"
    __table_args__ = (
        UniqueConstraint("charter_id", "tool_name", "operation", name="uq_agent_tool_grant"),
        CheckConstraint(
            "operation IN ('read','write','propose','execute')", name="ck_agent_tool_operation"
        ),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    charter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("config.agent_charter.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_filter: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    requires_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_limit_per_hour: Mapped[int | None] = mapped_column(Integer)

    charter: Mapped[AgentCharter] = relationship(back_populates="grants")


class AgentBudgetLedger(Base):
    """Daily consumption, so a budget is enforced against a fact rather than an
    in-memory counter that resets whenever the process restarts."""

    __tablename__ = "agent_budget_ledger"
    __table_args__ = (
        UniqueConstraint("charter_id", "ledger_date", name="uq_agent_budget_day"),
        {"schema": "config"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    charter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("config.agent_charter.id", ondelete="CASCADE"),
        nullable=False,
    )
    ledger_date: Mapped[date] = mapped_column(Date, nullable=False)
    tokens_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    actions_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
