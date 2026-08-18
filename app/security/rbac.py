"""Authorization: permission resolution, segregation of duties, gate authority.

Every check lives here rather than being scattered through business logic, so
there is exactly one place to read when someone asks "who can do this, and how
do you know?".

The rules that cannot be granted away:

  * an agent principal may never hold a ``gate.*`` permission
  * a requester may never decide their own gate
  * an administrator may not grant a permission they do not themselves hold
  * an assessor may not accept the residual risk they scored
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ActorType, utcnow
from app.models.iam import (
    GateAuthority,
    Permission,
    Role,
    RoleGrant,
    RolePermission,
    SodConstraint,
)
from app.security.auth import Principal


class AuthorizationError(Exception):
    """Base class for a refusal that should surface as HTTP 403."""

    code = "forbidden"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code


class PermissionDenied(AuthorizationError):
    code = "permission_denied"


class SodViolation(AuthorizationError):
    code = "sod_violation"


class AgentNotPermitted(AuthorizationError):
    code = "agent_not_permitted"


@dataclass(frozen=True)
class ResolvedAccess:
    permissions: frozenset[str]
    role_ids: tuple[uuid.UUID, ...]
    role_names: tuple[str, ...]


def _role_closure(db: Session, role_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    """Walk parent_role_id upwards so inherited permissions are included."""
    seen: set[uuid.UUID] = set()
    frontier = list(role_ids)
    while frontier:
        rid = frontier.pop()
        if rid in seen:
            continue
        seen.add(rid)
        parent = db.execute(
            select(Role.parent_role_id).where(Role.id == rid)
        ).scalar_one_or_none()
        if parent:
            frontier.append(parent)
    return seen


def resolve_access(db: Session, principal_id: uuid.UUID, tenant_id: uuid.UUID) -> ResolvedAccess:
    """Effective permissions for a principal, honouring expiry and inheritance."""
    now = utcnow()
    grants = db.execute(
        select(RoleGrant).where(
            RoleGrant.principal_id == principal_id,
            RoleGrant.tenant_id == tenant_id,
        )
    ).scalars().all()
    live = [g for g in grants if g.expires_at is None or g.expires_at > now]
    if not live:
        return ResolvedAccess(frozenset(), (), ())

    all_role_ids = _role_closure(db, [g.role_id for g in live])
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_(all_role_ids))
    ).scalars().all()
    names = db.execute(
        select(Role.name).where(Role.id.in_([g.role_id for g in live]))
    ).scalars().all()
    return ResolvedAccess(frozenset(rows), tuple(all_role_ids), tuple(names))


# --------------------------------------------------------------------------
# Assertions used by endpoints and tools
# --------------------------------------------------------------------------
def require(principal: Principal, *permissions: str) -> None:
    """Assert the principal holds every named permission. Default deny."""
    if "*" in principal.permissions:
        return
    missing = [p for p in permissions if p not in principal.permissions]
    if missing:
        raise PermissionDenied(
            f"Missing permission: {', '.join(missing)}", code="permission_denied"
        )


def require_any(principal: Principal, *permissions: str) -> str:
    if "*" in principal.permissions:
        return permissions[0]
    for p in permissions:
        if p in principal.permissions:
            return p
    raise PermissionDenied(f"Requires one of: {', '.join(permissions)}")


def assert_human(principal: Principal) -> None:
    """Gate decisions and approvals are human-only, without exception."""
    if not principal.is_human:
        raise AgentNotPermitted(
            "Approval decisions require a human principal; accountability cannot "
            "be delegated to an agent."
        )


def gate_permission_for(gate_type: str) -> str:
    """Map a gate type to the permission that decides it."""
    family = gate_type.split(".", 1)[0] if "." in gate_type else gate_type
    known = {
        "privacy", "access", "change", "risk", "supplier", "golive", "resilience",
        "workflow", "config", "rbac",
    }
    if family not in known:
        family = "risk"
    return f"gate.{family}.approve"


def assert_gate_authority(
    db: Session,
    principal: Principal,
    gate_type: str,
    approver_role_id: uuid.UUID | None,
    requested_by: uuid.UUID | None,
    role_ids: Sequence[uuid.UUID] = (),
) -> None:
    """Full gate check: human, holds the permission, holds the role, not the requester."""
    assert_human(principal)
    require(principal, gate_permission_for(gate_type))

    if requested_by and requested_by == principal.id:
        raise SodViolation(
            "The principal who raised this request cannot approve it. "
            "Route the decision to another authorised approver."
        )

    if approver_role_id:
        held = set(role_ids) or set(
            resolve_access(db, principal.id, principal.tenant_id).role_ids
        )
        if approver_role_id not in held and "*" not in principal.permissions:
            raise PermissionDenied(
                "This gate is reserved for a role the principal does not hold."
            )

    authorised_roles = db.execute(
        select(GateAuthority.role_id).where(GateAuthority.gate_type == gate_type)
    ).scalars().all()
    if authorised_roles:
        held = set(role_ids) or set(
            resolve_access(db, principal.id, principal.tenant_id).role_ids
        )
        if not held.intersection(authorised_roles) and "*" not in principal.permissions:
            raise PermissionDenied(
                f"No role held by this principal is authorised to decide '{gate_type}' gates."
            )


# --------------------------------------------------------------------------
# Grant-time validation
# --------------------------------------------------------------------------
def validate_grant(
    db: Session,
    granting_principal: Principal,
    target_principal_id: uuid.UUID,
    target_principal_type: ActorType,
    role_id: uuid.UUID,
) -> None:
    """Refuse a role grant that would breach SoD, escalate privilege, or make an
    agent accountable. Breaches are rejected, not warned about."""
    role = db.get(Role, role_id)
    if role is None:
        raise PermissionDenied("Role does not exist")

    role_perms = set(
        db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(_role_closure(db, [role_id])))
        ).scalars().all()
    )

    # 1. Agent non-accountability.
    if target_principal_type == ActorType.AGENT:
        gate_perms = sorted(p for p in role_perms if p.startswith("gate."))
        if gate_perms:
            raise AgentNotPermitted(
                f"Role '{role.name}' carries approval authority ({gate_perms[0]}) "
                "and cannot be granted to an agent principal."
            )
        if not role.agent_eligible:
            raise AgentNotPermitted(
                f"Role '{role.name}' is not marked agent-eligible."
            )

    # 2. Grantor limit — cannot grant beyond one's own authority.
    if "*" not in granting_principal.permissions:
        beyond = sorted(role_perms - set(granting_principal.permissions))
        if beyond:
            raise PermissionDenied(
                f"Cannot grant permissions the grantor does not hold: {beyond[0]}"
            )

    # 3. Mutually exclusive roles.
    existing_role_ids = set(
        db.execute(
            select(RoleGrant.role_id).where(RoleGrant.principal_id == target_principal_id)
        ).scalars().all()
    )
    if existing_role_ids:
        conflicts = db.execute(
            select(SodConstraint).where(
                (
                    (SodConstraint.role_a_id == role_id)
                    & (SodConstraint.role_b_id.in_(existing_role_ids))
                )
                | (
                    (SodConstraint.role_b_id == role_id)
                    & (SodConstraint.role_a_id.in_(existing_role_ids))
                )
            )
        ).scalars().first()
        if conflicts:
            other_id = (
                conflicts.role_b_id if conflicts.role_a_id == role_id else conflicts.role_a_id
            )
            other = db.get(Role, other_id)
            raise SodViolation(
                f"'{role.name}' and '{other.name if other else other_id}' are mutually "
                f"exclusive: {conflicts.reason or 'segregation of duties'}."
            )
