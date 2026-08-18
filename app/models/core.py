"""The workflow engine (schema ``core``).

Everything the platform does is a Run. A run executes a versioned workflow
definition activity by activity; each activity either completes automatically
or raises an approval gate; each produces evidence. That chain — run → activity
run → gate → evidence → model invocation — is what makes any decision
reconstructable after the fact.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Interval,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    ActorType,
    AutomationLevel,
    AutonomyTier,
    Base,
    GateDecision,
    GateReason,
    RunStatus,
    TimestampMixin,
    pg_enum,
    uuid_pk,
)


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflow"
    __table_args__ = (
        UniqueConstraint("tenant_id", "wf_code", "version", name="uq_workflow_code_version"),
        Index("ix_workflow_tenant_status", "tenant_id", "status"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    wf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    family: Mapped[str] = mapped_column(String(60), nullable=False)
    pillars: Mapped[list[str]] = mapped_column(ARRAY(String(20)), nullable=False, default=list)
    autonomy_tier: Mapped[AutonomyTier] = mapped_column(
        pg_enum(AutonomyTier, "autonomy_tier"), nullable=False, default=AutonomyTier.L3
    )
    owner_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lineage: Mapped[dict | None] = mapped_column(JSONB)

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="Activity.seq"
    )


class Activity(Base):
    """The five-part contract: What, Who, When, Input, Output (+ AI role, control)."""

    __tablename__ = "activity"
    __table_args__ = (
        UniqueConstraint("workflow_id", "act_code", name="uq_activity_code"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.workflow.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    act_code: Mapped[str] = mapped_column(String(10), nullable=False)
    what: Mapped[str] = mapped_column(Text, nullable=False)
    who_responsible: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    who_accountable_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="RESTRICT")
    )
    when_trigger: Mapped[str] = mapped_column(String(120), nullable=False, default="sequence")
    sla_interval: Mapped[object | None] = mapped_column(Interval)
    input_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_role: Mapped[str | None] = mapped_column(Text)
    task_class: Mapped[str | None] = mapped_column(String(60))
    automation: Mapped[AutomationLevel] = mapped_column(
        pg_enum(AutomationLevel, "automation_level"), nullable=False, default=AutomationLevel.AUTO
    )
    control_ref: Mapped[dict | None] = mapped_column(JSONB)
    is_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gate_type: Mapped[str | None] = mapped_column(String(60))
    gate_reason: Mapped[GateReason | None] = mapped_column(pg_enum(GateReason, "gate_reason"))

    workflow: Mapped[Workflow] = relationship(back_populates="activities")


class Run(Base, TimestampMixin):
    __tablename__ = "run"
    __table_args__ = (
        Index("ix_run_tenant_status", "tenant_id", "status"),
        Index("ix_run_sla", "sla_due_at"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.workflow.id", ondelete="RESTRICT"), nullable=False
    )
    wf_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger_source: Mapped[str] = mapped_column(String(120), nullable=False, default="manual")
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    status: Mapped[RunStatus] = mapped_column(
        pg_enum(RunStatus, "run_status"), nullable=False, default=RunStatus.PENDING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_activity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.activity.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context: Mapped[dict | None] = mapped_column(JSONB)
    subject_ref: Mapped[str | None] = mapped_column(String(120))

    workflow: Mapped[Workflow] = relationship()
    activity_runs: Mapped[list["ActivityRun"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="ActivityRun.started_at"
    )


class ActivityRun(Base):
    __tablename__ = "activity_run"
    __table_args__ = (
        Index("ix_activity_run_run", "run_id"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="CASCADE"), nullable=False
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.activity.id", ondelete="RESTRICT"), nullable=False
    )
    actor_type: Mapped[ActorType] = mapped_column(pg_enum(ActorType, "actor_type"), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    error: Mapped[str | None] = mapped_column(Text)

    run: Mapped[Run] = relationship(back_populates="activity_runs")
    activity: Mapped[Activity] = relationship()


class ApprovalGate(Base):
    __tablename__ = "approval_gate"
    __table_args__ = (
        CheckConstraint(
            "decision = 'pending' OR (approver_user_id IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_approval_gate_decided_complete",
        ),
        Index("ix_approval_gate_run", "run_id"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="RESTRICT"), nullable=False
    )
    activity_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.activity_run.id", ondelete="RESTRICT"), nullable=False
    )
    gate_type: Mapped[str] = mapped_column(String(60), nullable=False)
    reason: Mapped[GateReason] = mapped_column(pg_enum(GateReason, "gate_reason"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context: Mapped[dict | None] = mapped_column(JSONB)
    approver_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="RESTRICT")
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="RESTRICT")
    )
    decision: Mapped[GateDecision] = mapped_column(
        pg_enum(GateDecision, "gate_decision"), nullable=False, default=GateDecision.PENDING
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    run: Mapped[Run] = relationship()


class EvidenceRecord(Base):
    """Append-only. Content-hashed so tampering is detectable."""

    __tablename__ = "evidence_record"
    __table_args__ = (
        CheckConstraint(
            "(artifact_uri IS NOT NULL) <> (payload IS NOT NULL)",
            name="ck_evidence_one_of_uri_or_payload",
        ),
        Index("ix_evidence_run", "run_id"),
        Index("ix_evidence_subject", "subject_type", "subject_id"),
        {"schema": "core"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="RESTRICT")
    )
    activity_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.activity_run.id", ondelete="RESTRICT")
    )
    # Evidence may also attach directly to a compliance control or a risk.
    subject_type: Mapped[str | None] = mapped_column(String(40))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    content_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    lineage: Mapped[dict | None] = mapped_column(JSONB)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
