"""Domain registers (schema ``domain``).

These are the records the workflows create and maintain: the risk register, the
asset and supplier registers, incidents and breaches, the record of processing
activities and subject requests, and the business impact analyses and
continuity plans that carry ISO 22301.

Every register row can point back at the run that created or last changed it,
so any record traces to the governed process that produced it.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    DataClass,
    IncidentStatus,
    RiskStatus,
    Severity,
    SoftDeleteMixin,
    TimestampMixin,
    TreatmentStrategy,
    VersionedMixin,
    pg_enum,
    uuid_pk,
)


class RegisterMixin(TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """Common shape for every register row."""

    @staticmethod
    def tenant_column():
        return mapped_column(
            PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
        )


class Risk(Base, RegisterMixin):
    """Risk register entry with inherent and residual scoring on a 5×5 matrix."""

    __tablename__ = "risk"
    __table_args__ = (
        UniqueConstraint("tenant_id", "risk_ref", name="uq_risk_ref"),
        Index("ix_risk_tenant_status", "tenant_id", "status"),
        Index("ix_risk_residual", "tenant_id", "residual_score"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    risk_ref: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="information_security")
    # information_security | privacy | continuity | third_party | operational | regulatory
    asset_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    threat: Mapped[str | None] = mapped_column(Text)
    vulnerability: Mapped[str | None] = mapped_column(Text)

    inherent_likelihood: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    inherent_impact: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    inherent_score: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    residual_likelihood: Mapped[int | None] = mapped_column(Integer)
    residual_impact: Mapped[int | None] = mapped_column(Integer)
    residual_score: Mapped[int | None] = mapped_column(Integer)
    severity_band: Mapped[Severity] = mapped_column(
        pg_enum(Severity, "severity"), nullable=False, default=Severity.MEDIUM
    )

    treatment: Mapped[TreatmentStrategy] = mapped_column(
        pg_enum(TreatmentStrategy, "treatment_strategy"),
        nullable=False,
        default=TreatmentStrategy.MITIGATE,
    )
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    treatment_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    status: Mapped[RiskStatus] = mapped_column(
        pg_enum(RiskStatus, "risk_status"), nullable=False, default=RiskStatus.OPEN
    )
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acceptance_rationale: Mapped[str | None] = mapped_column(Text)
    review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linked_controls: Mapped[list | None] = mapped_column(JSONB)  # framework_control ref codes
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
    lineage: Mapped[dict | None] = mapped_column(JSONB)


class Asset(Base, RegisterMixin):
    __tablename__ = "asset"
    __table_args__ = (
        Index("ix_asset_tenant", "tenant_id"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(60), nullable=False, default="application")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    data_class: Mapped[DataClass] = mapped_column(
        pg_enum(DataClass, "data_class"), nullable=False, default=DataClass.INTERNAL
    )
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    hosts_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dr_linked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    location: Mapped[str | None] = mapped_column(String(120))
    revalidate_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class Supplier(Base, RegisterMixin):
    __tablename__ = "supplier"
    __table_args__ = (
        Index("ix_supplier_tenant", "tenant_id"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="tier_3")
    country: Mapped[str | None] = mapped_column(String(60))
    processes_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_access: Mapped[str | None] = mapped_column(String(60))
    is_critical_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="prospective")
    contacts: Mapped[dict | None] = mapped_column(JSONB)
    transfer_mechanism: Mapped[str | None] = mapped_column(String(60))
    contract_renewal_at: Mapped[date | None] = mapped_column(Date)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class SupplierAssessment(Base, RegisterMixin):
    __tablename__ = "supplier_assessment"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.supplier.id", ondelete="CASCADE"), nullable=False
    )
    assessment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="due_diligence")
    domain_scores: Mapped[dict | None] = mapped_column(JSONB)
    inherent_rating: Mapped[str | None] = mapped_column(String(20))
    residual_rating: Mapped[str | None] = mapped_column(String(20))
    remediation: Mapped[dict | None] = mapped_column(JSONB)
    assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reassess_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
    lineage: Mapped[dict | None] = mapped_column(JSONB)


class Incident(Base, RegisterMixin):
    __tablename__ = "incident"
    __table_args__ = (
        UniqueConstraint("tenant_id", "incident_no", name="uq_incident_no"),
        Index("ix_incident_tenant_status", "tenant_id", "status"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    incident_no: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    incident_type: Mapped[str] = mapped_column(String(60), nullable=False, default="security")
    severity: Mapped[Severity] = mapped_column(
        pg_enum(Severity, "severity"), nullable=False, default=Severity.MEDIUM
    )
    status: Mapped[IncidentStatus] = mapped_column(
        pg_enum(IncidentStatus, "incident_status"), nullable=False, default=IncidentStatus.RECORDED
    )
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    involves_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    capa: Mapped[dict | None] = mapped_column(JSONB)
    affected_asset_ids: Mapped[list | None] = mapped_column(JSONB)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class Breach(Base, RegisterMixin):
    """Personal-data breach with the 72-hour statutory clock."""

    __tablename__ = "breach"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.incident.id", ondelete="RESTRICT")
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_to_individuals: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    data_categories: Mapped[list | None] = mapped_column(JSONB)
    individuals_affected: Mapped[int | None] = mapped_column(Integer)
    clock_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notify_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    regulator_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    individuals_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_not_to_notify: Mapped[str | None] = mapped_column(Text)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class ProcessingRecord(Base, RegisterMixin):
    """Record of processing activity (Article 30 RoPA)."""

    __tablename__ = "processing_record"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_function: Mapped[str | None] = mapped_column(String(120))
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lawful_basis: Mapped[str] = mapped_column(String(60), nullable=False, default="legitimate_interests")
    special_category_basis: Mapped[str | None] = mapped_column(String(60))
    data_subjects: Mapped[list | None] = mapped_column(JSONB)
    data_categories: Mapped[list | None] = mapped_column(JSONB)
    recipients: Mapped[list | None] = mapped_column(JSONB)
    international_transfers: Mapped[dict | None] = mapped_column(JSONB)
    retention_rule: Mapped[str | None] = mapped_column(String(200))
    security_measures: Mapped[str | None] = mapped_column(Text)
    dpia_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dpia_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class DsarRequest(Base, RegisterMixin):
    __tablename__ = "dsar_request"
    __table_args__ = (
        Index("ix_dsar_tenant_status", "tenant_id", "status"),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    request_ref: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False, default="access")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    id_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exemptions_applied: Mapped[dict | None] = mapped_column(JSONB)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class BusinessImpactAnalysis(Base, RegisterMixin):
    """ISO 22301 clause 8.2 — impact over time drives RTO/RPO and MTPD."""

    __tablename__ = "business_impact_analysis"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    activity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_function: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    mtpd_hours: Mapped[int | None] = mapped_column(Integer)  # maximum tolerable period of disruption
    rto_hours: Mapped[int | None] = mapped_column(Integer)
    rpo_minutes: Mapped[int | None] = mapped_column(Integer)
    mbco: Mapped[str | None] = mapped_column(Text)  # minimum business continuity objective
    impact_over_time: Mapped[dict | None] = mapped_column(JSONB)  # {"1h":..,"4h":..,"24h":..}
    dependencies: Mapped[dict | None] = mapped_column(JSONB)  # people, systems, suppliers, sites
    supporting_asset_ids: Mapped[list | None] = mapped_column(JSONB)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class ContinuityPlan(Base, RegisterMixin):
    """ISO 22301 clauses 8.4–8.5 — the plan and its exercise history."""

    __tablename__ = "continuity_plan"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(40), nullable=False, default="business_continuity")
    # business_continuity | disaster_recovery | incident_response | crisis_communication
    scope: Mapped[str | None] = mapped_column(Text)
    bia_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.business_impact_analysis.id", ondelete="SET NULL")
    )
    rto_hours: Mapped[int | None] = mapped_column(Integer)
    rpo_minutes: Mapped[int | None] = mapped_column(Integer)
    strategy: Mapped[str | None] = mapped_column(Text)
    invocation_criteria: Mapped[str | None] = mapped_column(Text)
    response_team: Mapped[dict | None] = mapped_column(JSONB)
    single_points_of_failure: Mapped[dict | None] = mapped_column(JSONB)
    document_uri: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )


class ContinuityExercise(Base, RegisterMixin):
    """Evidence that a plan was tested — the clause 8.5 record auditors ask for."""

    __tablename__ = "continuity_exercise"
    __table_args__ = {"schema": "domain"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = RegisterMixin.tenant_column()
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.continuity_plan.id", ondelete="CASCADE"), nullable=False
    )
    exercise_type: Mapped[str] = mapped_column(String(40), nullable=False, default="tabletop")
    # tabletop | walkthrough | simulation | technical_failover | live
    scenario: Mapped[str | None] = mapped_column(Text)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    participants: Mapped[dict | None] = mapped_column(JSONB)
    rto_achieved_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))
    rpo_achieved_minutes: Mapped[float | None] = mapped_column(Numeric(8, 2))
    objectives_met: Mapped[bool | None] = mapped_column(Boolean)
    findings: Mapped[dict | None] = mapped_column(JSONB)
    report_uri: Mapped[str | None] = mapped_column(Text)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
