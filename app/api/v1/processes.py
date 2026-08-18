"""The process repository, the agent registry and AI oversight.

Three questions this exists to answer, none of which the platform could answer
before:

  * which process discharges a given clause, and which clause nothing discharges
  * what each agent is allowed to do, who is accountable for it, and what it refuses
  * whether human oversight of the AI is real or nominal

The last is the one an AI regulator or an assurance questionnaire will actually
probe. An organisation that automates compliance with AI and cannot evidence
the governance of that AI is arguing against itself.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.agents import registry
from app.api.deps import DbSession, requires
from app.models.audit import AuditLog
from app.models.base import GateDecision, utcnow
from app.models.compliance import Framework, FrameworkControl
from app.models.core import ApprovalGate
from app.models.llm import ModelInvocation
from app.processes import (
    DOMAIN_BY_CODE,
    DOMAINS,
    PROCESS_BY_CODE,
    PROCESSES,
    Automation,
    clause_coverage,
    statistics,
)

router = APIRouter(prefix="/processes", tags=["Process repository"])


@router.get("", summary="The process repository")
def list_processes(
    _=Depends(requires("data.register.read")),
    domain: Optional[str] = None,
    framework: Optional[str] = None,
) -> dict:
    processes = PROCESSES
    if domain:
        processes = tuple(p for p in processes if p.domain == domain.upper())
    if framework:
        processes = tuple(p for p in processes if framework in p.clauses)
    return {
        "statistics": statistics(),
        "domains": [
            {
                "code": d.code,
                "name": d.name,
                "purpose": d.purpose,
                "owner_role": d.owner_role,
                "process_count": len(d.processes),
            }
            for d in DOMAINS
        ],
        "data": [
            {
                "code": p.code,
                "name": p.name,
                "domain": p.domain,
                "domain_name": DOMAIN_BY_CODE[p.domain].name,
                "purpose": p.purpose,
                "owner_role": p.owner_role,
                "trigger": p.trigger,
                "cadence": p.cadence.value,
                "autonomy_tier": p.autonomy_tier,
                "clauses": {k: list(v) for k, v in p.clauses.items()},
                "activity_count": len(p.activities),
                "gate_count": len(p.gates),
                "unattended_rate": p.automation_rate,
                "kpis": list(p.kpis),
            }
            for p in processes
        ],
    }


@router.get("/coverage", summary="Which process discharges which clause")
def coverage(
    db: DbSession,
    principal=Depends(requires("rpt.dashboard.view")),
    framework: Optional[str] = None,
) -> dict:
    """Coverage in both directions.

    Claimed but unmapped matters as much as unclaimed: a process asserting it
    discharges a clause the catalogue does not contain is either a typo or a
    misunderstanding, and both are worth finding before an auditor does.
    """
    mapped = clause_coverage()
    frameworks = [framework] if framework else sorted(mapped)
    out = []

    for code in frameworks:
        catalogue = db.execute(
            select(FrameworkControl.ref_code)
            .join(Framework, Framework.id == FrameworkControl.framework_id)
            .where(Framework.code == code)
        ).scalars().all()
        catalogue_set = set(catalogue)
        claimed = mapped.get(code, {})

        # A process claiming "Annex A" covers the whole annex; expand it so the
        # arithmetic below is not distorted by a shorthand.
        expanded = set()
        for ref in claimed:
            if ref == "Annex A":
                expanded |= {c for c in catalogue_set if c.startswith("A.")}
            else:
                expanded.add(ref)

        uncovered = sorted(catalogue_set - expanded)
        unmatched = sorted(r for r in claimed if r not in catalogue_set and r != "Annex A")
        out.append(
            {
                "framework": code,
                "catalogue_size": len(catalogue_set),
                "clauses_claimed": len(expanded),
                "covered": len(catalogue_set & expanded),
                "coverage_pct": round(len(catalogue_set & expanded) / len(catalogue_set) * 100, 1)
                if catalogue_set
                else 0.0,
                "uncovered": uncovered[:100],
                "uncovered_count": len(uncovered),
                "claimed_but_not_in_catalogue": unmatched,
                "by_clause": {
                    ref: processes for ref, processes in sorted(claimed.items())
                },
            }
        )
    return {"data": out}


@router.get("/{code}", summary="One process in full")
def get_process(code: str, _=Depends(requires("data.register.read"))) -> dict:
    process = PROCESS_BY_CODE.get(code.upper())
    if process is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"No process {code}."}},
        )
    return {
        "code": process.code,
        "name": process.name,
        "domain": process.domain,
        "purpose": process.purpose,
        "owner_role": process.owner_role,
        "trigger": process.trigger,
        "cadence": process.cadence.value,
        "autonomy_tier": process.autonomy_tier,
        "clauses": {k: list(v) for k, v in process.clauses.items()},
        "kpis": list(process.kpis),
        "notes": process.notes,
        "unattended_rate": process.automation_rate,
        "activities": [
            {
                "code": a.code,
                "what": a.what,
                "responsible": a.responsible,
                "accountable": a.accountable,
                "trigger": a.trigger,
                "inputs": list(a.inputs),
                "outputs": list(a.outputs),
                "automation": a.automation.value,
                "agent": a.agent,
                "ai_role": a.ai_role,
                "min_confidence": a.min_confidence,
                "is_gate": a.automation is Automation.GATE,
                "gate_type": a.gate_type,
                "gate_reason": a.gate_reason,
                "control_refs": list(a.control_refs),
                "evidence": list(a.evidence),
                "sla_hours": a.sla_hours,
            }
            for a in process.activities
        ],
    }


# ==========================================================================
# Agents
# ==========================================================================
agent_router = APIRouter(prefix="/agents", tags=["AI agents"])


@agent_router.get("", summary="The agent registry")
def list_agents(_=Depends(requires("data.register.read"))) -> dict:
    return {
        "statistics": registry.statistics(),
        "data": [
            {
                "key": a.key,
                "name": a.name,
                "purpose": a.purpose,
                "accountable_role": a.accountable_role,
                "autonomy_tier": a.autonomy.value,
                "permissions": list(a.permissions),
                "task_classes": list(a.task_classes),
                "tools": list(a.tools),
                "refuses": list(a.refuses),
                "escalates_below_confidence": a.escalates_below_confidence,
                "processes": list(a.processes),
                "notes": a.notes,
                "holds_approval_authority": False,
            }
            for a in registry.AGENTS
        ],
        "note": (
            "No agent holds approval authority. This is structural: the "
            "registry refuses to construct an agent with a gate permission, and "
            "the gate check refuses a non-human principal independently."
        ),
    }


@agent_router.get("/{key}", summary="One agent")
def get_agent(key: str, _=Depends(requires("data.register.read"))) -> dict:
    agent = registry.AGENT_BY_KEY.get(key)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": f"No agent '{key}'."}},
        )
    activities = [
        {
            "process": p.code,
            "process_name": p.name,
            "activity": a.code,
            "what": a.what,
            "automation": a.automation.value,
            "ai_role": a.ai_role,
        }
        for p in PROCESSES
        for a in p.agent_activities
        if a.agent == key
    ]
    return {
        "key": agent.key,
        "name": agent.name,
        "purpose": agent.purpose,
        "accountable_role": agent.accountable_role,
        "autonomy_tier": agent.autonomy.value,
        "permissions": list(agent.permissions),
        "task_classes": list(agent.task_classes),
        "tools": list(agent.tools),
        "refuses": list(agent.refuses),
        "escalates_below_confidence": agent.escalates_below_confidence,
        "notes": agent.notes,
        "activities": activities,
        "activity_count": len(activities),
    }


# ==========================================================================
# AI oversight — PR-AIG-02
# ==========================================================================
oversight_router = APIRouter(prefix="/ai-oversight", tags=["AI governance"])


@oversight_router.get("", summary="Is human oversight of the AI real or nominal?")
def oversight(
    db: DbSession,
    days: int = Query(default=30, ge=1, le=365),
    principal=Depends(requires("rpt.dashboard.view")),
) -> dict:
    """Measures whether the humans in the loop are actually exercising judgement.

    Oversight that is recorded but not exercised is the failure this exists to
    catch, and it is invisible in a control test that only asks whether an
    approval step exists. Two signals: an approval rate at or near 100%, and
    decisions taken faster than the material could have been read.
    """
    since = utcnow() - timedelta(days=days)
    tenant_id = principal.tenant_id

    invocations = db.execute(
        select(
            ModelInvocation.task_class,
            func.count(ModelInvocation.id),
            func.avg(ModelInvocation.confidence),
            func.sum(func.coalesce(ModelInvocation.cost, 0)),
        )
        .where(
            ModelInvocation.tenant_id == tenant_id,
            ModelInvocation.created_at >= since,
            ModelInvocation.outcome == "ok",
        )
        .group_by(ModelInvocation.task_class)
    ).all()

    decided = db.execute(
        select(ApprovalGate)
        .where(
            ApprovalGate.tenant_id == tenant_id,
            ApprovalGate.decided_at.isnot(None),
            ApprovalGate.decided_at >= since,
        )
    ).scalars().all()

    approved = sum(1 for g in decided if g.decision is GateDecision.APPROVED)
    rejected = sum(1 for g in decided if g.decision is GateDecision.REJECTED)
    considered = [
        (g.decided_at - g.raised_at).total_seconds()
        for g in decided
        if g.decided_at and g.raised_at
    ]
    median_seconds = (
        sorted(considered)[len(considered) // 2] if considered else None
    )
    # Under a minute is not a review of an assessment; it is a click.
    hasty = sum(1 for s in considered if s < 60)

    findings: list[str] = []
    if decided and rejected == 0 and len(decided) >= 10:
        findings.append(
            f"All {len(decided)} decisions in this window were approvals. An "
            "approval rate of 100% over a meaningful sample usually indicates "
            "review is nominal rather than that nothing was ever wrong."
        )
    if considered and hasty / len(considered) > 0.5:
        findings.append(
            f"{hasty} of {len(considered)} decisions were taken within a minute "
            "of the gate being raised, which is less time than the material "
            "takes to read."
        )
    low_confidence = [
        {"task_class": t, "average_confidence": round(float(c), 3)}
        for t, n, c, _cost in invocations
        if c is not None and float(c) < 0.7
    ]
    if low_confidence:
        findings.append(
            "Average model confidence is below 0.70 for "
            f"{', '.join(t['task_class'] for t in low_confidence)}. Output at "
            "that level should be escalating, not accumulating."
        )

    return {
        "window_days": days,
        "agents_registered": len(registry.AGENTS),
        "gate_decisions": {
            "total": len(decided),
            "approved": approved,
            "rejected": rejected,
            "rejection_rate": round(rejected / len(decided), 3) if decided else None,
            "median_seconds_to_decide": round(median_seconds) if median_seconds else None,
            "decided_within_a_minute": hasty,
        },
        "model_use": [
            {
                "task_class": task_class,
                "calls": calls,
                "average_confidence": round(float(confidence), 3) if confidence else None,
                "cost": round(float(cost or 0), 4),
            }
            for task_class, calls, confidence, cost in invocations
        ],
        "findings": findings,
        "interpretation": (
            "No oversight concerns detected in this window."
            if not findings
            else "Human oversight may be nominal in the areas listed. "
            "See PR-AIG-02, which owns this control."
        ),
    }


@oversight_router.get("/decisions", summary="Every AI-influenced decision and who took it")
def ai_decisions(
    db: DbSession,
    days: int = Query(default=30, ge=1, le=365),
    principal=Depends(requires("sec.auditlog.read")),
) -> dict:
    """The record an AI auditor asks for: which model, which prompt version,
    which sources, and which named person owned the outcome."""
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == principal.tenant_id,
            AuditLog.created_at >= since,
            AuditLog.model.isnot(None),
        )
        .order_by(AuditLog.seq.desc())
        .limit(500)
    ).scalars().all()
    return {
        "window_days": days,
        "count": len(rows),
        "data": [
            {
                "seq": r.seq,
                "at": r.created_at.isoformat(),
                "action": r.action,
                "actor": r.actor_ref,
                "actor_type": r.actor_type.value,
                "entity": r.entity,
                "model": r.model,
                "prompt_version": r.prompt_version,
                "sources": r.sources,
                "confidence": (r.detail or {}).get("confidence"),
                "row_hash": r.row_hash[:16],
            }
            for r in rows
        ],
    }
