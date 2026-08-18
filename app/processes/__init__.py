"""The process repository.

This is the authoritative description of how the organisation runs its
management systems. It is data rather than prose, for three reasons that matter
more than elegance:

  * **The engine executes it.** A process defined here is a process the
    platform can actually run, gate and evidence. A process manual that lives
    in a document drifts from what the organisation does; this cannot, because
    it *is* what the organisation does.
  * **Clause coverage is computable.** Every process declares the clauses it
    discharges, so "which requirement is nobody satisfying?" is a query rather
    than a workshop.
  * **The manuals are generated from it.** The SOP manual is rendered from this
    module, so the documented procedure and the executed procedure cannot
    disagree.

Structure:

    Domain          a coherent area of accountability with a single owner
      Process       a repeatable unit of work with a trigger and an outcome
        Activity    the five-part contract: what, who, when, input, output

Each activity also declares its automation level and, where AI participates,
which agent does the work and what it is allowed to conclude. Nothing here
grants an agent authority to decide; gates are named explicitly and always
resolve to a person.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Automation(StrEnum):
    """How much of the activity the platform performs unaided.

    The distinction that matters is between ASSIST and AUTO. ASSIST means the
    model produces a draft and a person owns the output; AUTO means the
    platform's output stands on its own. Anything whose result would be relied
    on by an auditor without further review must be AUTO only if it is
    deterministic — a query, a calculation, a scheduled check — not if it is a
    judgement.
    """

    MANUAL = "manual"            # a person does it; the platform records it
    ASSIST = "assist"            # the model drafts, a person owns the result
    AUTO_NOTIFY = "auto_notify"  # the platform does it and tells the owner
    AUTO = "auto"                # the platform does it unaided
    GATE = "gate"                # stops for a named human decision


class Cadence(StrEnum):
    EVENT = "event_driven"
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    TRIENNIAL = "triennial"


@dataclass(frozen=True)
class Activity:
    """One step. The five-part contract, plus its AI and control bindings."""

    code: str
    what: str
    responsible: str                     # role name or "agent"
    accountable: str                     # role name — always a person
    trigger: str = "sequence"
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    automation: Automation = Automation.AUTO
    agent: str | None = None             # agent key from app.agents.registry
    ai_role: str | None = None           # what the model is asked to conclude
    task_class: str | None = None        # routes to a model via the gateway
    min_confidence: float | None = None  # below this, the step escalates
    gate_type: str | None = None
    gate_reason: str | None = None       # irreversible | statutory | high_risk | low_confidence
    control_refs: tuple[str, ...] = ()   # framework refs this step evidences
    evidence: tuple[str, ...] = ()       # evidence records it must produce
    sla_hours: int | None = None

    def __post_init__(self) -> None:
        if self.automation is Automation.GATE and not self.gate_type:
            raise ValueError(f"{self.code}: a gate must name its gate_type")
        if self.agent and self.automation is Automation.MANUAL:
            raise ValueError(f"{self.code}: a manual activity cannot have an agent")


@dataclass(frozen=True)
class Process:
    """A repeatable unit of work with an owner, a trigger and an outcome."""

    code: str
    name: str
    domain: str
    purpose: str
    owner_role: str
    trigger: str
    cadence: Cadence
    activities: tuple[Activity, ...]
    # Clauses and articles this process discharges. The key is the framework
    # code; the value is the set of references. This is what makes coverage
    # computable rather than asserted.
    clauses: dict[str, tuple[str, ...]] = field(default_factory=dict)
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    kpis: tuple[str, ...] = ()
    autonomy_tier: str = "L3"
    notes: str = ""

    @property
    def gates(self) -> tuple[Activity, ...]:
        return tuple(a for a in self.activities if a.automation is Automation.GATE)

    @property
    def agent_activities(self) -> tuple[Activity, ...]:
        return tuple(a for a in self.activities if a.agent)

    @property
    def automation_rate(self) -> float:
        """Share of steps the platform performs without a person acting.

        Deliberately counts ASSIST as human work. A draft still needs someone to
        read it, and counting drafting as automation is how vendors arrive at
        implausible numbers.
        """
        if not self.activities:
            return 0.0
        unattended = sum(
            1 for a in self.activities
            if a.automation in {Automation.AUTO, Automation.AUTO_NOTIFY}
        )
        return round(unattended / len(self.activities), 3)


@dataclass(frozen=True)
class Domain:
    code: str
    name: str
    purpose: str
    owner_role: str
    processes: tuple[str, ...]


# --------------------------------------------------------------------------
# Domains — ten areas of accountability, each with one owner
# --------------------------------------------------------------------------
DOMAINS: tuple[Domain, ...] = (
    Domain(
        code="GOV",
        name="Governance and management system",
        purpose=(
            "Establishes context, scope, policy, objectives and leadership "
            "commitment, and closes the management-system loop through internal "
            "audit, management review and improvement."
        ),
        owner_role="CISO",
        processes=("PR-GOV-01", "PR-GOV-02", "PR-GOV-03", "PR-GOV-04", "PR-GOV-05"),
    ),
    Domain(
        code="RSK",
        name="Risk management",
        purpose=(
            "Identifies, assesses, treats and monitors risk to information, "
            "personal data and operational continuity on one register and one "
            "scale."
        ),
        owner_role="Risk Officer",
        processes=("PR-RSK-01", "PR-RSK-02", "PR-RSK-03"),
    ),
    Domain(
        code="CMP",
        name="Compliance and assurance",
        purpose=(
            "Maintains the control library, evidences control operation "
            "continuously, and keeps the organisation audit-ready rather than "
            "audit-reactive."
        ),
        owner_role="Control Owner",
        processes=("PR-CMP-01", "PR-CMP-02", "PR-CMP-03", "PR-CMP-04", "PR-CMP-05"),
    ),
    Domain(
        code="PRV",
        name="Privacy operations",
        purpose=(
            "Discharges the controller and processor duties: lawful basis, "
            "records of processing, individual rights, impact assessments, "
            "transfers and breach notification."
        ),
        owner_role="DPO",
        processes=("PR-PRV-01", "PR-PRV-02", "PR-PRV-03", "PR-PRV-04", "PR-PRV-05"),
    ),
    Domain(
        code="SEC",
        name="Security operations",
        purpose=(
            "Detects, triages and resolves security events, and manages "
            "vulnerabilities and technical hygiene."
        ),
        owner_role="CISO",
        processes=("PR-SEC-01", "PR-SEC-02", "PR-SEC-03"),
    ),
    Domain(
        code="TPR",
        name="Third-party risk",
        purpose=(
            "Assesses, approves, contracts and monitors suppliers in proportion "
            "to the risk each engagement actually carries."
        ),
        owner_role="Control Owner",
        processes=("PR-TPR-01", "PR-TPR-02", "PR-TPR-03"),
    ),
    Domain(
        code="RES",
        name="Operational resilience",
        purpose=(
            "Understands what the organisation must be able to keep doing, how "
            "quickly it must recover, and proves it can."
        ),
        owner_role="Control Owner",
        processes=("PR-RES-01", "PR-RES-02", "PR-RES-03", "PR-RES-04"),
    ),
    Domain(
        code="PPL",
        name="People and access",
        purpose=(
            "Manages the identity lifecycle, entitlement, awareness and the "
            "human-factor controls around them."
        ),
        owner_role="Security Admin",
        processes=("PR-PPL-01", "PR-PPL-02", "PR-PPL-03"),
    ),
    Domain(
        code="CHG",
        name="Change and secure development",
        purpose=(
            "Governs change to systems and services so that security, privacy "
            "and continuity requirements are met before, not after, release."
        ),
        owner_role="Control Owner",
        processes=("PR-CHG-01", "PR-CHG-02"),
    ),
    Domain(
        code="APS",
        name="Application security",
        purpose=(
            "Runs ISO/IEC 27034: maintains the Organization Normative Framework "
            "and its Application Security Control library, and applies that "
            "library to each application project through a targeted and an "
            "actual level of trust. Added because securing an application is a "
            "different discipline from securing an organisation, and the "
            "existing change domain governs release, not control design."
        ),
        owner_role="CISO",
        processes=(
            "PR-APS-01", "PR-APS-02", "PR-APS-03", "PR-APS-04", "PR-APS-05",
            "PR-APS-06", "PR-APS-07", "PR-APS-08", "PR-APS-09", "PR-APS-10",
        ),
    ),
    Domain(
        code="AIG",
        name="AI governance",
        purpose=(
            "Governs the organisation's own use of AI — including this "
            "platform's agents — as a controlled activity with an inventory, "
            "risk classification, human oversight and post-market monitoring. "
            "Added because a platform that automates compliance with AI must be "
            "able to evidence the governance of that AI."
        ),
        owner_role="CISO",
        processes=(
            "PR-AIG-01", "PR-AIG-02", "PR-AIG-03", "PR-AIG-04", "PR-AIG-05",
            "PR-AIG-06", "PR-AIG-07", "PR-AIG-08", "PR-AIG-09", "PR-AIG-10",
            "PR-AIG-11", "PR-AIG-12",
        ),
    ),
)

DOMAIN_BY_CODE = {d.code: d for d in DOMAINS}


# --------------------------------------------------------------------------
# Shared clause inheritance across the Annex SL standards
# --------------------------------------------------------------------------
# ISO 22301, ISO/IEC 27001 and ISO/IEC 42001 all sit on the Annex SL harmonised
# structure, so a process that establishes context, assigns roles, runs an
# internal audit or handles a nonconformity discharges the same requirement in
# all three. Running that work once and mapping the evidence three ways is the
# largest saving available from an integrated management system.
#
# The saving is only legitimate for clauses that are genuinely common. The
# exclusions below are the ones an assessor probes first, and each is excluded
# for a specific reason rather than out of caution:
#
#   5.2   Policy. ISO/IEC 42001 5.2 is the *AI* policy, and an information
#         security policy is not one. PR-AIG-04 owns it.
#   6.1.2 / 6.1.3 / 8.2 / 8.3
#         Risk assessment and treatment. A security risk assessment does not ask
#         whether a model treats people unfairly, and the two Statements of
#         Applicability draw on different reference control sets. PR-AIG-06
#         owns the AI side.
#   6.1.4 / 8.4
#         AI system impact assessment. No other standard has an equivalent, so
#         there is nothing to inherit from. PR-AIG-07 owns it.
#   4.3   Scope. Each standard needs its own scope statement naming its own
#         subject matter — an AI scope that does not name the AI systems will
#         draw a nonconformity however well clause 4.1 is evidenced.
SHARED_ANNEX_SL_CLAUSES: frozenset[str] = frozenset(
    {
        "4.1", "4.2", "4.4",
        "5.1", "5.3",
        "6.1.1", "6.2", "6.3",
        "7.1", "7.2", "7.3", "7.4", "7.5",
        "8.1",
        "9.1", "9.2", "9.3",
        "10.1", "10.2",
    }
)

NEVER_INHERITED: frozenset[str] = frozenset(
    {"4.3", "5.2", "6.1.2", "6.1.3", "6.1.4", "8.2", "8.3", "8.4"}
)

# Source framework -> frameworks that may inherit its shared clause coverage.
CLAUSE_INHERITANCE: dict[str, tuple[str, ...]] = {
    "iso27001": ("iso42001",),
    "iso22301": ("iso42001",),
}


def _inherit_shared_clauses(processes: tuple[Process, ...]) -> tuple[Process, ...]:
    """Extend clause coverage across the Annex SL standards, conservatively.

    Only clauses in ``SHARED_ANNEX_SL_CLAUSES`` are inherited, and a clause is
    only added to a process that already discharges the identical reference in
    the source framework. Nothing here invents coverage: it records that one
    piece of work satisfies a requirement that appears, word for word in
    substance, in more than one standard.
    """
    from dataclasses import replace

    out: list[Process] = []
    for process in processes:
        additions: dict[str, set[str]] = {}
        for source, targets in CLAUSE_INHERITANCE.items():
            for ref in process.clauses.get(source, ()):
                if ref in NEVER_INHERITED or ref not in SHARED_ANNEX_SL_CLAUSES:
                    continue
                for target in targets:
                    if ref in process.clauses.get(target, ()):
                        continue
                    additions.setdefault(target, set()).add(ref)
        if not additions:
            out.append(process)
            continue
        merged = {k: tuple(v) for k, v in process.clauses.items()}
        for target, refs in additions.items():
            merged[target] = tuple(sorted(set(merged.get(target, ())) | refs))
        out.append(replace(process, clauses=merged))
    return tuple(out)


# --------------------------------------------------------------------------
# The repository itself
# --------------------------------------------------------------------------
def _load() -> tuple[Process, ...]:
    """Assembled at import so a malformed process fails fast, not at run time."""
    from app.processes.aims import AI_MANAGEMENT
    from app.processes.appsec import APPLICATION_SECURITY
    from app.processes.governance import COMPLIANCE, GOVERNANCE, RISK
    from app.processes.operations import (
        AI_GOVERNANCE,
        CHANGE,
        PEOPLE,
        PRIVACY,
        RESILIENCE,
        SECURITY,
        THIRD_PARTY,
    )

    return _inherit_shared_clauses(
        (
            *GOVERNANCE, *RISK, *COMPLIANCE, *PRIVACY, *SECURITY,
            *THIRD_PARTY, *RESILIENCE, *PEOPLE, *CHANGE,
            *AI_GOVERNANCE, *AI_MANAGEMENT, *APPLICATION_SECURITY,
        )
    )


PROCESSES: tuple[Process, ...] = _load()
PROCESS_BY_CODE: dict[str, Process] = {p.code: p for p in PROCESSES}


def validate() -> list[str]:
    """Structural checks on the repository. Returns the problems found.

    Run at start-up and in CI. A process repository that references a domain
    that does not exist, or a domain that lists a process nobody wrote, is a
    documentation defect that becomes an execution defect the moment the engine
    reads it.
    """
    problems: list[str] = []
    codes = set(PROCESS_BY_CODE)

    for domain in DOMAINS:
        for code in domain.processes:
            if code not in codes:
                problems.append(f"{domain.code} lists {code}, which does not exist")
    for process in PROCESSES:
        if process.domain not in DOMAIN_BY_CODE:
            problems.append(f"{process.code} belongs to unknown domain {process.domain}")
        elif process.code not in DOMAIN_BY_CODE[process.domain].processes:
            problems.append(f"{process.code} is not listed by its domain {process.domain}")
        if not process.activities:
            problems.append(f"{process.code} has no activities")
        if not process.clauses:
            problems.append(f"{process.code} discharges no clause")

        seen: set[str] = set()
        for activity in process.activities:
            if activity.code in seen:
                problems.append(f"{process.code}: duplicate activity code {activity.code}")
            seen.add(activity.code)
            # An agent must never be the accountable party. Accountability for
            # an outcome rests with a person, always.
            if activity.accountable.lower() in {"agent", "ai", "system"}:
                problems.append(
                    f"{process.code}/{activity.code}: an agent cannot be accountable"
                )
            if activity.automation is Automation.GATE and activity.agent:
                problems.append(
                    f"{process.code}/{activity.code}: a gate cannot be performed by an agent"
                )
            if activity.agent and not activity.task_class and activity.ai_role:
                problems.append(
                    f"{process.code}/{activity.code}: has an ai_role but no task_class to route it"
                )
    return problems


def clause_coverage() -> dict[str, dict[str, list[str]]]:
    """Which process discharges which clause, per framework.

    This is the query that makes the repository worth having: an unclaimed
    clause is a hole in the management system, and it is now findable.
    """
    coverage: dict[str, dict[str, list[str]]] = {}
    for process in PROCESSES:
        for framework, refs in process.clauses.items():
            bucket = coverage.setdefault(framework, {})
            for ref in refs:
                bucket.setdefault(ref, []).append(process.code)
    return coverage


def statistics() -> dict:
    gates = sum(len(p.gates) for p in PROCESSES)
    activities = sum(len(p.activities) for p in PROCESSES)
    agent_steps = sum(len(p.agent_activities) for p in PROCESSES)
    unattended = sum(
        1
        for p in PROCESSES
        for a in p.activities
        if a.automation in {Automation.AUTO, Automation.AUTO_NOTIFY}
    )
    return {
        "domains": len(DOMAINS),
        "processes": len(PROCESSES),
        "activities": activities,
        "gates": gates,
        "agent_assisted_activities": agent_steps,
        "unattended_activities": unattended,
        "unattended_rate": round(unattended / activities, 3) if activities else 0.0,
        "frameworks_covered": sorted(clause_coverage()),
    }
