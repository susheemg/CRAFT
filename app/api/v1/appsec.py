"""Application security and AI management endpoints.

Two registers and one computed gate.

The gate is the reason this router exists rather than the endpoints being folded
into the compliance router. ``GET /applications/{id}/release-decision`` returns
a decision the platform computed from measurement records — not an opinion, and
not a bare refusal. When it blocks, it names the controls responsible, because a
gate that only says no is an obstacle and a gate that says which six controls
are outstanding is a work list.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession, requires
from app.models.aims import AiImpactAssessment, AiSystem
from app.models.appsec import (
    Anf,
    AnfAsc,
    Application,
    Asc,
    AscEvidence,
    TrustLevel,
)
from app.models.base import utcnow
from app.security.rbac import AuthorizationError, assert_gate_authority
from app.services import appsec as svc
from app.services import audit
from app.services.appsec import AppSecError

router = APIRouter(prefix="/appsec", tags=["Application security"])
ai_router = APIRouter(prefix="/ai", tags=["AI management"])


def _appsec_error(exc: AppSecError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"error": {"code": "appsec_refused", "message": str(exc)}},
    )


def _not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": {"code": "not_found", "message": f"No such {what}."}}
    )


def _application(db, tenant_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    row = db.get(Application, application_id)
    if row is None or row.tenant_id != tenant_id or row.is_deleted:
        raise _not_found("application")
    return row


def _current_anf(db, application: Application) -> Anf:
    anf = db.execute(
        select(Anf)
        .where(Anf.application_id == application.id, Anf.status != "superseded")
        .order_by(Anf.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if anf is None:
        raise _not_found("Application Normative Framework for this application")
    return anf


# --------------------------------------------------------------------------
# The Organization Normative Framework
# --------------------------------------------------------------------------
@router.get("/onf", summary="The current Organization Normative Framework")
def get_onf(db: DbSession, principal=Depends(requires("compliance.manage"))) -> dict:
    try:
        onf = svc.current_onf(db, principal.tenant_id)
    except AppSecError as exc:
        raise _appsec_error(exc) from exc

    levels = svc.trust_levels(db, onf)
    ascs = db.execute(
        select(func.count(Asc.id)).where(Asc.onf_id == onf.id, Asc.status == "approved")
    ).scalar_one()
    return {
        "id": str(onf.id),
        "iteration": onf.iteration_no,
        "name": onf.name,
        "scope": onf.scope_statement,
        "status": onf.status,
        "approved_ascs": ascs,
        "trust_levels": [
            {
                "id": str(lvl.id),
                "level": lvl.level_no,
                "label": lvl.label,
                "is_level_zero": lvl.is_level_zero,
            }
            for lvl in levels
        ],
        # Surfaced rather than buried: a level requiring nothing the level below
        # requires tells an owner nothing, and it is invisible until somebody
        # computes an actual level of trust and gets a surprising answer.
        "level_design_issues": svc.onf_level_design_issues(db, onf),
    }


@router.get("/onf/controls", summary="The Application Security Control library")
def list_ascs(
    db: DbSession,
    principal=Depends(requires("compliance.manage")),
    stage: Optional[str] = None,
    human_verified_only: bool = False,
) -> dict:
    onf = svc.current_onf(db, principal.tenant_id)
    stmt = select(Asc).where(Asc.onf_id == onf.id).order_by(Asc.asc_uid)
    if stage:
        stmt = stmt.where(Asc.aslcrm_stage_code == stage)
    if human_verified_only:
        stmt = stmt.where(Asc.measurement_requires_human.is_(True))
    rows = list(db.execute(stmt).scalars())
    return {
        "items": [
            {
                "id": str(a.id),
                "uid": a.asc_uid,
                "label": a.label,
                "stage": a.aslcrm_stage_code,
                "layer": a.aslcrm_layer_code,
                "automation_capability": a.automation_capability,
                "measurement_requires_human": a.measurement_requires_human,
                "control_refs": a.control_refs,
                "status": a.status,
            }
            for a in rows
        ],
        "total": len(rows),
    }


# --------------------------------------------------------------------------
# Applications and their normative frameworks
# --------------------------------------------------------------------------
@router.get("/applications", summary="The application register")
def list_applications(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    rows = list(
        db.execute(
            select(Application)
            .where(
                Application.tenant_id == principal.tenant_id,
                Application.is_deleted.is_(False),
            )
            .order_by(Application.code)
            .limit(limit)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": str(a.id),
                "code": a.code,
                "name": a.name,
                "sourcing_model": a.sourcing_model,
                "criticality": a.criticality,
                "is_ai_system": a.is_ai_system,
                "status": a.status,
            }
            for a in rows
        ],
        "total": len(rows),
    }


@router.post(
    "/applications/{application_id}/anf",
    summary="Build the Application Normative Framework for a targeted level of trust",
    status_code=201,
)
def build_anf(
    application_id: uuid.UUID,
    payload: dict,
    db: DbSession,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    application = _application(db, principal.tenant_id, application_id)
    level_id = payload.get("targeted_trust_level_id")
    if not level_id:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "target_required",
                    "message": "A targeted level of trust must be supplied and approved by the application owner.",
                }
            },
        )
    level = db.get(TrustLevel, uuid.UUID(str(level_id)))
    if level is None or level.tenant_id != principal.tenant_id:
        raise _not_found("trust level")

    # Approving the target is the application owner's decision, so it goes
    # through gate authority rather than through whoever happens to hold
    # compliance.manage.
    approved_by = None
    if payload.get("approve_target"):
        try:
            assert_gate_authority(
                db,
                principal,
                "targeted_level_of_trust",
                approver_role_id=None,
                requested_by=None,
                role_ids=(),
            )
        except AuthorizationError as exc:
            raise HTTPException(
                status_code=403,
                detail={"error": {"code": "gate_authority_required", "message": str(exc)}},
            ) from exc
        approved_by = principal.id

    try:
        anf = svc.build_anf(db, application, level, approved_by=approved_by)
    except AppSecError as exc:
        raise _appsec_error(exc) from exc

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="appsec.anf.built",
        actor_type=principal.actor_type,
        actor_ref=principal.display,
        actor_id=principal.id,
        entity="anf",
        entity_id=anf.id,
        detail={
            "application": application.code,
            "targeted_level": level.level_no,
            "target_approved": bool(approved_by),
        },
    )
    return {
        "id": str(anf.id),
        "application": application.code,
        "version": anf.version,
        "targeted_level": level.level_no,
        "status": anf.status,
        "controls": db.execute(
            select(func.count(AnfAsc.id)).where(AnfAsc.anf_id == anf.id)
        ).scalar_one(),
    }


@router.get(
    "/applications/{application_id}/release-decision",
    summary="The computed release gate for an application",
)
def release_decision(
    application_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    application = _application(db, principal.tenant_id, application_id)
    anf = _current_anf(db, application)
    return {"application": application.code, **svc.release_decision(db, anf)}


@router.post(
    "/anf-controls/{selection_id}/evidence",
    summary="Record the activity or measurement half of a control",
    status_code=201,
)
def record_evidence(
    selection_id: uuid.UUID,
    payload: dict,
    db: DbSession,
    principal=Depends(requires("evidence.write")),
) -> dict:
    selection = db.get(AnfAsc, selection_id)
    if selection is None or selection.tenant_id != principal.tenant_id:
        raise _not_found("control selection")

    kind = payload.get("kind")
    if kind not in {"activity", "measurement"}:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "kind_required",
                    "message": "kind must be 'activity' or 'measurement'.",
                }
            },
        )

    from app.models.base import ActorType

    actor_type = "agent" if principal.actor_type is ActorType.AGENT else "human"
    try:
        row = svc.record_evidence(
            db,
            selection,
            kind=kind,
            actor_type=actor_type,
            actor_user_id=principal.id if actor_type == "human" else None,
            actor_agent_id=principal.id if actor_type == "agent" else None,
            outcome=payload.get("outcome", "pass"),
            result_detail=payload.get("result_detail") or {},
        )
    except AppSecError as exc:
        # A separation-of-duties refusal is a 409, not a 422: the request is
        # well formed and the caller is authorised — it is the sequence of who
        # did what that makes it inadmissible.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "separation_of_duties", "message": str(exc)}},
        ) from exc

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action=f"appsec.evidence.{kind}",
        actor_type=principal.actor_type,
        actor_ref=principal.display,
        actor_id=principal.id,
        entity="asc_evidence",
        entity_id=row.id,
        detail={"outcome": row.outcome, "provenance": row.provenance},
    )
    return {
        "id": str(row.id),
        "kind": row.kind,
        "outcome": row.outcome,
        "provenance": row.provenance,
    }


# --------------------------------------------------------------------------
# AI management
# --------------------------------------------------------------------------
@ai_router.get("/systems", summary="The AI system inventory")
def list_ai_systems(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
) -> dict:
    rows = list(
        db.execute(
            select(AiSystem)
            .where(AiSystem.tenant_id == principal.tenant_id, AiSystem.is_deleted.is_(False))
            .order_by(AiSystem.code)
        ).scalars()
    )
    return {
        "items": [
            {
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "lifecycle_stage": s.lifecycle_stage,
                "autonomy_level": s.autonomy_level,
                "intended_use": s.intended_use,
                "is_high_impact": s.is_high_impact,
                "has_owning_application": s.application_id is not None,
                "status": s.status,
            }
            for s in rows
        ],
        "total": len(rows),
        # A model wired into the gateway with no owning application has no ANF,
        # so no control set, so nothing measuring it. That is where the two
        # standards meet and where things fall between them.
        "unowned": [
            s.code for s in svc.ai_systems_without_application(db, principal.tenant_id)
        ],
    }


@ai_router.get(
    "/systems/{ai_system_id}/impact-assessments",
    summary="Impact assessments for an AI system",
)
def list_impact_assessments(
    ai_system_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    system = db.get(AiSystem, ai_system_id)
    if system is None or system.tenant_id != principal.tenant_id:
        raise _not_found("AI system")
    rows = list(
        db.execute(
            select(AiImpactAssessment)
            .where(AiImpactAssessment.ai_system_id == system.id)
            .order_by(AiImpactAssessment.version.desc())
        ).scalars()
    )
    return {
        "ai_system": system.code,
        "items": [
            {
                "id": str(a.id),
                "version": a.version,
                "trigger": a.trigger_reason,
                "status": a.status,
                "residual_rating": a.residual_rating,
                "draft_provenance": a.draft_provenance,
                "approved": a.approved_at is not None,
                "retain_until": a.retain_until.isoformat() if a.retain_until else None,
                # Reported per dimension because answering two of three and
                # calling it done is the failure mode this shape prevents.
                "dimensions_assessed": {
                    "individual": bool(a.individual_impacts),
                    "group": bool(a.group_impacts),
                    "societal": bool(a.societal_impacts),
                },
            }
            for a in rows
        ],
    }


@ai_router.get("/certification-block", summary="Why certification is blocked, if it is")
def certification_block(
    db: DbSession,
    framework: str = Query(default="iso42001"),
    principal=Depends(requires("compliance.manage")),
) -> dict:
    reason = svc.certification_block(framework)
    return {"framework": framework, "blocked": reason is not None, "reason": reason}
