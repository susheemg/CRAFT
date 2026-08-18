"""Organization Normative Framework seed — ISO/IEC 27034.

Iteration 1 of the ONF: the reference life cycle model, four levels of trust,
the contexts the organisation operates in, the mapping from CRAFT's own delivery
stages onto the reference stages, and the starter Application Security Control
library.

Each ASC carries both halves the standard requires — the security activity the
project team performs and the verification measurement the verification team
performs — because an ASC with only one of them is a checklist item, not a
control.

``measurement_requires_human`` is set on exactly the controls where an agent
attestation would be worthless: independent human review, and every control that
governs the agent estate itself.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Reference model (ISO/IEC 27034-1 clause 8.1.2.7), paraphrased
# --------------------------------------------------------------------------
ASLCRM_LAYERS: list[tuple[str, str, int, str]] = [
    ("APP_MGMT", "Application management", 1,
     "Governance activities: project management and application operation management."),
    ("APP_PROV", "Application provisioning and operation", 2,
     "Obtaining, building, deploying and using the application itself."),
    ("INFRA_MGMT", "Infrastructure management", 3,
     "IT service management activities supporting the application."),
    ("APP_AUDIT", "Application audit", 4,
     "Control and verification activities across provisioning and operation."),
]

ASLCRM_STAGES: list[tuple[str, str, str, int, str]] = [
    ("PREPARATION", "Preparation", "provisioning", 1,
     "Preliminary activities before the application is realised."),
    ("REALIZATION", "Realization", "provisioning", 2,
     "Development and acquisition of the application and its components."),
    ("TRANSITION", "Transition", "provisioning", 3,
     "Configuring, testing and deploying into the operating environment."),
    ("UTILIZATION", "Utilization and maintenance", "operation", 4,
     "Live use, including access management, logging and monitoring."),
    ("ARCHIVAL", "Archival", "operation", 5,
     "Retention of the application and its data after active use ends."),
    ("DESTRUCTION", "Destruction", "operation", 6,
     "Secure disposal of the application, its data and its components."),
]

ONF_SPEC: dict = {
    "iteration_no": 1,
    "name": "CRAFT ONF — iteration 1",
    "scope_statement": (
        "Every application the organisation builds, operates or acquires that "
        "processes customer, risk or compliance data — including the CRAFT "
        "platform itself and every AI system it invokes."
    ),
    "application_security_policy_ref": "POL-APPSEC-01",
    "status": "designed",
}

# (level_no, label, is_level_zero, description)
TRUST_LEVELS: list[tuple[int, str, bool, str]] = [
    (0, "Level zero — organisational floor", True,
     "The minimum the ONF committee accepts for any application. A project team cannot remove these."),
    (1, "Level one — internal, non-sensitive", False,
     "Internal tools handling no customer, personal or regulated data."),
    (2, "Level two — customer or personal data", False,
     "Applications processing customer, personal or supplier data."),
    (3, "Level three — regulated or safety-relevant", False,
     "Applications in certification scope, handling special-category data, or making "
     "consequential decisions about people."),
]

# (context_type, code, label)
ONF_CONTEXTS: list[tuple[str, str, str]] = [
    ("regulatory", "REG-ISO27001", "ISO/IEC 27001:2022 certification scope"),
    ("regulatory", "REG-ISO22301", "ISO 22301:2019 certification scope"),
    ("regulatory", "REG-ISO42001", "ISO/IEC 42001:2023 certification scope"),
    ("regulatory", "REG-UKGDPR", "UK GDPR and Data Protection Act 2018"),
    ("business", "BUS-GRC", "Enterprise GRC platform serving regulated customers"),
    ("business", "BUS-TPRM", "Third-party risk assessment and supplier assurance"),
    ("technological", "TEC-PYFAST", "Python 3.12 / FastAPI / Jinja2 single service"),
    ("technological", "TEC-PG16", "PostgreSQL 16 with row-level security and hash-chained audit"),
    ("technological", "TEC-RENDER", "Render managed deployment from GitHub"),
    ("technological", "TEC-MULTILLM", "Multi-provider LLM gateway with prompt caching"),
    ("technological", "TEC-MCP", "MCP JSON-RPC server exposing governed tools"),
]

LIFECYCLE_MODEL_NAME = "CRAFT delivery model"

# (local_code, local_label, aslcrm_stage, aslcrm_layer)
LIFECYCLE_MAP: list[tuple[str, str, str, str]] = [
    ("DISCOVER", "Discovery and requirements", "PREPARATION", "APP_MGMT"),
    ("DESIGN", "Architecture and design", "PREPARATION", "APP_PROV"),
    ("BUILD", "Build and unit test", "REALIZATION", "APP_PROV"),
    ("SOURCE", "Acquire or subscribe", "REALIZATION", "APP_PROV"),
    ("RELEASE", "Release and deploy", "TRANSITION", "APP_PROV"),
    ("RUN", "Run and support", "UTILIZATION", "INFRA_MGMT"),
    ("RETAIN", "Retention and archive", "ARCHIVAL", "INFRA_MGMT"),
    ("RETIRE", "Decommission", "DESTRUCTION", "INFRA_MGMT"),
    ("ASSURE", "Independent assurance", "UTILIZATION", "APP_AUDIT"),
]

SOURCE_NOTE = (
    "Written by CRAFT against the structure of ISO/IEC 27034-1:2011 clause 8. "
    "No standard text is reproduced. Reconcile against a licensed copy before "
    "certification use."
)

# Each entry: uid, label, stage, layer, trust levels, automation capability,
# whether measurement must be human, activity spec, measurement spec, mapped refs.
ASC_LIBRARY: list[dict] = [
    {
        "asc_uid": "ASC-GOV-OWNER",
        "label": "Named application owner holding recorded acceptance authority",
        "stage": "PREPARATION", "layer": "APP_MGMT", "levels": [0, 1, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Record a single accountable owner and the levels of trust they may accept.",
            "who": "Business lead", "when": "Before requirements are baselined",
            "how": "Application register entry plus a gate authority grant",
        },
        "measurement": {
            "what": "The owner is a named individual holding gate authority for the targeted level.",
            "who": "ONF committee delegate",
            "evidence": "domain.application row joined to iam.gate_authority",
        },
        "control_refs": ["iso27001:5.3", "iso42001:A.3.2"],
    },
    {
        "asc_uid": "ASC-REQ-SEC",
        "label": "Security and privacy requirements captured with the functional requirements",
        "stage": "PREPARATION", "layer": "APP_PROV", "levels": [0, 1, 2, 3],
        "automation": "assisted", "human_measurement": False,
        "activity": {
            "what": "Elicit functional and non-functional security requirements alongside business ones.",
            "who": "Product owner with a security domain expert", "when": "Discovery",
        },
        "measurement": {
            "what": "Every security requirement is testable and traced to a risk or a regulatory context.",
            "evidence": "Requirement register with context references",
        },
        "control_refs": ["iso42001:A.6.2.2"],
    },
    {
        "asc_uid": "ASC-RSK-APPRA",
        "label": "Application risk assessment producing a targeted level of trust",
        "stage": "PREPARATION", "layer": "APP_MGMT", "levels": [0, 1, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Assess threats, vulnerabilities and impact, and propose a targeted level of trust.",
            "who": "Risk Officer", "when": "Before the ANF is created",
            "method": "ISO/IEC 27005 aligned, scoped to one application",
        },
        "measurement": {
            "what": "The proposed level is approved by the application owner with its justification recorded.",
            "evidence": "compliance.anf.target_approved_by",
        },
        "control_refs": ["iso27001:6.1.2", "iso42001:6.1.2"],
    },
    {
        "asc_uid": "ASC-DES-THREAT",
        "label": "Threat model reviewed against the architecture before build starts",
        "stage": "PREPARATION", "layer": "APP_PROV", "levels": [2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Produce a threat model covering trust boundaries, data flows and abuse cases.",
            "who": "System architect with a security domain expert",
        },
        "measurement": {
            "what": "Every trust boundary carries at least one mitigation traced to an ASC or design decision.",
            "evidence": "Threat model artefact with ASC references",
        },
        "control_refs": ["iso42001:A.6.1.3"],
    },
    {
        "asc_uid": "ASC-DES-DATACLASS",
        "label": "Data classification and lawful basis fixed at design time",
        "stage": "PREPARATION", "layer": "APP_PROV", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": False,
        "activity": {
            "what": "Classify every data element and record the lawful basis for personal data.",
            "who": "Data owner with the DPO",
        },
        "measurement": {
            "what": "No unclassified element remains and every personal element carries a lawful basis.",
            "evidence": "domain.processing_record linkage",
        },
        "control_refs": ["iso27001:A.5.12", "uk_gdpr:Art.30", "iso42001:A.7.3"],
    },
    {
        "asc_uid": "ASC-BLD-SAST",
        "label": "Static analysis on every change with a blocking severity threshold",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [0, 1, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Run static application security testing on each pull request.",
            "who": "CI pipeline invoked by the application security agent",
            "when": "Every commit to a protected branch",
        },
        "measurement": {
            "what": "No unresolved finding at or above the blocking threshold reaches the main branch.",
            "evidence": "Pipeline artefact digest recorded on the evidence row",
        },
        "control_refs": ["iso27001:A.8.28"],
    },
    {
        "asc_uid": "ASC-BLD-SCA",
        "label": "Dependency and licence scanning with a maintained allowlist",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [0, 1, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Resolve the dependency tree and check it against vulnerability and licence policy.",
            "who": "CI pipeline invoked by the application security agent",
        },
        "measurement": {
            "what": "A bill of materials exists for the released artefact with no policy-violating component.",
            "evidence": "SBOM digest",
        },
        "control_refs": ["iso27001:A.8.8", "iso42001:A.4.4"],
    },
    {
        "asc_uid": "ASC-BLD-SECRET",
        "label": "Secret scanning across history, not only the diff",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [0, 1, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Scan the repository and its history for credentials, tokens and private keys.",
            "who": "CI pipeline invoked by the application security agent",
        },
        "measurement": {
            "what": "Zero live secrets; every historical hit has a documented rotation record.",
            "evidence": "Scan report plus rotation ticket",
        },
        "control_refs": ["iso27001:A.8.24", "iso27001:A.5.17"],
    },
    {
        "asc_uid": "ASC-BLD-REVIEW",
        "label": "Independent human review of every change to security-relevant code",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": (
                "A second engineer reviews changes touching authentication, authorisation, "
                "audit, cryptography, tenancy or the agent runtime."
            ),
            "who": "Peer engineer",
        },
        "measurement": {
            "what": "The approving reviewer is not the author and the review covered the sensitive paths.",
            "evidence": "Version control approval record",
            "note": (
                "Human-verifiable only. A model may summarise a diff; it may not attest "
                "that independent review took place."
            ),
        },
        "control_refs": ["iso27001:A.8.32"],
    },
    {
        "asc_uid": "ASC-BLD-TENANT",
        "label": "Tenant isolation proved by test as a non-owning database role",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [0, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Attempt cross-tenant reads and writes on every tenant table using the serving credential.",
            "who": "Test suite",
        },
        "measurement": {
            "what": (
                "Every attempt is refused and the test connects as a role that is neither "
                "superuser nor table owner."
            ),
            "evidence": "Test report naming the connecting role",
            "note": (
                "Written this way because row-level security silently does nothing for a "
                "superuser or a table owner without FORCE."
            ),
        },
        "control_refs": ["iso27001:A.8.3", "iso27001:A.5.15"],
    },
    {
        "asc_uid": "ASC-BLD-AUDITCHAIN",
        "label": "Audit chain integrity verified as part of the build",
        "stage": "REALIZATION", "layer": "APP_AUDIT", "levels": [0, 2, 3],
        "automation": "deterministic", "human_measurement": False,
        "activity": {
            "what": "Recompute the hash chain over the audit log and attempt an update and a delete.",
            "who": "Test suite",
        },
        "measurement": {
            "what": "The chain verifies and both mutation attempts are refused at the database.",
            "evidence": "audit.chain_check row",
        },
        "control_refs": ["iso27001:A.8.15", "iso42001:A.6.2.8"],
    },
    {
        "asc_uid": "ASC-SRC-SUPPLIER",
        "label": "Supplier and component assurance before first use",
        "stage": "REALIZATION", "layer": "APP_MGMT", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Assess the supplier of any acquired component or service against the TPRM standard.",
            "who": "Control Owner with the third-party agent drafting",
        },
        "measurement": {
            "what": "A residual risk decision exists within appetite, or a time-bound exception is in force.",
            "evidence": "domain.supplier_assessment",
        },
        "control_refs": ["iso27001:A.5.19", "iso42001:A.10.3"],
    },
    {
        "asc_uid": "ASC-AI-REQ",
        "label": "AI system requirements recorded before an AI component is introduced",
        "stage": "PREPARATION", "layer": "APP_PROV", "levels": [2, 3],
        "automation": "assisted", "human_measurement": False,
        "activity": {
            "what": "Register the AI system with intended use, prohibited use, autonomy and affected parties.",
            "who": "AI system owner",
        },
        "measurement": {
            "what": "A domain.ai_system row with intended_use exists before any production model call.",
            "evidence": "Register entry timestamp against first production invocation",
        },
        "control_refs": ["iso42001:A.6.2.2", "iso42001:A.9.4"],
    },
    {
        "asc_uid": "ASC-AI-IMPACT",
        "label": "AI system impact assessment approved before deployment",
        "stage": "TRANSITION", "layer": "APP_MGMT", "levels": [2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": (
                "Assess impacts on individuals, groups and society with benefits and "
                "mitigations, and obtain approval."
            ),
            "who": "AI system owner; the draft may be prepared by the AI impact agent",
        },
        "measurement": {
            "what": "An approved assessment naming a human approver predates the deployment gate.",
            "evidence": "domain.ai_impact_assessment",
        },
        "control_refs": ["iso42001:6.1.4", "iso42001:A.5.2", "iso42001:A.5.4", "iso42001:A.5.5"],
    },
    {
        "asc_uid": "ASC-AI-EVAL",
        "label": "Model evaluation against declared criteria before promotion",
        "stage": "TRANSITION", "layer": "APP_PROV", "levels": [2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": (
                "Run the declared evaluation suite covering accuracy, robustness, prompt "
                "injection resistance and refusal behaviour."
            ),
            "who": "Evaluation pipeline",
        },
        "measurement": {
            "what": "Results meet the criteria recorded on domain.ai_system.verification_criteria.",
            "evidence": "Evaluation report digest",
        },
        "control_refs": ["iso42001:A.6.2.4"],
    },
    {
        "asc_uid": "ASC-AI-PROV",
        "label": "Data provenance recorded for every dataset an AI system uses",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Record origin, acquisition basis, licence, lawful basis and preparation method.",
            "who": "Provenance agent, reviewed by the data owner",
        },
        "measurement": {
            "what": "No dataset reaches training or retrieval without a provenance row.",
            "evidence": "domain.ai_data_provenance",
        },
        "control_refs": ["iso42001:A.7.3", "iso42001:A.7.5", "uk_gdpr:Art.30"],
    },
    {
        "asc_uid": "ASC-AI-GUARD",
        "label": "Prompt, tool and output guardrails enforced at the gateway, not in the prompt",
        "stage": "REALIZATION", "layer": "APP_PROV", "levels": [2, 3],
        "automation": "deterministic", "human_measurement": False,
        "activity": {
            "what": "Enforce provider routing, tool allowlists, output filters and budgets in the gateway.",
            "who": "Platform Admin",
        },
        "measurement": {
            "what": "A test attempting a disallowed provider, a disallowed tool and a budget overrun is refused in all three cases.",
            "evidence": "Gateway policy test report",
            "note": (
                "Instructions inside a prompt are not a control. Only enforcement outside "
                "the model counts as evidence here."
            ),
        },
        "control_refs": ["iso42001:A.9.2", "iso42001:A.9.4", "iso27001:A.8.20"],
    },
    {
        "asc_uid": "ASC-AI-AGENTMANDATE",
        "label": "Every autonomous agent operates under an approved, bounded charter",
        "stage": "UTILIZATION", "layer": "APP_MGMT", "levels": [2, 3],
        "automation": "manual", "human_measurement": True,
        "activity": {
            "what": (
                "Approve a charter defining purpose, autonomy tier, tool grants, prohibited "
                "actions, budgets and kill switch."
            ),
            "who": "ONF committee with the CISO",
        },
        "measurement": {
            "what": (
                "No agent identity is enabled without a current approved charter, and no "
                "agent holds gate authority."
            ),
            "evidence": "config.agent_charter joined to iam.gate_authority",
            "note": (
                "Human-verifiable only by construction: this is the control that governs "
                "agents, so an agent must not measure it."
            ),
        },
        "control_refs": ["iso42001:A.3.2", "iso42001:A.9.2", "iso27001:A.5.2"],
    },
    {
        "asc_uid": "ASC-REL-GATE",
        "label": "Release gate refuses promotion while a mandatory ASC is unmeasured",
        "stage": "TRANSITION", "layer": "APP_MGMT", "levels": [0, 1, 2, 3],
        "automation": "deterministic", "human_measurement": False,
        "activity": {
            "what": "Compute the actual level of trust from measurement records and compare it to the target.",
            "who": "Level of trust calculation",
        },
        "measurement": {
            "what": (
                "Deployment is blocked whenever the actual level is below the target or a "
                "mandatory ASC lacks a passing measurement."
            ),
            "evidence": "core.approval_gate decision record",
        },
        "control_refs": ["iso42001:A.6.2.5"],
    },
    {
        "asc_uid": "ASC-REL-CONFIG",
        "label": "Deployment configuration and secrets sourced from managed configuration only",
        "stage": "TRANSITION", "layer": "INFRA_MGMT", "levels": [0, 1, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Supply all environment configuration and secrets through managed configuration.",
            "who": "Platform Admin",
        },
        "measurement": {
            "what": "The artefact contains no embedded credential and refuses to start on a default secret in production.",
            "evidence": "Startup assertion log",
        },
        "control_refs": ["iso27001:A.8.9", "iso27001:A.5.17"],
    },
    {
        "asc_uid": "ASC-RUN-ACCESS",
        "label": "Access reviewed on a schedule and on every role change",
        "stage": "UTILIZATION", "layer": "INFRA_MGMT", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Review who holds which role and gate authority, and revoke what is no longer needed.",
            "who": "Application owner",
            "when": "Quarterly and on any joiner, mover or leaver event",
        },
        "measurement": {
            "what": "Every privileged grant carries a review record inside the review period.",
            "evidence": "iam.role_grant review timestamps",
        },
        "control_refs": ["iso27001:A.5.18", "iso27001:A.8.2"],
    },
    {
        "asc_uid": "ASC-RUN-MONITOR",
        "label": "Security and AI behaviour monitoring with defined response thresholds",
        "stage": "UTILIZATION", "layer": "INFRA_MGMT", "levels": [0, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": (
                "Monitor authentication anomalies, gateway policy refusals, agent budget "
                "exhaustion and model performance drift."
            ),
            "who": "Monitoring agent",
        },
        "measurement": {
            "what": "Each declared threshold has fired at least once in test and raised the expected incident.",
            "evidence": "Monitoring test evidence and incident linkage",
        },
        "control_refs": ["iso27001:A.8.16", "iso42001:A.6.2.6"],
    },
    {
        "asc_uid": "ASC-RUN-CONTINUITY",
        "label": "Recovery objectives tested against the business impact analysis",
        "stage": "UTILIZATION", "layer": "INFRA_MGMT", "levels": [2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": "Exercise restoration of the application and its data within the recovery time objective.",
            "who": "Control Owner",
        },
        "measurement": {
            "what": "The exercise met the recovery time and point objectives, or a corrective action is open.",
            "evidence": "domain.continuity_exercise",
        },
        "control_refs": ["iso22301:8.4.4", "iso27001:A.5.29"],
    },
    {
        "asc_uid": "ASC-RUN-VULN",
        "label": "Vulnerability remediation inside severity-based service levels",
        "stage": "UTILIZATION", "layer": "INFRA_MGMT", "levels": [0, 2, 3],
        "automation": "automatable", "human_measurement": False,
        "activity": {
            "what": "Re-scan dependencies and the runtime image on a schedule and open remediation work.",
            "who": "Application security agent",
        },
        "measurement": {
            "what": "No vulnerability exceeds its remediation window without a time-bound accepted exception.",
            "evidence": "Vulnerability register ageing report",
        },
        "control_refs": ["iso27001:A.8.8"],
    },
    {
        "asc_uid": "ASC-ARC-RETENTION",
        "label": "Retention and disposal schedule applied to archived application data",
        "stage": "ARCHIVAL", "layer": "INFRA_MGMT", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": False,
        "activity": {
            "what": (
                "Apply the retention schedule to archived data, including AI training data "
                "and impact assessment records."
            ),
            "who": "Data owner",
        },
        "measurement": {
            "what": "Archived data carries a disposal date and nothing is retained past it without a legal hold.",
            "evidence": "Retention register",
        },
        "control_refs": ["uk_gdpr:Art.5", "iso27001:A.5.33", "iso42001:A.5.3"],
    },
    {
        "asc_uid": "ASC-DES-DISPOSAL",
        "label": "Verified destruction of application, data and credentials at decommission",
        "stage": "DESTRUCTION", "layer": "INFRA_MGMT", "levels": [0, 2, 3],
        "automation": "assisted", "human_measurement": True,
        "activity": {
            "what": (
                "Destroy or return data, revoke every credential and integration, and close "
                "the supplier relationship."
            ),
            "who": "Application owner with Platform Admin",
        },
        "measurement": {
            "what": (
                "A destruction certificate exists and no credential, webhook or MCP grant "
                "referencing the application remains active."
            ),
            "evidence": "Decommission checklist plus integration inventory diff",
        },
        "control_refs": ["iso27001:A.7.14", "iso27001:A.5.19", "iso42001:A.4.6"],
    },
    {
        "asc_uid": "ASC-AUD-INDEPENDENT",
        "label": "Independent audit of the application against its ANF",
        "stage": "UTILIZATION", "layer": "APP_AUDIT", "levels": [3],
        "automation": "manual", "human_measurement": True,
        "activity": {
            "what": (
                "An auditor independent of the delivery team verifies that every ANF "
                "measurement was performed and produced the expected result."
            ),
            "who": "Internal Auditor or an external verification team",
        },
        "measurement": {
            "what": "The actual level of trust is signed off by an auditor who performed none of the activities.",
            "evidence": "compliance.anf.audit_approved_by",
        },
        "control_refs": ["iso42001:9.2", "iso27001:9.2"],
    },
]


def level_zero_uids() -> list[str]:
    """The ASCs a project team cannot waive."""
    return [a["asc_uid"] for a in ASC_LIBRARY if 0 in a["levels"]]


def statistics() -> dict:
    return {
        "trust_levels": len(TRUST_LEVELS),
        "contexts": len(ONF_CONTEXTS),
        "ascs": len(ASC_LIBRARY),
        "level_zero_ascs": len(level_zero_uids()),
        "human_verified_ascs": sum(1 for a in ASC_LIBRARY if a["human_measurement"]),
        "aslcrm_stages": len(ASLCRM_STAGES),
        "aslcrm_layers": len(ASLCRM_LAYERS),
    }
