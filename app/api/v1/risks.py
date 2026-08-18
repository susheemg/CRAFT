"""Risk register endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, authz_exception, requires
from app.api.schemas import RiskAccept, RiskCreate, RiskOut, RiskRescore
from app.models.base import GateReason, RiskStatus, Severity, TreatmentStrategy, utcnow
from app.models.core import ApprovalGate, Run
from app.models.domain import Risk
from app.security.rbac import AuthorizationError, assert_gate_authority
from app.services import audit, engine, risk as risk_service
from app.services.outbox import publish
from app.services.risk import RiskError

router = APIRouter(prefix="/risks", tags=["Risk"])


def _risk_error(exc: RiskError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"error": {"code": "risk_invalid", "message": str(exc)}},
    )


def _get(db, tenant_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None or risk.tenant_id != tenant_id or risk.is_deleted:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such risk."}}
        )
    return risk


@router.get("", summary="List risks")
def list_risks(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    risk_status: Optional[str] = Query(default=None, alias="status"),
    band: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: int = Query(default=0, ge=0),
) -> dict:
    stmt = select(Risk).where(
        Risk.tenant_id == principal.tenant_id, Risk.is_deleted.is_(False)
    )
    if risk_status:
        stmt = stmt.where(Risk.status == RiskStatus(risk_status))
    if band:
        stmt = stmt.where(Risk.severity_band == Severity(band))
    if category:
        stmt = stmt.where(Risk.category == category)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = db.execute(
        stmt.order_by(
            func.coalesce(Risk.residual_score, Risk.inherent_score).desc(),
            Risk.created_at.desc(),
        )
        .offset(cursor)
        .limit(limit)
    ).scalars().all()
    return {
        "data": [RiskOut.model_validate(r).model_dump(mode="json") for r in rows],
        "total": total,
        "next_cursor": str(cursor + limit) if cursor + limit < total else None,
    }


@router.get("/summary", summary="Register summary and heatmap")
def summary(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    return {
        "summary": risk_service.register_summary(db, principal.tenant_id),
        "heatmap": risk_service.heatmap(db, principal.tenant_id),
        "top": [
            RiskOut.model_validate(r).model_dump(mode="json")
            for r in risk_service.top_risks(db, principal.tenant_id)
        ],
    }


@router.post("", response_model=RiskOut, status_code=201, summary="Add a risk")
def create_risk(
    payload: RiskCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("risk.manage")),
) -> RiskOut:
    try:
        risk = risk_service.create_risk(
            db,
            tenant_id=principal.tenant_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            threat=payload.threat,
            vulnerability=payload.vulnerability,
            inherent_likelihood=payload.inherent_likelihood,
            inherent_impact=payload.inherent_impact,
            residual_likelihood=payload.residual_likelihood,
            residual_impact=payload.residual_impact,
            treatment=TreatmentStrategy(payload.treatment),
            treatment_plan=payload.treatment_plan,
            owner_user_id=payload.owner_user_id,
            linked_controls=payload.linked_controls,
            review_days=payload.review_days,
            created_by=principal.id,
        )
    except RiskError as exc:
        raise _risk_error(exc) from exc

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="risk.created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="risk",
        entity_id=risk.id,
        after_state={
            "ref": risk.risk_ref,
            "title": risk.title,
            "inherent": risk.inherent_score,
            "residual": risk.residual_score,
            "band": risk.severity_band.value,
        },
        request_id=request_id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="risk.raised",
        payload={
            "risk_id": str(risk.id),
            "ref": risk.risk_ref,
            "band": risk.severity_band.value,
        },
        request_id=request_id,
    )
    db.commit()
    return RiskOut.model_validate(risk)


@router.get("/{risk_id}", response_model=RiskOut, summary="Retrieve a risk")
def get_risk(
    risk_id: uuid.UUID, db: DbSession, principal=Depends(requires("data.register.read"))
) -> RiskOut:
    return RiskOut.model_validate(_get(db, principal.tenant_id, risk_id))


@router.post("/{risk_id}:rescore", response_model=RiskOut, summary="Re-score residual risk")
def rescore(
    risk_id: uuid.UUID,
    payload: RiskRescore,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("risk.manage")),
) -> RiskOut:
    risk = _get(db, principal.tenant_id, risk_id)
    before = {"residual_score": risk.residual_score, "band": risk.severity_band.value}
    try:
        risk_service.rescore(
            db,
            risk,
            residual_likelihood=payload.residual_likelihood,
            residual_impact=payload.residual_impact,
            note=payload.note,
            updated_by=principal.id,
        )
    except RiskError as exc:
        raise _risk_error(exc) from exc
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="risk.rescored",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="risk",
        entity_id=risk.id,
        before_state=before,
        after_state={"residual_score": risk.residual_score, "band": risk.severity_band.value},
        request_id=request_id,
    )
    db.commit()
    return RiskOut.model_validate(risk)


@router.post(
    "/{risk_id}:accept",
    summary="Accept residual risk (raises a gate above appetite)",
)
def accept_risk(
    risk_id: uuid.UUID,
    payload: RiskAccept,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("risk.manage")),
) -> dict:
    """Below appetite this records the acceptance directly.

    At or above the appetite threshold it does something different: it raises
    an approval gate and returns 202. That is the point of the control — an
    exposure the organisation said it would not tolerate needs a named person
    to accept it, not a note from whoever happened to be scoring.
    """
    risk = _get(db, principal.tenant_id, risk_id)
    if risk.status == RiskStatus.ACCEPTED:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "already_accepted",
                    "message": f"{risk.risk_ref} was accepted on "
                    f"{risk.accepted_at.date() if risk.accepted_at else 'an earlier date'}.",
                }
            },
        )

    band = risk_service.band_for(risk.residual_score or risk.inherent_score)
    needs_gate = risk_service.requires_acceptance_gate(band)

    if needs_gate:
        try:
            assert_gate_authority(
                db,
                principal,
                "risk.residual_acceptance",
                approver_role_id=None,
                requested_by=None,
            )
        except AuthorizationError:
            # The requester is not authorised to accept: raise a gate for
            # someone who is, rather than refusing outright.
            run = Run(
                tenant_id=principal.tenant_id,
                workflow_id=_placeholder_workflow(db, principal.tenant_id),
                wf_version=1,
                trigger_source=f"risk:{risk.risk_ref}",
                initiated_by=principal.id,
                started_at=utcnow(),
                created_at=utcnow(),
                context={"risk_id": str(risk.id)},
            )
            db.add(run)
            db.flush()
            gate = engine.raise_gate(
                db,
                run=run,
                activity_run=None,
                gate_type="risk.residual_acceptance",
                reason=GateReason.HIGH_RISK,
                summary=f"Accept residual risk {risk.risk_ref}: {risk.title[:150]}",
                context={
                    "risk_id": str(risk.id),
                    "residual_score": risk.residual_score,
                    "band": band.value,
                    "rationale": payload.rationale,
                },
                requested_by=principal.id,
                due_hours=72,
            )
            db.commit()
            return {
                "status": "awaiting_approval",
                "gate_id": str(gate.id),
                "message": (
                    f"{risk.risk_ref} sits in the {band.value.replace('_', ' ')} band, "
                    "which is above appetite. An approver with residual-risk authority "
                    "must decide it."
                ),
            }

    try:
        risk_service.accept(
            db,
            risk,
            accepted_by=principal.id,
            rationale=payload.rationale,
            review_days=payload.review_days,
        )
    except RiskError as exc:
        raise _risk_error(exc) from exc

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="risk.accepted",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="risk",
        entity_id=risk.id,
        after_state={
            "status": "accepted",
            "band": band.value,
            "rationale": payload.rationale[:500],
        },
        request_id=request_id,
    )
    engine.record_evidence(
        db,
        tenant_id=principal.tenant_id,
        kind="attestation",
        title=f"Residual risk acceptance — {risk.risk_ref}",
        payload={
            "risk_ref": risk.risk_ref,
            "residual_score": risk.residual_score,
            "band": band.value,
            "rationale": payload.rationale,
            "accepted_by": str(principal.id),
        },
        subject_type="risk",
        subject_id=risk.id,
        created_by=principal.id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="risk.accepted",
        payload={"risk_id": str(risk.id), "ref": risk.risk_ref, "band": band.value},
        request_id=request_id,
    )
    db.commit()
    return {"status": "accepted", "risk": RiskOut.model_validate(risk).model_dump(mode="json")}


def _placeholder_workflow(db, tenant_id: uuid.UUID) -> uuid.UUID:
    """Attach an ad-hoc gate to the risk workflow so it has a run to belong to."""
    from app.models.core import Workflow

    wf = db.execute(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id, Workflow.wf_code == "WF-22"
        )
    ).scalars().first()
    if wf is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "workflow_missing",
                    "message": "The risk workflow (WF-22) is not deployed. Run the seeder.",
                }
            },
        )
    return wf.id
