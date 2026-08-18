"""Shipped control catalogues.

Three frameworks are seeded. Each entry is (ref, title, section, theme, type).

  * ``type='requirement'`` — a mandatory clause. It cannot be excluded from the
    Statement of Applicability, and leaving it unimplemented blocks
    certification readiness.
  * ``type='control'`` — an Annex A style control. It may be excluded with a
    written justification.

Titles follow the published clause and control names so the Statement of
Applicability lines up with what an auditor is holding. The catalogue is
reference data: it is versioned with the code, not edited by users. Guidance
text is CRAFT's own summary, written to be useful to an implementer, not
reproduced from the standards themselves — the standards are copyright and
must be purchased from ISO or a national member body.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# ISO/IEC 27001:2022 — management system clauses 4–10
# --------------------------------------------------------------------------
ISO27001_CLAUSES: list[tuple[str, str, str]] = [
    ("4.1", "Understanding the organisation and its context", "4. Context"),
    ("4.2", "Understanding the needs and expectations of interested parties", "4. Context"),
    ("4.3", "Determining the scope of the information security management system", "4. Context"),
    ("4.4", "Information security management system", "4. Context"),
    ("5.1", "Leadership and commitment", "5. Leadership"),
    ("5.2", "Information security policy", "5. Leadership"),
    ("5.3", "Organisational roles, responsibilities and authorities", "5. Leadership"),
    ("6.1.1", "Actions to address risks and opportunities — general", "6. Planning"),
    ("6.1.2", "Information security risk assessment", "6. Planning"),
    ("6.1.3", "Information security risk treatment and Statement of Applicability", "6. Planning"),
    ("6.2", "Information security objectives and planning to achieve them", "6. Planning"),
    ("6.3", "Planning of changes", "6. Planning"),
    ("7.1", "Resources", "7. Support"),
    ("7.2", "Competence", "7. Support"),
    ("7.3", "Awareness", "7. Support"),
    ("7.4", "Communication", "7. Support"),
    ("7.5", "Documented information", "7. Support"),
    ("8.1", "Operational planning and control", "8. Operation"),
    ("8.2", "Information security risk assessment (operational)", "8. Operation"),
    ("8.3", "Information security risk treatment (operational)", "8. Operation"),
    ("9.1", "Monitoring, measurement, analysis and evaluation", "9. Performance evaluation"),
    ("9.2", "Internal audit", "9. Performance evaluation"),
    ("9.3", "Management review", "9. Performance evaluation"),
    ("10.1", "Continual improvement", "10. Improvement"),
    ("10.2", "Nonconformity and corrective action", "10. Improvement"),
]

# --------------------------------------------------------------------------
# ISO/IEC 27001:2022 Annex A — 93 controls in four themes
# --------------------------------------------------------------------------
ANNEX_A_ORGANISATIONAL: list[tuple[str, str]] = [
    ("A.5.1", "Policies for information security"),
    ("A.5.2", "Information security roles and responsibilities"),
    ("A.5.3", "Segregation of duties"),
    ("A.5.4", "Management responsibilities"),
    ("A.5.5", "Contact with authorities"),
    ("A.5.6", "Contact with special interest groups"),
    ("A.5.7", "Threat intelligence"),
    ("A.5.8", "Information security in project management"),
    ("A.5.9", "Inventory of information and other associated assets"),
    ("A.5.10", "Acceptable use of information and other associated assets"),
    ("A.5.11", "Return of assets"),
    ("A.5.12", "Classification of information"),
    ("A.5.13", "Labelling of information"),
    ("A.5.14", "Information transfer"),
    ("A.5.15", "Access control"),
    ("A.5.16", "Identity management"),
    ("A.5.17", "Authentication information"),
    ("A.5.18", "Access rights"),
    ("A.5.19", "Information security in supplier relationships"),
    ("A.5.20", "Addressing information security within supplier agreements"),
    ("A.5.21", "Managing information security in the ICT supply chain"),
    ("A.5.22", "Monitoring, review and change management of supplier services"),
    ("A.5.23", "Information security for use of cloud services"),
    ("A.5.24", "Information security incident management planning and preparation"),
    ("A.5.25", "Assessment and decision on information security events"),
    ("A.5.26", "Response to information security incidents"),
    ("A.5.27", "Learning from information security incidents"),
    ("A.5.28", "Collection of evidence"),
    ("A.5.29", "Information security during disruption"),
    ("A.5.30", "ICT readiness for business continuity"),
    ("A.5.31", "Legal, statutory, regulatory and contractual requirements"),
    ("A.5.32", "Intellectual property rights"),
    ("A.5.33", "Protection of records"),
    ("A.5.34", "Privacy and protection of personally identifiable information"),
    ("A.5.35", "Independent review of information security"),
    ("A.5.36", "Compliance with policies, rules and standards for information security"),
    ("A.5.37", "Documented operating procedures"),
]

ANNEX_A_PEOPLE: list[tuple[str, str]] = [
    ("A.6.1", "Screening"),
    ("A.6.2", "Terms and conditions of employment"),
    ("A.6.3", "Information security awareness, education and training"),
    ("A.6.4", "Disciplinary process"),
    ("A.6.5", "Responsibilities after termination or change of employment"),
    ("A.6.6", "Confidentiality or non-disclosure agreements"),
    ("A.6.7", "Remote working"),
    ("A.6.8", "Information security event reporting"),
]

ANNEX_A_PHYSICAL: list[tuple[str, str]] = [
    ("A.7.1", "Physical security perimeters"),
    ("A.7.2", "Physical entry"),
    ("A.7.3", "Securing offices, rooms and facilities"),
    ("A.7.4", "Physical security monitoring"),
    ("A.7.5", "Protecting against physical and environmental threats"),
    ("A.7.6", "Working in secure areas"),
    ("A.7.7", "Clear desk and clear screen"),
    ("A.7.8", "Equipment siting and protection"),
    ("A.7.9", "Security of assets off-premises"),
    ("A.7.10", "Storage media"),
    ("A.7.11", "Supporting utilities"),
    ("A.7.12", "Cabling security"),
    ("A.7.13", "Equipment maintenance"),
    ("A.7.14", "Secure disposal or re-use of equipment"),
]

ANNEX_A_TECHNOLOGICAL: list[tuple[str, str]] = [
    ("A.8.1", "User endpoint devices"),
    ("A.8.2", "Privileged access rights"),
    ("A.8.3", "Information access restriction"),
    ("A.8.4", "Access to source code"),
    ("A.8.5", "Secure authentication"),
    ("A.8.6", "Capacity management"),
    ("A.8.7", "Protection against malware"),
    ("A.8.8", "Management of technical vulnerabilities"),
    ("A.8.9", "Configuration management"),
    ("A.8.10", "Information deletion"),
    ("A.8.11", "Data masking"),
    ("A.8.12", "Data leakage prevention"),
    ("A.8.13", "Information backup"),
    ("A.8.14", "Redundancy of information processing facilities"),
    ("A.8.15", "Logging"),
    ("A.8.16", "Monitoring activities"),
    ("A.8.17", "Clock synchronisation"),
    ("A.8.18", "Use of privileged utility programs"),
    ("A.8.19", "Installation of software on operational systems"),
    ("A.8.20", "Networks security"),
    ("A.8.21", "Security of network services"),
    ("A.8.22", "Segregation of networks"),
    ("A.8.23", "Web filtering"),
    ("A.8.24", "Use of cryptography"),
    ("A.8.25", "Secure development life cycle"),
    ("A.8.26", "Application security requirements"),
    ("A.8.27", "Secure system architecture and engineering principles"),
    ("A.8.28", "Secure coding"),
    ("A.8.29", "Security testing in development and acceptance"),
    ("A.8.30", "Outsourced development"),
    ("A.8.31", "Separation of development, test and production environments"),
    ("A.8.32", "Change management"),
    ("A.8.33", "Test information"),
    ("A.8.34", "Protection of information systems during audit testing"),
]

# Evidence prompts for the controls an assessor most often asks about first.
ISO27001_EVIDENCE_HINTS: dict[str, str] = {
    "6.1.2": "Risk assessment methodology document and the populated risk register.",
    "6.1.3": "Risk treatment plan and the signed Statement of Applicability.",
    "9.2": "Internal audit programme, audit reports and auditor independence record.",
    "9.3": "Management review minutes covering every required input and output.",
    "10.2": "Nonconformity log with root cause, correction and effectiveness check.",
    "A.5.1": "Approved information security policy with version, owner and review date.",
    "A.5.9": "Asset inventory export showing owner and classification for every asset.",
    "A.5.15": "Access control policy plus a sample of access request approvals.",
    "A.5.18": "Access review evidence: population, reviewer, decisions and revocations.",
    "A.5.30": "ICT continuity requirements traced to BIA outputs and tested recovery.",
    "A.6.3": "Training completion records for the whole population, with pass rates.",
    "A.8.8": "Vulnerability scan output and remediation records against SLA.",
    "A.8.13": "Backup schedule and a dated successful restore test report.",
    "A.8.15": "Log sources, retention period and evidence logs are protected from change.",
    "A.8.32": "Change records showing assessment, approval, testing and back-out.",
}

# --------------------------------------------------------------------------
# ISO 22301:2019 — business continuity management system
# --------------------------------------------------------------------------
ISO22301_CLAUSES: list[tuple[str, str, str]] = [
    ("4.1", "Understanding the organisation and its context", "4. Context"),
    ("4.2", "Understanding the needs and expectations of interested parties", "4. Context"),
    ("4.3", "Determining the scope of the business continuity management system", "4. Context"),
    ("4.4", "Business continuity management system", "4. Context"),
    ("5.1", "Leadership and commitment", "5. Leadership"),
    ("5.2", "Business continuity policy", "5. Leadership"),
    ("5.3", "Roles, responsibilities and authorities", "5. Leadership"),
    ("6.1", "Actions to address risks and opportunities", "6. Planning"),
    ("6.2", "Business continuity objectives and planning to achieve them", "6. Planning"),
    ("6.3", "Planning of changes to the BCMS", "6. Planning"),
    ("7.1", "Resources", "7. Support"),
    ("7.2", "Competence", "7. Support"),
    ("7.3", "Awareness", "7. Support"),
    ("7.4", "Communication", "7. Support"),
    ("7.5", "Documented information", "7. Support"),
    ("8.1", "Operational planning and control", "8. Operation"),
    ("8.2.2", "Business impact analysis", "8. Operation"),
    ("8.2.3", "Risk assessment", "8. Operation"),
    ("8.3.2", "Identification of business continuity strategies and solutions", "8. Operation"),
    ("8.3.3", "Selection of strategies and solutions", "8. Operation"),
    ("8.3.4", "Resource requirements", "8. Operation"),
    ("8.3.5", "Implementation of solutions", "8. Operation"),
    ("8.4.2", "Response structure", "8. Operation"),
    ("8.4.3", "Warning and communication", "8. Operation"),
    ("8.4.4", "Business continuity plans", "8. Operation"),
    ("8.4.5", "Recovery", "8. Operation"),
    ("8.5", "Exercise programme", "8. Operation"),
    ("8.6", "Evaluation of business continuity documentation and capabilities", "8. Operation"),
    ("9.1", "Monitoring, measurement, analysis and evaluation", "9. Performance evaluation"),
    ("9.2", "Internal audit", "9. Performance evaluation"),
    ("9.3", "Management review", "9. Performance evaluation"),
    ("10.1", "Nonconformity and corrective action", "10. Improvement"),
    ("10.2", "Continual improvement", "10. Improvement"),
]

ISO22301_EVIDENCE_HINTS: dict[str, str] = {
    "8.2.2": "Signed BIA covering every prioritised activity, with MTPD, RTO and RPO.",
    "8.2.3": "Risk assessment for the disruption scenarios that threaten those activities.",
    "8.4.4": "Current, approved continuity plans with named response roles.",
    "8.5": "Exercise schedule and post-exercise reports with findings and actions.",
    "8.6": "Evaluation record showing plans were reviewed after exercise or change.",
    "9.3": "Management review minutes covering BCMS performance and resource needs.",
}

# --------------------------------------------------------------------------
# UK GDPR / EU GDPR — articles carrying operational obligations
# --------------------------------------------------------------------------
GDPR_ARTICLES: list[tuple[str, str, str]] = [
    ("Art.5", "Principles relating to processing of personal data", "Principles"),
    ("Art.5(2)", "Accountability", "Principles"),
    ("Art.6", "Lawfulness of processing", "Lawful basis"),
    ("Art.7", "Conditions for consent", "Lawful basis"),
    ("Art.9", "Processing of special categories of personal data", "Lawful basis"),
    ("Art.12", "Transparent information, communication and modalities", "Individual rights"),
    ("Art.13", "Information to be provided where data are collected from the data subject",
     "Individual rights"),
    ("Art.14", "Information to be provided where data have not been obtained from the data subject",
     "Individual rights"),
    ("Art.15", "Right of access by the data subject", "Individual rights"),
    ("Art.16", "Right to rectification", "Individual rights"),
    ("Art.17", "Right to erasure", "Individual rights"),
    ("Art.18", "Right to restriction of processing", "Individual rights"),
    ("Art.20", "Right to data portability", "Individual rights"),
    ("Art.21", "Right to object", "Individual rights"),
    ("Art.22", "Automated individual decision-making, including profiling", "Individual rights"),
    ("Art.24", "Responsibility of the controller", "Accountability"),
    ("Art.25", "Data protection by design and by default", "Accountability"),
    ("Art.26", "Joint controllers", "Accountability"),
    ("Art.28", "Processor obligations and contracts", "Accountability"),
    ("Art.30", "Records of processing activities", "Accountability"),
    ("Art.32", "Security of processing", "Security"),
    ("Art.33", "Notification of a personal data breach to the supervisory authority", "Breach"),
    ("Art.34", "Communication of a personal data breach to the data subject", "Breach"),
    ("Art.35", "Data protection impact assessment", "Accountability"),
    ("Art.36", "Prior consultation with the supervisory authority", "Accountability"),
    ("Art.37", "Designation of the data protection officer", "Governance"),
    ("Art.38", "Position of the data protection officer", "Governance"),
    ("Art.39", "Tasks of the data protection officer", "Governance"),
    ("Art.44", "General principle for transfers of personal data", "Transfers"),
    ("Art.46", "Transfers subject to appropriate safeguards", "Transfers"),
    ("Art.49", "Derogations for specific situations", "Transfers"),
]

GDPR_EVIDENCE_HINTS: dict[str, str] = {
    "Art.30": "Record of processing activities, current and attested by each function.",
    "Art.32": "Technical and organisational measures documented and tested.",
    "Art.33": "Breach log showing the 72-hour clock, decision and notification record.",
    "Art.35": "Completed DPIAs for high-risk processing, with the DPO's advice recorded.",
    "Art.15": "Subject access request log with receipt date, statutory deadline and release.",
    "Art.28": "Processor contracts containing the Article 28(3) terms, plus due diligence.",
}

# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
FRAMEWORKS: list[dict] = [
    {
        "code": "iso27001",
        "name": "ISO/IEC 27001 Information security management",
        "issuer": "ISO/IEC",
        "edition": "2022",
        "certifiable": True,
        "sort_order": 10,
        "description": (
            "Requirements for establishing, implementing, maintaining and continually "
            "improving an information security management system, including the "
            "Annex A control set and the Statement of Applicability."
        ),
    },
    {
        "code": "iso22301",
        "name": "ISO 22301 Business continuity management",
        "issuer": "ISO",
        "edition": "2019",
        "certifiable": True,
        "sort_order": 20,
        "description": (
            "Requirements for a business continuity management system: impact analysis, "
            "continuity strategies, plans, exercising and evaluation."
        ),
    },
    {
        "code": "uk_gdpr",
        "name": "UK GDPR and Data Protection Act 2018",
        "issuer": "ICO",
        "edition": "2021 consolidated",
        "certifiable": False,
        "sort_order": 30,
        "description": (
            "Operational obligations for controllers and processors: lawful basis, "
            "transparency, individual rights, records of processing, security, breach "
            "notification, impact assessment and international transfers."
        ),
    },
]


def _theme_for(ref: str) -> str:
    if ref.startswith("A.5"):
        return "organisational"
    if ref.startswith("A.6"):
        return "people"
    if ref.startswith("A.7"):
        return "physical"
    if ref.startswith("A.8"):
        return "technological"
    return "management_system"


def iso27001_controls() -> list[dict]:
    out: list[dict] = []
    order = 0
    for ref, title, section in ISO27001_CLAUSES:
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
                "evidence_hint": ISO27001_EVIDENCE_HINTS.get(ref),
            }
        )
    annex = [
        ("A.5 Organisational controls", ANNEX_A_ORGANISATIONAL),
        ("A.6 People controls", ANNEX_A_PEOPLE),
        ("A.7 Physical controls", ANNEX_A_PHYSICAL),
        ("A.8 Technological controls", ANNEX_A_TECHNOLOGICAL),
    ]
    for section, items in annex:
        for ref, title in items:
            order += 1
            out.append(
                {
                    "ref_code": ref,
                    "title": title,
                    "section": section,
                    "theme": _theme_for(ref),
                    "control_type": "control",
                    "is_mandatory": False,
                    "sort_order": order,
                    "evidence_hint": ISO27001_EVIDENCE_HINTS.get(ref),
                }
            )
    return out


def iso22301_controls() -> list[dict]:
    return [
        {
            "ref_code": ref,
            "title": title,
            "section": section,
            "theme": "management_system",
            "control_type": "requirement",
            "is_mandatory": True,
            "sort_order": i + 1,
            "evidence_hint": ISO22301_EVIDENCE_HINTS.get(ref),
        }
        for i, (ref, title, section) in enumerate(ISO22301_CLAUSES)
    ]


def gdpr_controls() -> list[dict]:
    return [
        {
            "ref_code": ref,
            "title": title,
            "section": section,
            "theme": "privacy",
            "control_type": "requirement",
            "is_mandatory": True,
            "sort_order": i + 1,
            "evidence_hint": GDPR_EVIDENCE_HINTS.get(ref),
        }
        for i, (ref, title, section) in enumerate(GDPR_ARTICLES)
    ]


# ISO/IEC 42001 lives in its own module because its catalogue is a paraphrase
# pending reconciliation, and keeping that flag next to the data it qualifies is
# safer than a comment in a shared file.
from app.seed.catalogue_iso42001 import (  # noqa: E402
    FRAMEWORK_SPEC as ISO42001_FRAMEWORK,
    ISO42001_MAPPINGS,
    iso42001_controls,
)

FRAMEWORKS.append(ISO42001_FRAMEWORK)

CONTROLS_BY_FRAMEWORK = {
    "iso27001": iso27001_controls,
    "iso22301": iso22301_controls,
    "uk_gdpr": gdpr_controls,
    "iso42001": iso42001_controls,
}

# Cross-framework equivalences: one piece of evidence, several audits.
CONTROL_MAPPINGS: list[tuple[str, str, str, str]] = [
    ("iso27001", "A.5.34", "uk_gdpr", "Art.24"),
    ("iso27001", "A.8.24", "uk_gdpr", "Art.32"),
    ("iso27001", "A.8.13", "uk_gdpr", "Art.32"),
    ("iso27001", "A.5.24", "uk_gdpr", "Art.33"),
    ("iso27001", "A.5.26", "uk_gdpr", "Art.33"),
    ("iso27001", "A.5.19", "uk_gdpr", "Art.28"),
    ("iso27001", "A.5.20", "uk_gdpr", "Art.28"),
    ("iso27001", "A.8.25", "uk_gdpr", "Art.25"),
    ("iso27001", "A.5.30", "iso22301", "8.3.5"),
    ("iso27001", "A.5.29", "iso22301", "8.4.4"),
    ("iso27001", "A.8.14", "iso22301", "8.3.4"),
    ("iso27001", "9.2", "iso22301", "9.2"),
    ("iso27001", "9.3", "iso22301", "9.3"),
    ("iso27001", "6.1.2", "iso22301", "8.2.3"),
    ("iso27001", "7.5", "iso22301", "7.5"),
]

CONTROL_MAPPINGS.extend(ISO42001_MAPPINGS)
