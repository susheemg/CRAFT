"""Identity and access model (schema ``iam``).

Principals are humans *or* AI agents. Agents are first-class principals with
their own least-privilege grants, but a segregation-of-duties rule prevents an
agent principal from ever holding a gate-approval permission — accountability
resolves to a person.
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    ActorType,
    AutonomyTier,
    Base,
    TimestampMixin,
    pg_enum,
    uuid_pk,
)


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenant"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    region: Mapped[str] = mapped_column(String(40), nullable=False, default="uk")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class UserAccount(Base, TimestampMixin):
    """A human principal. Passwords are optional: federated users have none."""

    __tablename__ = "user_account"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_account_tenant_email"),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    idp_subject: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    mfa_enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    grants: Mapped[list["RoleGrant"]] = relationship(
        primaryjoin="foreign(RoleGrant.principal_id) == UserAccount.id",
        viewonly=True,
    )


class AgentIdentity(Base, TimestampMixin):
    """A non-human principal executing workflow activities."""

    __tablename__ = "agent_identity"
    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_key", name="uq_agent_identity_key"),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    agent_key: Mapped[str] = mapped_column(String(60), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    autonomy_tier: Mapped[AutonomyTier] = mapped_column(
        pg_enum(AutonomyTier, "autonomy_tier"), nullable=False, default=AutonomyTier.L3
    )
    guardrail_profile: Mapped[str] = mapped_column(String(60), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Role(Base, TimestampMixin):
    __tablename__ = "role"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    parent_role_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="SET NULL")
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # An agent-eligible role may be granted to an agent principal.
    agent_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "role_permission"
    __table_args__ = {"schema": "iam"}

    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.permission.id", ondelete="RESTRICT"), primary_key=True
    )
    scope: Mapped[str] = mapped_column(String(40), primary_key=True, default="all")

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class RoleGrant(Base):
    """Assignment of a role to a principal, optionally scoped and time-boxed."""

    __tablename__ = "role_grant"
    __table_args__ = (
        Index("ix_role_grant_principal", "principal_id"),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    principal_type: Mapped[ActorType] = mapped_column(pg_enum(ActorType, "actor_type"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="RESTRICT"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="all")
    granted_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_break_glass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    justification: Mapped[str | None] = mapped_column(Text)

    role: Mapped[Role] = relationship()


class SodConstraint(Base, TimestampMixin):
    """A pair of roles that may not be held by the same principal."""

    __tablename__ = "sod_constraint"
    __table_args__ = (
        CheckConstraint("role_a_id <> role_b_id", name="ck_sod_constraint_distinct"),
        UniqueConstraint("role_a_id", "role_b_id", name="uq_sod_constraint_pair"),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    role_a_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="CASCADE"), nullable=False
    )
    role_b_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="CASCADE"), nullable=False
    )
    rule: Mapped[str] = mapped_column(String(30), nullable=False, default="mutually_exclusive")
    reason: Mapped[str | None] = mapped_column(Text)


class GateAuthority(Base):
    """Which role may decide which gate type."""

    __tablename__ = "gate_authority"
    __table_args__ = (
        UniqueConstraint("gate_type", "role_id", name="uq_gate_authority"),
        {"schema": "iam"},
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    gate_type: Mapped[str] = mapped_column(String(60), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.role.id", ondelete="CASCADE"), nullable=False
    )
    conditions: Mapped[dict | None] = mapped_column(JSONB)


class ApiToken(Base, TimestampMixin):
    """Server-to-server token. Only the hash is stored, never the token."""

    __tablename__ = "api_token"
    __table_args__ = {"schema": "iam"}

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("iam.tenant.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    principal_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    principal_type: Mapped[ActorType] = mapped_column(pg_enum(ActorType, "actor_type"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    token_hint: Mapped[str] = mapped_column(String(12), nullable=False)
    scopes: Mapped[list | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
