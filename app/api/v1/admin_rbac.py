"""Administration of the access model.

Every grant passes through :func:`validate_grant` before it is written, so a
segregation-of-duties breach is refused at the point of creation rather than
detected later by a report. Three rules are enforced without exception:

  * an agent principal can never hold a role carrying approval authority
  * nobody can grant a permission they do not themselves hold
  * mutually exclusive roles cannot be combined on one principal
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, authz_exception, requires
from app.api.schemas import RoleCreate, RoleGrantCreate, SodConstraintCreate
from app.models.base import ActorType, utcnow
from app.models.iam import (
    AgentIdentity,
    GateAuthority,
    Permission,
    Role,
    RoleGrant,
    RolePermission,
    SodConstraint,
    UserAccount,
)
from app.security.rbac import AuthorizationError, resolve_access, validate_grant
from app.services import audit

router = APIRouter(prefix="/admin/rbac", tags=["Admin — access model"])


@router.get("/permissions", summary="The permission catalogue")
def list_permissions(db: DbSession, _=Depends(requires("admin.rbac.manage"))) -> dict:
    rows = db.execute(
        select(Permission).order_by(Permission.category, Permission.code)
    ).scalars().all()
    by_category: dict[str, list] = {}
    for p in rows:
        by_category.setdefault(p.category, []).append(
            {"code": p.code, "name": p.name, "description": p.description}
        )
    return {"categories": by_category, "total": len(rows)}


@router.get("/roles", summary="Roles and their permissions")
def list_roles(db: DbSession, principal=Depends(requires("admin.rbac.manage"))) -> dict:
    roles = db.execute(select(Role).order_by(Role.name)).scalars().all()
    perms = {p.id: p for p in db.execute(select(Permission)).scalars().all()}
    grants = dict(
        db.execute(
            select(RoleGrant.role_id, func.count(RoleGrant.id))
            .where(RoleGrant.tenant_id == principal.tenant_id)
            .group_by(RoleGrant.role_id)
        ).all()
    )
    out = []
    for role in roles:
        codes = sorted(
            perms[rp.permission_id].code
            for rp in db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).scalars().all()
            if rp.permission_id in perms
        )
        out.append(
            {
                "id": str(role.id),
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "agent_eligible": role.agent_eligible,
                "parent_role_id": str(role.parent_role_id) if role.parent_role_id else None,
                "permissions": codes,
                "gate_permissions": [c for c in codes if c.startswith("gate.")],
                "assigned_principals": grants.get(role.id, 0),
            }
        )
    return {"data": out}


@router.post("/roles", status_code=201, summary="Create a role")
def create_role(
    payload: RoleCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.rbac.manage")),
) -> dict:
    if db.execute(select(Role).where(Role.name == payload.name)).scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "conflict", "message": "That role name is taken."}},
        )
    perms = db.execute(
        select(Permission).where(Permission.code.in_(payload.permissions or []))
    ).scalars().all()
    unknown = set(payload.permissions or []) - {p.code for p in perms}
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "unknown_permission",
                    "message": f"Not in the catalogue: {', '.join(sorted(unknown))}",
                }
            },
        )
    # An agent-eligible role carrying approval authority would defeat the
    # accountability rule at grant time, so refuse it at definition time.
    gate_perms = [p.code for p in perms if p.code.startswith("gate.")]
    if payload.agent_eligible and gate_perms:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "agent_gate_conflict",
                    "message": (
                        f"An agent-eligible role cannot carry approval authority "
                        f"({gate_perms[0]}). Accountability for a decision must rest "
                        "with a person."
                    ),
                }
            },
        )
    beyond = sorted({p.code for p in perms} - set(principal.permissions))
    if beyond and "*" not in principal.permissions:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "grantor_limit",
                    "message": (
                        f"You cannot define a role carrying permissions you do not "
                        f"hold: {beyond[0]}"
                    ),
                }
            },
        )

    role = Role(
        name=payload.name,
        description=payload.description or None,
        parent_role_id=payload.parent_role_id,
        agent_eligible=payload.agent_eligible,
        is_system=False,
        created_at=utcnow(),
    )
    db.add(role)
    db.flush()
    for p in perms:
        db.add(RolePermission(role_id=role.id, permission_id=p.id, scope="all"))
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="rbac.role_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="role",
        entity_id=role.id,
        after_state={"name": role.name, "permissions": sorted(p.code for p in perms)},
        request_id=request_id,
    )
    db.commit()
    return {"id": str(role.id), "name": role.name, "permissions": len(perms)}


@router.get("/grants", summary="Who holds what")
def list_grants(db: DbSession, principal=Depends(requires("admin.rbac.manage"))) -> dict:
    rows = db.execute(
        select(RoleGrant, Role)
        .join(Role, Role.id == RoleGrant.role_id)
        .where(RoleGrant.tenant_id == principal.tenant_id)
        .order_by(RoleGrant.granted_at.desc())
    ).all()
    users = {
        u.id: u
        for u in db.execute(
            select(UserAccount).where(UserAccount.tenant_id == principal.tenant_id)
        ).scalars().all()
    }
    agents = {
        a.id: a
        for a in db.execute(
            select(AgentIdentity).where(AgentIdentity.tenant_id == principal.tenant_id)
        ).scalars().all()
    }
    now = utcnow()

    def who(g: RoleGrant) -> str:
        if g.principal_type == ActorType.AGENT:
            a = agents.get(g.principal_id)
            return f"agent:{a.agent_key}" if a else "agent:unknown"
        u = users.get(g.principal_id)
        return u.email if u else "user:unknown"

    return {
        "data": [
            {
                "id": str(g.id),
                "principal": who(g),
                "principal_type": g.principal_type.value,
                "role": r.name,
                "scope": g.scope,
                "granted_at": g.granted_at.isoformat(),
                "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                "expired": bool(g.expires_at and g.expires_at < now),
                "is_break_glass": g.is_break_glass,
                "justification": g.justification,
            }
            for g, r in rows
        ]
    }


@router.post("/grants", status_code=201, summary="Grant a role")
def create_grant(
    payload: RoleGrantCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.rbac.manage")),
) -> dict:
    principal_type = ActorType(payload.principal_type)
    if principal_type == ActorType.AGENT:
        if db.get(AgentIdentity, payload.principal_id) is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "not_found", "message": "No such agent identity."}},
            )
    elif db.get(UserAccount, payload.principal_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "No such user account."}},
        )

    try:
        validate_grant(
            db,
            granting_principal=principal,
            target_principal_id=payload.principal_id,
            target_principal_type=principal_type,
            role_id=payload.role_id,
        )
    except AuthorizationError as exc:
        audit.record(
            db,
            tenant_id=principal.tenant_id,
            action="rbac.grant_refused",
            outcome="failure",
            actor_type=principal.actor_type,
            actor_ref=principal.actor_ref,
            actor_id=principal.id,
            entity="role_grant",
            detail={
                "code": exc.code,
                "reason": str(exc)[:400],
                "target": str(payload.principal_id),
                "role_id": str(payload.role_id),
            },
            request_id=request_id,
        )
        db.commit()
        raise authz_exception(exc) from exc

    # Break-glass exists for genuine emergencies; it is time-boxed by design so
    # it cannot quietly become someone's standing access.
    if payload.is_break_glass and not payload.expires_days:
        payload.expires_days = 1
    if payload.is_break_glass and len(payload.justification) < 20:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "justification_required",
                    "message": "Break-glass access requires a written justification.",
                }
            },
        )

    grant = RoleGrant(
        tenant_id=principal.tenant_id,
        principal_id=payload.principal_id,
        principal_type=principal_type,
        role_id=payload.role_id,
        scope=payload.scope,
        granted_by=principal.id,
        granted_at=utcnow(),
        expires_at=utcnow() + timedelta(days=payload.expires_days)
        if payload.expires_days
        else None,
        is_break_glass=payload.is_break_glass,
        justification=payload.justification or None,
    )
    db.add(grant)
    db.flush()
    role = db.get(Role, payload.role_id)
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="rbac.grant_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="role_grant",
        entity_id=grant.id,
        after_state={
            "role": role.name,
            "principal_type": principal_type.value,
            "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            "break_glass": grant.is_break_glass,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(grant.id),
        "role": role.name,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
    }


@router.delete("/grants/{grant_id}", summary="Revoke a grant")
def revoke_grant(
    grant_id: uuid.UUID,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.rbac.manage")),
) -> dict:
    grant = db.get(RoleGrant, grant_id)
    if grant is None or grant.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such grant."}}
        )
    role = db.get(Role, grant.role_id)
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="rbac.grant_revoked",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="role_grant",
        entity_id=grant.id,
        before_state={"role": role.name if role else None, "scope": grant.scope},
        request_id=request_id,
    )
    db.delete(grant)
    db.commit()
    return {"revoked": True, "role": role.name if role else None}


@router.get("/sod", summary="Segregation-of-duties constraints")
def list_sod(db: DbSession, _=Depends(requires("admin.rbac.manage"))) -> dict:
    rows = db.execute(select(SodConstraint)).scalars().all()
    roles = {r.id: r.name for r in db.execute(select(Role)).scalars().all()}
    return {
        "data": [
            {
                "id": str(c.id),
                "role_a": roles.get(c.role_a_id),
                "role_b": roles.get(c.role_b_id),
                "rule": c.rule,
                "reason": c.reason,
            }
            for c in rows
        ]
    }


@router.post("/sod", status_code=201, summary="Add a segregation-of-duties constraint")
def create_sod(
    payload: SodConstraintCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.rbac.manage")),
) -> dict:
    if payload.role_a_id == payload.role_b_id:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "invalid_constraint",
                    "message": "A role cannot be mutually exclusive with itself.",
                }
            },
        )
    # Refuse to create a constraint that existing grants already violate:
    # otherwise the rule is on paper only.
    breaches = _existing_breaches(db, principal.tenant_id, payload.role_a_id, payload.role_b_id)
    if breaches:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "existing_violation",
                    "message": (
                        f"{len(breaches)} principal(s) already hold both roles. "
                        "Revoke one side first, or the constraint would be "
                        "unenforced from the day it was written."
                    ),
                    "details": [{"issue": b} for b in breaches[:10]],
                }
            },
        )
    constraint = SodConstraint(
        role_a_id=payload.role_a_id,
        role_b_id=payload.role_b_id,
        rule="mutually_exclusive",
        reason=payload.reason,
        created_at=utcnow(),
    )
    db.add(constraint)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="rbac.sod_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="sod_constraint",
        entity_id=constraint.id,
        after_state={"reason": payload.reason},
        request_id=request_id,
    )
    db.commit()
    return {"id": str(constraint.id)}


def _existing_breaches(db, tenant_id: uuid.UUID, role_a, role_b) -> list[str]:
    holders_a = set(
        db.execute(
            select(RoleGrant.principal_id).where(
                RoleGrant.tenant_id == tenant_id, RoleGrant.role_id == role_a
            )
        ).scalars().all()
    )
    holders_b = set(
        db.execute(
            select(RoleGrant.principal_id).where(
                RoleGrant.tenant_id == tenant_id, RoleGrant.role_id == role_b
            )
        ).scalars().all()
    )
    both = holders_a & holders_b
    if not both:
        return []
    users = {
        u.id: u.email
        for u in db.execute(
            select(UserAccount).where(UserAccount.id.in_(both))
        ).scalars().all()
    }
    return [users.get(pid, str(pid)) for pid in both]


@router.get("/gate-authority", summary="Which roles may decide which gates")
def gate_authority(db: DbSession, _=Depends(requires("admin.rbac.manage"))) -> dict:
    rows = db.execute(select(GateAuthority)).scalars().all()
    roles = {r.id: r.name for r in db.execute(select(Role)).scalars().all()}
    by_gate: dict[str, list[str]] = {}
    for row in rows:
        by_gate.setdefault(row.gate_type, []).append(roles.get(row.role_id, "?"))
    return {"data": [{"gate_type": g, "roles": sorted(r)} for g, r in sorted(by_gate.items())]}


@router.get("/principals/{principal_id}/access", summary="Effective access for a principal")
def effective_access(
    principal_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("admin.rbac.manage")),
) -> dict:
    """Effective access after role inheritance — what the principal can actually
    do, not what was written on the grants."""
    access = resolve_access(db, principal_id, principal.tenant_id)
    return {
        "principal_id": str(principal_id),
        "roles": sorted(access.role_names),
        "permissions": sorted(access.permissions),
        "gate_authority": sorted(p for p in access.permissions if p.startswith("gate.")),
    }


@router.get("/agents", summary="Agent identities")
def list_agents(db: DbSession, principal=Depends(requires("admin.rbac.manage"))) -> dict:
    rows = db.execute(
        select(AgentIdentity).where(AgentIdentity.tenant_id == principal.tenant_id)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(a.id),
                "agent_key": a.agent_key,
                "display_name": a.display_name,
                "autonomy_tier": a.autonomy_tier.value,
                "guardrail_profile": a.guardrail_profile,
                "status": a.status,
                "roles": sorted(resolve_access(db, a.id, a.tenant_id).role_names),
            }
            for a in rows
        ],
        "note": (
            "Agent principals execute work and draft assessments. None of them "
            "can hold approval authority: accountability rests with a person."
        ),
    }
