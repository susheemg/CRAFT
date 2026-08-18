"""Declarative base, shared mixins and the controlled vocabularies.

Conventions (Database Design Doc 5, Appendix B):
  * schemas and tables are lower_snake_case, singular nouns
  * primary key is ``id`` (uuid), foreign keys are ``<parent>_id``
  * timestamps carry an ``_at`` suffix and are timestamptz in UTC
  * booleans carry an ``is_``/``has_`` prefix
  * controlled vocabularies are native PostgreSQL enum types
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Controlled vocabularies — native PG enums so invalid values are impossible
# --------------------------------------------------------------------------
class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class AutonomyTier(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class AutomationLevel(StrEnum):
    AUTO = "auto"
    AUTO_NOTIFY = "auto_notify"
    GATE = "gate"
    ASSIST = "assist"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_GATE = "awaiting_gate"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateReason(StrEnum):
    IRREVERSIBLE = "irreversible"
    STATUTORY = "statutory"
    HIGH_RISK = "high_risk"
    LOW_CONFIDENCE = "low_confidence"


class GateDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Severity(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class IncidentStatus(StrEnum):
    RECORDED = "recorded"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    CLOSED = "closed"


class Pillar(StrEnum):
    GDPR = "gdpr"
    SECURITY = "security"
    PCI = "pci"
    BCP = "bcp"


class ActorType(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class DataClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ImplementationStatus(StrEnum):
    """Control implementation state on the compliance journey."""

    NOT_STARTED = "not_started"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    OPERATING = "operating"          # implemented and evidenced as operating effectively
    NOT_APPLICABLE = "not_applicable"


class TreatmentStrategy(StrEnum):
    MITIGATE = "mitigate"
    TRANSFER = "transfer"
    AVOID = "avoid"
    ACCEPT = "accept"


# Reusable Enum column factories -------------------------------------------
def pg_enum(py_enum, name: str) -> Enum:
    return Enum(
        py_enum,
        name=name,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
        create_type=True,
    )


# --------------------------------------------------------------------------
# Mixins
# --------------------------------------------------------------------------
def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), default=utcnow
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))


class TenantMixin:
    """Anchor for row-level security. Every business row carries a tenant."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VersionedMixin:
    """Optimistic concurrency — updates assert the row version."""

    row_version: Mapped[int] = mapped_column(nullable=False, default=1, server_default=text("1"))


__all__ = [
    "Base",
    "utcnow",
    "uuid_pk",
    "pg_enum",
    "TimestampMixin",
    "TenantMixin",
    "SoftDeleteMixin",
    "VersionedMixin",
    "AutonomyTier",
    "AutomationLevel",
    "RunStatus",
    "GateReason",
    "GateDecision",
    "Severity",
    "RiskStatus",
    "IncidentStatus",
    "Pillar",
    "ActorType",
    "DataClass",
    "ImplementationStatus",
    "TreatmentStrategy",
    "String",
    "Index",
]
