"""The agent registry.

Sixteen agents, each scoped to work it can do reliably, each with a named human
accountable for it, and none with authority to approve anything.

The design follows from what the evidence actually supports. Current practice
puts reliable agentic automation at roughly a fifth to two-fifths of repetitive
compliance work, with the remainder needing human judgement — and the boundary
between them is a governance question rather than a capability one. This
repository's own figure is 32% of activities unattended, which is inside that
band and was arrived at by classifying each activity rather than by aiming at a
number.

Four things are true of every agent here:

  * **It has a scope, and refuses outside it.** An agent asked to do something
    another agent owns says so rather than attempting it.
  * **It has an accountable person.** Not a team: a role that can be named in
    an audit finding.
  * **It cannot approve.** Agent principals structurally cannot hold gate
    permissions. An agent that reaches a decision point returns the gate and
    stops.
  * **It declares its confidence, and low confidence escalates.** An agent that
    is unsure is doing its job when it says so; the escalation is the feature.

The refusal list is deliberate and matches where the evidence says automation
fails: regulatory interpretation, risk acceptance, material external
communication, contextually complex exceptions, and final sign-off.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AutonomyTier(StrEnum):
    """How far an agent may act before a person is involved.

    The tier is a property of the agent in a context, not of the model. The
    same model runs at L4 for evidence collection and L1 during a live crisis.
    """

    L1 = "L1"  # Observes and reports. Takes no action.
    L2 = "L2"  # Drafts for a named person, who owns the output.
    L3 = "L3"  # Acts on reversible things; anything irreversible raises a gate.
    L4 = "L4"  # Acts unattended within a bounded, deterministic scope.


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    purpose: str
    accountable_role: str
    autonomy: AutonomyTier
    # Permissions the agent's service principal holds. None may begin "gate.".
    permissions: tuple[str, ...]
    task_classes: tuple[str, ...]
    tools: tuple[str, ...]
    # What this agent must decline even when asked, and why in one line.
    refuses: tuple[str, ...]
    escalates_below_confidence: float = 0.75
    processes: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        offending = [p for p in self.permissions if p.startswith("gate.")]
        if offending:
            raise ValueError(
                f"Agent '{self.key}' declares approval authority ({offending[0]}). "
                "Accountability for a decision cannot rest with an agent."
            )


# The refusals every agent shares. Stated once so they cannot drift apart.
UNIVERSAL_REFUSALS: tuple[str, ...] = (
    "Approving anything — every decision point returns a gate for a named person.",
    "Interpreting what a law or regulation requires of this organisation; that is a legal judgement.",
    "Accepting risk on the organisation's behalf, at any severity.",
    "Communicating with a regulator, an auditor, a customer or a data subject without human approval.",
    "Asserting that a control operates without an evidence record behind the claim.",
    "Inventing a clause reference, a citation, a date or a document name.",
)


AGENTS: tuple[Agent, ...] = (
    Agent(
        key="orchestrator",
        name="Orchestration agent",
        purpose=(
            "Plans and sequences work across processes: starts runs on their "
            "trigger, routes activities to the right agent, tracks SLAs, chases "
            "what is late and escalates what is stuck. It does no compliance "
            "reasoning of its own."
        ),
        accountable_role="Platform Admin",
        autonomy=AutonomyTier.L4,
        permissions=("wf.execute", "data.register.read", "data.register.write", "rpt.dashboard.view"),
        # Deliberately empty. Routing is decided by the process definition, not
        # by a model, which is what allows this agent to run unattended.
        task_classes=(),
        tools=("start_run", "advance_run", "raise_action", "notify", "query_registers"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Judging the substance of any assessment; it moves work, it does not evaluate it.",
        ),
        escalates_below_confidence=0.9,
        processes=("PR-CMP-01", "PR-CMP-03", "PR-PPL-01", "PR-PPL-02", "PR-PPL-03", "PR-CHG-01"),
        notes=(
            "L4 is justified because its actions are deterministic and "
            "reversible: scheduling, routing and notifying. It writes no "
            "conclusions."
        ),
    ),
    Agent(
        key="evidence",
        name="Evidence agent",
        purpose=(
            "Collects, hashes, files and freshness-checks evidence, and runs "
            "automated control tests against source systems. The highest-volume "
            "and most reliably automated work in the platform."
        ),
        accountable_role="Control Owner",
        # L3, not L4: collection and hashing are deterministic, but summarising
        # evidence for a reviewer is a judgement, and an agent is governed at
        # the level of the least deterministic thing it does.
        autonomy=AutonomyTier.L3,
        permissions=("evidence.write", "data.register.read", "compliance.manage", "wf.execute"),
        task_classes=("evidence_summary",),
        tools=(
            "run_control_test", "collect_evidence", "hash_and_file", "check_freshness",
            "assemble_pack", "query_connector",
        ),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Concluding that a control is effective; it reports what the evidence shows.",
            "Filling a gap in evidence with an inference about what probably happened.",
        ),
        escalates_below_confidence=0.75,
        processes=("PR-CMP-02", "PR-CMP-05", "PR-GOV-03", "PR-SEC-02", "PR-SEC-03", "PR-PPL-02"),
        notes=(
            "Collection and comparison are mechanical and run as AUTO in the "
            "processes that use them. Summarisation is marked ASSIST and read "
            "by a person. The agent is tiered to the latter."
        ),
    ),
    Agent(
        key="control_assessor",
        name="Control assessment agent",
        purpose=(
            "Assesses control implementation against requirement, drafts gaps "
            "and remediation, and performs cause analysis. Produces the "
            "reasoning a control owner then owns."
        ),
        accountable_role="Control Owner",
        autonomy=AutonomyTier.L2,
        permissions=("compliance.manage", "data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        task_classes=("control_assessment", "gap_analysis", "policy_drafting", "classification"),
        tools=("read_control", "read_evidence", "draft_assessment", "raise_gap", "map_controls"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Attesting a control; attestation is a personal statement by its owner.",
            "Closing a gap; closure requires verified evidence and a human decision.",
        ),
        escalates_below_confidence=0.75,
        processes=("PR-CMP-01", "PR-CMP-02", "PR-CMP-03", "PR-GOV-02", "PR-GOV-05", "PR-CHG-01", "PR-CHG-02"),
    ),
    Agent(
        key="risk_analyst",
        name="Risk analysis agent",
        purpose=(
            "Drafts risk statements, proposes inherent and residual scores with "
            "reasoning, maps controls to risks, and watches for signals that "
            "should move the register."
        ),
        accountable_role="Risk Officer",
        autonomy=AutonomyTier.L2,
        permissions=("risk.manage", "data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        task_classes=("risk_drafting", "control_assessment", "classification"),
        tools=("read_risk_register", "draft_risk", "propose_score", "correlate_signals", "read_controls"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Accepting residual risk, which is the single decision the register exists to record.",
            "Moving a risk on the register without a person confirming the movement.",
            "Reducing a residual score for a control that is claimed but not evidenced.",
        ),
        escalates_below_confidence=0.7,
        processes=("PR-RSK-01", "PR-RSK-02", "PR-RSK-03", "PR-SEC-02"),
    ),
    Agent(
        key="privacy",
        name="Privacy operations agent",
        purpose=(
            "Runs the mechanical parts of privacy: request classification and "
            "clock calculation, estate search, pack assembly with redaction "
            "proposals, processing-record drafting and drift detection."
        ),
        accountable_role="DPO",
        autonomy=AutonomyTier.L2,
        permissions=(
            "data.register.read", "data.register.write", "data.pii.read",
            "compliance.manage", "evidence.write", "wf.execute",
        ),
        task_classes=("classification", "dpia_drafting", "evidence_summary", "control_assessment"),
        tools=("search_estate", "classify_request", "compute_deadline", "assemble_pack",
               "propose_redactions", "draft_processing_record"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Releasing a subject access response; disclosure is irreversible and may expose a third party.",
            "Deciding whether to notify a supervisory authority or a data subject.",
            "Determining lawful basis or the adequacy of a transfer mechanism.",
            "Concluding that an incident is not a breach; uncertainty resolves towards the clock running.",
        ),
        escalates_below_confidence=0.85,
        processes=("PR-PRV-01", "PR-PRV-02", "PR-PRV-03", "PR-PRV-04", "PR-PRV-05"),
        notes=(
            "The highest escalation threshold in the registry apart from "
            "resilience, because privacy errors are statutory and usually "
            "irreversible. Over-escalation here costs a review; under-escalation "
            "costs a notifiable breach."
        ),
    ),
    Agent(
        key="third_party",
        name="Third-party risk agent",
        purpose=(
            "Tiers engagements by inherent exposure, processes questionnaire "
            "responses, scores supplier domains against evidence, and monitors "
            "suppliers between assessments."
        ),
        accountable_role="Control Owner",
        autonomy=AutonomyTier.L2,
        permissions=("data.register.read", "data.register.write", "risk.manage", "evidence.write", "wf.execute"),
        task_classes=("supplier_assessment", "classification", "evidence_summary"),
        tools=("score_questionnaire", "read_certifications", "monitor_supplier", "draft_conditions"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Approving a supplier engagement or confirming a contract is adequate.",
            "Accepting a certificate whose scope it cannot verify covers the service being bought.",
        ),
        escalates_below_confidence=0.8,
        processes=("PR-TPR-01", "PR-TPR-02", "PR-TPR-03"),
    ),
    Agent(
        key="resilience",
        name="Resilience agent",
        purpose=(
            "Drafts business impact analyses and continuity plans, designs "
            "exercise scenarios, and analyses exercise results against stated "
            "objectives."
        ),
        accountable_role="Control Owner",
        autonomy=AutonomyTier.L2,
        permissions=("data.register.read", "data.register.write", "compliance.manage", "evidence.write", "wf.execute"),
        task_classes=("bia_drafting", "policy_drafting", "gap_analysis", "classification"),
        tools=("map_dependencies", "draft_bia", "draft_plan", "design_exercise", "analyse_exercise"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Invoking continuity arrangements or declaring a crisis.",
            "Approving recovery objectives; the tolerance for disruption is a business decision.",
            "Recording an exercise as passed when the achieved recovery missed the objective.",
        ),
        escalates_below_confidence=0.75,
        processes=("PR-RES-01", "PR-RES-02", "PR-RES-03", "PR-RES-04"),
        notes="Drops to L1 during a live invocation: it records and informs, it does not act.",
    ),
    Agent(
        key="regulatory_watch",
        name="Regulatory change agent",
        purpose=(
            "Scans for change in law, regulation and standards, triages "
            "relevance to the scope, and maps a confirmed change to the "
            "controls, policies and records it touches."
        ),
        accountable_role="DPO",
        autonomy=AutonomyTier.L2,
        permissions=("data.register.read", "data.register.write", "compliance.manage", "wf.execute"),
        task_classes=("classification", "gap_analysis", "policy_drafting"),
        tools=("scan_sources", "triage_relevance", "map_impact", "read_obligations", "web_fetch"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Stating what a new obligation requires of this organisation.",
            "Concluding that a change does not apply; non-applicability is a legal position.",
            "Treating a proposal, a consultation or a political agreement as though it were in force.",
        ),
        escalates_below_confidence=0.85,
        processes=("PR-CMP-04", "PR-GOV-01", "PR-AIG-01"),
        notes=(
            "The distinction between agreed, adopted, published and in force is "
            "where this agent will fail if it is going to. It reports status and "
            "date, never a conclusion about applicability."
        ),
    ),
    Agent(
        key="incident",
        name="Incident agent",
        purpose=(
            "Enriches security events with asset, owner and data context, "
            "proposes triage classification, and drafts timelines and cause "
            "analysis after the fact."
        ),
        accountable_role="CISO",
        autonomy=AutonomyTier.L2,
        permissions=("data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        task_classes=("classification", "evidence_summary", "gap_analysis"),
        tools=("enrich_event", "classify_incident", "build_timeline", "read_asset_context"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Taking containment action on a production system.",
            "Ruling out personal data involvement; that determination starts a statutory clock.",
        ),
        escalates_below_confidence=0.8,
        processes=("PR-SEC-01", "PR-PRV-03"),
    ),
    Agent(
        key="audit",
        name="Audit agent",
        purpose=(
            "Plans audit coverage, selects and documents samples, prepares "
            "working papers, and drafts observations and responses to external "
            "auditor requests."
        ),
        accountable_role="Internal Auditor",
        autonomy=AutonomyTier.L2,
        permissions=("audit.conduct", "data.register.read", "evidence.write", "sec.auditlog.read", "wf.execute"),
        task_classes=("control_assessment", "gap_analysis", "evidence_summary"),
        tools=("plan_coverage", "select_sample", "prepare_working_paper", "draft_observation", "read_evidence"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Forming the audit opinion; the conclusion and the independence behind it belong to the auditor.",
            "Validating its own work — an agent cannot provide assurance over a process it executed.",
            "Issuing anything to an external auditor.",
        ),
        escalates_below_confidence=0.8,
        processes=("PR-GOV-03", "PR-CMP-05"),
        notes=(
            "Segregation of duties applies to agents as well as people. Where "
            "this agent has drafted work in a process, its output cannot be the "
            "assurance over that same process."
        ),
    ),
    Agent(
        key="reporting",
        name="Reporting agent",
        purpose=(
            "Computes and assembles: readiness figures, management review packs, "
            "objective performance, AI oversight metrics. Deterministic "
            "aggregation, not judgement."
        ),
        accountable_role="Platform Admin",
        autonomy=AutonomyTier.L4,
        permissions=("rpt.dashboard.view", "data.register.read", "compliance.manage", "sec.auditlog.read"),
        task_classes=(),
        tools=("compute_readiness", "assemble_pack", "aggregate_metrics", "render_report"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Adjusting, smoothing or narrating a figure; it reports what the data says.",
            "Presenting a readiness figure without the evidence discount applied.",
        ),
        escalates_below_confidence=1.0,
        processes=("PR-GOV-02", "PR-GOV-04", "PR-CMP-05", "PR-AIG-02", "PR-AIG-03"),
        notes=(
            "L4 with no task classes at all: this agent runs queries and "
            "arithmetic. It calls no model, which is why its figures are "
            "reproducible."
        ),
    ),
    Agent(
        key="onf_steward",
        name="Normative framework steward",
        purpose=(
            "Maintains the Application Security Control library and the "
            "Organization Normative Framework around it: drafts control "
            "definitions, selects the set a targeted level of trust requires, "
            "and translates each control into the delivery team's own stage "
            "vocabulary."
        ),
        accountable_role="Control Owner",
        autonomy=AutonomyTier.L2,
        permissions=("compliance.manage", "data.register.read", "data.register.write", "wf.execute"),
        task_classes=("asc_design", "gap_analysis", "control_assessment", "classification"),
        tools=("read_asc_library", "propose_asc", "select_asc_set", "map_lifecycle", "read_controls"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Approving an ONF iteration or an ASC; the library is the committee's to authorise.",
            "Defining or changing level zero, which is the floor a project team cannot go below.",
            "Waiving any control, at any level of trust.",
        ),
        escalates_below_confidence=0.75,
        processes=(
            "PR-APS-01", "PR-APS-02", "PR-APS-03", "PR-APS-04",
            "PR-APS-06", "PR-APS-08", "PR-APS-10",
        ),
        notes=(
            "Selecting controls for a level of trust is deterministic and could run "
            "unattended, and does — the process marks those steps AUTO. Designing a "
            "new control is judgement, so the agent as a whole sits at L2."
        ),
    ),
    Agent(
        key="appsec",
        name="Application security execution agent",
        purpose=(
            "Runs the automatable security activities — static analysis, "
            "dependency and licence scanning, secret scanning, tenant isolation "
            "tests and vulnerability re-scans — and records the activity half of "
            "each Application Security Control."
        ),
        accountable_role="Control Owner",
        autonomy=AutonomyTier.L3,
        permissions=("data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        # No task classes: every activity this agent performs is a tool run whose
        # output is reproducible. It calls no model, which is what makes its
        # records safe to write without review.
        task_classes=(),
        tools=("run_pipeline_scan", "record_asc_activity", "read_asc_library", "raise_action"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Recording any verification measurement; it performs activities and nothing else.",
            "Changing a blocking severity threshold, which would let it grade its own work.",
            "Suppressing or dismissing a finding.",
        ),
        escalates_below_confidence=0.95,
        processes=("PR-APS-02", "PR-APS-09"),
        notes=(
            "A separate identity from the verification agent rather than a mode of "
            "one agent. The database separates duties by actor identity, so a single "
            "agent with two modes would defeat the trigger entirely."
        ),
    ),
    Agent(
        key="verification",
        name="Verification measurement agent",
        purpose=(
            "Records the measurement half of an Application Security Control from "
            "independent tool output, runs AI system evaluation suites, and "
            "escalates every failure inside the declared window."
        ),
        accountable_role="Internal Auditor",
        autonomy=AutonomyTier.L3,
        permissions=("data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        task_classes=(),
        tools=("record_asc_measurement", "run_evaluation_suite", "read_evidence", "raise_action"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Measuring any control marked as requiring a human verifier.",
            "Measuring a control whose security activity it performed.",
            "Amending an outcome once written; a correction is a new record with a reason.",
        ),
        escalates_below_confidence=0.95,
        processes=("PR-APS-09", "PR-AIG-12"),
        notes=(
            "The database refuses both of the first two refusals independently. The "
            "refusal list states the intent; the trigger is what makes it true."
        ),
    ),
    Agent(
        key="provenance",
        name="Data provenance agent",
        purpose=(
            "Discovers configured providers, models and compute from the live "
            "gateway, and records origin, acquisition basis, licence, quality "
            "result and preparation method for every dataset an AI system uses."
        ),
        accountable_role="DPO",
        autonomy=AutonomyTier.L3,
        permissions=("data.register.read", "data.register.write", "evidence.write", "wf.execute"),
        task_classes=(),
        tools=("read_llm_config", "record_provenance", "run_quality_checks", "read_dataset_registry"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Determining a lawful basis for personal data, which is a legal judgement.",
            "Marking a dataset approved for training or retrieval.",
            "Recording provenance it cannot trace to a source record.",
        ),
        escalates_below_confidence=0.9,
        processes=("PR-AIG-05", "PR-AIG-08"),
        notes=(
            "Writes final records rather than proposals, which is why PR-AIG-08 "
            "carries a sampling review by the data owner behind it. Bounded autonomy "
            "without a review behind it is just unattended writing."
        ),
    ),
    Agent(
        key="ai_impact",
        name="AI impact assessment agent",
        purpose=(
            "Assembles the inputs for an AI system impact assessment and drafts "
            "the individual, group and societal dimensions separately, saying "
            "explicitly where the evidence does not support a conclusion."
        ),
        accountable_role="DPO",
        autonomy=AutonomyTier.L2,
        permissions=("data.register.read", "data.register.write", "wf.execute"),
        task_classes=("impact_assessment", "classification"),
        tools=("read_ai_system", "read_provenance", "read_incidents", "draft_impact_assessment"),
        refuses=UNIVERSAL_REFUSALS
        + (
            "Setting a residual impact rating.",
            "Approving an assessment; the database refuses an approved record with no human approver.",
            "Assessing any AI system of which this agent forms a part.",
        ),
        escalates_below_confidence=0.9,
        processes=("PR-AIG-07",),
        notes=(
            "The lowest-trust agent in the estate by design. ISO/IEC 42001 A.5 asks "
            "what an AI system does to people; a model drafting that about its own "
            "estate is the clearest case where fluency would be mistaken for "
            "assurance, so the draft never becomes a record on its own."
        ),
    ),
)

AGENT_BY_KEY: dict[str, Agent] = {a.key: a for a in AGENTS}


def validate() -> list[str]:
    """Checks the registry against the process repository."""
    from app.processes import PROCESS_BY_CODE, PROCESSES

    problems: list[str] = []

    for agent in AGENTS:
        for code in agent.processes:
            if code not in PROCESS_BY_CODE:
                problems.append(f"{agent.key} claims unknown process {code}")
        if agent.autonomy is AutonomyTier.L4 and agent.task_classes:
            # An unattended agent that calls a model is making unreviewed
            # judgements. If it needs a model, it is not L4.
            problems.append(
                f"{agent.key} runs unattended at L4 but routes to a model "
                f"({', '.join(agent.task_classes)}); unattended work must be deterministic"
            )

    # Every agent-assisted activity must name an agent that exists and holds a
    # matching task class, or the process cannot actually run.
    for process in PROCESSES:
        for activity in process.agent_activities:
            agent = AGENT_BY_KEY.get(activity.agent or "")
            if agent is None:
                problems.append(f"{process.code}/{activity.code}: unknown agent '{activity.agent}'")
                continue
            if activity.task_class and activity.task_class not in agent.task_classes:
                problems.append(
                    f"{process.code}/{activity.code}: {agent.key} is not routed for "
                    f"task class '{activity.task_class}'"
                )
    return problems


def statistics() -> dict:
    by_tier: dict[str, int] = {}
    for agent in AGENTS:
        by_tier[agent.autonomy.value] = by_tier.get(agent.autonomy.value, 0) + 1
    return {
        "agents": len(AGENTS),
        "by_autonomy_tier": dict(sorted(by_tier.items())),
        "agents_with_approval_authority": 0,  # structurally enforced in __post_init__
        "distinct_task_classes": sorted({t for a in AGENTS for t in a.task_classes}),
        "universal_refusals": len(UNIVERSAL_REFUSALS),
    }
