"""The workflow and gate engine.

A run walks the activities of a versioned workflow definition. For each
activity the engine resolves the actor, records a step, and then either
completes it automatically or raises a human approval gate and stops. Nothing
proceeds past an open gate.

Gates are inserted where the definition says ``automation='gate'`` and,
independently, wherever a control demands one. That second path is the point:
the maximum-automation directive never removes a control — where the two
conflict, the control wins and the step becomes a gate.

Every transition writes an audit row and every completed activity writes an
evidence record, so a run can be reconstructed from the log alone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import (
    ActorType,
    AutomationLevel,
    GateDecision,
    GateReason,
    RunStatus,
    utcnow,
)
from app.models.core import Activity, ActivityRun, ApprovalGate, EvidenceRecord, Run, Workflow
from app.security.auth import Principal
from app.security.crypto import canonical_hash
from app.services import audit
from app.services.outbox import publish


class EngineError(Exception):
    code = "engine_error"


class GateOpen(EngineError):
    code = "gate_open"


@dataclass
class StepResult:
    run: Run
    activity_run: ActivityRun | None
    gate: ApprovalGate | None
    finished: bool

    @property
    def awaiting_gate(self) -> bool:
        return self.gate is not None and self.gate.decision == GateDecision.PENDING


def _workflow_activities(db: Session, workflow_id: uuid.UUID) -> list[Activity]:
    return list(
        db.execute(
            select(Activity).where(Activity.workflow_id == workflow_id).order_by(Activity.seq)
        ).scalars().all()
    )


def start_run(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    workflow_code: str,
    principal: Principal,
    context: dict | None = None,
    trigger_source: str = "manual",
    subject_ref: str | None = None,
    sla_days: int | None = None,
) -> Run:
    workflow = db.execute(
        select(Workflow)
        .where(
            Workflow.tenant_id == tenant_id,
            Workflow.wf_code == workflow_code,
            Workflow.status == "active",
        )
        .order_by(Workflow.version.desc())
    ).scalars().first()
    if workflow is None:
        raise EngineError(
            f"No active workflow with code '{workflow_code}'. Deploy it first."
        )

    run = Run(
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        wf_version=workflow.version,
        trigger_source=trigger_source,
        initiated_by=principal.id,
        status=RunStatus.RUNNING,
        started_at=utcnow(),
        sla_due_at=utcnow() + timedelta(days=sla_days) if sla_days else None,
        context=context or {},
        subject_ref=subject_ref,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(run)
    db.flush()

    audit.record(
        db,
        tenant_id=tenant_id,
        action="run.started",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="run",
        entity_id=run.id,
        detail={"workflow": workflow_code, "version": workflow.version,
                "trigger": trigger_source},
    )
    publish(db, tenant_id=tenant_id, topic="run.started",
            payload={"run_id": str(run.id), "workflow": workflow_code})
    return run


def _needs_gate(activity: Activity, confidence: float | None) -> GateReason | None:
    """The four exception tests. Any one of them makes the step a gate."""
    if activity.is_gate or activity.automation == AutomationLevel.GATE:
        return activity.gate_reason or GateReason.HIGH_RISK
    control = activity.control_ref or {}
    if control.get("irreversible"):
        return GateReason.IRREVERSIBLE
    if control.get("statutory"):
        return GateReason.STATUTORY
    if control.get("high_risk"):
        return GateReason.HIGH_RISK
    if confidence is not None and confidence < float(control.get("min_confidence", 0.7)):
        return GateReason.LOW_CONFIDENCE
    return None


def execute_next(
    db: Session,
    run: Run,
    principal: Principal,
    *,
    output: dict | None = None,
    confidence: float | None = None,
) -> StepResult:
    """Advance the run by one activity."""
    if run.status in (RunStatus.COMPLETED, RunStatus.CANCELLED, RunStatus.FAILED):
        raise EngineError(f"Run is {run.status.value} and cannot advance.")

    open_gate = db.execute(
        select(ApprovalGate).where(
            ApprovalGate.run_id == run.id, ApprovalGate.decision == GateDecision.PENDING
        )
    ).scalars().first()
    if open_gate:
        raise GateOpen(
            "This run is waiting on an approval gate. Decide the gate before continuing."
        )

    activities = _workflow_activities(db, run.workflow_id)
    done = {
        ar.activity_id
        for ar in db.execute(
            select(ActivityRun).where(
                ActivityRun.run_id == run.id, ActivityRun.status == "done"
            )
        ).scalars().all()
    }
    remaining = [a for a in activities if a.id not in done]
    if not remaining:
        return complete_run(db, run, principal)

    activity = remaining[0]
    actor_type = (
        ActorType.HUMAN if activity.automation == AutomationLevel.ASSIST else principal.actor_type
    )
    step = ActivityRun(
        run_id=run.id,
        activity_id=activity.id,
        actor_type=actor_type,
        actor_ref=principal.actor_ref,
        status="pending",
        started_at=utcnow(),
        output=output,
        confidence=confidence,
    )
    db.add(step)
    db.flush()
    run.current_activity_id = activity.id

    reason = _needs_gate(activity, confidence)
    if reason:
        gate = raise_gate(
            db,
            run=run,
            activity_run=step,
            gate_type=activity.gate_type or "risk.approve",
            reason=reason,
            summary=activity.what[:400],
            context={"activity": activity.act_code, "output": output},
            approver_role_id=activity.who_accountable_role_id,
            requested_by=principal.id,
        )
        return StepResult(run=run, activity_run=step, gate=gate, finished=False)

    step.status = "done"
    step.ended_at = utcnow()
    record_evidence(
        db,
        tenant_id=run.tenant_id,
        run_id=run.id,
        activity_run_id=step.id,
        kind="activity_output",
        title=f"{activity.act_code}: {activity.what[:120]}",
        payload={"output": output or {}, "confidence": confidence},
        created_by=principal.id,
    )
    audit.record(
        db,
        tenant_id=run.tenant_id,
        action="activity.completed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="activity_run",
        entity_id=step.id,
        detail={"activity": activity.act_code, "run_id": str(run.id)},
    )
    db.flush()

    if len(remaining) == 1:
        return complete_run(db, run, principal)
    return StepResult(run=run, activity_run=step, gate=None, finished=False)


def complete_run(db: Session, run: Run, principal: Principal) -> StepResult:
    run.status = RunStatus.COMPLETED
    run.completed_at = utcnow()
    run.current_activity_id = None
    db.flush()
    audit.record(
        db,
        tenant_id=run.tenant_id,
        action="run.completed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="run",
        entity_id=run.id,
        detail={
            "within_sla": bool(
                run.sla_due_at is None or run.completed_at <= run.sla_due_at
            )
        },
    )
    publish(
        db,
        tenant_id=run.tenant_id,
        topic="run.completed",
        payload={"run_id": str(run.id), "status": "completed"},
    )
    return StepResult(run=run, activity_run=None, gate=None, finished=True)


def cancel_run(db: Session, run: Run, principal: Principal, reason: str) -> Run:
    run.status = RunStatus.CANCELLED
    run.completed_at = utcnow()
    db.flush()
    audit.record(
        db,
        tenant_id=run.tenant_id,
        action="run.cancelled",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="run",
        entity_id=run.id,
        detail={"reason": reason},
    )
    return run


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------
def raise_gate(
    db: Session,
    *,
    run: Run,
    activity_run: ActivityRun | None,
    gate_type: str,
    reason: GateReason,
    summary: str,
    context: dict | None = None,
    approver_role_id: uuid.UUID | None = None,
    requested_by: uuid.UUID | None = None,
    due_hours: int | None = None,
) -> ApprovalGate:
    gate = ApprovalGate(
        tenant_id=run.tenant_id,
        run_id=run.id,
        activity_run_id=activity_run.id if activity_run else None,
        gate_type=gate_type,
        reason=reason,
        summary=summary,
        context=context or {},
        approver_role_id=approver_role_id,
        requested_by=requested_by,
        decision=GateDecision.PENDING,
        raised_at=utcnow(),
        due_at=utcnow() + timedelta(hours=due_hours) if due_hours else None,
    )
    db.add(gate)
    run.status = RunStatus.AWAITING_GATE
    db.flush()

    audit.record(
        db,
        tenant_id=run.tenant_id,
        action="gate.raised",
        actor_type=ActorType.SYSTEM,
        actor_ref="engine",
        entity="approval_gate",
        entity_id=gate.id,
        detail={
            "gate_type": gate_type,
            "reason": reason.value,
            "run_id": str(run.id),
            "summary": summary[:200],
        },
    )
    publish(
        db,
        tenant_id=run.tenant_id,
        topic="gate.raised",
        payload={
            "gate_id": str(gate.id),
            "run_id": str(run.id),
            "gate_type": gate_type,
            "reason": reason.value,
        },
    )
    return gate


def decide_gate(
    db: Session,
    gate: ApprovalGate,
    principal: Principal,
    *,
    decision: GateDecision,
    rationale: str,
) -> ApprovalGate:
    """Record a human decision. Authorisation is asserted by the caller
    (``rbac.assert_gate_authority``) before this is reached."""
    if gate.decision != GateDecision.PENDING:
        raise EngineError(
            f"This gate was already {gate.decision.value} at "
            f"{gate.decided_at.isoformat() if gate.decided_at else 'an earlier time'}."
        )
    if decision == GateDecision.REJECTED and len(rationale.strip()) < 10:
        raise EngineError("A rejection needs a rationale the requester can act on.")

    before = {"decision": gate.decision.value}
    gate.decision = decision
    gate.rationale = rationale.strip() or None
    gate.approver_user_id = principal.id
    gate.decided_at = utcnow()
    db.flush()

    run = db.get(Run, gate.run_id)
    step = db.get(ActivityRun, gate.activity_run_id) if gate.activity_run_id else None
    if step:
        step.status = "done" if decision == GateDecision.APPROVED else "failed"
        step.ended_at = utcnow()
    if run:
        run.status = (
            RunStatus.RUNNING if decision == GateDecision.APPROVED else RunStatus.CANCELLED
        )
        if decision != GateDecision.APPROVED:
            run.completed_at = utcnow()

    record_evidence(
        db,
        tenant_id=gate.tenant_id,
        run_id=gate.run_id,
        activity_run_id=gate.activity_run_id,
        kind="approval_decision",
        title=f"{gate.gate_type} — {decision.value}",
        payload={
            "gate_type": gate.gate_type,
            "reason": gate.reason.value,
            "decision": decision.value,
            "rationale": gate.rationale,
            "approver": str(principal.id),
        },
        created_by=principal.id,
    )
    audit.record(
        db,
        tenant_id=gate.tenant_id,
        action="gate.decided",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="approval_gate",
        entity_id=gate.id,
        before_state=before,
        after_state={"decision": decision.value, "rationale": gate.rationale},
        detail={"gate_type": gate.gate_type, "run_id": str(gate.run_id)},
    )
    publish(
        db,
        tenant_id=gate.tenant_id,
        topic="gate.decided",
        payload={
            "gate_id": str(gate.id),
            "run_id": str(gate.run_id),
            "decision": decision.value,
            "gate_type": gate.gate_type,
        },
    )
    return gate


def pending_gates(
    db: Session, tenant_id: uuid.UUID, role_ids: list[uuid.UUID] | None = None
) -> list[ApprovalGate]:
    stmt = select(ApprovalGate).where(
        ApprovalGate.tenant_id == tenant_id, ApprovalGate.decision == GateDecision.PENDING
    )
    if role_ids:
        stmt = stmt.where(
            (ApprovalGate.approver_role_id.in_(role_ids))
            | (ApprovalGate.approver_role_id.is_(None))
        )
    return list(db.execute(stmt.order_by(ApprovalGate.raised_at)).scalars().all())


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------
def record_evidence(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    kind: str,
    title: str,
    payload: dict | None = None,
    artifact_uri: str | None = None,
    run_id: uuid.UUID | None = None,
    activity_run_id: uuid.UUID | None = None,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    lineage: dict | None = None,
    valid_days: int | None = None,
    created_by: uuid.UUID | None = None,
) -> EvidenceRecord:
    """Append an evidence record. Content-hashed and append-only.

    Exactly one of ``payload`` or ``artifact_uri`` is stored: large artefacts
    live in object storage, and the database keeps the pointer and the hash.
    """
    if (payload is None) == (artifact_uri is None):
        raise EngineError(
            "Evidence needs exactly one of an inline payload or an artefact URI."
        )
    digest = canonical_hash(payload if payload is not None else {"uri": artifact_uri})
    record = EvidenceRecord(
        tenant_id=tenant_id,
        run_id=run_id,
        activity_run_id=activity_run_id,
        subject_type=subject_type,
        subject_id=subject_id,
        kind=kind,
        title=title[:200],
        artifact_uri=artifact_uri,
        payload=payload,
        content_hash=bytes.fromhex(digest),
        lineage=lineage,
        collected_at=utcnow(),
        valid_until=utcnow() + timedelta(days=valid_days) if valid_days else None,
        created_at=utcnow(),
        created_by=created_by,
    )
    db.add(record)
    db.flush()
    return record
