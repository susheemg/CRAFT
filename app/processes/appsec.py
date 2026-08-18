"""Application security processes — ISO/IEC 27034-1:2011 and -2:2015.

Two loops, and they are not the same loop.

The **ONF management process** (PR-APS-01 to 05) runs at organisation level and
iterates: design, implement, monitor, improve, audit. It maintains the ASC
library everything else draws on.

The **Application Security Management Process** (PR-APS-06 to 10) runs once per
application project: specify, assess risk and set a target, build the ANF,
perform and measure the controls, then audit.

The junction with ISO/IEC 42001 is PR-APS-06 activity A4. An application that
carries an AI system runs both this track and the AI governance track. It does
not run one and claim the other, and a mapping between the two frameworks does
not change that.
"""

from __future__ import annotations

from app.processes import Activity, Automation, Cadence, Process

# ==========================================================================
# ONF management — the organisation-level loop
# ==========================================================================
ONF_MANAGEMENT: tuple[Process, ...] = (
    Process(
        code="PR-APS-01",
        name="Design the Organization Normative Framework iteration",
        domain="APS",
        purpose=(
            "Sets what application security means in this organisation for this "
            "iteration: the contexts, the levels of trust, and the Application "
            "Security Controls that make up the library. Built iteratively "
            "because an ONF attempted in one pass is never finished."
        ),
        owner_role="CISO",
        trigger="Committee mandated, or the improvement loop has raised a redesign need",
        cadence=Cadence.ANNUAL,
        # Claims ISO/IEC 42001 A.6.1.3 (processes for responsible design) but not
        # 6.1.3: the ASC library is not the AI Statement of Applicability.
        clauses={"iso27001": ("6.1.3", "8.1"), "iso42001": ("A.6.1.3",)},
        inputs=("context_analysis", "risk_register", "audit_findings"),
        outputs=("onf_iteration", "asc_library", "trust_levels", "lifecycle_stage_map"),
        kpis=(
            "Every ASC carries both an activity and a measurement",
            "Exactly one level zero defined per iteration",
        ),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Set application security goals and the scope of this ONF iteration.",
                responsible="CISO",
                accountable="CISO",
                inputs=("context_analysis", "audit_findings"),
                outputs=("onf_iteration_scope",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:6.1.3",),
            ),
            Activity(
                code="A2",
                what=(
                    "Document the business, regulatory and technological contexts "
                    "that apply to applications in this iteration."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("obligation_register", "asset_register", "supplier_register"),
                outputs=("onf_contexts",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role=(
                    "Propose context entries with a retrievable source for each, and "
                    "flag which have changed since the last iteration."
                ),
                task_class="gap_analysis",
                control_refs=("iso27001:4.1",),
            ),
            Activity(
                code="A3",
                what=(
                    "Define the levels of trust, including exactly one level zero — "
                    "the floor a project team cannot go below."
                ),
                responsible="CISO",
                accountable="CISO",
                inputs=("onf_iteration_scope",),
                outputs=("trust_levels",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:6.1.3",),
                evidence=("trust_level_definition",),
            ),
            Activity(
                code="A4",
                what=(
                    "Design the Application Security Controls for this iteration. Each "
                    "needs a security activity and a verification measurement performed "
                    "by different parties — one without the other is a checklist item."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("trust_levels", "onf_contexts", "risk_register"),
                outputs=("asc_library",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role=(
                    "Draft ASC definitions with both halves specified, and flag any "
                    "control whose measurement an agent should not be permitted to make."
                ),
                task_class="asc_design",
                control_refs=("iso27001:6.1.3", "iso42001:A.6.1.3"),
            ),
            Activity(
                code="A5",
                what=(
                    "Map the organisation's own delivery stages onto the reference life "
                    "cycle model, so an ASC can be issued in the delivery team's own words."
                ),
                responsible="Control Owner",
                accountable="CISO",
                inputs=("asc_library",),
                outputs=("lifecycle_stage_map",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Propose the mapping and identify reference stages with no local equivalent.",
                task_class="gap_analysis",
            ),
            Activity(
                code="A6",
                what="Approve the iteration scope and the ASC library.",
                responsible="CISO",
                accountable="CISO",
                inputs=("asc_library", "trust_levels", "lifecycle_stage_map"),
                outputs=("approved_onf_iteration",),
                automation=Automation.GATE,
                gate_type="onf_iteration_approval",
                gate_reason="irreversible",
                control_refs=("iso27001:5.1",),
            ),
        ),
        notes=(
            "A reference stage with no local stage mapped to it makes every ASC placed "
            "there unschedulable, which is why A5 reports the gap rather than skipping it."
        ),
    ),
    Process(
        code="PR-APS-02",
        name="Implement and communicate the ONF",
        domain="APS",
        purpose=(
            "Turns approved ASC definitions into things delivery teams can actually "
            "do: pipeline automation for the automatable ones, training for the rest, "
            "and publication in each team's own vocabulary."
        ),
        owner_role="Control Owner",
        trigger="ONF iteration approved",
        cadence=Cadence.ANNUAL,
        clauses={"iso27001": ("7.2", "7.3", "8.1"), "iso42001": ("7.2", "7.3")},
        inputs=("approved_onf_iteration",),
        outputs=("published_asc_library", "pipeline_controls", "training_records"),
        kpis=("Every implemented ASC has a trained actor",),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what="Assess the impact and complexity of building each designed ONF element.",
                responsible="Control Owner",
                accountable="CISO",
                inputs=("approved_onf_iteration",),
                outputs=("implementation_plan",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Estimate effort per element and identify dependencies between them.",
                task_class="asc_design",
            ),
            Activity(
                code="A2",
                what="Build the automation an automatable ASC needs in the delivery pipeline.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("implementation_plan",),
                outputs=("pipeline_controls",),
                automation=Automation.AUTO_NOTIFY,
                agent="appsec",
                control_refs=("iso27001:A.8.28",),
            ),
            Activity(
                code="A3",
                what=(
                    "Translate each ASC into the delivery team's own stage vocabulary "
                    "using the life cycle mapping."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("asc_library", "lifecycle_stage_map"),
                outputs=("translated_asc_set",),
                automation=Automation.AUTO,
                agent="onf_steward",
            ),
            Activity(
                code="A4",
                what="Determine and deliver the training each actor needs to use the element.",
                responsible="Control Owner",
                accountable="CISO",
                inputs=("translated_asc_set",),
                outputs=("training_records",),
                automation=Automation.ASSIST,
                control_refs=("iso27001:7.2", "iso42001:7.2"),
                evidence=("training_completion",),
            ),
            Activity(
                code="A5",
                what="Publish the ASC library to delivery teams and to the governed tool surface.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("translated_asc_set",),
                outputs=("published_asc_library",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
            ),
        ),
    ),
    Process(
        code="PR-APS-03",
        name="Monitor and review the ONF",
        domain="APS",
        purpose=(
            "Tests whether the ONF is doing anything. An ASC that is never measured, "
            "or that always passes, is usually measuring nothing — surfacing that "
            "matters more than the pass rate."
        ),
        owner_role="Control Owner",
        trigger="Quarterly, or a change in a business, regulatory or technological context",
        cadence=Cadence.QUARTERLY,
        clauses={"iso27001": ("9.1",), "iso42001": ("9.1",)},
        inputs=("published_asc_library", "asc_evidence"),
        outputs=("onf_review_record", "improvement_candidates"),
        kpis=(
            "Every application carries a targeted and an actual level of trust",
            "Zero ASCs with no measurement in the review period",
        ),
        autonomy_tier="L4",
        activities=(
            Activity(
                code="A1",
                what="Apply the defined measurement methods to each ONF element.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("asc_evidence",),
                outputs=("onf_measurement_set",),
                automation=Automation.AUTO,
                agent="reporting",
                control_refs=("iso27001:9.1",),
            ),
            Activity(
                code="A2",
                what=(
                    "Confirm every application in the register carries both a targeted "
                    "and an actual level of trust."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("application_register",),
                outputs=("level_of_trust_completeness",),
                automation=Automation.AUTO,
                agent="reporting",
            ),
            Activity(
                code="A3",
                what="Confirm every application has had a risk assessment inside its review period.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("application_register", "risk_register"),
                outputs=("assessment_currency_report",),
                automation=Automation.AUTO,
                agent="reporting",
            ),
            Activity(
                code="A4",
                what=(
                    "Flag ASCs that are never measured, always pass, or always fail as "
                    "candidates for redesign."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("onf_measurement_set",),
                outputs=("improvement_candidates",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Explain why each flagged ASC is not discriminating, and propose a change.",
                task_class="asc_design",
            ),
            Activity(
                code="A5",
                what="Record the review results and the improvements they identify.",
                responsible="Control Owner",
                accountable="CISO",
                inputs=("onf_measurement_set", "improvement_candidates"),
                outputs=("onf_review_record",),
                automation=Automation.ASSIST,
                evidence=("onf_review",),
                control_refs=("iso27001:9.1",),
            ),
        ),
    ),
    Process(
        code="PR-APS-04",
        name="Improve the ONF from project feedback",
        domain="APS",
        purpose=(
            "Closes the loop the standard calls for explicitly: what application "
            "projects learned goes back into the library, rather than staying in the "
            "project that learned it."
        ),
        owner_role="Control Owner",
        trigger="Review findings, project feedback, an audit finding, or an incident",
        cadence=Cadence.QUARTERLY,
        clauses={"iso27001": ("10.1", "10.2"), "iso42001": ("10.1", "10.2")},
        inputs=("onf_review_record", "asc_evidence", "audit_findings"),
        outputs=("onf_backlog",),
        kpis=("Repeated waivers on the same ASC trigger a redesign within one iteration",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Collect feedback from completed application projects on ASC usability and cost.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("asc_evidence",),
                outputs=("project_feedback",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
            ),
            Activity(
                code="A2",
                what="Analyse root causes behind failed measurements and repeated waivers.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("project_feedback", "onf_review_record"),
                outputs=("root_cause_analysis",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Group failures by cause and distinguish a bad control from a bad process.",
                task_class="asc_design",
                control_refs=("iso27001:10.2",),
            ),
            Activity(
                code="A3",
                what="Decide which ONF elements to redesign in the next iteration.",
                responsible="CISO",
                accountable="CISO",
                inputs=("root_cause_analysis",),
                outputs=("onf_backlog",),
                automation=Automation.MANUAL,
            ),
        ),
    ),
    Process(
        code="PR-APS-05",
        name="Audit the ONF",
        domain="APS",
        purpose=(
            "Independent verification that the ONF exists, is used, and that "
            "applications comply with it. Conclusions are a human act; the agent "
            "assembles the pack and stops there."
        ),
        owner_role="Internal Auditor",
        trigger="Audit programme schedule",
        cadence=Cadence.ANNUAL,
        clauses={"iso27001": ("9.2",), "iso42001": ("9.2",)},
        inputs=("asc_library", "asc_evidence", "onf_review_record"),
        outputs=("onf_audit_report", "audit_findings"),
        kpis=("Auditor independent of the ONF committee in 100% of audits",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Establish the audit programme and confirm auditor competence and independence.",
                responsible="Internal Auditor",
                accountable="CISO",
                outputs=("onf_audit_programme",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:9.2",),
            ),
            Activity(
                code="A2",
                what=(
                    "Assemble the audit pack: ONF elements, responsibility records, "
                    "change history and prior findings."
                ),
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("asc_library", "asc_evidence"),
                outputs=("onf_audit_pack",),
                automation=Automation.AUTO_NOTIFY,
                agent="audit",
            ),
            Activity(
                code="A3",
                what=(
                    "Verify that the verification activities of each ONF sub-process were "
                    "performed, and that applications comply with the ONF."
                ),
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("onf_audit_pack",),
                outputs=("onf_audit_findings",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:9.2", "iso42001:9.2"),
                evidence=("audit_working_paper",),
            ),
            Activity(
                code="A4",
                what="Record findings, root causes and agreed remediation with owners and dates.",
                responsible="Internal Auditor",
                accountable="CISO",
                inputs=("onf_audit_findings",),
                outputs=("onf_audit_report", "audit_findings"),
                automation=Automation.ASSIST,
                control_refs=("iso27001:10.2",),
            ),
        ),
        notes=(
            "No agent performs A3 or A4. An agent auditing the controls that bound "
            "agents is the clearest case where fluency would be mistaken for assurance."
        ),
    ),
)


# ==========================================================================
# ASMP — the per-application loop
# ==========================================================================
ASMP: tuple[Process, ...] = (
    Process(
        code="PR-APS-06",
        name="Specify application requirements and environment",
        domain="APS",
        purpose=(
            "Registers the application and fixes which contexts apply to it, which is "
            "what makes every later selection of controls defensible rather than "
            "arbitrary."
        ),
        owner_role="Control Owner",
        trigger="A new application project starts, or an existing application enters the register",
        cadence=Cadence.EVENT,
        clauses={"iso27001": ("8.1",), "iso42001": ("A.6.2.2",)},
        inputs=("onf_contexts", "asset_register"),
        outputs=("application_record", "selected_contexts"),
        kpis=("Zero applications in production without a register entry",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Register the application with its owner, sourcing model, criticality "
                    "and whether it carries an AI system."
                ),
                responsible="Control Owner",
                accountable="Control Owner",
                outputs=("application_record",),
                automation=Automation.ASSIST,
                control_refs=("iso27001:A.5.9",),
            ),
            Activity(
                code="A2",
                what="Select the business, regulatory and technological contexts that apply.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("onf_contexts", "application_record"),
                outputs=("selected_contexts",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
            ),
            Activity(
                code="A3",
                what="Record actors, specifications and the information the application handles.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("application_record",),
                outputs=("application_specification",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Draft the specification and classify the data elements it names.",
                task_class="asc_design",
                control_refs=("iso27001:A.5.12",),
            ),
            Activity(
                code="A4",
                what=(
                    "Where the application carries an AI system, create the AI system "
                    "register entry and hand off to the AI governance track."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("application_record",),
                outputs=("ai_system_record",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
                control_refs=("iso42001:A.6.2.2",),
            ),
        ),
        notes=(
            "A4 is the single junction between ISO/IEC 27034 and ISO/IEC 42001. An "
            "AI-bearing application runs both tracks."
        ),
    ),
    Process(
        code="PR-APS-07",
        name="Assess application security risk and set the targeted level of trust",
        domain="APS",
        purpose=(
            "Produces the one number the rest of the ASMP depends on. The owner "
            "approves it, which is what makes the control set a decision rather than "
            "a default."
        ),
        owner_role="Risk Officer",
        trigger="Application requirements baselined, or a material change to the application or its contexts",
        cadence=Cadence.EVENT,
        # Deliberately does NOT claim ISO/IEC 42001 6.1.2 or 8.2. An application
        # security risk assessment asks what an attacker could do; the AI risk
        # assessment asks what the system could do to people. PR-AIG-06 owns that.
        clauses={"iso27001": ("6.1.2", "8.2")},
        inputs=("application_record", "selected_contexts", "application_specification"),
        outputs=("application_risk_assessment", "targeted_level_of_trust"),
        kpis=("Targeted level of trust approved by a named owner in 100% of projects",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Identify threats, vulnerabilities and impacts at the application level.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("application_specification", "selected_contexts"),
                outputs=("application_threat_set",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Draft the threat and vulnerability set and cite the context that raises each.",
                task_class="risk_drafting",
                control_refs=("iso27001:6.1.2",),
            ),
            Activity(
                code="A2",
                what="Analyse and evaluate the risks against the organisation's criteria.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("application_threat_set",),
                outputs=("application_risk_assessment",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Propose inherent and residual scores with the reasoning for each.",
                task_class="risk_drafting",
            ),
            Activity(
                code="A3",
                what="Derive security requirements and propose a targeted level of trust.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("application_risk_assessment",),
                outputs=("proposed_level_of_trust",),
                automation=Automation.ASSIST,
            ),
            Activity(
                code="A4",
                what="The application owner approves the targeted level of trust.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("proposed_level_of_trust",),
                outputs=("targeted_level_of_trust",),
                automation=Automation.GATE,
                gate_type="targeted_level_of_trust",
                gate_reason="high_risk",
                evidence=("level_of_trust_approval",),
            ),
        ),
    ),
    Process(
        code="PR-APS-08",
        name="Create and maintain the Application Normative Framework",
        domain="APS",
        purpose=(
            "Selects from the library exactly the controls the target requires, in the "
            "project's own stage vocabulary. Level-zero controls come with it and "
            "cannot be removed."
        ),
        owner_role="Control Owner",
        trigger="Targeted level of trust approved, or a context or target change mid-project",
        cadence=Cadence.EVENT,
        # Selecting application security controls for a level of trust is not AI
        # risk treatment, so no ISO/IEC 42001 6.1.3 claim is made here.
        clauses={"iso27001": ("6.1.3", "8.1")},
        inputs=("targeted_level_of_trust", "asc_library", "lifecycle_stage_map"),
        outputs=("application_normative_framework",),
        kpis=("Zero level-zero controls waived",),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Select every ASC required at the targeted level of trust, including "
                    "all level-zero controls."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("targeted_level_of_trust", "asc_library"),
                outputs=("selected_asc_set",),
                automation=Automation.AUTO,
                agent="onf_steward",
                control_refs=("iso27001:6.1.3",),
            ),
            Activity(
                code="A2",
                what="Translate each selected ASC into the project's own life cycle stage.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("selected_asc_set", "lifecycle_stage_map"),
                outputs=("staged_asc_set",),
                automation=Automation.AUTO,
                agent="onf_steward",
            ),
            Activity(
                code="A3",
                what=(
                    "Derive the project life cycle by dropping stages the project does "
                    "not use — an in-house build has no acquisition stage."
                ),
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("staged_asc_set",),
                outputs=("project_lifecycle",),
                automation=Automation.ASSIST,
                agent="onf_steward",
                ai_role="Propose which stages are inapplicable and say why for each.",
                task_class="gap_analysis",
            ),
            Activity(
                code="A4",
                what="Record any waiver of a non-level-zero ASC with its reason and approver.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("staged_asc_set",),
                outputs=("asc_waivers",),
                automation=Automation.MANUAL,
                evidence=("asc_waiver",),
            ),
            Activity(
                code="A5",
                what="Issue the ANF to the project and verification teams.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("staged_asc_set", "project_lifecycle"),
                outputs=("application_normative_framework",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
            ),
        ),
        notes=(
            "Carrying dead stages makes an ANF look complied-with when it is only "
            "inapplicable, which is why A3 removes them explicitly rather than leaving "
            "them unmeasured."
        ),
    ),
    Process(
        code="PR-APS-09",
        name="Provision and operate the application under its ANF",
        domain="APS",
        purpose=(
            "Performs the controls and measures them, with the two halves done by "
            "different actors. The database refuses a measurement recorded by whoever "
            "performed the activity, so the separation is not advisory."
        ),
        owner_role="Control Owner",
        trigger="ANF issued",
        cadence=Cadence.CONTINUOUS,
        clauses={"iso27001": ("8.1", "A.8.28", "A.8.8"), "iso42001": ("8.3",)},
        inputs=("application_normative_framework",),
        outputs=("asc_evidence", "actual_level_of_trust"),
        kpis=(
            "Zero measurements recorded by the actor that performed the activity",
            "Failed measurements escalated within the declared window",
        ),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what="Perform the security activity of each ASC at its mapped stage.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("application_normative_framework",),
                outputs=("asc_activity_evidence",),
                automation=Automation.AUTO_NOTIFY,
                agent="appsec",
                control_refs=("iso27001:A.8.28", "iso27001:A.8.8", "iso27001:A.8.24"),
                evidence=("asc_activity",),
            ),
            Activity(
                code="A2",
                what=(
                    "Perform the verification measurement of each ASC. A different actor "
                    "from the one that performed the activity, always."
                ),
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("asc_activity_evidence",),
                outputs=("asc_measurement_evidence",),
                automation=Automation.AUTO_NOTIFY,
                agent="verification",
                evidence=("asc_measurement",),
            ),
            Activity(
                code="A3",
                what="Escalate any failed measurement to the application owner within the declared window.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("asc_measurement_evidence",),
                outputs=("asc_escalations",),
                automation=Automation.AUTO_NOTIFY,
                agent="verification",
                sla_hours=24,
            ),
            Activity(
                code="A4",
                what="Recompute the actual level of trust whenever a measurement is recorded.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("asc_measurement_evidence",),
                outputs=("actual_level_of_trust",),
                automation=Automation.AUTO,
                agent="reporting",
            ),
            Activity(
                code="A5",
                what=(
                    "Release gate: refuse promotion while the actual level of trust sits "
                    "below the target or a mandatory control lacks a passing measurement."
                ),
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("actual_level_of_trust",),
                outputs=("release_decision",),
                automation=Automation.GATE,
                gate_type="application_release",
                gate_reason="irreversible",
                control_refs=("iso42001:A.6.2.5",),
            ),
        ),
    ),
    Process(
        code="PR-APS-10",
        name="Audit the security of the application",
        domain="APS",
        purpose=(
            "Determines the actual level of trust and puts it in front of the owner, "
            "who either accepts it or mandates adjustments. This is the step that "
            "makes the target mean something."
        ),
        owner_role="Internal Auditor",
        trigger="Release candidate ready, periodic schedule, or application owner request",
        cadence=Cadence.EVENT,
        clauses={"iso27001": ("9.2",), "iso42001": ("9.2",)},
        inputs=("application_normative_framework", "asc_evidence"),
        outputs=("application_audit_report", "actual_level_of_trust"),
        kpis=("Actual level of trust signed off by an auditor who performed no activity",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Assemble the audit pack: every ASC, its activity record, its "
                    "measurement record and the supporting evidence."
                ),
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("asc_evidence",),
                outputs=("application_audit_pack",),
                automation=Automation.AUTO_NOTIFY,
                agent="audit",
            ),
            Activity(
                code="A2",
                what="Verify every measurement in the ANF was performed and produced the expected result.",
                responsible="Internal Auditor",
                accountable="Internal Auditor",
                inputs=("application_audit_pack",),
                outputs=("verification_conclusions",),
                automation=Automation.MANUAL,
                control_refs=("iso27001:9.2",),
                evidence=("audit_working_paper",),
            ),
            Activity(
                code="A3",
                what="Determine and record the actual level of trust.",
                responsible="agent",
                accountable="Internal Auditor",
                inputs=("verification_conclusions",),
                outputs=("actual_level_of_trust",),
                automation=Automation.AUTO,
                agent="reporting",
            ),
            Activity(
                code="A4",
                what="The application owner accepts the audit result, or mandates security adjustments.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("actual_level_of_trust", "verification_conclusions"),
                outputs=("application_audit_report",),
                automation=Automation.GATE,
                gate_type="application_security_acceptance",
                gate_reason="high_risk",
            ),
            Activity(
                code="A5",
                what="Feed lessons back to the ONF improvement loop.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("application_audit_report",),
                outputs=("project_feedback",),
                automation=Automation.AUTO_NOTIFY,
                agent="onf_steward",
                control_refs=("iso27001:10.1",),
            ),
        ),
    ),
)

APPLICATION_SECURITY: tuple[Process, ...] = ONF_MANAGEMENT + ASMP
