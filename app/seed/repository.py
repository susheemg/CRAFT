"""Materialise the process repository and the agent registry into the database.

The repository in :mod:`app.processes` is the specification. This module makes
it executable: each process becomes a workflow the engine can run, each
activity becomes a step with its automation level and gate, and each agent
becomes a service principal with exactly the permissions its scope needs and
none that would let it approve anything.

Two rules are enforced here rather than assumed:

  * **A per-agent role.** Each agent gets its own role carrying only its
    declared permissions, instead of everything sharing one broad "AI Agent"
    role. If the privacy agent is compromised or misconfigured, its reach is
    the privacy agent's reach.
  * **Version on change.** A workflow whose definition has changed gets a new
    version rather than a silent edit, because a run that has already executed
    was executed against a particular definition, and an auditor will ask which.

Loading is idempotent. Running it twice changes nothing.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.registry import AGENTS, Agent
from app.models.base import (
    ActorType,
    AutomationLevel,
    AutonomyTier,
    GateReason,
    utcnow,
)
from app.models.core import Activity as ActivityRow
from app.models.core import Workflow
from app.models.iam import (
    AgentIdentity,
    Permission,
    Role,
    RoleGrant,
    RolePermission,
    Tenant,
)
from app.processes import (
    DOMAIN_BY_CODE,
    PROCESSES,
    Automation,
    Process,
)
from app.security.crypto import canonical_hash

log = logging.getLogger(__name__)

# The repository's automation vocabulary maps onto the engine's, except for
# MANUAL, which the engine expresses as an assisted step with no agent: the
# platform still records it, a person still performs it.
_AUTOMATION = {
    Automation.MANUAL: AutomationLevel.ASSIST,
    Automation.ASSIST: AutomationLevel.ASSIST,
    Automation.AUTO_NOTIFY: AutomationLevel.AUTO_NOTIFY,
    Automation.AUTO: AutomationLevel.AUTO,
    Automation.GATE: AutomationLevel.GATE,
}


def _definition(process: Process) -> dict:
    """The stored, hashable form of a process.

    Everything an auditor would need to know about how the process was defined
    when a given run executed, and nothing that changes between loads.
    """
    return {
        "code": process.code,
        "name": process.name,
        "domain": process.domain,
        "purpose": process.purpose,
        "trigger": process.trigger,
        "cadence": process.cadence.value,
        "owner_role": process.owner_role,
        "clauses": {k: list(v) for k, v in sorted(process.clauses.items())},
        "kpis": list(process.kpis),
        "notes": process.notes,
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
                "task_class": a.task_class,
                "min_confidence": a.min_confidence,
                "gate_type": a.gate_type,
                "gate_reason": a.gate_reason,
                "control_refs": list(a.control_refs),
                "evidence": list(a.evidence),
                "sla_hours": a.sla_hours,
            }
            for a in process.activities
        ],
    }


def _role_for_agent(db: Session, agent: Agent) -> Role:
    """One role per agent, carrying only what that agent's scope needs."""
    name = f"Agent — {agent.name}"
    role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
    if role is None:
        role = Role(
            name=name,
            description=(
                f"{agent.purpose} Accountable role: {agent.accountable_role}. "
                f"Autonomy tier {agent.autonomy.value}. Holds no approval authority."
            ),
            is_system=True,
            agent_eligible=True,
            created_at=utcnow(),
        )
        db.add(role)
        db.flush()

    permissions = {
        p.code: p
        for p in db.execute(
            select(Permission).where(Permission.code.in_(agent.permissions))
        ).scalars().all()
    }
    missing = set(agent.permissions) - set(permissions)
    if missing:
        raise RuntimeError(
            f"Agent '{agent.key}' needs permissions that are not in the catalogue: "
            f"{', '.join(sorted(missing))}"
        )

    held = {
        rp.permission_id
        for rp in db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        ).scalars().all()
    }
    for permission in permissions.values():
        if permission.id not in held:
            db.add(
                RolePermission(role_id=role.id, permission_id=permission.id, scope="all")
            )
    db.flush()
    return role


def load_agents(db: Session, tenant: Tenant) -> dict:
    """Provision a service principal per agent, scoped to its own role."""
    created, updated = 0, 0
    for agent in AGENTS:
        role = _role_for_agent(db, agent)
        identity = db.execute(
            select(AgentIdentity).where(
                AgentIdentity.tenant_id == tenant.id,
                AgentIdentity.agent_key == agent.key,
            )
        ).scalar_one_or_none()

        if identity is None:
            identity = AgentIdentity(
                tenant_id=tenant.id,
                agent_key=agent.key,
                display_name=agent.name,
                autonomy_tier=AutonomyTier(agent.autonomy.value),
                guardrail_profile=agent.key,
                status="active",
                created_at=utcnow(),
            )
            db.add(identity)
            db.flush()
            created += 1
        else:
            # An autonomy change is governed by PR-AIG-02 and gated. The loader
            # keeps the record in step with the registry but never widens
            # authority on its own: permissions come from the role.
            if identity.autonomy_tier.value != agent.autonomy.value:
                identity.autonomy_tier = AutonomyTier(agent.autonomy.value)
                updated += 1
            identity.display_name = agent.name

        exists = db.execute(
            select(RoleGrant).where(
                RoleGrant.principal_id == identity.id, RoleGrant.role_id == role.id
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                RoleGrant(
                    tenant_id=tenant.id,
                    principal_id=identity.id,
                    principal_type=ActorType.AGENT,
                    role_id=role.id,
                    scope="all",
                    granted_at=utcnow(),
                    justification=(
                        f"Provisioned from the agent registry. Scope: {agent.purpose[:200]}"
                    ),
                )
            )
    db.flush()
    return {"agents_created": created, "agents_retiered": updated}


def load_processes(db: Session, tenant: Tenant) -> dict:
    """Materialise every process as an executable workflow."""
    roles = {r.name: r for r in db.execute(select(Role)).scalars().all()}
    created, versioned, unchanged = 0, 0, 0

    for process in PROCESSES:
        definition = _definition(process)
        digest = canonical_hash(definition)

        existing = db.execute(
            select(Workflow)
            .where(Workflow.tenant_id == tenant.id, Workflow.wf_code == process.code)
            .order_by(Workflow.version.desc())
        ).scalars().first()

        if existing is not None and (existing.definition or {}).get("_hash") == digest:
            unchanged += 1
            continue

        version = 1
        if existing is not None:
            # Supersede rather than edit. Runs already executed against the old
            # definition, and the audit trail has to be able to say which.
            existing.status = "superseded"
            version = existing.version + 1
            versioned += 1
        else:
            created += 1

        owner = roles.get(process.owner_role)
        workflow = Workflow(
            tenant_id=tenant.id,
            wf_code=process.code,
            name=process.name,
            family=process.domain,
            pillars=_pillars(process),
            autonomy_tier=AutonomyTier(process.autonomy_tier),
            owner_role_id=owner.id if owner else None,
            version=version,
            status="active",
            definition={**definition, "_hash": digest},
            created_at=utcnow(),
        )
        db.add(workflow)
        db.flush()

        for seq, activity in enumerate(process.activities, start=1):
            accountable = roles.get(activity.accountable)
            db.add(
                ActivityRow(
                    workflow_id=workflow.id,
                    seq=seq,
                    act_code=activity.code,
                    what=activity.what,
                    who_responsible={
                        "actor": "agent" if activity.agent else activity.responsible,
                        "agent_key": activity.agent,
                        "role": activity.responsible,
                    },
                    who_accountable_role_id=accountable.id if accountable else None,
                    when_trigger=activity.trigger,
                    input_refs={"inputs": list(activity.inputs)},
                    output_refs={
                        "outputs": list(activity.outputs),
                        "evidence": list(activity.evidence),
                    },
                    ai_role=activity.ai_role,
                    task_class=activity.task_class,
                    automation=_AUTOMATION[activity.automation],
                    control_ref=_control_ref(activity),
                    is_gate=activity.automation is Automation.GATE,
                    gate_type=activity.gate_type,
                    gate_reason=GateReason(activity.gate_reason)
                    if activity.gate_reason
                    else None,
                )
            )
    db.flush()
    return {
        "workflows_created": created,
        "workflows_versioned": versioned,
        "workflows_unchanged": unchanged,
    }


def _pillars(process: Process) -> list[str]:
    """Map framework coverage onto the platform's compliance pillars."""
    mapping = {"iso27001": "security", "iso22301": "bcp", "uk_gdpr": "gdpr"}
    return sorted({mapping[f] for f in process.clauses if f in mapping})


def _control_ref(activity) -> dict:
    """The engine reads this to decide whether a step needs a gate.

    The four exception tests live here: an activity that is irreversible,
    statutory, high-risk or low-confidence stops for a person.
    """
    ref: dict = {}
    for control in activity.control_refs:
        framework, _, clause = control.partition(":")
        ref.setdefault(framework, []).append(clause or control)
    if activity.min_confidence is not None:
        ref["min_confidence"] = activity.min_confidence
    if activity.gate_reason:
        ref[activity.gate_reason] = True
    if activity.sla_hours:
        ref["sla_hours"] = activity.sla_hours
    return ref


def load(db: Session, tenant: Tenant) -> dict:
    """Load the whole repository. Idempotent."""
    from app.processes import validate as validate_processes
    from app.agents.registry import validate as validate_agents

    problems = validate_processes() + validate_agents()
    if problems:
        # Refusing to load a repository that does not hold together is the point.
        # A workflow referencing an agent that cannot perform it fails at the
        # moment someone depends on it, which is the worst time to find out.
        raise RuntimeError(
            "The process repository does not validate; refusing to load:\n  - "
            + "\n  - ".join(problems)
        )

    summary = {**load_agents(db, tenant), **load_processes(db, tenant)}
    log.info(
        "Process repository loaded: %s workflows created, %s versioned, %s unchanged",
        summary["workflows_created"],
        summary["workflows_versioned"],
        summary["workflows_unchanged"],
    )
    return summary
