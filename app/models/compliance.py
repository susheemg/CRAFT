"""Compliance journey model (schemas ``ref`` and ``compliance``).

``ref.framework`` and ``ref.framework_control`` are the shipped, read-mostly
catalogue: ISO/IEC 27001:2022 (clauses 4–10 plus the 93 Annex A controls),
ISO 22301:2019 (clauses 4–10) and the UK/EU GDPR articles that carry
operational obligations.

``compliance.control_implementation`` is the tenant's position against each of
those catalogue items — applicability, status, owner, maturity, evidence and
next review. Readiness is computed from that table, never asserted.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ImplementationStatus,
    Severity,
    TimestampMixin,
    pg_enum,
    uuid_pk,
)


class Framework(Base):
    """A standard or regulation the organisation is working towards."""

    __tablename__ = "framework"
    __table_args__ = {"schema": "ref"}

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    edition: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text)
    certifiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    controls: Mapped[list["FrameworkControl"]] = relationship(
        back_populates="framework", order_by="FrameworkControl.sort_order"
    )


class FrameworkControl(Base):
    """One requirement, clause or control within a framework."""

    __tablename__ = "framework_control"
    __table_args__ = (
        UniqueConstraint("framework_id", "ref_code", name="uq_framework_control_ref"),
        Index("ix_framework_control_framework", "framework_id"),
        {"schema": "ref"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    framework_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework.id", ondelete="CASCADE"), nullable=False
    )
    ref_code: Mapped[str] = mapped_column(String(30), nullable=False)  # e.g. A.5.7, 8.4, Art.30
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    theme: Mapped[str | None] = mapped_column(String(60))  # organisational|people|physical|technological
    control_type: Mapped[str] = mapped_column(String(30), nullable=False, default="requirement")
    # 'requirement' = mandatory clause; 'control' = Annex A style, may be excluded in the SoA
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    guidance: Mapped[str | None] = mapped_column(Text)
    evidence_hint: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped[Framework] = relationship(back_populates="controls")


class ControlMapping(Base):
    """Cross-framework equivalence, so one piece of evidence serves many audits."""

    __tablename__ = "control_mapping"
    __table_args__ = (
        UniqueConstraint("source_control_id", "target_control_id", name="uq_control_mapping"),
        {"schema": "ref"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_control_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework_control.id", ondelete="CASCADE"), nullable=False
    )
    target_control_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework_control.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False, default="equivalent")


class ComplianceProgramme(Base, TimestampMixin):
    """A tenant's journey towards one framework: scope, target date, phase."""

    __tablename__ = "programme"
    __table_args__ = (
        UniqueConstraint("tenant_id", "framework_id", name="uq_programme_tenant_framework"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework.id", ondelete="RESTRICT"), nullable=False
    )
    scope_statement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    phase: Mapped[str] = mapped_column(String(40), nullable=False, default="initiation")
    # initiation | gap_analysis | implementation | internal_audit | management_review
    # | certification_stage_1 | certification_stage_2 | certified | surveillance
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_date: Mapped[date | None] = mapped_column(Date)
    certification_body: Mapped[str | None] = mapped_column(String(160))
    certified_on: Mapped[date | None] = mapped_column(Date)
    certificate_expires_on: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    framework: Mapped[Framework] = relationship()


class ControlImplementation(Base, TimestampMixin):
    """The tenant's position against one catalogue control."""

    __tablename__ = "control_implementation"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "framework_control_id", name="uq_control_impl_tenant_control"
        ),
        Index("ix_control_impl_status", "tenant_id", "status"),
        Index("ix_control_impl_review", "tenant_id", "next_review_at"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    framework_control_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework_control.id", ondelete="RESTRICT"), nullable=False
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.programme.id", ondelete="SET NULL")
    )
    is_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # The SoA requires a written justification for inclusion *and* exclusion.
    applicability_justification: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ImplementationStatus] = mapped_column(
        pg_enum(ImplementationStatus, "implementation_status"),
        nullable=False,
        default=ImplementationStatus.NOT_STARTED,
    )
    maturity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0–5 CMMI-style
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    implementation_note: Mapped[str | None] = mapped_column(Text)
    how_implemented: Mapped[str | None] = mapped_column(Text)
    linked_policy_uri: Mapped[str | None] = mapped_column(Text)
    last_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_assessment: Mapped[dict | None] = mapped_column(JSONB)  # model, prompt version, citations

    control: Mapped[FrameworkControl] = relationship()


class Gap(Base, TimestampMixin):
    """A shortfall against a control, with remediation tracked to closure."""

    __tablename__ = "gap"
    __table_args__ = (
        Index("ix_gap_tenant_status", "tenant_id", "status"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    control_implementation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.control_implementation.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(
        pg_enum(Severity, "severity"), nullable=False, default=Severity.MEDIUM
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="assessment")
    # assessment | internal_audit | external_audit | incident | ai_review
    remediation_plan: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linked_risk_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )

    control_implementation: Mapped[ControlImplementation] = relationship()


class ReadinessSnapshot(Base):
    """Point-in-time readiness, so the trend line is real history, not a recompute."""

    __tablename__ = "readiness_snapshot"
    __table_args__ = (
        Index("ix_readiness_prog_time", "programme_id", "captured_at"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.programme.id", ondelete="CASCADE"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    readiness_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    evidenced_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    average_maturity: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=0)
    applicable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[dict | None] = mapped_column(JSONB)
