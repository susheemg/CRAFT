"""ISO/IEC 42001:2023 catalogue — AI management system.

Clauses 4 to 10, plus the 38 normative Annex A controls across nine control
objectives. Loaded into ``ref.framework_control`` alongside the other three
frameworks, so a 42001 control implementation, gap and readiness figure work
exactly the way a 27001 one does.

Two things are deliberate and should not be quietly reversed:

* **Titles are CRAFT's own paraphrases, not the published control names.** The
  other catalogues in this package follow published clause names closely; this
  one does not, because ISO/IEC 42001 is a 2023 standard whose Annex A wording
  is short enough that following it closely would amount to reproducing it.
  ``RECONCILED`` below stays ``False`` until someone has compared the catalogue
  line by line against a licensed copy, and certification readiness must not be
  claimed while it is ``False``.

* **Mappings to other frameworks assert contribution, not equivalence.** An
  ISO/IEC 27001 control being implemented does not make the analogous 42001
  control satisfied. Over-mapping is how integrated management systems inflate
  readiness, and it is the failure an assessor probes first.
"""

from __future__ import annotations

# Set true only after a line-by-line comparison against a licensed copy of the
# standard, recorded as an attestation. app.services.appsec.certification_block
# reads this.
RECONCILED: bool = False

SOURCE_NOTE = (
    "Catalogue entry written by CRAFT as a paraphrase of ISO/IEC 42001:2023. "
    "No standard text is reproduced. Reconcile against a licensed copy before "
    "certification use."
)

# --------------------------------------------------------------------------
# Clauses 4-10 (Annex SL harmonised structure)
# --------------------------------------------------------------------------
ISO42001_CLAUSES: list[tuple[str, str, str]] = [
    ("4.1", "Understanding the organisation and its context", "4. Context"),
    ("4.2", "Understanding the needs and expectations of interested parties", "4. Context"),
    ("4.3", "Determining the scope of the AI management system", "4. Context"),
    ("4.4", "AI management system", "4. Context"),
    ("5.1", "Leadership and commitment", "5. Leadership"),
    ("5.2", "AI policy", "5. Leadership"),
    ("5.3", "Organisational roles, responsibilities and authorities", "5. Leadership"),
    ("6.1.1", "Actions to address risks and opportunities — general", "6. Planning"),
    ("6.1.2", "AI risk assessment", "6. Planning"),
    ("6.1.3", "AI risk treatment and Statement of Applicability", "6. Planning"),
    ("6.1.4", "AI system impact assessment", "6. Planning"),
    ("6.2", "AI objectives and planning to achieve them", "6. Planning"),
    ("6.3", "Planning of changes", "6. Planning"),
    ("7.1", "Resources", "7. Support"),
    ("7.2", "Competence", "7. Support"),
    ("7.3", "Awareness", "7. Support"),
    ("7.4", "Communication", "7. Support"),
    ("7.5", "Documented information", "7. Support"),
    ("8.1", "Operational planning and control", "8. Operation"),
    ("8.2", "AI risk assessment (operational)", "8. Operation"),
    ("8.3", "AI risk treatment (operational)", "8. Operation"),
    ("8.4", "AI system impact assessment (operational)", "8. Operation"),
    ("9.1", "Monitoring, measurement, analysis and evaluation", "9. Performance evaluation"),
    ("9.2", "Internal audit", "9. Performance evaluation"),
    ("9.3", "Management review", "9. Performance evaluation"),
    ("10.1", "Continual improvement", "10. Improvement"),
    ("10.2", "Nonconformity and corrective action", "10. Improvement"),
]

# --------------------------------------------------------------------------
# Annex A — nine control objectives
# --------------------------------------------------------------------------
ANNEX_A_OBJECTIVES: dict[str, str] = {
    "A.2": "A.2 Policies related to AI",
    "A.3": "A.3 Internal organisation",
    "A.4": "A.4 Resources for AI systems",
    "A.5": "A.5 Assessing impacts of AI systems",
    "A.6": "A.6 AI system life cycle",
    "A.7": "A.7 Data for AI systems",
    "A.8": "A.8 Information for interested parties",
    "A.9": "A.9 Use of AI systems",
    "A.10": "A.10 Third-party and customer relationships",
}

# (ref, paraphrased topic, objective key, evidence hint)
ANNEX_A_CONTROLS: list[tuple[str, str, str, str]] = [
    ("A.2.2", "AI policy", "A.2",
     "The approved AI policy, with its approval record and effective date."),
    ("A.2.3", "Alignment with other organisational policies", "A.2",
     "A register of policies the AI policy affects or is affected by."),
    ("A.2.4", "Review of the AI policy", "A.2",
     "Review records at the planned interval, including reviews that changed nothing."),

    ("A.3.2", "AI roles and responsibilities", "A.3",
     "Role definitions and grants covering the AI life cycle."),
    ("A.3.3", "Reporting of concerns", "A.3",
     "A concerns channel that does not route through the owner of the system being questioned."),

    ("A.4.2", "Resource documentation", "A.4",
     "Resource records per AI system, per life cycle stage."),
    ("A.4.3", "Data resources", "A.4",
     "Dataset inventory linked to the AI systems that consume it."),
    ("A.4.4", "Tooling resources", "A.4",
     "Tooling inventory with versions and supplier links."),
    ("A.4.5", "System and computing resources", "A.4",
     "Compute and hosting records, including provider and region."),
    ("A.4.6", "Human resources and competence", "A.4",
     "Named roles and competences across build, run, change and decommission."),

    ("A.5.2", "AI system impact assessment process", "A.5",
     "The documented assessment process and its trigger conditions."),
    ("A.5.3", "Documentation and retention of impact assessments", "A.5",
     "Completed assessments with an explicit retention date."),
    ("A.5.4", "Impacts on individuals and groups", "A.5",
     "Assessed individual and group impacts, approved by a named person."),
    ("A.5.5", "Societal impacts", "A.5",
     "Assessed societal impacts, approved by a named person."),

    ("A.6.1.2", "Objectives for responsible development", "A.6",
     "Recorded development objectives and the measures taken to meet them."),
    ("A.6.1.3", "Processes for responsible design and development", "A.6",
     "The documented design and development process for AI systems."),
    ("A.6.2.2", "AI system requirements and specification", "A.6",
     "Requirements records for new systems and material enhancements."),
    ("A.6.2.3", "Documentation of design and development", "A.6",
     "Design records traceable to objectives, requirements and criteria."),
    ("A.6.2.4", "Verification and validation", "A.6",
     "Evaluation results against declared criteria, run before promotion."),
    ("A.6.2.5", "AI system deployment", "A.6",
     "A deployment plan and a gate record confirming prerequisites were met."),
    ("A.6.2.6", "Operation and monitoring", "A.6",
     "Monitoring configuration, thresholds, and repair, update and support arrangements."),
    ("A.6.2.7", "Technical documentation", "A.6",
     "Documentation per interested-party category, in a form they can use."),
    ("A.6.2.8", "Recording of event logs", "A.6",
     "Logging configuration naming the life cycle phases at which logging is on."),

    ("A.7.2", "Data management for development", "A.7",
     "The documented data management process for AI development."),
    ("A.7.3", "Acquisition of data", "A.7",
     "Acquisition and selection records per dataset."),
    ("A.7.4", "Quality of data", "A.7",
     "Data quality criteria and the result of applying them."),
    ("A.7.5", "Data provenance", "A.7",
     "Provenance records spanning the life cycles of the data and the system."),
    ("A.7.6", "Data preparation", "A.7",
     "Preparation methods used and the criteria for selecting them."),

    ("A.8.2", "System documentation and information for users", "A.8",
     "Published user information covering intended use and limitations."),
    ("A.8.3", "External reporting", "A.8",
     "A working channel for interested parties to report adverse impacts."),
    ("A.8.4", "Communication of incidents", "A.8",
     "An incident communication plan for users of the AI system."),
    ("A.8.5", "Information for interested parties", "A.8",
     "A register of reporting obligations and the reports made against them."),

    ("A.9.2", "Processes for responsible use", "A.9",
     "The documented processes governing responsible use."),
    ("A.9.3", "Objectives for responsible use", "A.9",
     "Recorded objectives guiding responsible use."),
    ("A.9.4", "Intended use", "A.9",
     "Gateway policy enforcement evidence — not an instruction inside a prompt."),

    ("A.10.2", "Allocating responsibilities", "A.10",
     "Responsibility allocation across the organisation, partners, suppliers and customers."),
    ("A.10.3", "Suppliers", "A.10",
     "Supplier assurance results against the responsible AI approach."),
    ("A.10.4", "Customers", "A.10",
     "Recorded customer expectations feeding the responsible use objectives."),
]

ISO42001_EVIDENCE_HINTS: dict[str, str] = {
    "4.3": "A scope statement that names the AI systems in scope and the organisation's role for each.",
    "6.1.2": "AI risk criteria, the assessment method, and assessments run against it.",
    "6.1.3": "The Statement of Applicability, with a justification for every control and a reason for every exclusion.",
    "6.1.4": "Approved AI system impact assessments predating deployment.",
    "9.2": "An audit programme covering the AIMS, run by an auditor independent of the audited activity.",
    "9.3": "Management review minutes with the full input agenda and recorded decisions.",
    "10.2": "Nonconformity records with root cause, action and an effectiveness review.",
    **{ref: hint for ref, _topic, _obj, hint in ANNEX_A_CONTROLS},
}


def iso42001_controls() -> list[dict]:
    """Clauses first, then Annex A, in the shape ``ref.framework_control`` wants."""
    out: list[dict] = []
    order = 0

    for ref, title, section in ISO42001_CLAUSES:
        order += 1
        out.append(
            {
                "ref_code": ref,
                "title": title,
                "section": section,
                "theme": "management_system",
                "control_type": "requirement",
                "is_mandatory": True,
                "sort_order": order,
                "evidence_hint": ISO42001_EVIDENCE_HINTS.get(ref),
                "guidance": SOURCE_NOTE,
            }
        )

    for ref, topic, objective, hint in ANNEX_A_CONTROLS:
        order += 1
        out.append(
            {
                "ref_code": ref,
                "title": topic,
                "section": ANNEX_A_OBJECTIVES[objective],
                "theme": "ai_governance",
                # Annex A of 42001 is normative but selective: a control may be
                # excluded with a written justification, exactly like 27001.
                "control_type": "control",
                "is_mandatory": False,
                "sort_order": order,
                "evidence_hint": hint,
                "guidance": SOURCE_NOTE,
            }
        )
    return out


FRAMEWORK_SPEC: dict = {
    "code": "iso42001",
    "name": "ISO/IEC 42001 Artificial intelligence management system",
    "issuer": "ISO/IEC",
    "edition": "2023",
    "certifiable": True,
    "sort_order": 15,
    "description": (
        "Requirements for establishing, implementing, maintaining and continually "
        "improving an AI management system, including the Annex A reference "
        "controls and the AI system impact assessment. Catalogue entries are "
        "CRAFT paraphrases pending reconciliation against a licensed copy."
    ),
}

# Contribution, not equivalence. Each pairing means "evidence for one materially
# helps the other"; none means "implementing one satisfies the other".
ISO42001_MAPPINGS: list[tuple[str, str, str, str]] = [
    ("iso42001", "5.2", "iso27001", "5.2"),
    ("iso42001", "5.3", "iso27001", "5.3"),
    ("iso42001", "6.1.3", "iso27001", "6.1.3"),
    ("iso42001", "7.5", "iso27001", "7.5"),
    ("iso42001", "9.2", "iso27001", "9.2"),
    ("iso42001", "9.3", "iso27001", "9.3"),
    ("iso42001", "10.2", "iso27001", "10.2"),
    ("iso42001", "A.3.2", "iso27001", "A.5.2"),
    ("iso42001", "A.6.2.8", "iso27001", "A.8.15"),
    ("iso42001", "A.8.4", "iso27001", "A.5.26"),
    ("iso42001", "A.10.3", "iso27001", "A.5.19"),
    # Complementary, not substitutable: a DPIA covers individual harms and says
    # nothing about societal impact, so neither discharges the other.
    ("iso42001", "A.5.4", "uk_gdpr", "Art.35"),
    ("iso42001", "A.7.5", "uk_gdpr", "Art.30"),
    # A single-provider model dependency is a continuity risk that looks like a
    # software licence on a conventional BIA.
    ("iso42001", "A.6.2.6", "iso22301", "8.4.4"),
]
