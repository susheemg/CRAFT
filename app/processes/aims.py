"""AI management system processes — ISO/IEC 42001:2023.

These sit alongside PR-AIG-01 to 03, which already carry AI inventory and risk
classification, human oversight, and post-market monitoring. What is added here
is what ISO/IEC 42001 asks for and those three do not: the AI policy and its
review, AI-specific risk assessment and treatment with a Statement of
Applicability, the AI system impact assessment, data governance for AI, the
information owed to interested parties, and the third-party allocation of
responsibility across the AI life cycle.

One boundary is worth stating plainly, because it is the mistake this track
exists to prevent. Clauses 6.1.2, 6.1.3, 6.1.4, 8.2, 8.3 and 8.4 are *not*
shared with ISO/IEC 27001 even though they carry the same numbers. An
information security risk assessment does not assess whether a model treats
people unfairly, and a data protection impact assessment says nothing about
societal impact. Nothing in this repository lets one discharge the other.
"""

from __future__ import annotations

from app.processes import Activity, Automation, Cadence, Process

AI_MANAGEMENT: tuple[Process, ...] = (
    Process(
        code="PR-AIG-04",
        name="Establish and review the AI policy",
        domain="AIG",
        purpose=(
            "Gives management direction on how AI is developed, bought and used, "
            "and keeps it current. The review is the part organisations skip, "
            "which is why the record of a review that changed nothing still has "
            "to exist."
        ),
        owner_role="CISO",
        trigger="AIMS scope approved, annual review, or a material change in AI use or regulation",
        cadence=Cadence.ANNUAL,
        clauses={"iso42001": ("4.3", "4.4", "5.2", "A.2.2", "A.2.3", "A.2.4", "A.9.3")},
        inputs=("context_analysis", "ai_inventory", "obligation_register"),
        outputs=("ai_policy", "policy_impact_register", "policy_review_record"),
        kpis=("AI policy reviewed within 12 months", "Every affected policy identified"),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A0",
                what=(
                    "Define the AI management system scope, naming the AI systems in "
                    "scope and the organisation's role for each — developer, provider, "
                    "user, deployer or partner."
                ),
                responsible="CISO",
                accountable="CISO",
                inputs=("context_analysis", "ai_inventory"),
                outputs=("aims_scope_statement",),
                automation=Automation.MANUAL,
                control_refs=("iso42001:4.3", "iso42001:4.4"),
                evidence=("aims_scope",),
            ),
            Activity(
                code="A1",
                what="Draft the AI policy covering development, procurement and use of AI systems.",
                responsible="agent",
                accountable="CISO",
                inputs=("context_analysis", "ai_inventory"),
                outputs=("draft_ai_policy",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role="Draft the policy and cite the obligation behind each commitment it makes.",
                task_class="policy_drafting",
                control_refs=("iso42001:A.2.2",),
            ),
            Activity(
                code="A2",
                what="Identify every other organisational policy the AI policy affects or is affected by.",
                responsible="agent",
                accountable="CISO",
                inputs=("draft_ai_policy", "policy_set"),
                outputs=("policy_impact_register",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Map overlaps and contradictions between the AI policy and existing policy.",
                task_class="control_assessment",
                control_refs=("iso42001:A.2.3",),
            ),
            Activity(
                code="A3",
                what="Record the objectives that guide responsible use of AI systems.",
                responsible="CISO",
                accountable="CISO",
                inputs=("draft_ai_policy",),
                outputs=("responsible_use_objectives",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.9.3",),
            ),
            Activity(
                code="A4",
                what="Approve and publish the AI policy.",
                responsible="CISO",
                accountable="CISO",
                inputs=("draft_ai_policy", "policy_impact_register"),
                outputs=("ai_policy",),
                automation=Automation.GATE,
                gate_type="ai.policy_approval",
                gate_reason="irreversible",
                evidence=("ai_policy_approval",),
            ),
            Activity(
                code="A5",
                what=(
                    "Run the scheduled review and record its outcome, including where "
                    "the conclusion was that nothing needed to change."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("ai_policy",),
                outputs=("policy_review_record",),
                automation=Automation.AUTO_NOTIFY,
                agent="reporting",
                control_refs=("iso42001:A.2.4",),
                evidence=("ai_policy_review",),
            ),
        ),
    ),
    Process(
        code="PR-AIG-05",
        name="AI resource documentation and competence",
        domain="AIG",
        purpose=(
            "Records what each AI system actually depends on — data, tooling, "
            "compute and people. Discovered from the live gateway configuration "
            "rather than from a spreadsheet, because an AI register maintained by "
            "memory is stale within two quarters."
        ),
        owner_role="CISO",
        trigger="A new AI system, model, dataset, tool or provider is introduced or changed",
        cadence=Cadence.CONTINUOUS,
        clauses={"iso42001": ("7.1", "7.2", "A.4.2", "A.4.3", "A.4.4", "A.4.5", "A.4.6")},
        inputs=("model_gateway_config", "ai_inventory", "supplier_register"),
        outputs=("ai_resource_register", "ai_competence_matrix"),
        kpis=("Zero configured models absent from the resource register",),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Discover configured providers, models and routes from the gateway "
                    "and propose resource entries for each AI system."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("model_gateway_config",),
                outputs=("proposed_ai_resources",),
                automation=Automation.AUTO_NOTIFY,
                agent="provenance",
                control_refs=("iso42001:A.4.2", "iso42001:A.4.5"),
            ),
            Activity(
                code="A2",
                what="Document the data and tooling resources each AI system relies on.",
                responsible="agent",
                accountable="CISO",
                inputs=("proposed_ai_resources", "ai_inventory"),
                outputs=("ai_resource_register",),
                automation=Automation.AUTO_NOTIFY,
                agent="provenance",
                control_refs=("iso42001:A.4.3", "iso42001:A.4.4"),
            ),
            Activity(
                code="A3",
                what=(
                    "Record the human resources and competences covering development, "
                    "deployment, operation, change, maintenance, transfer, "
                    "decommissioning, verification and integration."
                ),
                responsible="CISO",
                accountable="CISO",
                inputs=("ai_inventory",),
                outputs=("ai_competence_matrix",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.4.6", "iso42001:7.2"),
                evidence=("competence_record",),
            ),
            Activity(
                code="A4",
                what="Approve the resource entry before the AI system reaches production.",
                responsible="CISO",
                accountable="CISO",
                inputs=("ai_resource_register", "ai_competence_matrix"),
                outputs=("approved_ai_resources",),
                automation=Automation.GATE,
                gate_type="ai.resource_approval",
                gate_reason="high_risk",
            ),
        ),
    ),
    Process(
        code="PR-AIG-06",
        name="AI risk assessment, treatment and Statement of Applicability",
        domain="AIG",
        purpose=(
            "Assesses risk arising from AI on AI-specific criteria and produces the "
            "Statement of Applicability. Separate from the information security "
            "risk process on purpose: a security assessment does not ask whether a "
            "model treats people unfairly."
        ),
        owner_role="Risk Officer",
        trigger="New or materially changed AI system, planned interval, or an AI incident",
        cadence=Cadence.QUARTERLY,
        clauses={"iso42001": ("6.1.1", "6.1.2", "6.1.3", "8.2", "8.3")},
        inputs=("ai_inventory", "ai_resource_register", "risk_criteria"),
        outputs=("ai_risk_register", "ai_treatment_plan", "statement_of_applicability"),
        kpis=(
            "Every AI system assessed within its review period",
            "Zero controls claiming satisfaction from more than one inbound mapping",
        ),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Apply the AI risk criteria across the AI system life cycle.",
                responsible="agent",
                accountable="Risk Officer",
                inputs=("ai_inventory", "ai_resource_register"),
                outputs=("ai_risk_draft",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Draft AI risks by life cycle stage, distinguishing them from security risks.",
                task_class="risk_drafting",
                control_refs=("iso42001:6.1.2",),
            ),
            Activity(
                code="A2",
                what="Evaluate against the acceptance criteria and select treatment options.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("ai_risk_draft",),
                outputs=("ai_treatment_plan",),
                automation=Automation.ASSIST,
                agent="risk_analyst",
                ai_role="Propose treatment options with the reasoning for each.",
                task_class="risk_drafting",
                control_refs=("iso42001:6.1.3",),
            ),
            Activity(
                code="A3",
                what=(
                    "Determine the necessary controls and compare them against Annex A, "
                    "generating a Statement of Applicability entry for every reference "
                    "control with a justification, and a reason for every exclusion."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("ai_treatment_plan",),
                outputs=("draft_statement_of_applicability",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Draft applicability and justification per control; never mark one satisfied.",
                task_class="control_assessment",
                control_refs=("iso42001:6.1.3",),
            ),
            Activity(
                code="A4",
                what=(
                    "Report over-mapping: any control claiming satisfaction from more "
                    "than one inbound cross-framework mapping."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("draft_statement_of_applicability",),
                outputs=("over_mapping_report",),
                automation=Automation.AUTO,
                agent="reporting",
            ),
            Activity(
                code="A5",
                what="Accept residual AI risk, or record a time-bound exception.",
                responsible="Risk Officer",
                accountable="Risk Officer",
                inputs=("ai_treatment_plan",),
                outputs=("ai_risk_register",),
                automation=Automation.GATE,
                gate_type="ai.residual_risk_acceptance",
                gate_reason="high_risk",
                evidence=("residual_acceptance",),
            ),
            Activity(
                code="A6",
                what="Approve the Statement of Applicability.",
                responsible="CISO",
                accountable="CISO",
                inputs=("draft_statement_of_applicability", "over_mapping_report"),
                outputs=("statement_of_applicability",),
                automation=Automation.GATE,
                gate_type="ai.soa_approval",
                gate_reason="statutory",
                evidence=("soa_approval",),
            ),
        ),
        notes=(
            "Over-mapping is how integrated management systems inflate readiness. A4 "
            "reports it rather than resolving it, because deciding which mapping is "
            "the real one is a judgement."
        ),
    ),
    Process(
        code="PR-AIG-07",
        name="AI system impact assessment",
        domain="AIG",
        purpose=(
            "Assesses what an AI system does to individuals, to groups and to "
            "society. The three dimensions are assessed and recorded separately so "
            "that answering two of three cannot look like a finished assessment."
        ),
        owner_role="DPO",
        trigger="New AI system, material change, periodic review, incident, or regulatory change",
        cadence=Cadence.EVENT,
        clauses={"iso42001": ("6.1.4", "8.4", "A.5.2", "A.5.3", "A.5.4", "A.5.5")},
        inputs=("ai_inventory", "ai_data_provenance", "evaluation_results", "incident_register"),
        outputs=("ai_impact_assessment",),
        kpis=(
            "Approved assessment predates deployment in 100% of cases",
            "Every approved assessment names a human approver",
        ),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Assemble the inputs: intended use, affected parties, data "
                    "provenance, evaluation results and prior incidents."
                ),
                responsible="agent",
                accountable="DPO",
                inputs=("ai_inventory", "ai_data_provenance", "incident_register"),
                outputs=("impact_assessment_inputs",),
                automation=Automation.AUTO_NOTIFY,
                agent="ai_impact",
                control_refs=("iso42001:A.5.2",),
            ),
            Activity(
                code="A2",
                what=(
                    "Draft the assessment across the individual, group and societal "
                    "dimensions, with benefits and mitigations."
                ),
                responsible="agent",
                accountable="DPO",
                inputs=("impact_assessment_inputs",),
                outputs=("draft_impact_assessment",),
                automation=Automation.ASSIST,
                agent="ai_impact",
                ai_role=(
                    "Draft each impact dimension separately and say explicitly where the "
                    "evidence does not support a conclusion."
                ),
                task_class="impact_assessment",
                min_confidence=0.9,
                control_refs=("iso42001:A.5.4", "iso42001:A.5.5"),
            ),
            Activity(
                code="A3",
                what=(
                    "Review and complete the assessment, adding the judgements a model "
                    "cannot make, with affected-party representation where relevant."
                ),
                responsible="DPO",
                accountable="DPO",
                inputs=("draft_impact_assessment",),
                outputs=("completed_impact_assessment",),
                automation=Automation.MANUAL,
                control_refs=("iso42001:6.1.4",),
            ),
            Activity(
                code="A4",
                what=(
                    "Where personal data is involved, cross-reference the data protection "
                    "impact assessment without treating either as satisfying the other."
                ),
                responsible="DPO",
                accountable="DPO",
                inputs=("completed_impact_assessment", "dpia_register"),
                outputs=("dpia_cross_reference",),
                automation=Automation.ASSIST,
                agent="privacy",
                ai_role="Identify overlaps and, more importantly, what each assessment does not cover.",
                task_class="dpia_drafting",
            ),
            Activity(
                code="A5",
                what="Approve the assessment and set its retention period.",
                responsible="CISO",
                accountable="CISO",
                inputs=("completed_impact_assessment",),
                outputs=("ai_impact_assessment",),
                automation=Automation.GATE,
                gate_type="ai.impact_assessment_approval",
                gate_reason="statutory",
                control_refs=("iso42001:A.5.3", "iso42001:8.4"),
                evidence=("ai_impact_approval",),
            ),
        ),
        notes=(
            "A2 is the lowest-autonomy agent step in the repository. A model drafting "
            "an assessment of what an AI estate does to people — including the estate "
            "it belongs to — produces something fluent, complete-looking and "
            "unaccountable, so the database refuses an approved assessment that names "
            "no human approver."
        ),
    ),
    Process(
        code="PR-AIG-08",
        name="Data governance for AI systems",
        domain="AIG",
        purpose=(
            "Records where the data came from, on what basis, at what quality and "
            "prepared how — for every dataset an AI system trains on or retrieves "
            "from."
        ),
        owner_role="DPO",
        trigger="A dataset is acquired, prepared, changed or retired",
        cadence=Cadence.CONTINUOUS,
        clauses={"iso42001": ("A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6")},
        inputs=("dataset_registry", "processing_records"),
        outputs=("ai_data_provenance", "data_quality_results"),
        kpis=("Zero datasets promoted without a provenance record and a quality result",),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what="Record acquisition and selection details for each dataset.",
                responsible="agent",
                accountable="DPO",
                inputs=("dataset_registry",),
                outputs=("acquisition_records",),
                automation=Automation.AUTO_NOTIFY,
                agent="provenance",
                control_refs=("iso42001:A.7.3",),
            ),
            Activity(
                code="A2",
                what="Apply the data quality criteria and record the result.",
                responsible="agent",
                accountable="DPO",
                inputs=("acquisition_records",),
                outputs=("data_quality_results",),
                automation=Automation.AUTO,
                agent="provenance",
                control_refs=("iso42001:A.7.4",),
            ),
            Activity(
                code="A3",
                what="Record provenance across the life cycles of the data and the AI system.",
                responsible="agent",
                accountable="DPO",
                inputs=("acquisition_records", "data_quality_results"),
                outputs=("ai_data_provenance",),
                automation=Automation.AUTO_NOTIFY,
                agent="provenance",
                control_refs=("iso42001:A.7.5",),
                evidence=("provenance_record",),
            ),
            Activity(
                code="A4",
                what="Record the preparation methods used and the criteria for choosing them.",
                responsible="Control Owner",
                accountable="DPO",
                inputs=("ai_data_provenance",),
                outputs=("preparation_records",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.7.6", "iso42001:A.7.2"),
            ),
            Activity(
                code="A5",
                what=(
                    "Where the dataset contains personal data, link it to the processing "
                    "record and confirm the lawful basis."
                ),
                responsible="DPO",
                accountable="DPO",
                inputs=("ai_data_provenance", "processing_records"),
                outputs=("lawful_basis_confirmation",),
                automation=Automation.ASSIST,
                agent="privacy",
                ai_role="Identify datasets with personal data and no linked processing record.",
                task_class="dpia_drafting",
                control_refs=("uk_gdpr:Art.30",),
            ),
            Activity(
                code="A6",
                what="Sample-review the provenance entries the agent recorded.",
                responsible="Control Owner",
                accountable="DPO",
                inputs=("ai_data_provenance",),
                outputs=("provenance_review",),
                automation=Automation.MANUAL,
            ),
        ),
        notes=(
            "A6 exists because the provenance agent writes final records rather than "
            "proposals. Bounded autonomy needs a sampling review behind it, or it is "
            "just unattended writing."
        ),
    ),
    Process(
        code="PR-AIG-09",
        name="Information for interested parties and AI incident communication",
        domain="AIG",
        purpose=(
            "Gives users what they need to use the system within its intended use, "
            "gives outsiders a way to report harm, and makes sure both reach "
            "somebody when an AI incident occurs."
        ),
        owner_role="CISO",
        trigger="System documentation change, an adverse impact report, or an AI incident",
        cadence=Cadence.CONTINUOUS,
        clauses={"iso42001": ("7.4", "7.5", "A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.3.3", "A.6.2.7")},
        inputs=("ai_inventory", "incident_register", "obligation_register"),
        outputs=("ai_user_documentation", "adverse_impact_channel", "ai_incident_communications"),
        kpis=("Adverse impact reports acknowledged within the declared window",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Publish the information users need to operate the AI system within "
                    "its intended use, and the technical documentation each interested-"
                    "party category requires."
                ),
                responsible="agent",
                accountable="CISO",
                inputs=("ai_inventory",),
                outputs=("ai_user_documentation",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Draft user-facing documentation covering intended use and limitations.",
                task_class="policy_drafting",
                control_refs=("iso42001:A.8.2", "iso42001:A.6.2.7", "iso42001:7.5"),
            ),
            Activity(
                code="A2",
                what=(
                    "Operate an external channel through which interested parties can "
                    "report adverse impacts, and a concerns channel that does not route "
                    "through the owner of the system being questioned."
                ),
                responsible="Control Owner",
                accountable="CISO",
                outputs=("adverse_impact_channel",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.8.3", "iso42001:A.3.3"),
            ),
            Activity(
                code="A3",
                what="Classify an incoming report, link it to the AI system and harm type, and raise an incident.",
                responsible="agent",
                accountable="CISO",
                inputs=("adverse_impact_channel",),
                outputs=("ai_incident_link",),
                automation=Automation.ASSIST,
                agent="incident",
                ai_role="Classify the harm type and propose severity; do not close anything.",
                task_class="classification",
                control_refs=("iso42001:A.8.4",),
            ),
            Activity(
                code="A4",
                what="Execute the incident communication plan for users of the AI system.",
                responsible="CISO",
                accountable="CISO",
                inputs=("ai_incident_link",),
                outputs=("ai_incident_communications",),
                automation=Automation.GATE,
                gate_type="ai.external_communication",
                gate_reason="statutory",
                control_refs=("iso42001:A.8.4", "iso42001:7.4"),
            ),
            Activity(
                code="A5",
                what="Maintain the register of reporting obligations to interested parties and supervisory bodies.",
                responsible="agent",
                accountable="CISO",
                inputs=("obligation_register",),
                outputs=("ai_reporting_obligations",),
                automation=Automation.ASSIST,
                agent="regulatory_watch",
                ai_role="Propose obligation entries with a retrievable source for each.",
                task_class="gap_analysis",
                control_refs=("iso42001:A.8.5",),
            ),
        ),
    ),
    Process(
        code="PR-AIG-10",
        name="Responsible use of AI systems and agent mandates",
        domain="AIG",
        purpose=(
            "Governs how AI is actually used, including this platform's own agents. "
            "Every agent runs under an approved charter with a tier, tool grants, "
            "prohibited actions, a budget and a kill switch — enforced at the "
            "gateway, not requested in a prompt."
        ),
        owner_role="CISO",
        trigger="An agent charter is created or changed, or usage drifts from intended use",
        cadence=Cadence.CONTINUOUS,
        clauses={"iso42001": ("5.3", "A.9.2", "A.9.4", "A.3.2", "A.6.2.6", "A.6.2.8")},
        inputs=("ai_inventory", "agent_registry", "model_gateway_config"),
        outputs=("agent_charters", "gateway_policy_evidence", "drift_reports"),
        kpis=(
            "Zero agent identities enabled without a current approved charter",
            "Zero agents holding gate authority",
        ),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what="Define the processes governing responsible use of AI systems.",
                responsible="CISO",
                accountable="CISO",
                inputs=("ai_policy",),
                outputs=("responsible_use_processes",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.9.2",),
            ),
            Activity(
                code="A2",
                what=(
                    "Approve an agent charter for every agent identity: purpose, "
                    "autonomy tier, tool grants, prohibited actions, budgets and kill "
                    "switch."
                ),
                responsible="CISO",
                accountable="CISO",
                inputs=("agent_registry",),
                outputs=("agent_charters",),
                automation=Automation.GATE,
                gate_type="ai.agent_charter_approval",
                gate_reason="irreversible",
                control_refs=("iso42001:A.3.2", "iso42001:A.9.2", "iso42001:5.3"),
                evidence=("agent_charter_approval",),
            ),
            Activity(
                code="A3",
                what=(
                    "Enforce intended-use policy at the model gateway: provider routing, "
                    "tool allowlists, output filters and token budgets."
                ),
                responsible="Platform Admin",
                accountable="CISO",
                inputs=("agent_charters", "model_gateway_config"),
                outputs=("gateway_policy_evidence",),
                automation=Automation.AUTO,
                control_refs=("iso42001:A.9.4",),
                evidence=("gateway_policy_test",),
            ),
            Activity(
                code="A4",
                what=(
                    "Enable event logging for the declared life cycle phases, at minimum "
                    "while the system is in use."
                ),
                responsible="Platform Admin",
                accountable="CISO",
                inputs=("ai_inventory",),
                outputs=("event_logging_configuration",),
                automation=Automation.AUTO,
                control_refs=("iso42001:A.6.2.8",),
            ),
            Activity(
                code="A5",
                what="Detect and raise drift between recorded intended use and observed invocation patterns.",
                responsible="agent",
                accountable="CISO",
                inputs=("model_invocations", "ai_inventory"),
                outputs=("drift_reports",),
                automation=Automation.ASSIST,
                agent="incident",
                ai_role="Describe how observed use diverges from recorded intended use.",
                task_class="classification",
                control_refs=("iso42001:A.6.2.6",),
            ),
            Activity(
                code="A6",
                what="Review agent budget ledgers, escalation counts and any disabled charters.",
                responsible="CISO",
                accountable="CISO",
                inputs=("agent_charters",),
                outputs=("agent_oversight_review",),
                automation=Automation.ASSIST,
                evidence=("agent_oversight_record",),
            ),
        ),
        notes=(
            "A3 is deliberately marked as an enforced control rather than an assisted "
            "one. Instructions inside a prompt are not a control; only enforcement "
            "outside the model counts as evidence here."
        ),
    ),
    Process(
        code="PR-AIG-11",
        name="AI third-party and customer relationships",
        domain="AIG",
        purpose=(
            "Apportions responsibility across the AI supply chain and keeps the "
            "organisation accountable for the part it kept. Reuses the supplier "
            "register rather than creating a second one."
        ),
        owner_role="Control Owner",
        trigger="A new AI supplier, partner or customer relationship, or annual reassessment",
        cadence=Cadence.ANNUAL,
        clauses={"iso42001": ("A.10.2", "A.10.3", "A.10.4"), "iso27001": ("A.5.19",)},
        inputs=("supplier_register", "ai_inventory", "contract_register"),
        outputs=("ai_responsibility_allocation", "ai_supplier_assurance"),
        kpis=("Every AI supplier has a current assurance status",),
        autonomy_tier="L2",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Allocate life cycle responsibilities across the organisation, "
                    "partners, suppliers, customers and other third parties."
                ),
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("ai_inventory", "supplier_register"),
                outputs=("ai_responsibility_allocation",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.10.2",),
            ),
            Activity(
                code="A2",
                what=(
                    "Assess whether supplier services, products or materials align with "
                    "the organisation's responsible AI approach."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("supplier_register", "ai_responsibility_allocation"),
                outputs=("ai_supplier_findings",),
                automation=Automation.ASSIST,
                agent="third_party",
                ai_role="Draft the assurance finding; do not set the assurance status.",
                task_class="supplier_assessment",
                control_refs=("iso42001:A.10.3", "iso27001:A.5.19"),
            ),
            Activity(
                code="A3",
                what=(
                    "Reflect the allocation in contractual terms: model change "
                    "notification, evaluation access and incident reporting."
                ),
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("ai_responsibility_allocation",),
                outputs=("ai_contract_terms",),
                automation=Automation.MANUAL,
                control_refs=("iso42001:A.10.2",),
            ),
            Activity(
                code="A4",
                what=(
                    "Capture customer expectations relating to AI and feed them into the "
                    "responsible use objectives."
                ),
                responsible="Control Owner",
                accountable="CISO",
                outputs=("ai_customer_expectations",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.10.4",),
            ),
            Activity(
                code="A5",
                what="Set the supplier assurance status, or record a time-bound exception.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("ai_supplier_findings",),
                outputs=("ai_supplier_assurance",),
                automation=Automation.GATE,
                gate_type="ai.supplier_assurance",
                gate_reason="high_risk",
                evidence=("supplier_assurance_decision",),
            ),
            Activity(
                code="A6",
                what="Reassess on schedule and on any supplier model or policy change.",
                responsible="agent",
                accountable="Control Owner",
                inputs=("ai_supplier_assurance",),
                outputs=("ai_supplier_reassessment",),
                automation=Automation.AUTO_NOTIFY,
                agent="third_party",
                control_refs=("iso42001:A.10.3",),
            ),
        ),
    ),
    Process(
        code="PR-AIG-12",
        name="Responsible AI system life cycle and deployment control",
        domain="AIG",
        purpose=(
            "Governs an AI system from requirements through verification to "
            "deployment and operation, so that the impact assessment, the "
            "evaluation criteria and the logging configuration are all in place "
            "before anything reaches a user."
        ),
        owner_role="Control Owner",
        trigger="An AI system enters design, or a release candidate is ready",
        cadence=Cadence.EVENT,
        clauses={
            "iso42001": (
                "6.2", "6.3", "8.1", "A.6.1.2", "A.6.2.3", "A.6.2.4", "A.6.2.5",
            )
        },
        inputs=("ai_inventory", "ai_impact_assessment", "ai_resource_register"),
        outputs=("ai_design_documentation", "evaluation_report", "ai_deployment_decision"),
        kpis=("Zero deployments without an approved impact assessment predating them",),
        autonomy_tier="L3",
        activities=(
            Activity(
                code="A1",
                what=(
                    "Record the objectives guiding responsible development and the "
                    "measures taken to achieve them."
                ),
                responsible="Control Owner",
                accountable="CISO",
                outputs=("responsible_development_objectives",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.6.1.2", "iso42001:6.2"),
            ),
            Activity(
                code="A2",
                what=(
                    "Document design and development against objectives, requirements "
                    "and specification criteria."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("responsible_development_objectives",),
                outputs=("ai_design_documentation",),
                automation=Automation.ASSIST,
                agent="control_assessor",
                ai_role="Draft the design record and flag requirements with no design decision behind them.",
                task_class="policy_drafting",
                control_refs=("iso42001:A.6.2.3",),
            ),
            Activity(
                code="A3",
                what=(
                    "Run verification and validation against the declared criteria: "
                    "accuracy, robustness, prompt injection resistance and refusal "
                    "behaviour."
                ),
                responsible="agent",
                accountable="Control Owner",
                inputs=("ai_design_documentation",),
                outputs=("evaluation_report",),
                automation=Automation.AUTO_NOTIFY,
                agent="verification",
                control_refs=("iso42001:A.6.2.4",),
                evidence=("evaluation_report",),
            ),
            Activity(
                code="A4",
                what="Confirm the deployment prerequisites and record the deployment plan.",
                responsible="Control Owner",
                accountable="Control Owner",
                inputs=("evaluation_report", "ai_impact_assessment"),
                outputs=("ai_deployment_plan",),
                automation=Automation.ASSIST,
                control_refs=("iso42001:A.6.2.5", "iso42001:6.3"),
            ),
            Activity(
                code="A5",
                what=(
                    "Deployment gate: approved impact assessment, evaluation criteria "
                    "met, deployment plan recorded, event logging enabled."
                ),
                responsible="CISO",
                accountable="CISO",
                inputs=("ai_deployment_plan",),
                outputs=("ai_deployment_decision",),
                automation=Automation.GATE,
                gate_type="ai.deployment_approval",
                gate_reason="irreversible",
                control_refs=("iso42001:A.6.2.5", "iso42001:8.1"),
                evidence=("ai_deployment_approval",),
            ),
        ),
    ),
)
