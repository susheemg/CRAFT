"""Runs, approval gates, continuity records and privacy registers."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, authz_exception, requires
from app.api.schemas import (
    BiaCreate,
    ContinuityPlanCreate,
    DsarCreate,
    ExerciseCreate,
    GateDecideRequest,
    IncidentCreate,
    ProcessingRecordCreate,
    RunAdvanceRequest,
    RunStartRequest,
)
from app.models.base import GateDecision, IncidentStatus, Severity, utcnow
from app.models.core import ActivityRun, ApprovalGate, EvidenceRecord, Run, Workflow
from app.models.domain import (
    Breach,
    BusinessImpactAnalysis,
    ContinuityExercise,
    ContinuityPlan,
    DsarRequest,
    Incident,
    ProcessingRecord,
)
from app.security.rbac import AuthorizationError, assert_gate_authority, resolve_access
from app.services import audit, engine
from app.services.engine import EngineError, GateOpen
from app.services.outbox import publish

router = APIRouter(tags=["Operations"])

# Statutory clocks, in one place so they are auditable and changeable.
DSAR_RESPONSE_DAYS = 30
BREACH_NOTIFY_HOURS = 72


# ==========================================================================
# Approval gates — the approver inbox
# ==========================================================================
@router.get("/gates", summary="The approver inbox")
def list_gates(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    gate_status: str = Query(default="pending", alias="status"),
    mine: bool = Query(default=True, description="Only gates this principal could decide"),
) -> dict:
    access = resolve_access(db, principal.id, principal.tenant_id)
    stmt = select(ApprovalGate).where(ApprovalGate.tenant_id == principal.tenant_id)
    if gate_status != "all":
        stmt = stmt.where(ApprovalGate.decision == GateDecision(gate_status))
    rows = db.execute(stmt.order_by(ApprovalGate.raised_at.desc()).limit(200)).scalars().all()

    def can_decide(g: ApprovalGate) -> bool:
        if not principal.is_human:
            return False
        from app.security.rbac import gate_permission_for

        if gate_permission_for(g.gate_type) not in principal.permissions:
            return False
        if g.requested_by == principal.id:
            return False
        if g.approver_role_id and g.approver_role_id not in access.role_ids:
            return False
        return True

    items = [g for g in rows if not mine or can_decide(g)]
    return {
        "data": [
            {
                "id": str(g.id),
                "gate_type": g.gate_type,
                "reason": g.reason.value,
                "summary": g.summary,
                "context": g.context,
                "decision": g.decision.value,
                "raised_at": g.raised_at.isoformat(),
                "due_at": g.due_at.isoformat() if g.due_at else None,
                "overdue": bool(
                    g.due_at and g.due_at < utcnow() and g.decision == GateDecision.PENDING
                ),
                "run_id": str(g.run_id),
                "you_can_decide": can_decide(g),
                "decided_at": g.decided_at.isoformat() if g.decided_at else None,
                "rationale": g.rationale,
            }
            for g in items
        ],
        "pending_total": sum(1 for g in rows if g.decision == GateDecision.PENDING),
    }


@router.post("/gates/{gate_id}:decide", summary="Approve or reject a gate (human only)")
def decide_gate(
    gate_id: uuid.UUID,
    payload: GateDecideRequest,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.read")),
) -> dict:
    """Three checks run before any state changes: the principal is human, holds
    the gate permission and the authorised role, and did not raise the request."""
    gate = db.get(ApprovalGate, gate_id)
    if gate is None or gate.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such gate."}}
        )
    try:
        assert_gate_authority(
            db,
            principal,
            gate.gate_type,
            approver_role_id=gate.approver_role_id,
            requested_by=gate.requested_by,
        )
    except AuthorizationError as exc:
        audit.record(
            db,
            tenant_id=principal.tenant_id,
            action="gate.decision_refused",
            outcome="failure",
            actor_type=principal.actor_type,
            actor_ref=principal.actor_ref,
            actor_id=principal.id,
            entity="approval_gate",
            entity_id=gate.id,
            detail={"code": exc.code, "reason": str(exc)[:300]},
            request_id=request_id,
        )
        db.commit()
        raise authz_exception(exc) from exc

    try:
        engine.decide_gate(
            db,
            gate,
            principal,
            decision=GateDecision(payload.decision),
            rationale=payload.rationale,
        )
    except EngineError as exc:
        raise HTTPException(
            status_code=409, detail={"error": {"code": exc.code, "message": str(exc)}}
        ) from exc

    # A residual-risk gate carries its effect back to the risk register.
    if gate.gate_type == "risk.residual_acceptance" and payload.decision == "approved":
        _apply_risk_acceptance(db, gate, principal)

    db.commit()
    return {
        "id": str(gate.id),
        "decision": gate.decision.value,
        "decided_at": gate.decided_at.isoformat(),
        "approver": principal.display,
    }


def _apply_risk_acceptance(db, gate: ApprovalGate, principal) -> None:
    from app.models.domain import Risk
    from app.services import risk as risk_service

    risk_id = (gate.context or {}).get("risk_id")
    if not risk_id:
        return
    risk = db.get(Risk, uuid.UUID(risk_id))
    if risk is None:
        return
    rationale = (gate.context or {}).get("rationale") or gate.rationale or ""
    if len(rationale) < 20:
        rationale = (
            f"Accepted at gate {gate.id} by {principal.display}. "
            f"{gate.rationale or 'No further rationale recorded.'}"
        )
    risk_service.accept(
        db, risk, accepted_by=principal.id, rationale=rationale, review_days=180
    )
    publish(
        db,
        tenant_id=gate.tenant_id,
        topic="risk.accepted",
        payload={"risk_id": str(risk.id), "ref": risk.risk_ref, "via_gate": str(gate.id)},
    )


# ==========================================================================
# Runs
# ==========================================================================
@router.get("/runs", summary="List workflow runs")
def list_runs(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    run_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    stmt = select(Run, Workflow).join(Workflow, Workflow.id == Run.workflow_id).where(
        Run.tenant_id == principal.tenant_id
    )
    if run_status:
        from app.models.base import RunStatus

        stmt = stmt.where(Run.status == RunStatus(run_status))
    rows = db.execute(stmt.order_by(Run.started_at.desc()).limit(limit)).all()
    return {
        "data": [
            {
                "id": str(r.id),
                "workflow": w.wf_code,
                "workflow_name": w.name,
                "status": r.status.value,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
                "overdue": bool(
                    r.sla_due_at and r.sla_due_at < utcnow() and r.completed_at is None
                ),
                "trigger": r.trigger_source,
            }
            for r, w in rows
        ]
    }


@router.post("/runs", status_code=201, summary="Start a workflow run")
def start_run(
    payload: RunStartRequest,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("wf.execute")),
) -> dict:
    try:
        run = engine.start_run(
            db,
            tenant_id=principal.tenant_id,
            workflow_code=payload.workflow_code,
            principal=principal,
            context=payload.context,
            subject_ref=payload.subject_ref,
            sla_days=payload.sla_days,
        )
    except EngineError as exc:
        raise HTTPException(
            status_code=422, detail={"error": {"code": exc.code, "message": str(exc)}}
        ) from exc
    db.commit()
    return {"id": str(run.id), "workflow": payload.workflow_code, "status": run.status.value}


@router.post("/runs/{run_id}:advance", summary="Advance a run by one activity")
def advance_run(
    run_id: uuid.UUID,
    payload: RunAdvanceRequest,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("wf.execute")),
) -> dict:
    run = db.get(Run, run_id)
    if run is None or run.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such run."}}
        )
    try:
        result = engine.execute_next(
            db, run, principal, output=payload.output, confidence=payload.confidence
        )
    except GateOpen as exc:
        raise HTTPException(
            status_code=409, detail={"error": {"code": exc.code, "message": str(exc)}}
        ) from exc
    except EngineError as exc:
        raise HTTPException(
            status_code=422, detail={"error": {"code": exc.code, "message": str(exc)}}
        ) from exc
    db.commit()
    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "finished": result.finished,
        "awaiting_gate": result.awaiting_gate,
        "gate_id": str(result.gate.id) if result.gate else None,
    }


@router.get("/runs/{run_id}", summary="Retrieve a run with its full trail")
def get_run(
    run_id: uuid.UUID, db: DbSession, principal=Depends(requires("data.register.read"))
) -> dict:
    run = db.get(Run, run_id)
    if run is None or run.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such run."}}
        )
    workflow = db.get(Workflow, run.workflow_id)
    steps = db.execute(
        select(ActivityRun).where(ActivityRun.run_id == run.id).order_by(ActivityRun.started_at)
    ).scalars().all()
    gates = db.execute(
        select(ApprovalGate).where(ApprovalGate.run_id == run.id)
    ).scalars().all()
    evidence = db.execute(
        select(EvidenceRecord).where(EvidenceRecord.run_id == run.id)
    ).scalars().all()
    return {
        "id": str(run.id),
        "workflow": workflow.wf_code,
        "workflow_name": workflow.name,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "context": run.context,
        "activities": [
            {
                "id": str(s.id),
                "actor": s.actor_ref,
                "actor_type": s.actor_type.value,
                "status": s.status,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "confidence": float(s.confidence) if s.confidence is not None else None,
                "output": s.output,
            }
            for s in steps
        ],
        "gates": [
            {
                "id": str(g.id),
                "gate_type": g.gate_type,
                "reason": g.reason.value,
                "decision": g.decision.value,
                "rationale": g.rationale,
                "decided_at": g.decided_at.isoformat() if g.decided_at else None,
            }
            for g in gates
        ],
        "evidence": [
            {
                "id": str(e.id),
                "kind": e.kind,
                "title": e.title,
                "content_hash": e.content_hash.hex(),
            }
            for e in evidence
        ],
    }


# ==========================================================================
# ISO 22301 — business impact analysis, plans and exercises
# ==========================================================================
@router.get("/continuity/bias", summary="List business impact analyses")
def list_bias(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(
        select(BusinessImpactAnalysis)
        .where(
            BusinessImpactAnalysis.tenant_id == principal.tenant_id,
            BusinessImpactAnalysis.is_deleted.is_(False),
        )
        .order_by(BusinessImpactAnalysis.priority, BusinessImpactAnalysis.activity_name)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(b.id),
                "activity_name": b.activity_name,
                "business_function": b.business_function,
                "priority": b.priority,
                "mtpd_hours": b.mtpd_hours,
                "rto_hours": b.rto_hours,
                "rpo_minutes": b.rpo_minutes,
                "approved_at": b.approved_at.isoformat() if b.approved_at else None,
                "next_review_at": b.next_review_at.isoformat() if b.next_review_at else None,
            }
            for b in rows
        ]
    }


@router.post("/continuity/bias", status_code=201, summary="Record a business impact analysis")
def create_bia(
    payload: BiaCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    bia = BusinessImpactAnalysis(
        tenant_id=principal.tenant_id,
        activity_name=payload.activity_name,
        business_function=payload.business_function or None,
        priority=payload.priority,
        mtpd_hours=payload.mtpd_hours,
        rto_hours=payload.rto_hours,
        rpo_minutes=payload.rpo_minutes,
        mbco=payload.mbco or None,
        impact_over_time=payload.impact_over_time,
        dependencies=payload.dependencies,
        owner_user_id=principal.id,
        next_review_at=utcnow() + timedelta(days=365),
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(bia)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="continuity.bia_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="business_impact_analysis",
        entity_id=bia.id,
        after_state={
            "activity": bia.activity_name,
            "mtpd_hours": bia.mtpd_hours,
            "rto_hours": bia.rto_hours,
            "rpo_minutes": bia.rpo_minutes,
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(bia.id), "activity_name": bia.activity_name}


@router.get("/continuity/plans", summary="List continuity plans")
def list_plans(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(
        select(ContinuityPlan)
        .where(
            ContinuityPlan.tenant_id == principal.tenant_id,
            ContinuityPlan.is_deleted.is_(False),
        )
        .order_by(ContinuityPlan.name)
    ).scalars().all()
    exercises = dict(
        db.execute(
            select(ContinuityExercise.plan_id, func.max(ContinuityExercise.performed_at))
            .where(ContinuityExercise.tenant_id == principal.tenant_id)
            .group_by(ContinuityExercise.plan_id)
        ).all()
    )
    now = utcnow()
    return {
        "data": [
            {
                "id": str(p.id),
                "name": p.name,
                "plan_type": p.plan_type,
                "rto_hours": p.rto_hours,
                "rpo_minutes": p.rpo_minutes,
                "approved_at": p.approved_at.isoformat() if p.approved_at else None,
                "last_exercised_at": exercises[p.id].isoformat()
                if exercises.get(p.id)
                else None,
                # Clause 8.5 expects exercising at planned intervals; twelve
                # months is the common certification expectation.
                "exercise_overdue": bool(
                    not exercises.get(p.id) or (now - exercises[p.id]).days > 365
                ),
            }
            for p in rows
        ]
    }


@router.post("/continuity/plans", status_code=201, summary="Record a continuity plan")
def create_plan(
    payload: ContinuityPlanCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    if payload.bia_id:
        bia = db.get(BusinessImpactAnalysis, payload.bia_id)
        if bia is None or bia.tenant_id != principal.tenant_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "invalid_reference",
                        "message": "That business impact analysis does not exist.",
                    }
                },
            )
        if payload.rto_hours and bia.mtpd_hours and payload.rto_hours > bia.mtpd_hours:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "rto_exceeds_mtpd",
                        "message": (
                            f"The plan's recovery time objective ({payload.rto_hours}h) "
                            f"is longer than the maximum tolerable period of disruption "
                            f"({bia.mtpd_hours}h) in the linked analysis."
                        ),
                    }
                },
            )
    plan = ContinuityPlan(
        tenant_id=principal.tenant_id,
        name=payload.name,
        plan_type=payload.plan_type,
        scope=payload.scope or None,
        bia_id=payload.bia_id,
        rto_hours=payload.rto_hours,
        rpo_minutes=payload.rpo_minutes,
        strategy=payload.strategy or None,
        invocation_criteria=payload.invocation_criteria or None,
        response_team=payload.response_team,
        document_uri=payload.document_uri,
        next_review_at=utcnow() + timedelta(days=365),
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(plan)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="continuity.plan_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="continuity_plan",
        entity_id=plan.id,
        after_state={"name": plan.name, "type": plan.plan_type},
        request_id=request_id,
    )
    db.commit()
    return {"id": str(plan.id), "name": plan.name}


@router.post("/continuity/exercises", status_code=201, summary="Record a plan exercise")
def create_exercise(
    payload: ExerciseCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    """The exercise record is the evidence ISO 22301 clause 8.5 asks for, so it
    writes an evidence record as well as a register row."""
    plan = db.get(ContinuityPlan, payload.plan_id)
    if plan is None or plan.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such plan."}}
        )
    exercise = ContinuityExercise(
        tenant_id=principal.tenant_id,
        plan_id=plan.id,
        exercise_type=payload.exercise_type,
        scenario=payload.scenario or None,
        performed_at=payload.performed_at or utcnow(),
        participants=payload.participants,
        rto_achieved_hours=payload.rto_achieved_hours,
        rpo_achieved_minutes=payload.rpo_achieved_minutes,
        objectives_met=payload.objectives_met,
        findings=payload.findings,
        report_uri=payload.report_uri,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(exercise)
    db.flush()

    missed_rto = (
        payload.rto_achieved_hours is not None
        and plan.rto_hours is not None
        and float(payload.rto_achieved_hours) > plan.rto_hours
    )
    engine.record_evidence(
        db,
        tenant_id=principal.tenant_id,
        kind="report",
        title=f"Continuity exercise — {plan.name} ({payload.exercise_type})",
        payload={
            "plan": plan.name,
            "type": payload.exercise_type,
            "scenario": payload.scenario,
            "rto_target_hours": plan.rto_hours,
            "rto_achieved_hours": payload.rto_achieved_hours,
            "objectives_met": payload.objectives_met,
            "findings": payload.findings,
        },
        subject_type="continuity_plan",
        subject_id=plan.id,
        valid_days=365,
        created_by=principal.id,
    )
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="continuity.exercise_recorded",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="continuity_exercise",
        entity_id=exercise.id,
        after_state={
            "plan": plan.name,
            "objectives_met": payload.objectives_met,
            "rto_missed": missed_rto,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(exercise.id),
        "plan": plan.name,
        "rto_missed": missed_rto,
        "message": (
            "Recovery took longer than the plan's objective. Raise a gap against "
            "the continuity control so this is tracked to closure."
            if missed_rto
            else "Exercise recorded and attached to the plan as evidence."
        ),
    }


# ==========================================================================
# Privacy registers
# ==========================================================================
@router.get("/privacy/processing-records", summary="Record of processing activities (Art.30)")
def list_ropa(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(
        select(ProcessingRecord)
        .where(
            ProcessingRecord.tenant_id == principal.tenant_id,
            ProcessingRecord.is_deleted.is_(False),
        )
        .order_by(ProcessingRecord.name)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "business_function": r.business_function,
                "purpose": r.purpose,
                "lawful_basis": r.lawful_basis,
                "data_categories": r.data_categories,
                "international_transfers": r.international_transfers,
                "retention_rule": r.retention_rule,
                "dpia_required": r.dpia_required,
                "attested_at": r.attested_at.isoformat() if r.attested_at else None,
                "attestation_stale": bool(
                    not r.attested_at or (utcnow() - r.attested_at).days > 365
                ),
            }
            for r in rows
        ]
    }


@router.post("/privacy/processing-records", status_code=201, summary="Add a processing record")
def create_ropa(
    payload: ProcessingRecordCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    record = ProcessingRecord(
        tenant_id=principal.tenant_id,
        name=payload.name,
        business_function=payload.business_function or None,
        purpose=payload.purpose,
        lawful_basis=payload.lawful_basis,
        special_category_basis=payload.special_category_basis,
        data_subjects=payload.data_subjects,
        data_categories=payload.data_categories,
        recipients=payload.recipients,
        international_transfers=payload.international_transfers,
        retention_rule=payload.retention_rule or None,
        security_measures=payload.security_measures or None,
        dpia_required=payload.dpia_required,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(record)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="privacy.processing_record_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="processing_record",
        entity_id=record.id,
        after_state={"name": record.name, "lawful_basis": record.lawful_basis},
        request_id=request_id,
    )
    db.commit()
    return {"id": str(record.id), "name": record.name}


@router.get("/privacy/dsar", summary="Subject requests and their statutory clocks")
def list_dsar(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(
        select(DsarRequest)
        .where(DsarRequest.tenant_id == principal.tenant_id, DsarRequest.is_deleted.is_(False))
        .order_by(DsarRequest.sla_due_at.nulls_last())
    ).scalars().all()
    now = utcnow()
    return {
        "data": [
            {
                "id": str(r.id),
                "ref": r.request_ref,
                "request_type": r.request_type,
                "status": r.status,
                "received_at": r.received_at.isoformat(),
                "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
                "days_remaining": (r.sla_due_at - now).days if r.sla_due_at else None,
                "overdue": bool(
                    r.sla_due_at and r.sla_due_at < now and r.status != "released"
                ),
                "id_verified": r.id_verified,
            }
            for r in rows
        ]
    }


@router.post("/privacy/dsar", status_code=201, summary="Log a subject request")
def create_dsar(
    payload: DsarCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    received = payload.received_at or utcnow()
    count = db.execute(
        select(func.count(DsarRequest.id)).where(DsarRequest.tenant_id == principal.tenant_id)
    ).scalar_one()
    record = DsarRequest(
        tenant_id=principal.tenant_id,
        request_ref=f"DSAR-{count + 1:04d}",
        subject_ref=payload.subject_ref,
        request_type=payload.request_type,
        received_at=received,
        sla_due_at=received + timedelta(days=DSAR_RESPONSE_DAYS),
        status="received",
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(record)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="privacy.dsar_logged",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="dsar_request",
        entity_id=record.id,
        after_state={
            "ref": record.request_ref,
            "type": record.request_type,
            "due": record.sla_due_at.isoformat(),
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(record.id),
        "ref": record.request_ref,
        "sla_due_at": record.sla_due_at.isoformat(),
        "message": (
            f"The statutory response deadline is {record.sla_due_at.date()}. "
            "Verify the requester's identity before searching the estate."
        ),
    }


@router.get("/incidents", summary="List incidents")
def list_incidents(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(
        select(Incident)
        .where(Incident.tenant_id == principal.tenant_id, Incident.is_deleted.is_(False))
        .order_by(Incident.created_at.desc())
        .limit(200)
    ).scalars().all()
    breaches = {
        b.incident_id: b
        for b in db.execute(
            select(Breach).where(Breach.tenant_id == principal.tenant_id)
        ).scalars().all()
        if b.incident_id
    }
    now = utcnow()
    out = []
    for i in rows:
        breach = breaches.get(i.id)
        out.append(
            {
                "id": str(i.id),
                "incident_no": i.incident_no,
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "incident_type": i.incident_type,
                "involves_personal_data": i.involves_personal_data,
                "detected_at": i.detected_at.isoformat() if i.detected_at else None,
                "breach": None
                if not breach
                else {
                    "id": str(breach.id),
                    "notify_due_at": breach.notify_due_at.isoformat()
                    if breach.notify_due_at
                    else None,
                    "hours_remaining": round(
                        (breach.notify_due_at - now).total_seconds() / 3600, 1
                    )
                    if breach.notify_due_at
                    else None,
                    "regulator_notified": bool(breach.regulator_notified_at),
                },
            }
        )
    return {"data": out}


@router.post("/incidents", status_code=201, summary="Raise an incident")
def create_incident(
    payload: IncidentCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("data.register.write")),
) -> dict:
    """Where personal data is involved, the 72-hour clock starts here.

    Starting it automatically is deliberate: the deadline runs from awareness,
    and awareness is the moment the incident is recorded, not the moment
    someone remembers to open a breach record.
    """
    count = db.execute(
        select(func.count(Incident.id)).where(Incident.tenant_id == principal.tenant_id)
    ).scalar_one()
    detected = payload.detected_at or utcnow()
    incident = Incident(
        tenant_id=principal.tenant_id,
        incident_no=f"INC-{count + 1:04d}",
        title=payload.title,
        description=payload.description or None,
        incident_type=payload.incident_type,
        severity=Severity(payload.severity),
        status=IncidentStatus.RECORDED,
        detected_at=detected,
        involves_personal_data=payload.involves_personal_data,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(incident)
    db.flush()

    breach_id = None
    if payload.involves_personal_data:
        breach = Breach(
            tenant_id=principal.tenant_id,
            incident_id=incident.id,
            summary=payload.title,
            risk_to_individuals="unknown",
            clock_started_at=detected,
            notify_due_at=detected + timedelta(hours=BREACH_NOTIFY_HOURS),
            created_at=utcnow(),
            created_by=principal.id,
        )
        db.add(breach)
        db.flush()
        breach_id = str(breach.id)
        publish(
            db,
            tenant_id=principal.tenant_id,
            topic="breach.detected",
            payload={
                "incident_no": incident.incident_no,
                "breach_id": breach_id,
                "notify_due_at": breach.notify_due_at.isoformat(),
            },
            request_id=request_id,
        )

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="incident.created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="incident",
        entity_id=incident.id,
        after_state={
            "incident_no": incident.incident_no,
            "severity": incident.severity.value,
            "personal_data": payload.involves_personal_data,
        },
        request_id=request_id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="incident.created",
        payload={"incident_id": str(incident.id), "incident_no": incident.incident_no},
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(incident.id),
        "incident_no": incident.incident_no,
        "breach_id": breach_id,
        "message": (
            f"Personal data is involved, so the {BREACH_NOTIFY_HOURS}-hour "
            "notification clock has started. Assess the risk to individuals and "
            "take the notification decision to the DPO."
            if breach_id
            else "Incident recorded."
        ),
    }
