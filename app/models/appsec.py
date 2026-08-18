"""Application security model — ISO/IEC 27034-1:2011 and -2:2015.

Five concepts carry the standard, and all five are persisted here.

``ref.aslcrm_stage`` / ``ref.aslcrm_layer``
    The Application Security Life Cycle Reference Model. Reference data, seeded
    with the code, never edited by users — the same treatment the framework
    catalogue gets.

``compliance.onf``
    One row per *iteration* of the Organization Normative Framework. 27034-2
    clause 5.4 is explicit that the ONF is built incrementally; making the
    iteration the unit of approval is what stops it becoming a document that is
    never finished.

``compliance.asc``
    The Application Security Control library. Activity and measurement are
    separate JSONB documents rather than one blob, because the standard's whole
    point is that the project team performs one and the verification team
    performs the other. Collapsing them erases the control.

``compliance.anf``
    The per-application subset of the ONF, versioned because the standard
    anticipates the regulatory context shifting or the owner raising the target
    mid-project, and requires owner approval each time.

``compliance.asc_evidence``
    Both halves of an ASC in one table, discriminated by ``kind``. They share a
    table so separation of duties can be enforced by a single trigger over a
    single relation rather than by a join the application has to remember.
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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ImplementationStatus,
    SoftDeleteMixin,
    TimestampMixin,
    VersionedMixin,
    pg_enum,
    uuid_pk,
)


def _tenant() -> Mapped[uuid.UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )


# --------------------------------------------------------------------------
# Reference: the Application Security Life Cycle Reference Model
# --------------------------------------------------------------------------
SOURCE_NOTE = (
    "Structural label written by CRAFT from ISO/IEC 27034-1:2011 clause 8.1.2.7. "
    "Paraphrased, not reproduced. Reconcile against a licensed copy before "
    "certification use."
)


class AslcrmLayer(Base):
    """One of the four vertical layers of the reference model."""

    __tablename__ = "aslcrm_layer"
    __table_args__ = {"schema": "ref"}

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str] = mapped_column(Text, nullable=False, default=SOURCE_NOTE)


class AslcrmStage(Base):
    """One of the six stages, across the provisioning and operation phases."""

    __tablename__ = "aslcrm_stage"
    __table_args__ = (
        CheckConstraint("phase IN ('provisioning','operation')", name="ck_aslcrm_stage_phase"),
        {"schema": "ref"},
    )

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    phase: Mapped[str] = mapped_column(String(20), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str] = mapped_column(Text, nullable=False, default=SOURCE_NOTE)


# --------------------------------------------------------------------------
# Organization Normative Framework
# --------------------------------------------------------------------------
class Onf(Base, TimestampMixin):
    """One iteration of the Organization Normative Framework."""

    __tablename__ = "onf"
    __table_args__ = (
        UniqueConstraint("tenant_id", "iteration_no", name="uq_onf_iteration"),
        CheckConstraint(
            "status IN ('draft','scoped','designed','implemented','monitored',"
            "'audited','superseded')",
            name="ck_onf_status",
        ),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    iteration_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope_statement: Mapped[str] = mapped_column(Text, nullable=False)
    application_security_policy_ref: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    committee_mandate_ref: Mapped[str | None] = mapped_column(String(120))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contexts: Mapped[list["OnfContext"]] = relationship(
        back_populates="onf", cascade="all, delete-orphan"
    )
    trust_levels: Mapped[list["TrustLevel"]] = relationship(
        back_populates="onf", cascade="all, delete-orphan", order_by="TrustLevel.level_no"
    )


class OnfCommitteeMember(Base, TimestampMixin):
    """Named committee roles. 27034-2 5.4.3 wants a mandate, not a mailing list."""

    __tablename__ = "onf_committee_member"
    __table_args__ = {"schema": "compliance"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id", ondelete="CASCADE"), nullable=False
    )
    role_label: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="SET NULL")
    )
    is_chair: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    appointed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OnfContext(Base, TimestampMixin):
    """Business, regulatory and technological contexts for an ONF iteration."""

    __tablename__ = "onf_context"
    __table_args__ = (
        UniqueConstraint("onf_id", "context_type", "code", name="uq_onf_context"),
        CheckConstraint(
            "context_type IN ('business','regulatory','technological')",
            name="ck_onf_context_type",
        ),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id", ondelete="CASCADE"), nullable=False
    )
    context_type: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    external_ref: Mapped[str | None] = mapped_column(String(300))

    onf: Mapped[Onf] = relationship(back_populates="contexts")


class TrustLevel(Base, TimestampMixin):
    """An organisation-defined level of trust.

    Exactly one level zero per iteration, enforced by a partial unique index in
    migration 0006 — a table-level constraint cannot express "unique where true".
    """

    __tablename__ = "trust_level"
    __table_args__ = (
        UniqueConstraint("onf_id", "level_no", name="uq_trust_level_no"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id", ondelete="CASCADE"), nullable=False
    )
    level_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_level_zero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    onf: Mapped[Onf] = relationship(back_populates="trust_levels")


class Asc(Base, TimestampMixin, VersionedMixin):
    """An Application Security Control: an activity and its measurement."""

    __tablename__ = "asc"
    __table_args__ = (
        UniqueConstraint("tenant_id", "onf_id", "asc_uid", "version", name="uq_asc_uid_version"),
        CheckConstraint(
            "automation_capability IN ('manual','assisted','automatable','deterministic')",
            name="ck_asc_automation",
        ),
        CheckConstraint(
            "status IN ('draft','validated','approved','deprecated')", name="ck_asc_status"
        ),
        Index("ix_asc_stage", "aslcrm_stage_code"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id", ondelete="CASCADE"), nullable=False
    )
    asc_uid: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    aslcrm_layer_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("ref.aslcrm_layer.code")
    )
    aslcrm_stage_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("ref.aslcrm_stage.code")
    )
    # what / how / where / who / when / how much — the six dimensions the
    # standard asks an ASC to answer, kept as documents rather than columns so
    # a domain expert can extend one without a migration.
    activity_spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    measurement_spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    activity_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    measurement_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    automation_capability: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    # Set true for anything an agent must not attest to: independent review, and
    # every control that governs the agent estate itself.
    measurement_requires_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    control_refs: Mapped[list[str]] = mapped_column(
        ARRAY(String(40)), nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_note: Mapped[str | None] = mapped_column(Text)


class AscEdge(Base):
    """ASCs form a graph, not a tree: one activity can unlock several, and a
    successor can have several prerequisites."""

    __tablename__ = "asc_edge"
    __table_args__ = (
        CheckConstraint("parent_asc_id <> child_asc_id", name="ck_asc_edge_no_self"),
        {"schema": "compliance"},
    )

    parent_asc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.asc.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_asc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.asc.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = _tenant()


class AscTrustLevel(Base):
    """Which ASCs a given level of trust requires."""

    __tablename__ = "asc_trust_level"
    __table_args__ = {"schema": "compliance"}

    asc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.asc.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trust_level_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.trust_level.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = _tenant()
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LifecycleStageMap(Base, TimestampMixin):
    """The organisation's own delivery stages mapped onto the reference model.

    27034 deliberately imposes no life cycle. This mapping is the mechanism that
    lets an ASC be issued to a delivery team in the team's own vocabulary.
    """

    __tablename__ = "lifecycle_stage_map"
    __table_args__ = (
        UniqueConstraint("onf_id", "model_name", "local_stage_code", name="uq_lifecycle_stage"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    local_stage_code: Mapped[str] = mapped_column(String(30), nullable=False)
    local_stage_label: Mapped[str] = mapped_column(String(120), nullable=False)
    aslcrm_stage_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("ref.aslcrm_stage.code"), nullable=False
    )
    aslcrm_layer_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("ref.aslcrm_layer.code")
    )


# --------------------------------------------------------------------------
# The application register and its Application Normative Framework
# --------------------------------------------------------------------------
class Application(Base, TimestampMixin, SoftDeleteMixin, VersionedMixin):
    """An application the organisation builds, operates or acquires."""

    __tablename__ = "application"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_application_code"),
        CheckConstraint(
            "sourcing_model IN ('in_house','outsourced','cots','saas','hybrid')",
            name="ck_application_sourcing",
        ),
        CheckConstraint(
            "status IN ('proposed','active','archived','destroyed')", name="ck_application_status"
        ),
        {"schema": "domain"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="SET NULL")
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.asset.id", ondelete="SET NULL")
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("domain.supplier.id", ondelete="SET NULL")
    )
    sourcing_model: Mapped[str] = mapped_column(String(20), nullable=False, default="in_house")
    # The junction with ISO/IEC 42001. An application flagged here runs both the
    # ASMP and the AIMS processes; it does not run one and claim the other.
    is_ai_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lifecycle_model_name: Mapped[str | None] = mapped_column(String(80))
    criticality: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class Anf(Base, TimestampMixin):
    """The Application Normative Framework for one application, versioned."""

    __tablename__ = "anf"
    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_anf_version"),
        CheckConstraint(
            "status IN ('draft','targeted','active','audited','superseded')", name="ck_anf_status"
        ),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("domain.application.id", ondelete="CASCADE"),
        nullable=False,
    )
    onf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.onf.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    targeted_trust_level_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.trust_level.id")
    )
    actual_trust_level_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.trust_level.id")
    )
    actual_level_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_assessment_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # The application owner approves the target. A human, always: enforced by
    # the gate authority model and asserted by test.
    target_approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    audit_approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    audit_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    selections: Mapped[list["AnfAsc"]] = relationship(
        back_populates="anf", cascade="all, delete-orphan"
    )


class AnfAsc(Base, TimestampMixin):
    """One ASC selected into an ANF, placed at the project's own stage."""

    __tablename__ = "anf_asc"
    __table_args__ = (
        UniqueConstraint("anf_id", "asc_id", name="uq_anf_asc"),
        # A level-zero ASC is the organisational floor. 27034-1 8.3.2 says the
        # project team must not change it, so waiving one is impossible rather
        # than discouraged.
        CheckConstraint(
            "NOT (is_level_zero AND waived_at IS NOT NULL)", name="ck_anf_asc_level_zero_locked"
        ),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    anf_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.anf.id", ondelete="CASCADE"), nullable=False
    )
    asc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.asc.id"), nullable=False
    )
    local_stage_code: Mapped[str | None] = mapped_column(String(30))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_level_zero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waiver_reason: Mapped[str | None] = mapped_column(Text)
    waived_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    waived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    anf: Mapped[Anf] = relationship(back_populates="selections")


class AscEvidence(Base, TimestampMixin):
    """The performance record for one half of one ASC on one application.

    ``provenance`` is not decoration. Labelling agent output lets an auditor
    filter the evidence base to human-attested records; without the label they
    must take the whole set on trust or reject it.
    """

    __tablename__ = "asc_evidence"
    __table_args__ = (
        CheckConstraint("kind IN ('activity','measurement')", name="ck_asc_evidence_kind"),
        CheckConstraint(
            "actor_type IN ('human','agent','system')", name="ck_asc_evidence_actor_type"
        ),
        CheckConstraint(
            "outcome IN ('pending','pass','fail','partial','not_applicable')",
            name="ck_asc_evidence_outcome",
        ),
        CheckConstraint(
            "provenance IN ('human_attested','ai_generated','ai_assisted','tool_output')",
            name="ck_asc_evidence_provenance",
        ),
        CheckConstraint(
            "actor_type <> 'human' OR actor_user_id IS NOT NULL",
            name="ck_asc_evidence_human_named",
        ),
        CheckConstraint(
            "actor_type <> 'agent' OR actor_agent_id IS NOT NULL",
            name="ck_asc_evidence_agent_named",
        ),
        Index("ix_asc_evidence_anf_asc_kind", "anf_asc_id", "kind"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    anf_asc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.anf_asc.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="SET NULL")
    )
    actor_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.agent_identity.id", ondelete="SET NULL")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.run.id", ondelete="SET NULL")
    )
    evidence_record_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("core.evidence_record.id", ondelete="SET NULL")
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    provenance: Mapped[str] = mapped_column(String(20), nullable=False, default="human_attested")
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------
# Framework-agnostic Statement of Applicability
# --------------------------------------------------------------------------
class SoaEntry(Base, TimestampMixin):
    """One Statement of Applicability line, for any framework.

    ISO/IEC 27001 6.1.3 d), ISO/IEC 42001 6.1.3 d) and the ONF's ASC selection
    all require the same artefact. Building it once and pointing three
    frameworks at it is the single largest overlap saving in this release.
    """

    __tablename__ = "soa_entry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "programme_id", "control_ref", name="uq_soa_entry"),
        # An exclusion with no reason is the defect an auditor looks for first.
        CheckConstraint(
            "is_applicable OR exclusion_reason IS NOT NULL", name="ck_soa_exclusion_reasoned"
        ),
        Index("ix_soa_entry_framework", "framework_id"),
        {"schema": "compliance"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("compliance.programme.id", ondelete="CASCADE"),
    )
    framework_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework.id", ondelete="CASCADE")
    )
    framework_control_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ref.framework_control.id", ondelete="CASCADE")
    )
    control_ref: Mapped[str] = mapped_column(String(40), nullable=False)
    is_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # risk_treatment | legal | contractual | business
    inclusion_basis: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list
    )
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        pg_enum(ImplementationStatus, "implementation_status"),
        nullable=False,
        default=ImplementationStatus.NOT_STARTED,
    )
    linked_asc_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("compliance.asc.id", ondelete="SET NULL")
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.user_account.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_note: Mapped[str | None] = mapped_column(Text)
