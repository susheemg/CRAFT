"""Governance, risk, compliance and assurance processes.

Clause references are to the requirement being discharged, not to a paraphrase
of it. Where a process claims a clause, an auditor should be able to follow the
run history and see the clause satisfied.
"""

from __future__ import annotations

from app.processes import Activity, Automation, Cadence, Process

# ==========================================================================
# GOV — Governance and management system
# ==========================================================================
GOVERNANCE: tuple[Process, ...] = (
    Process(
        code="PR-GOV-01",
        name="Establish and maintain management system scope and context",
        domain="GOV",
        purpose=(
            "Fixes what the management system covers and why, which every other "
            "process depends on. An unclear scope is the most common reason a "
            "certification audit fails before it examines a single control."
        ),
        owner_role="CISO",
        trigger="Annual review, or a material change to the business, estate or legal obligations",
        cadence=Cadence.ANNUAL,
        clauses={
            "iso27001": ("4.1", "4.2", "4.3", "4.4", "5.1", "5.2"),
            "iso22301": ("4.1", "4.2", "4.3", "4.4", "5.1", "5.2"),
            "uk_gdpr": ("Art.5", "Art.24"),
        },
        outputs=("scope_statement", "context_analysis", "interested_parties_register", "policy_set"),
        kpis=("Scope reviewed within 12 months", "Zero scope exclusions without justification"),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Assemble the internal and external issues bearing on the "
                    "management system: business model, estate, regulatory "
                    "obligations, contractual commitments and dependencies."
                ),
                responsible="agent",
                accountable="CISO",
                trigger="Annual cycle or material change",
                inputs=("asset_register", "supplier_register", "processing_records", "obligation_register"),
                outputs=("context_analysis",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role=(
                    "Draft the context analysis from the registers and flag "
                    "anything that changed materially since the last cycle."
                ),
                task_class="policy_drafting",
                control_refs=("iso27001:4.1", "iso22301:4.1"),
            ),
            Activity(
                code="A2",
                what=(
                    "Identify interested parties and their requirements, "
                    "distinguishing legal obligations from commercial expectations."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("context_analysis", "contract_register"),
                outputs=("interested_parties_register",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role="Draft the register and cite the source of each stated requirement.",
                task_class="policy_drafting",
                control_refs=("iso27001:4.2", "iso22301:4.2"),
            ),
            Activity(
                code="A3",
                what="Define the scope boundary, including exclusions and the reason for each.",
                responsible="CISO",
                accountable="CISO",
                inputs=("context_analysis", "interested_parties_register"),
                outputs=("draft_scope_statement",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role=(
                    "Draft the boundary and test each proposed exclusion against "
                    "the clauses that cannot be excluded."
                ),
                task_class="policy_drafting",
                min_confidence=0.8,
                control_refs=("iso27001:4.3", "iso22301:4.3"),
            ),
            Activity(
                code="A4",
                what="Approve the scope and the policy set at leadership level.",
                responsible="CISO",
                accountable="CISO",
                inputs=("draft_scope_statement", "policy_set"),
                outputs=("approved_scope", "approved_policies"),
                automation=Automation.GATE,
                gate_type="governance.scope_approval",
                gate_reason="statutory",
                control_refs=("iso27001:5.1", "iso27001:5.2", "iso22301:5.2"),
                evidence=("scope_approval_record",),
            ),
            Activity(
                code="A5",
                what="Publish the approved scope and policies and record acknowledgement.",
                responsible="agent",
                accountable="CISO",
                inputs=("approved_scope", "approved_policies"),
                outputs=("publication_record",),
                automation=Automation.AUTO_NOTIFY,
                agent="evidence",
                control_refs=("iso27001:5.2", "iso27001:7.5"),
                evidence=("policy_publication_record",),
            ),
        ),
    ),
    Process(
        code="PR-GOV-02",
        name="Set and monitor management system objectives",
        domain="GOV",
        purpose=(
            "Turns policy into measurable objectives and keeps them visible. "
            "Objectives without measurement are the clause auditors most often "
            "find satisfied on paper only."
        ),
        owner_role="CISO",
        trigger="Annual planning cycle; quarterly measurement",
        cadence=Cadence.QUARTERLY,
        clauses={
            "iso27001": ("6.2", "9.1"),
            "iso22301": ("6.2", "9.1"),
        },
        outputs=("objective_register", "performance_report"),
        kpis=("Objectives measured quarterly", "Objectives with a named owner and target"),
        activities=(
            Activity(
                code="A1",
                what="Derive candidate objectives from policy, risk position and readiness gaps.",
                responsible="agent",
                accountable="CISO",
                inputs=("approved_policies", "risk_register", "readiness_snapshot"),
                outputs=("candidate_objectives",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Propose objectives that are measurable and tied to a named shortfall.",
                task_class="policy_drafting",
                control_refs=("iso27001:6.2",),
            ),
            Activity(
                code="A2",
                what="Agree objectives, targets, owners and measurement method.",
                responsible="CISO",
                accountable="CISO",
                inputs=("candidate_objectives",),
                outputs=("objective_register",),
                automation=Automation.GATE,
                gate_type="governance.objectives_approval",
                gate_reason="high_risk",
                control_refs=("iso27001:6.2",),
            ),
            Activity(
                code="A3",
                what="Measure performance against each objective and report the trend.",
                responsible="agent",
                accountable="CISO",
                trigger="Quarterly",
                inputs=("objective_register", "readiness_snapshot", "risk_register", "gap_register"),
                outputs=("performance_report",),
                automation=Automation.AUTO,
                agent="reporting",
                ai_role=None,
                control_refs=("iso27001:9.1", "iso22301:9.1"),
                evidence=("performance_measurement_record",),
            ),
        ),
    ),
    Process(
        code="PR-GOV-03",
        name="Internal audit",
        domain="GOV",
        purpose=(
            "Provides independent assurance that the management system conforms "
            "and operates. Independence is enforced by segregation of duties: an "
            "auditor cannot hold an operator or control-owner role."
        ),
        owner_role="Internal Auditor",
        trigger="Audit programme schedule, or a triggering event",
        cadence=Cadence.ANNUAL,
        clauses={
            "iso27001": ("9.2", "9.2.1", "9.2.2"),
            "iso22301": ("9.2",),
        },
        outputs=("audit_programme", "audit_report", "nonconformity_records"),
        kpis=("Programme coverage of all clauses over three years", "Findings closed within agreed dates"),
        autonomy_tier="L2",
        notes=(
            "AI participates in sampling, working-paper preparation and evidence "
            "retrieval. It does not form the audit opinion: the conclusion, and "
            "the independence that gives it value, belong to the auditor."
        ),
        activities=(
            Activity(
                code="A1",
                what="Plan the audit programme so that every clause is covered across the cycle.",
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("clause_coverage_map", "risk_register", "previous_findings"),
                outputs=("audit_programme",),
                automation=Automation.ASSIST,
                agent="audit",
                ai_role=(
                    "Propose a programme weighted to risk and to clauses least "
                    "recently examined, and show the coverage it achieves."
                ),
                task_class="gap_analysis",
                control_refs=("iso27001:9.2.2",),
            ),
            Activity(
                code="A2",
                what="Select the sample for each control in scope and record the basis of selection.",
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("audit_programme", "population_data"),
                outputs=("sample_selection",),
                automation=Automation.AUTO,
                agent="audit",
                ai_role=None,
                control_refs=("iso27001:9.2",),
                evidence=("sample_selection_record",),
            ),
            Activity(
                code="A3",
                what="Retrieve the evidence for each sampled item and prepare the working paper.",
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("sample_selection",),
                outputs=("working_papers",),
                automation=Automation.AUTO_NOTIFY,
                agent="evidence",
                ai_role="Assemble and summarise the evidence; flag anything missing or expired.",
                task_class="evidence_summary",
                min_confidence=0.75,
                control_refs=("iso27001:9.2",),
            ),
            Activity(
                code="A4",
                what="Test the control and reach a conclusion on its operating effectiveness.",
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("working_papers",),
                outputs=("test_conclusions",),
                automation=Automation.ASSIST,
                agent="audit",
                ai_role=(
                    "Draft the observation and the proposed rating; the auditor "
                    "reaches the conclusion."
                ),
                task_class="control_assessment",
                min_confidence=0.8,
                control_refs=("iso27001:9.2",),
            ),
            Activity(
                code="A5",
                what="Raise nonconformities with severity, cause and required correction.",
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("test_conclusions",),
                outputs=("nonconformity_records",),
                automation=Automation.ASSIST,
                agent="audit",
                ai_role="Draft the finding, its cause analysis and a proportionate correction.",
                task_class="gap_analysis",
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A6",
                what="Issue the audit report to management.",
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("test_conclusions", "nonconformity_records"),
                outputs=("audit_report",),
                automation=Automation.GATE,
                gate_type="audit.report_issue",
                gate_reason="irreversible",
                control_refs=("iso27001:9.2.2",),
                evidence=("internal_audit_report",),
            ),
        ),
    ),
    Process(
        code="PR-GOV-04",
        name="Management review",
        domain="GOV",
        purpose=(
            "The clause that closes the loop. Every required input is assembled "
            "automatically, because the usual failure is not poor judgement in "
            "the review but a review held without the inputs the standard names."
        ),
        owner_role="CISO",
        trigger="Scheduled review, or a significant change or incident",
        cadence=Cadence.ANNUAL,
        clauses={
            "iso27001": ("9.3", "9.3.1", "9.3.2", "9.3.3"),
            "iso22301": ("9.3",),
        },
        outputs=("management_review_minutes", "review_decisions"),
        kpis=("All required inputs present at review", "Decisions tracked to closure"),
        activities=(
            Activity(
                code="A1",
                what=(
                    "Assemble every input the standard requires: audit results, "
                    "objective performance, nonconformities, risk position, "
                    "interested-party feedback, and the status of prior actions."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("audit_report", "performance_report", "risk_register", "gap_register", "prior_actions"),
                outputs=("review_pack",),
                automation=Automation.AUTO,
                agent="reporting",
                ai_role=None,
                control_refs=("iso27001:9.3.2", "iso22301:9.3"),
                evidence=("management_review_pack",),
            ),
            Activity(
                code="A2",
                what="Confirm the pack is complete against the clause before the meeting is held.",
                responsible="agent",
                accountable="CISO",
                inputs=("review_pack",),
                outputs=("completeness_check",),
                automation=Automation.AUTO_NOTIFY,
                agent="control_assessor",
                ai_role=(
                    "Check each required input is present and non-empty, and name "
                    "any that is missing."
                ),
                task_class="control_assessment",
                control_refs=("iso27001:9.3.2",),
            ),
            Activity(
                code="A3",
                what="Hold the review and record decisions on improvement, resources and change.",
                responsible="CISO",
                accountable="CISO",
                inputs=("review_pack", "completeness_check"),
                outputs=("management_review_minutes", "review_decisions"),
                automation=Automation.GATE,
                gate_type="governance.management_review",
                gate_reason="statutory",
                control_refs=("iso27001:9.3.3", "iso22301:9.3"),
                evidence=("management_review_minutes",),
            ),
            Activity(
                code="A4",
                what="Convert decisions into tracked actions with owners and dates.",
                responsible="agent",
                accountable="CISO",
                inputs=("review_decisions",),
                outputs=("improvement_actions",),
                automation=Automation.AUTO_NOTIFY,
                agent="orchestrator",
                control_refs=("iso27001:10.1",),
            ),
        ),
    ),
    Process(
        code="PR-GOV-05",
        name="Nonconformity and continual improvement",
        domain="GOV",
        purpose=(
            "Handles what went wrong: correction, cause, and whether the same "
            "cause exists elsewhere. Cause analysis is where this clause is "
            "usually thin, so the process forces it before closure."
        ),
        owner_role="Control Owner",
        trigger="Nonconformity from any source: audit, incident, exercise, complaint",
        cadence=Cadence.EVENT,
        clauses={
            "iso27001": ("10.1", "10.2"),
            "iso22301": ("10.1", "10.2"),
            "uk_gdpr": ("Art.24",),
        },
        outputs=("correction_record", "cause_analysis", "effectiveness_check"),
        kpis=("Cause recorded for every nonconformity", "Recurrence rate of closed findings"),
        activities=(
            Activity(
                code="A1",
                what="Record the nonconformity and take immediate correction to limit consequence.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("finding",),
                outputs=("correction_record",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Draft the correction and identify what is affected right now.",
                task_class="gap_analysis",
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A2",
                what="Analyse the cause and determine whether it exists elsewhere in the estate.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("correction_record", "control_implementations", "incident_history"),
                outputs=("cause_analysis", "similar_exposure"),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role=(
                    "Analyse cause and search for the same weakness in other "
                    "controls or systems, citing what supports each match."
                ),
                task_class="gap_analysis",
                min_confidence=0.75,
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A3",
                what="Agree corrective action addressing the cause, not only the symptom.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("cause_analysis",),
                outputs=("corrective_action",),
                automation=Automation.ASSIST,
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A4",
                what="Verify the action worked before closing the finding.",
                responsible="agent",
                accountable="Control Owner",
                trigger="On the agreed verification date",
                inputs=("corrective_action",),
                outputs=("effectiveness_check",),
                automation=Automation.AUTO_NOTIFY,
                agent="evidence",
                ai_role="Check the evidence shows the action took effect, and say so plainly if it does not.",
                task_class="evidence_summary",
                min_confidence=0.8,
                control_refs=("iso27001:10.2",),
                evidence=("corrective_action_effectiveness",),
            ),
        ),
    ),
)


# ==========================================================================
# RSK — Risk management
# ==========================================================================
RISK: tuple[Process, ...] = (
    Process(
        code="PR-RSK-01",
        name="Risk identification and assessment",
        domain="RSK",
        purpose=(
            "Produces a defensible risk position on one scale, across "
            "information security, privacy and continuity, so that treatment "
            "priorities can be compared across domains."
        ),
        owner_role="Risk Officer",
        trigger="New asset, supplier, change, incident, threat intelligence, or scheduled review",
        cadence=Cadence.EVENT,
        clauses={
            "iso27001": ("6.1.1", "6.1.2", "8.2"),
            "iso22301": ("6.1", "8.2.3"),
            "uk_gdpr": ("Art.24", "Art.32"),
        },
        outputs=("risk_record", "inherent_score", "residual_score"),
        kpis=("Risks reviewed within their cycle", "Share of risks with residual score and named owner"),
        activities=(
            Activity(
                code="A1",
                what="Capture the risk as threat, vulnerability, asset and consequence.",
                responsible="agent",
                accountable="Risk Officer",
                trigger="Triggering event",
                inputs=("trigger_event", "asset_register", "threat_intelligence"),
                outputs=("risk_statement",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Draft the risk statement and cite the source of the trigger.",
                task_class="risk_drafting",
                control_refs=("iso27001:6.1.2",),
            ),
            Activity(
                code="A2",
                what="Score inherent likelihood and impact before existing controls.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("risk_statement",),
                outputs=("inherent_score",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Propose scores with the reasoning for each, on the organisation's 5x5 scale.",
                task_class="risk_drafting",
                min_confidence=0.7,
                control_refs=("iso27001:6.1.2",),
            ),
            Activity(
                code="A3",
                what="Identify the controls actually in place and re-score residual risk.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("inherent_score", "control_implementations"),
                outputs=("residual_score", "linked_controls"),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role=(
                    "Map operating controls to the risk and justify the reduction; "
                    "a control that is implemented but unevidenced does not reduce it."
                ),
                task_class="control_assessment",
                min_confidence=0.75,
                control_refs=("iso27001:6.1.3", "uk_gdpr:Art.32"),
            ),
            Activity(
                code="A4",
                what="Confirm the assessment and assign the risk owner.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("residual_score",),
                outputs=("assessed_risk",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:6.1.2",),
                evidence=("risk_assessment_record",),
            ),
        ),
    ),
    Process(
        code="PR-RSK-02",
        name="Risk treatment and acceptance",
        domain="RSK",
        purpose=(
            "Decides what to do about the risk and, where it is tolerated, "
            "records who tolerated it and why. Acceptance above appetite is a "
            "named decision, never a default."
        ),
        owner_role="Risk Officer",
        trigger="Completion of an assessment, or a change in residual position",
        cadence=Cadence.EVENT,
        clauses={
            "iso27001": ("6.1.3", "8.3", "6.1.3.d"),
            "iso22301": ("6.1", "8.3"),
            "uk_gdpr": ("Art.32", "Art.35"),
        },
        outputs=("treatment_plan", "acceptance_record", "statement_of_applicability_input"),
        kpis=("Risks above appetite with a recorded acceptance or plan", "Treatment actions delivered by date"),
        activities=(
            Activity(
                code="A1",
                what="Select the treatment strategy: mitigate, transfer, avoid or accept.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("assessed_risk",),
                outputs=("treatment_strategy",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role=(
                    "Draft options with the cost, the effect on residual score, "
                    "and the controls each would require."
                ),
                task_class="risk_drafting",
                control_refs=("iso27001:6.1.3",),
            ),
            Activity(
                code="A2",
                what="Determine the controls needed and record them for the Statement of Applicability.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("treatment_strategy",),
                outputs=("required_controls", "statement_of_applicability_input"),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Map the treatment to Annex A controls and identify any not yet applicable.",
                task_class="control_assessment",
                min_confidence=0.75,
                control_refs=("iso27001:6.1.3.c", "iso27001:6.1.3.d"),
            ),
            Activity(
                code="A3",
                what="Produce the treatment plan with owner, actions and dates.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("required_controls",),
                outputs=("treatment_plan",),
                automation=Automation.ASSIST,
                control_refs=("iso27001:6.1.3.e",),
            ),
            Activity(
                code="A4",
                what="Obtain risk owner approval of the plan and of any residual risk retained.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("treatment_plan",),
                outputs=("approved_plan",),
                automation=Automation.GATE,
                gate_type="risk.treatment_approval",
                gate_reason="high_risk",
                control_refs=("iso27001:6.1.3.f",),
            ),
            Activity(
                code="A5",
                what="Accept residual risk that remains above appetite.",
                responsible="Risk Officer",
                accountable="CISO",
                inputs=("approved_plan", "residual_score"),
                outputs=("acceptance_record",),
                automation=Automation.GATE,
                gate_type="risk.residual_acceptance",
                gate_reason="high_risk",
                control_refs=("iso27001:6.1.3.f", "iso27001:8.3"),
                evidence=("residual_risk_acceptance",),
            ),
        ),
    ),
    Process(
        code="PR-RSK-03",
        name="Continuous risk monitoring and review",
        domain="RSK",
        purpose=(
            "Keeps the register current between assessments. This is where "
            "continuous monitoring earns its place: a register reviewed annually "
            "describes last year's organisation."
        ),
        owner_role="Risk Officer",
        trigger="Continuous; escalation on threshold breach",
        cadence=Cadence.CONTINUOUS,
        clauses={
            "iso27001": ("8.2", "9.1"),
            "iso22301": ("8.2", "9.1"),
        },
        outputs=("risk_movement_report", "review_actions"),
        kpis=("Overdue risk reviews", "Mean time from signal to register update"),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what="Detect signals that could move a risk: incidents, control failures, supplier events, threat intelligence.",
                responsible="agent",
                accountable="Risk Officer",
                trigger="Continuous",
                inputs=("incident_register", "control_test_results", "supplier_events", "threat_feeds"),
                outputs=("risk_signals",),
                automation=Automation.AUTO,
                agent="risk_analyst",
                ai_role=None,
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A2",
                what="Assess whether a signal changes the residual position of any risk.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("risk_signals", "risk_register"),
                outputs=("proposed_movements",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role=(
                    "Say which risks the signal affects and in which direction, "
                    "with the evidence. Propose only; the register changes when a "
                    "person agrees."
                ),
                task_class="risk_drafting",
                min_confidence=0.8,
                control_refs=("iso27001:8.2",),
            ),
            Activity(
                code="A3",
                what="Escalate any movement that crosses appetite.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("proposed_movements",),
                outputs=("escalations",),
                automation=Automation.AUTO_NOTIFY,
                agent="orchestrator",
                control_refs=("iso27001:8.2",),
                sla_hours=4,
            ),
            Activity(
                code="A4",
                what="Confirm or reject each proposed movement and re-open assessment where needed.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("proposed_movements", "escalations"),
                outputs=("risk_movement_report",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:8.2",),
            ),
        ),
    ),
)


# ==========================================================================
# CMP — Compliance and assurance
# ==========================================================================
COMPLIANCE: tuple[Process, ...] = (
    Process(
        code="PR-CMP-01",
        name="Control library and applicability maintenance",
        domain="CMP",
        purpose=(
            "Maintains the control set and the Statement of Applicability, "
            "including the justification for every exclusion — the document a "
            "certification auditor reads first."
        ),
        owner_role="Control Owner",
        trigger="Programme start, scope change, standard revision, or annual review",
        cadence=Cadence.ANNUAL,
        clauses={
            "iso27001": ("6.1.3.d", "Annex A"),
            "iso22301": ("8.1",),
            "uk_gdpr": ("Art.24", "Art.32"),
        },
        outputs=("control_library", "statement_of_applicability"),
        kpis=("Exclusions with justification", "Controls with a named owner"),
        activities=(
            Activity(
                code="A1",
                what="Materialise an implementation record for every control in the framework.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("framework_catalogue", "scope_statement"),
                outputs=("control_implementations",),
                automation=Automation.AUTO,
                agent="orchestrator",
                control_refs=("iso27001:6.1.3.d",),
            ),
            Activity(
                code="A2",
                what="Propose applicability for each control against the scope and the risk treatment.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("control_implementations", "risk_treatment_plans", "scope_statement"),
                outputs=("applicability_proposals",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role=(
                    "Propose applicable or excluded with a justification an "
                    "auditor would accept. Mandatory clauses cannot be excluded."
                ),
                task_class="control_assessment",
                min_confidence=0.8,
                control_refs=("iso27001:6.1.3.d",),
            ),
            Activity(
                code="A3",
                what="Approve the Statement of Applicability.",
                responsible="CISO",
                accountable="CISO",
                inputs=("applicability_proposals",),
                outputs=("statement_of_applicability",),
                automation=Automation.GATE,
                gate_type="compliance.soa_approval",
                gate_reason="statutory",
                control_refs=("iso27001:6.1.3.d",),
                evidence=("statement_of_applicability",),
            ),
        ),
    ),
    Process(
        code="PR-CMP-02",
        name="Continuous control monitoring",
        domain="CMP",
        purpose=(
            "Replaces the annual evidence scramble with a live signal. Machine-"
            "testable controls are tested on a schedule against the source "
            "system; the rest are attested on a cycle by their owner."
        ),
        owner_role="Control Owner",
        trigger="Continuous, on each control's own test frequency",
        cadence=Cadence.CONTINUOUS,
        clauses={
            "iso27001": ("9.1", "A.5.35", "A.5.36"),
            "iso22301": ("9.1",),
            "uk_gdpr": ("Art.32",),
        },
        outputs=("control_test_results", "drift_alerts", "evidence_records"),
        kpis=("Share of controls under automated test", "Mean time from drift to alert", "Evidence freshness"),
        autonomy_tier="L3",
        notes=(
            "This is the highest-value automation in the platform and the one "
            "with the clearest boundary: collecting and comparing evidence is "
            "mechanical, deciding what a shortfall means is not."
        ),
        activities=(
            Activity(
                code="A1",
                what="Run each control's automated test against its source system on schedule.",
                responsible="agent",
                accountable="Control Owner",
                trigger="Per-control test frequency",
                inputs=("control_implementations", "connector_configuration"),
                outputs=("raw_test_results",),
                automation=Automation.AUTO,
                agent="evidence",
                ai_role=None,
                control_refs=("iso27001:9.1",),
                evidence=("automated_control_test",),
            ),
            Activity(
                code="A2",
                what="Compare the result against the control's expected state and detect drift.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("raw_test_results", "expected_state"),
                outputs=("drift_alerts", "pass_records"),
                automation=Automation.AUTO,
                agent="evidence",
                ai_role=None,
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A3",
                what="Hash and file the result as evidence against the control.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("raw_test_results",),
                outputs=("evidence_records",),
                automation=Automation.AUTO,
                agent="evidence",
                control_refs=("iso27001:7.5.3",),
                evidence=("control_evidence_record",),
            ),
            Activity(
                code="A4",
                what="Assess what a drift means and whether it is a gap, an exception or noise.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("drift_alerts", "control_implementations"),
                outputs=("drift_assessment",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role=(
                    "Assess severity and recommend gap, exception or dismissal, "
                    "citing the evidence. Recommend only."
                ),
                task_class="control_assessment",
                min_confidence=0.8,
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A5",
                what="Request attestation for controls that cannot be tested automatically.",
                responsible="agent",
                accountable="Control Owner",
                trigger="On the control's attestation cycle",
                inputs=("control_implementations",),
                outputs=("attestation_requests",),
                automation=Automation.AUTO_NOTIFY,
                agent="orchestrator",
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A6",
                what="Attest the control's status and effectiveness.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("attestation_requests", "evidence_records"),
                outputs=("attestation",),
                automation=Automation.GATE,
                gate_type="compliance.control_attestation",
                gate_reason="statutory",
                control_refs=("iso27001:9.1",),
                evidence=("control_attestation",),
            ),
        ),
    ),
    Process(
        code="PR-CMP-03",
        name="Gap remediation",
        domain="CMP",
        purpose=(
            "Takes a shortfall from identification to verified closure. Overdue "
            "remediation is among the first things an external auditor samples."
        ),
        owner_role="Control Owner",
        trigger="Gap raised by assessment, monitoring, audit, incident or exercise",
        cadence=Cadence.EVENT,
        clauses={
            "iso27001": ("10.1", "10.2", "6.1.3"),
            "iso22301": ("10.1",),
        },
        outputs=("gap_record", "remediation_plan", "closure_evidence"),
        kpis=("Overdue gaps", "Mean time to close by severity", "Reopened gap rate"),
        activities=(
            Activity(
                code="A1",
                what="Record the gap with severity rated on consequence if unaddressed.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("finding",),
                outputs=("gap_record",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Draft the gap in terms an auditor would accept and rate its severity.",
                task_class="gap_analysis",
                min_confidence=0.75,
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A2",
                what="Draft a proportionate remediation plan with effort and a realistic date.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("gap_record",),
                outputs=("remediation_plan",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Propose the plan and the effort it needs; do not promise dates the owner has not agreed.",
                task_class="gap_analysis",
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A3",
                what="Agree the plan, owner and date.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("remediation_plan",),
                outputs=("agreed_plan",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A4",
                what="Track progress and escalate before, not after, the date is missed.",
                responsible="agent",
                accountable="Control Owner",
                trigger="Continuous",
                inputs=("agreed_plan",),
                outputs=("progress_status", "escalations"),
                automation=Automation.AUTO_NOTIFY,
                agent="orchestrator",
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A5",
                what="Verify closure against evidence before the gap is closed.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("agreed_plan", "evidence_records"),
                outputs=("closure_evidence",),
                automation=Automation.ASSIST,
                agent="evidence",
                ai_role=(
                    "State whether the evidence demonstrates closure. If it does "
                    "not, say what is missing rather than closing on assertion."
                ),
                task_class="evidence_summary",
                min_confidence=0.8,
                control_refs=("iso27001:10.2",),
                evidence=("gap_closure_evidence",),
            ),
            Activity(
                code="A6",
                what="Close the gap.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("closure_evidence",),
                outputs=("closed_gap",),
                automation=Automation.GATE,
                gate_type="compliance.gap_closure",
                gate_reason="statutory",
                control_refs=("iso27001:10.2",),
            ),
        ),
    ),
    Process(
        code="PR-CMP-04",
        name="Regulatory and standards change management",
        domain="CMP",
        purpose=(
            "Detects change in obligations and maps it to the controls and "
            "policies it affects, so the organisation learns about a new duty "
            "before an auditor tells it."
        ),
        owner_role="DPO",
        trigger="Continuous horizon scanning; confirmed change",
        cadence=Cadence.CONTINUOUS,
        clauses={
            "iso27001": ("4.2", "A.5.31", "A.5.34"),
            "iso22301": ("4.2",),
            "uk_gdpr": ("Art.24",),
        },
        outputs=("obligation_register", "impact_assessment", "change_actions"),
        kpis=("Lag from publication to impact assessment", "Obligations with named owner"),
        autonomy_tier="L2",
        notes=(
            "Detection and mapping are automated; interpretation is not. What a "
            "new obligation actually requires of this organisation is a legal "
            "judgement and stays with the DPO or counsel."
        ),
        activities=(
            Activity(
                code="A1",
                what="Monitor sources for change to law, regulation, standards and codes in scope.",
                responsible="agent",
                accountable="DPO",
                trigger="Continuous",
                inputs=("obligation_register", "source_feeds"),
                outputs=("candidate_changes",),
                automation=Automation.AUTO,
                agent="regulatory_watch",
                ai_role=None,
                control_refs=("iso27001:A.5.31",),
            ),
            Activity(
                code="A2",
                what="Triage each candidate for relevance to the organisation's scope.",
                responsible="agent",
                accountable="DPO",
                inputs=("candidate_changes", "scope_statement", "processing_records"),
                outputs=("relevant_changes",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role=(
                    "Say whether this applies to the organisation and why, citing "
                    "the provision. Where jurisdiction or applicability is "
                    "genuinely unclear, say so rather than guessing."
                ),
                task_class="classification",
                min_confidence=0.85,
                control_refs=("iso27001:A.5.31",),
            ),
            Activity(
                code="A3",
                what="Map the change to affected controls, policies, processes and records.",
                responsible="agent",
                accountable="DPO",
                inputs=("relevant_changes", "control_library", "policy_set"),
                outputs=("impact_map",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role="Identify every artefact the change touches and cite the link.",
                task_class="gap_analysis",
                min_confidence=0.8,
                control_refs=("iso27001:A.5.31",),
            ),
            Activity(
                code="A4",
                what="Interpret what the change requires of this organisation.",
                responsible="DPO",
                accountable="DPO",
                inputs=("relevant_changes", "impact_map"),
                outputs=("impact_assessment",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:A.5.31", "uk_gdpr:Art.24"),
                evidence=("regulatory_impact_assessment",),
            ),
            Activity(
                code="A5",
                what="Raise the actions needed to meet the obligation by its date.",
                responsible="agent",
                accountable="DPO",
                inputs=("impact_assessment",),
                outputs=("change_actions",),
                automation=Automation.AUTO_NOTIFY,
                agent="orchestrator",
                control_refs=("iso27001:10.1",),
            ),
        ),
    ),
    Process(
        code="PR-CMP-05",
        name="Certification and external audit readiness",
        domain="CMP",
        purpose=(
            "Keeps the organisation ready for a stage 1 or stage 2 audit at any "
            "time, and runs the audit itself when it comes."
        ),
        owner_role="CISO",
        trigger="Certification cycle, surveillance visit, or customer audit",
        cadence=Cadence.ANNUAL,
        clauses={
            "iso27001": ("9.2", "9.3", "10.2"),
            "iso22301": ("9.2", "9.3"),
        },
        outputs=("readiness_report", "evidence_pack", "audit_response"),
        kpis=("Certification blockers open", "Evidence pack assembly time", "External findings raised"),
        activities=(
            Activity(
                code="A1",
                what="Assess certification readiness and list every blocker with its owner.",
                responsible="agent",
                accountable="CISO",
                trigger="Continuous",
                inputs=("control_implementations", "gap_register", "audit_report", "management_review_minutes"),
                outputs=("readiness_report",),
                automation=Automation.AUTO,
                agent="reporting",
                ai_role=None,
                control_refs=("iso27001:9.3",),
            ),
            Activity(
                code="A2",
                what="Assemble the evidence pack for the clauses and controls in scope of the visit.",
                responsible="agent",
                accountable="CISO",
                inputs=("audit_scope", "evidence_records"),
                outputs=("evidence_pack",),
                automation=Automation.AUTO_NOTIFY,
                agent="evidence",
                ai_role="Assemble and index the evidence; flag anything expired or missing.",
                task_class="evidence_summary",
                control_refs=("iso27001:7.5.3",),
            ),
            Activity(
                code="A3",
                what="Draft responses to auditor requests and questions.",
                responsible="agent",
                accountable="CISO",
                trigger="On each auditor request",
                inputs=("auditor_request", "evidence_pack"),
                outputs=("draft_response",),
                automation=Automation.ASSIST,
                agent="audit",
                ai_role=(
                    "Draft a response grounded in the evidence on file. Never "
                    "assert a control operates without an evidence record behind it."
                ),
                task_class="evidence_summary",
                min_confidence=0.85,
                control_refs=("iso27001:9.2",),
            ),
            Activity(
                code="A4",
                what="Approve and issue each response to the external auditor.",
                responsible="CISO",
                accountable="CISO",
                inputs=("draft_response",),
                outputs=("audit_response",),
                automation=Automation.GATE,
                gate_type="audit.external_response",
                gate_reason="irreversible",
                control_refs=("iso27001:9.2",),
                evidence=("external_audit_response",),
            ),
        ),
    ),
)
