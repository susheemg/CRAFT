# Standard Operating Procedure Manual

**CRAFT — Governance, Risk and Compliance**

Generated 2026-08-18 from the process repository (`app/processes`). Version 1.0.

---

## How to read this manual

This manual is generated from the same definitions the platform executes. There is no separate written procedure that could disagree with it: if a step appears here, the engine runs it, and if the engine runs a step, it appears here. Regenerating the manual after a change to the repository is how the document stays true.

Each process states its purpose, its owner, what triggers it, and the clauses it discharges. Each activity states the five-part contract — what is done, who does it, who is accountable, what goes in, what comes out — plus whether the platform performs it, whether AI drafts it, and whether it stops for a human decision.

### The rule that governs every process

**Accountability never rests with an agent.** An AI agent may gather, draft, score and propose. It may not approve. Every decision point in this manual resolves to a named human role, and the platform enforces that structurally rather than by convention: an agent principal cannot hold approval authority, and the gate check refuses a non-human principal independently of what permissions it was granted.

### Where work stops for a person

A process stops at a gate when any of four tests is met:

| Test | Meaning |
|---|---|
| `irreversible` | The step is stopped because the action cannot be undone. |
| `statutory` | The step is stopped because a legal duty attaches to the decision. |
| `high_risk` | The step is stopped because the exposure or value is material. |
| `low_confidence` | The step is stopped because the model's confidence was below the threshold. |

### The shape of the repository

| Measure | Value |
|---|---|
| Domains | 11 |
| Processes | 55 |
| Activities | 243 |
| Human decision gates | 43 |
| Activities with AI participation | 158 |
| Activities performed unattended | 80 (32.9%) |

The unattended figure counts only steps the platform completes without a person acting. AI-drafted steps are counted as human work, because a draft still has to be read. Counting drafting as automation is how implausible automation claims are arrived at, and the figure above sits deliberately inside the 20–40% band that current practice supports for repetitive compliance work.

---

## Process index

### GOV — Governance and management system

*Establishes context, scope, policy, objectives and leadership commitment, and closes the management-system loop through internal audit, management review and improvement.*

**Domain owner:** CISO

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-GOV-01` | Establish and maintain management system scope and context | CISO | annual | 1 |
| `PR-GOV-02` | Set and monitor management system objectives | CISO | quarterly | 1 |
| `PR-GOV-03` | Internal audit | Internal Auditor | annual | 1 |
| `PR-GOV-04` | Management review | CISO | annual | 1 |
| `PR-GOV-05` | Nonconformity and continual improvement | Control Owner | event driven | 0 |

### RSK — Risk management

*Identifies, assesses, treats and monitors risk to information, personal data and operational continuity on one register and one scale.*

**Domain owner:** Risk Officer

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-RSK-01` | Risk identification and assessment | Risk Officer | event driven | 0 |
| `PR-RSK-02` | Risk treatment and acceptance | Risk Officer | event driven | 2 |
| `PR-RSK-03` | Continuous risk monitoring and review | Risk Officer | continuous | 0 |

### CMP — Compliance and assurance

*Maintains the control library, evidences control operation continuously, and keeps the organisation audit-ready rather than audit-reactive.*

**Domain owner:** Control Owner

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-CMP-01` | Control library and applicability maintenance | Control Owner | annual | 1 |
| `PR-CMP-02` | Continuous control monitoring | Control Owner | continuous | 1 |
| `PR-CMP-03` | Gap remediation | Control Owner | event driven | 1 |
| `PR-CMP-04` | Regulatory and standards change management | DPO | continuous | 0 |
| `PR-CMP-05` | Certification and external audit readiness | CISO | annual | 1 |

### PRV — Privacy operations

*Discharges the controller and processor duties: lawful basis, records of processing, individual rights, impact assessments, transfers and breach notification.*

**Domain owner:** DPO

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-PRV-01` | Records of processing and lawful basis | DPO | annual | 1 |
| `PR-PRV-02` | Data subject rights request | DPO | event driven | 1 |
| `PR-PRV-03` | Personal data breach assessment and notification | DPO | event driven | 2 |
| `PR-PRV-04` | Data protection impact assessment | DPO | event driven | 1 |
| `PR-PRV-05` | International transfers and retention | DPO | annual | 1 |

### SEC — Security operations

*Detects, triages and resolves security events, and manages vulnerabilities and technical hygiene.*

**Domain owner:** CISO

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-SEC-01` | Security event triage and incident response | CISO | event driven | 0 |
| `PR-SEC-02` | Vulnerability and patch management | CISO | continuous | 1 |
| `PR-SEC-03` | Logging, monitoring and detection assurance | CISO | monthly | 0 |

### TPR — Third-party risk

*Assesses, approves, contracts and monitors suppliers in proportion to the risk each engagement actually carries.*

**Domain owner:** Control Owner

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-TPR-01` | Supplier inherent risk and tiering | Control Owner | event driven | 0 |
| `PR-TPR-02` | Supplier due diligence and approval | Control Owner | event driven | 2 |
| `PR-TPR-03` | Ongoing supplier monitoring and exit | Control Owner | continuous | 0 |

### RES — Operational resilience

*Understands what the organisation must be able to keep doing, how quickly it must recover, and proves it can.*

**Domain owner:** Control Owner

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-RES-01` | Business impact analysis | Control Owner | annual | 1 |
| `PR-RES-02` | Continuity strategy and plan development | Control Owner | annual | 1 |
| `PR-RES-03` | Exercising and testing | Control Owner | annual | 0 |
| `PR-RES-04` | Crisis invocation and recovery | CISO | event driven | 2 |

### PPL — People and access

*Manages the identity lifecycle, entitlement, awareness and the human-factor controls around them.*

**Domain owner:** Security Admin

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-PPL-01` | Joiner, mover, leaver | Security Admin | event driven | 1 |
| `PR-PPL-02` | Access recertification | Security Admin | quarterly | 1 |
| `PR-PPL-03` | Awareness and competence | Security Admin | annual | 0 |

### CHG — Change and secure development

*Governs change to systems and services so that security, privacy and continuity requirements are met before, not after, release.*

**Domain owner:** Control Owner

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-CHG-01` | Change management | Control Owner | event driven | 1 |
| `PR-CHG-02` | Secure development and go-live assurance | CISO | event driven | 1 |

### APS — Application security

*Runs ISO/IEC 27034: maintains the Organization Normative Framework and its Application Security Control library, and applies that library to each application project through a targeted and an actual level of trust. Added because securing an application is a different discipline from securing an organisation, and the existing change domain governs release, not control design.*

**Domain owner:** CISO

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-APS-01` | Design the Organization Normative Framework iteration | CISO | annual | 1 |
| `PR-APS-02` | Implement and communicate the ONF | Control Owner | annual | 0 |
| `PR-APS-03` | Monitor and review the ONF | Control Owner | quarterly | 0 |
| `PR-APS-04` | Improve the ONF from project feedback | Control Owner | quarterly | 0 |
| `PR-APS-05` | Audit the ONF | Internal Auditor | annual | 0 |
| `PR-APS-06` | Specify application requirements and environment | Control Owner | event driven | 0 |
| `PR-APS-07` | Assess application security risk and set the targeted level of trust | Risk Officer | event driven | 1 |
| `PR-APS-08` | Create and maintain the Application Normative Framework | Control Owner | event driven | 0 |
| `PR-APS-09` | Provision and operate the application under its ANF | Control Owner | continuous | 1 |
| `PR-APS-10` | Audit the security of the application | Internal Auditor | event driven | 1 |

### AIG — AI governance

*Governs the organisation's own use of AI — including this platform's agents — as a controlled activity with an inventory, risk classification, human oversight and post-market monitoring. Added because a platform that automates compliance with AI must be able to evidence the governance of that AI.*

**Domain owner:** CISO

| Process | Name | Owner | Cadence | Gates |
|---|---|---|---|---|
| `PR-AIG-01` | AI system inventory and risk classification | CISO | quarterly | 1 |
| `PR-AIG-02` | AI human oversight and decision accountability | CISO | continuous | 1 |
| `PR-AIG-03` | AI performance monitoring and drift | CISO | continuous | 1 |
| `PR-AIG-04` | Establish and review the AI policy | CISO | annual | 1 |
| `PR-AIG-05` | AI resource documentation and competence | CISO | continuous | 1 |
| `PR-AIG-06` | AI risk assessment, treatment and Statement of Applicability | Risk Officer | quarterly | 2 |
| `PR-AIG-07` | AI system impact assessment | DPO | event driven | 1 |
| `PR-AIG-08` | Data governance for AI systems | DPO | continuous | 0 |
| `PR-AIG-09` | Information for interested parties and AI incident communication | CISO | continuous | 1 |
| `PR-AIG-10` | Responsible use of AI systems and agent mandates | CISO | continuous | 1 |
| `PR-AIG-11` | AI third-party and customer relationships | Control Owner | annual | 1 |
| `PR-AIG-12` | Responsible AI system life cycle and deployment control | Control Owner | event driven | 1 |

---

## PR-GOV-01 — Establish and maintain management system scope and context

Fixes what the management system covers and why, which every other process depends on. An unclear scope is the most common reason a certification audit fails before it examines a single control.

| | |
|---|---|
| **Domain** | GOV |
| **Process owner** | CISO |
| **Trigger** | Annual review, or a material change to the business, estate or legal obligations |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 20% |

**Clauses discharged**

- ISO 22301:2019: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2
- ISO/IEC 27001:2022: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2
- iso42001: 4.1, 4.2, 4.4, 5.1
- UK GDPR: Art.5, Art.24

**How this process is measured**

- Scope reviewed within 12 months
- Zero scope exclusions without justification

### Procedure

#### A1. Assemble the internal and external issues bearing on the management system: business model, estate, regulatory obligations, contractual commitments and dependencies.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Annual cycle or material change |
| **Input** | asset_register, supplier_register, processing_records, obligation_register |
| **Output** | context_analysis |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:4.1, iso22301:4.1 |

**AI participation — Regulatory change agent**

- *Asked to:* Draft the context analysis from the registers and flag anything that changed materially since the last cycle.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Identify interested parties and their requirements, distinguishing legal obligations from commercial expectations.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | context_analysis, contract_register |
| **Output** | interested_parties_register |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:4.2, iso22301:4.2 |

**AI participation — Regulatory change agent**

- *Asked to:* Draft the register and cite the source of each stated requirement.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A3. Define the scope boundary, including exclusions and the reason for each.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | context_analysis, interested_parties_register |
| **Output** | draft_scope_statement |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:4.3, iso22301:4.3 |

**AI participation — Control assessment agent**

- *Asked to:* Draft the boundary and test each proposed exclusion against the clauses that cannot be excluded.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A4. Approve the scope and the policy set at leadership level. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_scope_statement, policy_set |
| **Output** | approved_scope, approved_policies |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:5.1, iso27001:5.2, iso22301:5.2 |
| **Records produced** | scope_approval_record |

> **This step stops for a human decision** (`governance.scope_approval`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Publish the approved scope and policies and record acknowledgement.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | approved_scope, approved_policies |
| **Output** | publication_record |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:5.2, iso27001:7.5 |
| **Records produced** | policy_publication_record |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-GOV-02 — Set and monitor management system objectives

Turns policy into measurable objectives and keeps them visible. Objectives without measurement are the clause auditors most often find satisfied on paper only.

| | |
|---|---|
| **Domain** | GOV |
| **Process owner** | CISO |
| **Trigger** | Annual planning cycle; quarterly measurement |
| **Cadence** | quarterly |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 6.2, 9.1
- ISO/IEC 27001:2022: 6.2, 9.1
- iso42001: 6.2, 9.1

**How this process is measured**

- Objectives measured quarterly
- Objectives with a named owner and target

### Procedure

#### A1. Derive candidate objectives from policy, risk position and readiness gaps.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | approved_policies, risk_register, readiness_snapshot |
| **Output** | candidate_objectives |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.2 |

**AI participation — Control assessment agent**

- *Asked to:* Propose objectives that are measurable and tied to a named shortfall.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Agree objectives, targets, owners and measurement method. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | candidate_objectives |
| **Output** | objective_register |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:6.2 |

> **This step stops for a human decision** (`governance.objectives_approval`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A3. Measure performance against each objective and report the trend.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Quarterly |
| **Input** | objective_register, readiness_snapshot, risk_register, gap_register |
| **Output** | performance_report |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1, iso22301:9.1 |
| **Records produced** | performance_measurement_record |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

---

## PR-GOV-03 — Internal audit

Provides independent assurance that the management system conforms and operates. Independence is enforced by segregation of duties: an auditor cannot hold an operator or control-owner role.

| | |
|---|---|
| **Domain** | GOV |
| **Process owner** | Internal Auditor |
| **Trigger** | Audit programme schedule, or a triggering event |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 9.2
- ISO/IEC 27001:2022: 9.2, 9.2.1, 9.2.2
- iso42001: 9.2

**How this process is measured**

- Programme coverage of all clauses over three years
- Findings closed within agreed dates

> AI participates in sampling, working-paper preparation and evidence retrieval. It does not form the audit opinion: the conclusion, and the independence that gives it value, belong to the auditor.

### Procedure

#### A1. Plan the audit programme so that every clause is covered across the cycle.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | clause_coverage_map, risk_register, previous_findings |
| **Output** | audit_programme |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:9.2.2 |

**AI participation — Audit agent**

- *Asked to:* Propose a programme weighted to risk and to clauses least recently examined, and show the coverage it achieves.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A2. Select the sample for each control in scope and record the basis of selection.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | audit_programme, population_data |
| **Output** | sample_selection |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.2 |
| **Records produced** | sample_selection_record |

**AI participation — Audit agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A3. Retrieve the evidence for each sampled item and prepare the working paper.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | sample_selection |
| **Output** | working_papers |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:9.2 |

**AI participation — Evidence agent**

- *Asked to:* Assemble and summarise the evidence; flag anything missing or expired.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Test the control and reach a conclusion on its operating effectiveness.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | working_papers |
| **Output** | test_conclusions |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:9.2 |

**AI participation — Audit agent**

- *Asked to:* Draft the observation and the proposed rating; the auditor reaches the conclusion.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A5. Raise nonconformities with severity, cause and required correction.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | test_conclusions |
| **Output** | nonconformity_records |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Audit agent**

- *Asked to:* Draft the finding, its cause analysis and a proportionate correction.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A6. Issue the audit report to management. 🛑

| | |
|---|---|
| **Who performs it** | Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | test_conclusions, nonconformity_records |
| **Output** | audit_report |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:9.2.2 |
| **Records produced** | internal_audit_report |

> **This step stops for a human decision** (`audit.report_issue`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-GOV-04 — Management review

The clause that closes the loop. Every required input is assembled automatically, because the usual failure is not poor judgement in the review but a review held without the inputs the standard names.

| | |
|---|---|
| **Domain** | GOV |
| **Process owner** | CISO |
| **Trigger** | Scheduled review, or a significant change or incident |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 75% |

**Clauses discharged**

- ISO 22301:2019: 9.3
- ISO/IEC 27001:2022: 9.3, 9.3.1, 9.3.2, 9.3.3
- iso42001: 9.3

**How this process is measured**

- All required inputs present at review
- Decisions tracked to closure

### Procedure

#### A1. Assemble every input the standard requires: audit results, objective performance, nonconformities, risk position, interested-party feedback, and the status of prior actions.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | audit_report, performance_report, risk_register, gap_register, prior_actions |
| **Output** | review_pack |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.3.2, iso22301:9.3 |
| **Records produced** | management_review_pack |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A2. Confirm the pack is complete against the clause before the meeting is held.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | review_pack |
| **Output** | completeness_check |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:9.3.2 |

**AI participation — Control assessment agent**

- *Asked to:* Check each required input is present and non-empty, and name any that is missing.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Hold the review and record decisions on improvement, resources and change. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | review_pack, completeness_check |
| **Output** | management_review_minutes, review_decisions |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:9.3.3, iso22301:9.3 |
| **Records produced** | management_review_minutes |

> **This step stops for a human decision** (`governance.management_review`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A4. Convert decisions into tracked actions with owners and dates.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | review_decisions |
| **Output** | improvement_actions |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:10.1 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

---

## PR-GOV-05 — Nonconformity and continual improvement

Handles what went wrong: correction, cause, and whether the same cause exists elsewhere. Cause analysis is where this clause is usually thin, so the process forces it before closure.

| | |
|---|---|
| **Domain** | GOV |
| **Process owner** | Control Owner |
| **Trigger** | Nonconformity from any source: audit, incident, exercise, complaint |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 25% |

**Clauses discharged**

- ISO 22301:2019: 10.1, 10.2
- ISO/IEC 27001:2022: 10.1, 10.2
- iso42001: 10.1, 10.2
- UK GDPR: Art.24

**How this process is measured**

- Cause recorded for every nonconformity
- Recurrence rate of closed findings

### Procedure

#### A1. Record the nonconformity and take immediate correction to limit consequence.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | finding |
| **Output** | correction_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Control assessment agent**

- *Asked to:* Draft the correction and identify what is affected right now.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Analyse the cause and determine whether it exists elsewhere in the estate.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | correction_record, control_implementations, incident_history |
| **Output** | cause_analysis, similar_exposure |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Control assessment agent**

- *Asked to:* Analyse cause and search for the same weakness in other controls or systems, citing what supports each match.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Agree corrective action addressing the cause, not only the symptom.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | cause_analysis |
| **Output** | corrective_action |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

#### A4. Verify the action worked before closing the finding.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | On the agreed verification date |
| **Input** | corrective_action |
| **Output** | effectiveness_check |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:10.2 |
| **Records produced** | corrective_action_effectiveness |

**AI participation — Evidence agent**

- *Asked to:* Check the evidence shows the action took effect, and say so plainly if it does not.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

---

## PR-RSK-01 — Risk identification and assessment

Produces a defensible risk position on one scale, across information security, privacy and continuity, so that treatment priorities can be compared across domains.

| | |
|---|---|
| **Domain** | RSK |
| **Process owner** | Risk Officer |
| **Trigger** | New asset, supplier, change, incident, threat intelligence, or scheduled review |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO 22301:2019: 6.1, 8.2.3
- ISO/IEC 27001:2022: 6.1.1, 6.1.2, 8.2
- iso42001: 6.1.1
- UK GDPR: Art.24, Art.32

**How this process is measured**

- Risks reviewed within their cycle
- Share of risks with residual score and named owner

### Procedure

#### A1. Capture the risk as threat, vulnerability, asset and consequence.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | Triggering event |
| **Input** | trigger_event, asset_register, threat_intelligence |
| **Output** | risk_statement |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.2 |

**AI participation — Risk analysis agent**

- *Asked to:* Draft the risk statement and cite the source of the trigger.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A2. Score inherent likelihood and impact before existing controls.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | risk_statement |
| **Output** | inherent_score |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.2 |

**AI participation — Risk analysis agent**

- *Asked to:* Propose scores with the reasoning for each, on the organisation's 5x5 scale.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A3. Identify the controls actually in place and re-score residual risk.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | inherent_score, control_implementations |
| **Output** | residual_score, linked_controls |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3, uk_gdpr:Art.32 |

**AI participation — Risk analysis agent**

- *Asked to:* Map operating controls to the risk and justify the reduction; a control that is implemented but unevidenced does not reduce it.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Risk Officer

#### A4. Confirm the assessment and assign the risk owner.

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | residual_score |
| **Output** | assessed_risk |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:6.1.2 |
| **Records produced** | risk_assessment_record |

---

## PR-RSK-02 — Risk treatment and acceptance

Decides what to do about the risk and, where it is tolerated, records who tolerated it and why. Acceptance above appetite is a named decision, never a default.

| | |
|---|---|
| **Domain** | RSK |
| **Process owner** | Risk Officer |
| **Trigger** | Completion of an assessment, or a change in residual position |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 2 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO 22301:2019: 6.1, 8.3
- ISO/IEC 27001:2022: 6.1.3, 8.3, 6.1.3.d
- UK GDPR: Art.32, Art.35

**How this process is measured**

- Risks above appetite with a recorded acceptance or plan
- Treatment actions delivered by date

### Procedure

#### A1. Select the treatment strategy: mitigate, transfer, avoid or accept.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | assessed_risk |
| **Output** | treatment_strategy |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3 |

**AI participation — Risk analysis agent**

- *Asked to:* Draft options with the cost, the effect on residual score, and the controls each would require.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A2. Determine the controls needed and record them for the Statement of Applicability.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | treatment_strategy |
| **Output** | required_controls, statement_of_applicability_input |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3.c, iso27001:6.1.3.d |

**AI participation — Control assessment agent**

- *Asked to:* Map the treatment to Annex A controls and identify any not yet applicable.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Produce the treatment plan with owner, actions and dates.

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | required_controls |
| **Output** | treatment_plan |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3.e |

#### A4. Obtain risk owner approval of the plan and of any residual risk retained. 🛑

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | treatment_plan |
| **Output** | approved_plan |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:6.1.3.f |

> **This step stops for a human decision** (`risk.treatment_approval`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Accept residual risk that remains above appetite. 🛑

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | approved_plan, residual_score |
| **Output** | acceptance_record |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:6.1.3.f, iso27001:8.3 |
| **Records produced** | residual_risk_acceptance |

> **This step stops for a human decision** (`risk.residual_acceptance`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-RSK-03 — Continuous risk monitoring and review

Keeps the register current between assessments. This is where continuous monitoring earns its place: a register reviewed annually describes last year's organisation.

| | |
|---|---|
| **Domain** | RSK |
| **Process owner** | Risk Officer |
| **Trigger** | Continuous; escalation on threshold breach |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO 22301:2019: 8.2, 9.1
- ISO/IEC 27001:2022: 8.2, 9.1
- iso42001: 9.1

**How this process is measured**

- Overdue risk reviews
- Mean time from signal to register update

### Procedure

#### A1. Detect signals that could move a risk: incidents, control failures, supplier events, threat intelligence.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | Continuous |
| **Input** | incident_register, control_test_results, supplier_events, threat_feeds |
| **Output** | risk_signals |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1 |

**AI participation — Risk analysis agent**

- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A2. Assess whether a signal changes the residual position of any risk.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | risk_signals, risk_register |
| **Output** | proposed_movements |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:8.2 |

**AI participation — Risk analysis agent**

- *Asked to:* Say which risks the signal affects and in which direction, with the evidence. Propose only; the register changes when a person agrees.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Risk Officer

#### A3. Escalate any movement that crosses appetite.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | proposed_movements |
| **Output** | escalations |
| **Mode** | Performed by the platform, owner notified |
| **Target** | Within 4 hours |
| **Evidences** | iso27001:8.2 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A4. Confirm or reject each proposed movement and re-open assessment where needed.

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | proposed_movements, escalations |
| **Output** | risk_movement_report |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:8.2 |

---

## PR-CMP-01 — Control library and applicability maintenance

Maintains the control set and the Statement of Applicability, including the justification for every exclusion — the document a certification auditor reads first.

| | |
|---|---|
| **Domain** | CMP |
| **Process owner** | Control Owner |
| **Trigger** | Programme start, scope change, standard revision, or annual review |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 8.1
- ISO/IEC 27001:2022: 6.1.3.d, Annex A
- iso42001: 8.1
- UK GDPR: Art.24, Art.32

**How this process is measured**

- Exclusions with justification
- Controls with a named owner

### Procedure

#### A1. Materialise an implementation record for every control in the framework.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | framework_catalogue, scope_statement |
| **Output** | control_implementations |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:6.1.3.d |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A2. Propose applicability for each control against the scope and the risk treatment.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | control_implementations, risk_treatment_plans, scope_statement |
| **Output** | applicability_proposals |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3.d |

**AI participation — Control assessment agent**

- *Asked to:* Propose applicable or excluded with a justification an auditor would accept. Mandatory clauses cannot be excluded.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A3. Approve the Statement of Applicability. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | applicability_proposals |
| **Output** | statement_of_applicability |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:6.1.3.d |
| **Records produced** | statement_of_applicability |

> **This step stops for a human decision** (`compliance.soa_approval`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-CMP-02 — Continuous control monitoring

Replaces the annual evidence scramble with a live signal. Machine-testable controls are tested on a schedule against the source system; the rest are attested on a cycle by their owner.

| | |
|---|---|
| **Domain** | CMP |
| **Process owner** | Control Owner |
| **Trigger** | Continuous, on each control's own test frequency |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 67% |

**Clauses discharged**

- ISO 22301:2019: 9.1
- ISO/IEC 27001:2022: 9.1, A.5.35, A.5.36
- iso42001: 9.1
- UK GDPR: Art.32

**How this process is measured**

- Share of controls under automated test
- Mean time from drift to alert
- Evidence freshness

> This is the highest-value automation in the platform and the one with the clearest boundary: collecting and comparing evidence is mechanical, deciding what a shortfall means is not.

### Procedure

#### A1. Run each control's automated test against its source system on schedule.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | Per-control test frequency |
| **Input** | control_implementations, connector_configuration |
| **Output** | raw_test_results |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1 |
| **Records produced** | automated_control_test |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Compare the result against the control's expected state and detect drift.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | raw_test_results, expected_state |
| **Output** | drift_alerts, pass_records |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1 |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Hash and file the result as evidence against the control.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | raw_test_results |
| **Output** | evidence_records |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:7.5.3 |
| **Records produced** | control_evidence_record |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Assess what a drift means and whether it is a gap, an exception or noise.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | drift_alerts, control_implementations |
| **Output** | drift_assessment |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:9.1 |

**AI participation — Control assessment agent**

- *Asked to:* Assess severity and recommend gap, exception or dismissal, citing the evidence. Recommend only.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A5. Request attestation for controls that cannot be tested automatically.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | On the control's attestation cycle |
| **Input** | control_implementations |
| **Output** | attestation_requests |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:9.1 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A6. Attest the control's status and effectiveness. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | attestation_requests, evidence_records |
| **Output** | attestation |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:9.1 |
| **Records produced** | control_attestation |

> **This step stops for a human decision** (`compliance.control_attestation`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-CMP-03 — Gap remediation

Takes a shortfall from identification to verified closure. Overdue remediation is among the first things an external auditor samples.

| | |
|---|---|
| **Domain** | CMP |
| **Process owner** | Control Owner |
| **Trigger** | Gap raised by assessment, monitoring, audit, incident or exercise |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 17% |

**Clauses discharged**

- ISO 22301:2019: 10.1
- ISO/IEC 27001:2022: 10.1, 10.2, 6.1.3
- iso42001: 10.1, 10.2

**How this process is measured**

- Overdue gaps
- Mean time to close by severity
- Reopened gap rate

### Procedure

#### A1. Record the gap with severity rated on consequence if unaddressed.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | finding |
| **Output** | gap_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Control assessment agent**

- *Asked to:* Draft the gap in terms an auditor would accept and rate its severity.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Draft a proportionate remediation plan with effort and a realistic date.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | gap_record |
| **Output** | remediation_plan |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Control assessment agent**

- *Asked to:* Propose the plan and the effort it needs; do not promise dates the owner has not agreed.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Agree the plan, owner and date.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | remediation_plan |
| **Output** | agreed_plan |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:10.2 |

#### A4. Track progress and escalate before, not after, the date is missed.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | Continuous |
| **Input** | agreed_plan |
| **Output** | progress_status, escalations |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:9.1 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A5. Verify closure against evidence before the gap is closed.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | agreed_plan, evidence_records |
| **Output** | closure_evidence |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |
| **Records produced** | gap_closure_evidence |

**AI participation — Evidence agent**

- *Asked to:* State whether the evidence demonstrates closure. If it does not, say what is missing rather than closing on assertion.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A6. Close the gap. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | closure_evidence |
| **Output** | closed_gap |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:10.2 |

> **This step stops for a human decision** (`compliance.gap_closure`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-CMP-04 — Regulatory and standards change management

Detects change in obligations and maps it to the controls and policies it affects, so the organisation learns about a new duty before an auditor tells it.

| | |
|---|---|
| **Domain** | CMP |
| **Process owner** | DPO |
| **Trigger** | Continuous horizon scanning; confirmed change |
| **Cadence** | continuous |
| **Autonomy tier** | L2 |
| **Human decision gates** | 0 |
| **Unattended steps** | 40% |

**Clauses discharged**

- ISO 22301:2019: 4.2
- ISO/IEC 27001:2022: 4.2, A.5.31, A.5.34
- iso42001: 4.2
- UK GDPR: Art.24

**How this process is measured**

- Lag from publication to impact assessment
- Obligations with named owner

> Detection and mapping are automated; interpretation is not. What a new obligation actually requires of this organisation is a legal judgement and stays with the DPO or counsel.

### Procedure

#### A1. Monitor sources for change to law, regulation, standards and codes in scope.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | Continuous |
| **Input** | obligation_register, source_feeds |
| **Output** | candidate_changes |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.5.31 |

**AI participation — Regulatory change agent**

- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Triage each candidate for relevance to the organisation's scope.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | candidate_changes, scope_statement, processing_records |
| **Output** | relevant_changes |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.31 |

**AI participation — Regulatory change agent**

- *Asked to:* Say whether this applies to the organisation and why, citing the provision. Where jurisdiction or applicability is genuinely unclear, say so rather than guessing.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A3. Map the change to affected controls, policies, processes and records.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | relevant_changes, control_library, policy_set |
| **Output** | impact_map |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.31 |

**AI participation — Regulatory change agent**

- *Asked to:* Identify every artefact the change touches and cite the link.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* DPO

#### A4. Interpret what the change requires of this organisation.

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | relevant_changes, impact_map |
| **Output** | impact_assessment |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:A.5.31, uk_gdpr:Art.24 |
| **Records produced** | regulatory_impact_assessment |

#### A5. Raise the actions needed to meet the obligation by its date.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | impact_assessment |
| **Output** | change_actions |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:10.1 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

---

## PR-CMP-05 — Certification and external audit readiness

Keeps the organisation ready for a stage 1 or stage 2 audit at any time, and runs the audit itself when it comes.

| | |
|---|---|
| **Domain** | CMP |
| **Process owner** | CISO |
| **Trigger** | Certification cycle, surveillance visit, or customer audit |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO 22301:2019: 9.2, 9.3
- ISO/IEC 27001:2022: 9.2, 9.3, 10.2
- iso42001: 10.2, 9.2, 9.3

**How this process is measured**

- Certification blockers open
- Evidence pack assembly time
- External findings raised

### Procedure

#### A1. Assess certification readiness and list every blocker with its owner.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Continuous |
| **Input** | control_implementations, gap_register, audit_report, management_review_minutes |
| **Output** | readiness_report |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.3 |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A2. Assemble the evidence pack for the clauses and controls in scope of the visit.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | audit_scope, evidence_records |
| **Output** | evidence_pack |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:7.5.3 |

**AI participation — Evidence agent**

- *Asked to:* Assemble and index the evidence; flag anything expired or missing.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Draft responses to auditor requests and questions.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | On each auditor request |
| **Input** | auditor_request, evidence_pack |
| **Output** | draft_response |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:9.2 |

**AI participation — Audit agent**

- *Asked to:* Draft a response grounded in the evidence on file. Never assert a control operates without an evidence record behind it.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* Internal Auditor

#### A4. Approve and issue each response to the external auditor. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_response |
| **Output** | audit_response |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:9.2 |
| **Records produced** | external_audit_response |

> **This step stops for a human decision** (`audit.external_response`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-PRV-01 — Records of processing and lawful basis

Maintains the Article 30 record and the lawful basis behind every processing activity. Everything else in privacy depends on knowing what is processed, why, and on what basis.

| | |
|---|---|
| **Domain** | PRV |
| **Process owner** | DPO |
| **Trigger** | New or changed processing; annual attestation |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 20% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.34, A.8.11
- UK GDPR: Art.5, Art.6, Art.9, Art.30

**How this process is measured**

- Records attested within 12 months
- Records with documented lawful basis

### Procedure

#### A1. Capture the processing activity: purpose, categories, subjects, recipients, transfers, retention.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | New processing declared, or discovery from system inventory |
| **Input** | intake_form, asset_register, supplier_register |
| **Output** | draft_processing_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.30 |

**AI participation — Privacy operations agent**

- *Asked to:* Draft the record from what was declared and flag any field left unstated.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Determine the lawful basis, and the additional condition where special category data is involved.

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | draft_processing_record |
| **Output** | lawful_basis_determination |
| **Mode** | Performed by a person |
| **Evidences** | uk_gdpr:Art.6, uk_gdpr:Art.9 |
| **Records produced** | lawful_basis_record |

#### A3. Screen for the need for an impact assessment.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | draft_processing_record, lawful_basis_determination |
| **Output** | dpia_screening |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.35 |

**AI participation — Privacy operations agent**

- *Asked to:* Apply the high-risk criteria and say whether an assessment is required, likely required, or not required, with reasons.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A4. Approve the record for the Article 30 register. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | draft_processing_record, lawful_basis_determination |
| **Output** | processing_record |
| **Mode** | **Human decision required** |
| **Evidences** | uk_gdpr:Art.30 |
| **Records produced** | processing_record_approval |

> **This step stops for a human decision** (`privacy.lawful_basis`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Re-attest the record annually and detect drift from the systems it describes.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | Annual, or on detected change |
| **Input** | processing_record, system_inventory |
| **Output** | attestation_request, drift_findings |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | uk_gdpr:Art.30 |

**AI participation — Privacy operations agent**

- *Asked to:* Compare the record against current system reality and report differences.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

---

## PR-PRV-02 — Data subject rights request

Handles an individual exercising their rights, within the statutory period, without disclosing anyone else's data in the process.

| | |
|---|---|
| **Domain** | PRV |
| **Process owner** | DPO |
| **Trigger** | Request received through any channel |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.34
- UK GDPR: Art.12, Art.15, Art.16, Art.17, Art.18, Art.20, Art.21

**How this process is measured**

- Responses within the statutory period
- Requests where identity verification stalled

> Release is a gate for a specific reason: a subject access response usually contains third-party personal data, and disclosing it is an irreversible breach of someone else's rights.

### Procedure

#### A1. Log the request, classify its type and start the statutory clock from receipt.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | Request received |
| **Input** | request |
| **Output** | dsar_record, statutory_deadline |
| **Mode** | Performed by the platform |
| **Target** | Within 24 hours |
| **Evidences** | uk_gdpr:Art.12 |

**AI participation — Privacy operations agent**

- *Asked to:* Classify the right being exercised and compute the deadline.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Verify the requester's identity proportionately to the data at stake.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | dsar_record |
| **Output** | identity_verification |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 72 hours |
| **Evidences** | uk_gdpr:Art.12 |

**AI participation — Privacy operations agent**

- *Asked to:* Check the evidence supplied against the verification standard and say what is missing.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A3. Search the estate for the subject's data across every system in the Article 30 register.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | identity_verification, processing_records, system_connectors |
| **Output** | search_results |
| **Mode** | Performed by the platform |
| **Evidences** | uk_gdpr:Art.15 |
| **Records produced** | dsar_search_record |

**AI participation — Privacy operations agent**

- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A4. Assemble the response pack and mark third-party data and exemptions for redaction.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | search_results |
| **Output** | draft_response_pack, redaction_proposals |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.15 |

**AI participation — Privacy operations agent**

- *Asked to:* Assemble the pack and identify every item containing another person's data or falling under an exemption. Over-inclusion here is a breach; flag anything uncertain for review.
- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A5. Review redactions and confirm the pack discloses nothing it should not.

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | draft_response_pack, redaction_proposals |
| **Output** | reviewed_pack |
| **Mode** | Performed by a person |
| **Evidences** | uk_gdpr:Art.15 |

#### A6. Release the response to the data subject. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | reviewed_pack |
| **Output** | release_record |
| **Mode** | **Human decision required** |
| **Evidences** | uk_gdpr:Art.12, uk_gdpr:Art.15 |
| **Records produced** | dsar_release_record |

> **This step stops for a human decision** (`privacy.dsar_release`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-PRV-03 — Personal data breach assessment and notification

Runs the 72-hour clock from awareness. The deadline runs from the moment the organisation knows, which is why the clock starts when the incident is recorded rather than when someone opens a breach file.

| | |
|---|---|
| **Domain** | PRV |
| **Process owner** | DPO |
| **Trigger** | Incident involving personal data |
| **Cadence** | event driven |
| **Autonomy tier** | L2 |
| **Human decision gates** | 2 |
| **Unattended steps** | 17% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.24, A.5.26, A.6.8
- UK GDPR: Art.33, Art.34, Art.5

**How this process is measured**

- Notifications within 72 hours
- Time from detection to breach determination

### Procedure

#### A1. Determine whether the incident is a personal data breach and start the clock.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | Incident recorded with personal data involvement |
| **Input** | incident |
| **Output** | breach_determination, clock_start |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 4 hours |
| **Evidences** | uk_gdpr:Art.33 |

**AI participation — Privacy operations agent**

- *Asked to:* Assess against the breach definition and cite the basis. If it is genuinely unclear, treat it as a breach and say why — the clock is running either way.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Establish the facts: categories, approximate numbers, cause, containment.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | breach_determination, incident_evidence |
| **Output** | breach_facts |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 12 hours |
| **Evidences** | uk_gdpr:Art.33 |

**AI participation — Incident agent**

- *Asked to:* Assemble what is known and state plainly what is not yet known.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

#### A3. Assess the risk to the rights and freedoms of the individuals affected.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | breach_facts |
| **Output** | risk_to_individuals |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 24 hours |
| **Evidences** | uk_gdpr:Art.33, uk_gdpr:Art.34 |

**AI participation — Privacy operations agent**

- *Asked to:* Draft the assessment with the factors driving it; the DPO reaches the conclusion.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A4. Decide whether to notify the supervisory authority. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | risk_to_individuals |
| **Output** | notification_decision |
| **Mode** | **Human decision required** |
| **Target** | Within 72 hours |
| **Evidences** | uk_gdpr:Art.33 |
| **Records produced** | breach_notification_decision |

> **This step stops for a human decision** (`privacy.breach_notify`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Decide whether the individuals themselves must be told. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | risk_to_individuals, notification_decision |
| **Output** | subject_notification_decision |
| **Mode** | **Human decision required** |
| **Evidences** | uk_gdpr:Art.34 |

> **This step stops for a human decision** (`privacy.subject_notification`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A6. Record the decision, the reasoning and any submission reference.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | notification_decision, subject_notification_decision |
| **Output** | breach_record |
| **Mode** | Performed by the platform |
| **Evidences** | uk_gdpr:Art.33.5 |
| **Records produced** | breach_register_entry |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-PRV-04 — Data protection impact assessment

Assesses high-risk processing before it starts, and determines whether the regulator must be consulted.

| | |
|---|---|
| **Domain** | PRV |
| **Process owner** | DPO |
| **Trigger** | Screening indicates high risk; new technology or large-scale processing |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.8.25, A.8.27
- UK GDPR: Art.35, Art.36, Art.25

**How this process is measured**

- DPIAs completed before processing begins
- Consultations required and made

### Procedure

#### A1. Describe the processing, its necessity and its proportionality.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | processing_record, system_design |
| **Output** | processing_description |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.35.7 |

**AI participation — Privacy operations agent**

- *Asked to:* Draft the description and test the necessity argument against the stated purpose.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Assess risks to individuals and the measures that address them.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | processing_description, control_implementations |
| **Output** | risk_assessment, proposed_measures |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.35.7, uk_gdpr:Art.25 |

**AI participation — Privacy operations agent**

- *Asked to:* Identify risks to individuals specifically, not risks to the organisation.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* DPO

#### A3. Consult the data protection officer and, where appropriate, affected individuals.

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | risk_assessment |
| **Output** | dpo_opinion |
| **Mode** | Performed by a person |
| **Evidences** | uk_gdpr:Art.35.2 |

#### A4. Decide whether residual high risk requires prior consultation with the regulator. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | risk_assessment, dpo_opinion |
| **Output** | consultation_decision |
| **Mode** | **Human decision required** |
| **Evidences** | uk_gdpr:Art.36 |
| **Records produced** | dpia_report |

> **This step stops for a human decision** (`privacy.dpia_decision`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-PRV-05 — International transfers and retention

Governs where personal data goes and how long it stays. Both are areas where the record and the reality drift apart quietly.

| | |
|---|---|
| **Domain** | PRV |
| **Process owner** | DPO |
| **Trigger** | New transfer or recipient; retention schedule review |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 25% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.14, A.8.10
- UK GDPR: Art.5.1.e, Art.44, Art.46, Art.49

**How this process is measured**

- Transfers with a valid mechanism
- Data held beyond its retention rule

### Procedure

#### A1. Identify the transfer, the destination and the mechanism relied on.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | processing_records, supplier_register |
| **Output** | transfer_register |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.44 |

**AI participation — Privacy operations agent**

- *Asked to:* Draft the entry and flag any transfer with no mechanism recorded.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Assess the destination's legal regime and any supplementary measures needed.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | transfer_register |
| **Output** | transfer_risk_assessment |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.46 |
| **Records produced** | transfer_risk_assessment |

**AI participation — Privacy operations agent**

- *Asked to:* Draft the assessment. Adequacy status and the sufficiency of supplementary measures are legal judgements; present the position, do not conclude it.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A3. Enforce retention: detect data held beyond its rule and raise disposal actions.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | Scheduled |
| **Input** | retention_schedule, system_inventory |
| **Output** | retention_exceptions |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | uk_gdpr:Art.5.1.e, iso27001:A.8.10 |
| **Records produced** | retention_review_record |

**AI participation — Privacy operations agent**

- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A4. Authorise disposal. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | retention_exceptions |
| **Output** | disposal_authorisation |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.8.10 |

> **This step stops for a human decision** (`privacy.disposal_authorisation`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-SEC-01 — Security event triage and incident response

Takes a signal to a decision quickly, and routes anything touching personal data into the breach clock.

| | |
|---|---|
| **Domain** | SEC |
| **Process owner** | CISO |
| **Trigger** | Alert, report or detection |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 40% |

**Clauses discharged**

- ISO 22301:2019: 8.4
- ISO/IEC 27001:2022: A.5.24, A.5.25, A.5.26, A.5.27, A.6.8
- UK GDPR: Art.32, Art.33

**How this process is measured**

- Time to triage
- Incidents with lessons captured
- Repeat incidents by cause

### Procedure

#### A1. Record the event and enrich it with asset, owner and data-classification context.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Alert received |
| **Input** | alert, asset_register, processing_records |
| **Output** | enriched_event |
| **Mode** | Performed by the platform |
| **Target** | Within 1 hours |
| **Evidences** | iso27001:A.5.24 |

**AI participation — Incident agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

#### A2. Triage: classify severity, type and whether personal data is involved.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | enriched_event |
| **Output** | triage_decision |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 2 hours |
| **Evidences** | iso27001:A.5.25 |

**AI participation — Incident agent**

- *Asked to:* Classify and give the reasoning. Where personal data involvement is uncertain, say yes and let a person rule it out: the cost of a false positive is a review, the cost of a false negative is a missed statutory deadline.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

#### A3. Contain and eradicate, recording each action as it is taken.

| | |
|---|---|
| **Who performs it** | Operator |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | triage_decision |
| **Output** | response_actions |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:A.5.26 |

#### A4. Hand off to breach assessment where personal data is involved.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | triage_decision |
| **Output** | breach_referral |
| **Mode** | Performed by the platform, owner notified |
| **Target** | Within 2 hours |
| **Evidences** | uk_gdpr:Art.33 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A5. Conduct the post-incident review and feed the cause into improvement.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | response_actions |
| **Output** | post_incident_review |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.27 |
| **Records produced** | post_incident_review |

**AI participation — Incident agent**

- *Asked to:* Draft the timeline and cause analysis from the recorded actions.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

---

## PR-SEC-02 — Vulnerability and patch management

Finds technical weakness and closes it within the window its severity warrants.

| | |
|---|---|
| **Domain** | SEC |
| **Process owner** | CISO |
| **Trigger** | Scan results, advisory, or threat intelligence |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 60% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.8.8, A.8.9, A.8.19, A.8.32
- UK GDPR: Art.32

**How this process is measured**

- Vulnerabilities open beyond SLA by severity
- Patch coverage

### Procedure

#### A1. Ingest findings from scanners and advisories and deduplicate against the register.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Continuous |
| **Input** | scanner_output, advisories, asset_register |
| **Output** | vulnerability_register |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.8 |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Prioritise by exploitability and by the business value of the affected asset.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | vulnerability_register, asset_register |
| **Output** | prioritised_queue |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.8 |

**AI participation — Risk analysis agent**

- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A3. Remediate within the window for the severity.

| | |
|---|---|
| **Who performs it** | Operator |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | prioritised_queue |
| **Output** | remediation_actions |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:A.8.8 |

#### A4. Approve any exception where remediation is not possible within the window. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | prioritised_queue |
| **Output** | exception_records |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.8.8 |

> **This step stops for a human decision** (`security.vulnerability_exception`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Verify closure by re-test rather than by assertion.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | remediation_actions |
| **Output** | verification_results |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.8 |
| **Records produced** | vulnerability_closure_evidence |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-SEC-03 — Logging, monitoring and detection assurance

Assures that the things meant to be watched are actually being watched. A detection control that stopped working is invisible until it is needed.

| | |
|---|---|
| **Domain** | SEC |
| **Process owner** | CISO |
| **Trigger** | Continuous; monthly assurance review |
| **Cadence** | monthly |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 100% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.8.15, A.8.16, A.8.17, A.5.28
- UK GDPR: Art.32

**How this process is measured**

- Log source coverage against the asset register
- Sources silent beyond threshold

### Procedure

#### A1. Compare log sources actually reporting against the assets that should report.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Daily |
| **Input** | log_sources, asset_register |
| **Output** | coverage_report, silent_sources |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.15, iso27001:A.8.16 |
| **Records produced** | log_coverage_evidence |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Raise a gap where a source has fallen silent or coverage has regressed.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | silent_sources |
| **Output** | detection_gaps |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.8.16 |

**AI participation — Control assessment agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Confirm clock synchronisation and log protection remain in force.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Weekly |
| **Input** | log_sources |
| **Output** | integrity_check |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.17 |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-TPR-01 — Supplier inherent risk and tiering

Decides how much diligence an engagement actually warrants, before any is done. Tiering every supplier the same way is how diligence budgets are wasted on low-risk vendors and skipped on critical ones.

| | |
|---|---|
| **Domain** | TPR |
| **Process owner** | Control Owner |
| **Trigger** | New engagement or material change of scope |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO 22301:2019: 8.3
- ISO/IEC 27001:2022: A.5.19, A.5.21
- UK GDPR: Art.28

**How this process is measured**

- Engagements tiered before contract
- Tier changes at reassessment

### Procedure

#### A1. Capture the engagement: service, data accessed, criticality, jurisdictions, subcontracting.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | engagement_request |
| **Output** | engagement_profile |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.19 |

**AI participation — Third-party risk agent**

- *Asked to:* Draft the profile from the request and name every field left unanswered.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A2. Score inherent risk and assign a tier that sets the diligence depth.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | engagement_profile |
| **Output** | inherent_risk_profile, diligence_scope |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.19 |

**AI participation — Third-party risk agent**

- *Asked to:* Score exposure to the organisation — not the supplier's controls, which are not yet known — and justify the tier.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

---

## PR-TPR-02 — Supplier due diligence and approval

Assesses the supplier's controls against the exposure, and approves or refuses the engagement.

| | |
|---|---|
| **Domain** | TPR |
| **Process owner** | Control Owner |
| **Trigger** | Completion of tiering |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 2 |
| **Unattended steps** | 20% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.19, A.5.20, A.5.21, A.5.22
- UK GDPR: Art.28, Art.32, Art.44

**How this process is measured**

- Assessment turnaround
- Engagements approved with open conditions

### Procedure

#### A1. Issue the questionnaire scoped to the tier and collect responses and certifications.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | diligence_scope |
| **Output** | responses, certifications |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.5.19 |

**AI participation — Third-party risk agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A2. Assess responses domain by domain and reconcile them against evidence supplied.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | responses, certifications |
| **Output** | domain_scores, concerns |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.19, uk_gdpr:Art.28 |

**AI participation — Third-party risk agent**

- *Asked to:* Score each domain and cite the response supporting it. Where a certificate's scope does not cover the service being bought, say so — that is the most common misread.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A3. Determine residual risk and the conditions to attach to approval.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | domain_scores, concerns, inherent_risk_profile |
| **Output** | residual_rating, contract_requirements |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.20, uk_gdpr:Art.28.3 |

**AI participation — Third-party risk agent**

- *Asked to:* Propose residual rating and the specific clauses the contract must carry.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A4. Approve or refuse the engagement. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | residual_rating |
| **Output** | engagement_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.19 |
| **Records produced** | supplier_approval_record |

> **This step stops for a human decision** (`supplier.engagement`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Confirm the executed contract carries the required clauses before service begins. 🛑

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | contract_requirements, executed_contract |
| **Output** | contract_confirmation |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.20, uk_gdpr:Art.28.3 |

> **This step stops for a human decision** (`supplier.contract`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-TPR-03 — Ongoing supplier monitoring and exit

Watches the supplier between assessments and governs exit. Most third-party incidents happen to suppliers that passed diligence some time ago.

| | |
|---|---|
| **Domain** | TPR |
| **Process owner** | Control Owner |
| **Trigger** | Continuous monitoring; contract renewal; termination |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 8.3
- ISO/IEC 27001:2022: A.5.22, A.5.23
- UK GDPR: Art.28

**How this process is measured**

- Critical suppliers reassessed within cycle
- Exits with data return or destruction evidenced

### Procedure

#### A1. Monitor for supplier events: breaches, certificate expiry, adverse media, financial distress.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | Continuous |
| **Input** | supplier_register, external_feeds |
| **Output** | monitoring_signals |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.5.22 |

**AI participation — Third-party risk agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A2. Decide whether a signal warrants reassessment ahead of cycle.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | monitoring_signals |
| **Output** | reassessment_trigger |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.22 |

**AI participation — Third-party risk agent**

- *Asked to:* Recommend reassess or note, with the reasoning.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A3. On exit, confirm data return or destruction and access revocation.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | termination_notice |
| **Output** | exit_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.22, uk_gdpr:Art.28.3.g |
| **Records produced** | supplier_exit_record |

**AI participation — Third-party risk agent**

- *Asked to:* Assemble the exit checklist and identify what remains outstanding.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

---

## PR-RES-01 — Business impact analysis

Establishes what must keep running, how quickly it must recover, and how much data loss is tolerable.

| | |
|---|---|
| **Domain** | RES |
| **Process owner** | Control Owner |
| **Trigger** | Annual review, new activity, or material change |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO 22301:2019: 8.2, 8.2.2, 8.2.3
- ISO/IEC 27001:2022: A.5.29, A.5.30

**How this process is measured**

- Prioritised activities with current BIA
- RTOs shorter than MTPD

### Procedure

#### A1. Identify the prioritised activity and map its dependencies: people, systems, suppliers, sites.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | activity_register, asset_register, supplier_register |
| **Output** | dependency_map |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso22301:8.2.2 |

**AI participation — Resilience agent**

- *Asked to:* Draft the dependency map from the registers and flag single points of failure.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Analyse impact over time and derive MTPD, RTO, RPO and the minimum objective.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | dependency_map |
| **Output** | recovery_objectives |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso22301:8.2.2 |

**AI participation — Resilience agent**

- *Asked to:* Draft the impact profile and derive objectives; the RTO must be shorter than the MTPD.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Approve the analysis and its recovery objectives. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | recovery_objectives |
| **Output** | bia_record |
| **Mode** | **Human decision required** |
| **Evidences** | iso22301:8.2.3 |
| **Records produced** | approved_bia |

> **This step stops for a human decision** (`resilience.bia_signoff`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-RES-02 — Continuity strategy and plan development

Turns approved recovery objectives into arrangements that can actually meet them.

| | |
|---|---|
| **Domain** | RES |
| **Process owner** | Control Owner |
| **Trigger** | Approved BIA, or change to the estate |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO 22301:2019: 8.3, 8.3.1, 8.3.2, 8.3.3, 8.4, 8.4.1, 8.4.2

**How this process is measured**

- Plans approved and current
- Plans meeting their stated RTO at exercise

### Procedure

#### A1. Identify strategy options that meet the RTO within available resources.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | bia_record |
| **Output** | strategy_options |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso22301:8.3.2 |

**AI participation — Resilience agent**

- *Asked to:* Draft options with cost, achievable recovery time and the gap to the objective.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Select the strategy and specify the resources it requires.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | strategy_options |
| **Output** | continuity_strategy, resource_requirements |
| **Mode** | Performed by a person |
| **Evidences** | iso22301:8.3.3 |

#### A3. Write the plan: invocation criteria, roles, procedures, communications.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | continuity_strategy |
| **Output** | draft_plan |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso22301:8.4.2 |

**AI participation — Resilience agent**

- *Asked to:* Draft the plan in the house structure and flag anything the strategy leaves unresolved.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Approve the plan. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | draft_plan |
| **Output** | continuity_plan |
| **Mode** | **Human decision required** |
| **Evidences** | iso22301:8.4.1 |
| **Records produced** | approved_continuity_plan |

> **This step stops for a human decision** (`resilience.plan_approval`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-RES-03 — Exercising and testing

Proves the plan works. An unexercised plan is a document, and clause 8.5 exists because organisations discover this during the incident rather than before it.

| | |
|---|---|
| **Domain** | RES |
| **Process owner** | Control Owner |
| **Trigger** | Exercise schedule; significant change to the plan or estate |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 8.5, 9.1
- ISO/IEC 27001:2022: A.5.29, A.5.30
- iso42001: 9.1

**How this process is measured**

- Plans exercised within 12 months
- Exercises meeting stated RTO
- Findings closed

### Procedure

#### A1. Design a scenario that genuinely tests the plan's assumptions.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | continuity_plan, risk_register, incident_history |
| **Output** | exercise_scenario |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso22301:8.5 |

**AI participation — Resilience agent**

- *Asked to:* Propose a scenario that stresses the plan's weakest assumption, drawn from the risk register and real incidents.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Run the exercise and record what actually happened against the clock.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | exercise_scenario |
| **Output** | exercise_log, achieved_objectives |
| **Mode** | Performed by a person |
| **Evidences** | iso22301:8.5 |
| **Records produced** | exercise_record |

#### A3. Compare achieved recovery against the objective and raise a gap where it was missed.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | exercise_log, recovery_objectives |
| **Output** | exercise_report, improvement_actions |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso22301:8.5, iso22301:10.1 |
| **Records produced** | exercise_report |

**AI participation — Resilience agent**

- *Asked to:* Report the shortfall plainly; an exercise that missed its RTO is a finding, not a pass.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-RES-04 — Crisis invocation and recovery

Governs live invocation, where speed matters and the decision is irreversible.

| | |
|---|---|
| **Domain** | RES |
| **Process owner** | CISO |
| **Trigger** | Disruption meeting invocation criteria |
| **Cadence** | event driven |
| **Autonomy tier** | L1 |
| **Human decision gates** | 2 |
| **Unattended steps** | 25% |

**Clauses discharged**

- ISO 22301:2019: 8.4, 8.4.3, 8.4.4, 8.4.5

**How this process is measured**

- Time from disruption to invocation decision
- Recovery within RTO

> Autonomy is deliberately lowest here. During a live incident the platform informs and records; it does not act. An agent invoking failover on a false positive would cause the outage it was meant to contain.

### Procedure

#### A1. Assess the disruption against invocation criteria and brief the response team.

| | |
|---|---|
| **Who performs it** | Resilience agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | disruption_report, continuity_plan |
| **Output** | invocation_assessment |
| **Mode** | AI-drafted, person owns the output |
| **Target** | Within 1 hours |
| **Evidences** | iso22301:8.4.3 |

**AI participation — Resilience agent**

- *Asked to:* Compare the situation against the criteria and present the position. Do not conclude.
- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Control Owner

#### A2. Decide to invoke. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | invocation_assessment |
| **Output** | invocation_record |
| **Mode** | **Human decision required** |
| **Evidences** | iso22301:8.4.3 |
| **Records produced** | invocation_decision |

> **This step stops for a human decision** (`resilience.live_failover`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A3. Record actions, decisions and communications throughout recovery.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Continuous during invocation |
| **Input** | invocation_record |
| **Output** | recovery_log |
| **Mode** | Performed by the platform |
| **Evidences** | iso22301:8.4.4 |
| **Records produced** | crisis_log |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Stand down and begin the post-incident review. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | recovery_log |
| **Output** | stand_down_record |
| **Mode** | **Human decision required** |
| **Evidences** | iso22301:8.4.5 |

> **This step stops for a human decision** (`resilience.stand_down`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-PPL-01 — Joiner, mover, leaver

Ensures access matches role at all times, and ends promptly when it should.

| | |
|---|---|
| **Domain** | PPL |
| **Process owner** | Security Admin |
| **Trigger** | HR event |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 75% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.16, A.5.17, A.5.18, A.6.1, A.6.2, A.6.5
- UK GDPR: Art.32

**How this process is measured**

- Leaver access revoked within SLA
- Orphaned accounts detected

### Procedure

#### A1. Derive the entitlement set from the role and provision it.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | HR joiner or mover event |
| **Input** | hr_event, role_entitlement_map |
| **Output** | provisioning_plan |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.5.16, iso27001:A.5.18 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A2. Approve any entitlement beyond the role's standard set. 🛑

| | |
|---|---|
| **Who performs it** | Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | provisioning_plan |
| **Output** | approved_exception |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.18 |

> **This step stops for a human decision** (`access.privileged_grant`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A3. Revoke access on the leaver date and confirm it took effect.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | HR leaver event |
| **Input** | hr_event |
| **Output** | revocation_record |
| **Mode** | Performed by the platform |
| **Target** | Within 24 hours |
| **Evidences** | iso27001:A.5.18, iso27001:A.6.5 |
| **Records produced** | access_revocation_evidence |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

#### A4. Reconcile accounts against the HR record and raise any that do not match.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | Daily |
| **Input** | account_inventory, hr_record |
| **Output** | orphan_findings |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.5.16 |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-PPL-02 — Access recertification

Periodically re-justifies who has what, and removes what cannot be justified.

| | |
|---|---|
| **Domain** | PPL |
| **Process owner** | Security Admin |
| **Trigger** | Recertification cycle by system criticality |
| **Cadence** | quarterly |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.16, A.5.18, A.8.2

**How this process is measured**

- Campaign completion rate
- Entitlements revoked at review

### Procedure

#### A1. Assemble the review pack per reviewer, with last-used data to make the decision informed.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | entitlement_inventory, usage_telemetry |
| **Output** | review_packs |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.5.18 |

**AI participation — Evidence agent**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Highlight entitlements that look anomalous or unused.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | review_packs |
| **Output** | flagged_entitlements |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.18 |

**AI participation — Control assessment agent**

- *Asked to:* Flag outliers against role peers and long-unused access, with the reasoning.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Review and decide on each entitlement. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | review_packs, flagged_entitlements |
| **Output** | recertification_decisions |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.18 |
| **Records produced** | recertification_record |

> **This step stops for a human decision** (`access.recertification`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A4. Execute revocations and confirm they took effect.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | recertification_decisions |
| **Output** | revocations |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.5.18 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

---

## PR-PPL-03 — Awareness and competence

Maintains and evidences the competence the standards require of the people operating controls.

| | |
|---|---|
| **Domain** | PPL |
| **Process owner** | Security Admin |
| **Trigger** | Onboarding; annual cycle; role change |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO 22301:2019: 7.2, 7.3
- ISO/IEC 27001:2022: 7.2, 7.3, A.6.3
- iso42001: 7.2, 7.3
- UK GDPR: Art.39

**How this process is measured**

- Training completion by due date
- Roles with a defined competence profile

### Procedure

#### A1. Determine the competence each role requires and identify the shortfall.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | role_definitions, competence_records |
| **Output** | competence_gaps |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:7.2 |

**AI participation — Control assessment agent**

- *Asked to:* Map role to required competence and name the gap for each person.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Assign and track training to close the shortfall.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Security Admin |
| **Who is accountable** | Security Admin |
| **When** | sequence |
| **Input** | competence_gaps |
| **Output** | training_completion |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:7.2, iso27001:A.6.3 |
| **Records produced** | training_evidence |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

---

## PR-CHG-01 — Change management

Ensures change is assessed for security, privacy and continuity impact before it reaches production.

| | |
|---|---|
| **Domain** | CHG |
| **Process owner** | Control Owner |
| **Trigger** | Change request raised |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO 22301:2019: 8.1
- ISO/IEC 27001:2022: 8.1, A.8.32, A.8.9
- iso42001: 8.1
- UK GDPR: Art.25, Art.35

**How this process is measured**

- Emergency changes as a share of total
- Changes reversed after release

### Procedure

#### A1. Assess the change for security, privacy and continuity impact.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | change_request, asset_register, processing_records |
| **Output** | impact_assessment |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:8.1, uk_gdpr:Art.25 |

**AI participation — Control assessment agent**

- *Asked to:* Identify affected controls, processing activities and recovery objectives, and say whether a DPIA is triggered.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A2. Decide go or no-go. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | impact_assessment |
| **Output** | approval_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.8.32 |
| **Records produced** | change_approval_record |

> **This step stops for a human decision** (`change.go_no_go`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A3. Update affected records after release: controls, processing records, recovery objectives.

| | |
|---|---|
| **Who performs it** | Orchestration agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | approval_decision, release_record |
| **Output** | record_updates |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:8.1 |

**AI participation — Orchestration agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* Platform Admin

---

## PR-CHG-02 — Secure development and go-live assurance

Builds requirements in at design time and confirms them before release rather than after.

| | |
|---|---|
| **Domain** | CHG |
| **Process owner** | CISO |
| **Trigger** | New system or significant feature entering design |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.8.25, A.8.26, A.8.27, A.8.28, A.8.29, A.8.31
- UK GDPR: Art.25

**How this process is measured**

- Findings raised at design versus at release
- Go-lives with open high findings

### Procedure

#### A1. Derive security and privacy requirements for the design.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | design_document, processing_records, control_library |
| **Output** | security_requirements |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.8.25, uk_gdpr:Art.25 |

**AI participation — Control assessment agent**

- *Asked to:* Derive requirements from the control library and data protection by design obligations.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Verify requirements are met by test evidence before release.

| | |
|---|---|
| **Who performs it** | Evidence agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | security_requirements, test_evidence |
| **Output** | test_results |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.8.29 |

**AI participation — Evidence agent**

- *Asked to:* State which requirements are evidenced and which are asserted but not demonstrated.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A3. Approve go-live. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | test_results |
| **Output** | golive_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.8.31 |
| **Records produced** | golive_approval |

> **This step stops for a human decision** (`golive.security_by_design`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-APS-01 — Design the Organization Normative Framework iteration

Sets what application security means in this organisation for this iteration: the contexts, the levels of trust, and the Application Security Controls that make up the library. Built iteratively because an ONF attempted in one pass is never finished.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | CISO |
| **Trigger** | Committee mandated, or the improvement loop has raised a redesign need |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO/IEC 27001:2022: 6.1.3, 8.1
- iso42001: 8.1, A.6.1.3

**How this process is measured**

- Every ASC carries both an activity and a measurement
- Exactly one level zero defined per iteration

> A reference stage with no local stage mapped to it makes every ASC placed there unschedulable, which is why A5 reports the gap rather than skipping it.

### Procedure

#### A1. Set application security goals and the scope of this ONF iteration.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | context_analysis, audit_findings |
| **Output** | onf_iteration_scope |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:6.1.3 |

#### A2. Document the business, regulatory and technological contexts that apply to applications in this iteration.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | obligation_register, asset_register, supplier_register |
| **Output** | onf_contexts |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:4.1 |

**AI participation — Regulatory change agent**

- *Asked to:* Propose context entries with a retrievable source for each, and flag which have changed since the last iteration.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A3. Define the levels of trust, including exactly one level zero — the floor a project team cannot go below.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | onf_iteration_scope |
| **Output** | trust_levels |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:6.1.3 |
| **Records produced** | trust_level_definition |

#### A4. Design the Application Security Controls for this iteration. Each needs a security activity and a verification measurement performed by different parties — one without the other is a checklist item.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | trust_levels, onf_contexts, risk_register |
| **Output** | asc_library |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.3, iso42001:A.6.1.3 |

**AI participation — Normative framework steward**

- *Asked to:* Draft ASC definitions with both halves specified, and flag any control whose measurement an agent should not be permitted to make.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A5. Map the organisation's own delivery stages onto the reference life cycle model, so an ASC can be issued in the delivery team's own words.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | asc_library |
| **Output** | lifecycle_stage_map |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Normative framework steward**

- *Asked to:* Propose the mapping and identify reference stages with no local equivalent.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A6. Approve the iteration scope and the ASC library. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | asc_library, trust_levels, lifecycle_stage_map |
| **Output** | approved_onf_iteration |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:5.1 |

> **This step stops for a human decision** (`onf_iteration_approval`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-APS-02 — Implement and communicate the ONF

Turns approved ASC definitions into things delivery teams can actually do: pipeline automation for the automatable ones, training for the rest, and publication in each team's own vocabulary.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | ONF iteration approved |
| **Cadence** | annual |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 60% |

**Clauses discharged**

- ISO/IEC 27001:2022: 7.2, 7.3, 8.1
- iso42001: 7.2, 7.3, 8.1

**How this process is measured**

- Every implemented ASC has a trained actor

### Procedure

#### A1. Assess the impact and complexity of building each designed ONF element.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | approved_onf_iteration |
| **Output** | implementation_plan |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Normative framework steward**

- *Asked to:* Estimate effort per element and identify dependencies between them.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Build the automation an automatable ASC needs in the delivery pipeline.

| | |
|---|---|
| **Who performs it** | Application security execution agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | implementation_plan |
| **Output** | pipeline_controls |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.8.28 |

**AI participation — Application security execution agent**

- *Escalates to a person below confidence:* 0.95
- *Accountable for this agent:* Control Owner

#### A3. Translate each ASC into the delivery team's own stage vocabulary using the life cycle mapping.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | asc_library, lifecycle_stage_map |
| **Output** | translated_asc_set |
| **Mode** | Performed by the platform |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Determine and deliver the training each actor needs to use the element.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | translated_asc_set |
| **Output** | training_records |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:7.2, iso42001:7.2 |
| **Records produced** | training_completion |

#### A5. Publish the ASC library to delivery teams and to the governed tool surface.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | translated_asc_set |
| **Output** | published_asc_library |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-APS-03 — Monitor and review the ONF

Tests whether the ONF is doing anything. An ASC that is never measured, or that always passes, is usually measuring nothing — surfacing that matters more than the pass rate.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | Quarterly, or a change in a business, regulatory or technological context |
| **Cadence** | quarterly |
| **Autonomy tier** | L4 |
| **Human decision gates** | 0 |
| **Unattended steps** | 60% |

**Clauses discharged**

- ISO/IEC 27001:2022: 9.1
- iso42001: 9.1

**How this process is measured**

- Every application carries a targeted and an actual level of trust
- Zero ASCs with no measurement in the review period

### Procedure

#### A1. Apply the defined measurement methods to each ONF element.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | asc_evidence |
| **Output** | onf_measurement_set |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1 |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A2. Confirm every application in the register carries both a targeted and an actual level of trust.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | application_register |
| **Output** | level_of_trust_completeness |
| **Mode** | Performed by the platform |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A3. Confirm every application has had a risk assessment inside its review period.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | application_register, risk_register |
| **Output** | assessment_currency_report |
| **Mode** | Performed by the platform |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A4. Flag ASCs that are never measured, always pass, or always fail as candidates for redesign.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | onf_measurement_set |
| **Output** | improvement_candidates |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Normative framework steward**

- *Asked to:* Explain why each flagged ASC is not discriminating, and propose a change.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A5. Record the review results and the improvements they identify.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | onf_measurement_set, improvement_candidates |
| **Output** | onf_review_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:9.1 |
| **Records produced** | onf_review |

---

## PR-APS-04 — Improve the ONF from project feedback

Closes the loop the standard calls for explicitly: what application projects learned goes back into the library, rather than staying in the project that learned it.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | Review findings, project feedback, an audit finding, or an incident |
| **Cadence** | quarterly |
| **Autonomy tier** | L2 |
| **Human decision gates** | 0 |
| **Unattended steps** | 33% |

**Clauses discharged**

- ISO/IEC 27001:2022: 10.1, 10.2
- iso42001: 10.1, 10.2

**How this process is measured**

- Repeated waivers on the same ASC trigger a redesign within one iteration

### Procedure

#### A1. Collect feedback from completed application projects on ASC usability and cost.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | asc_evidence |
| **Output** | project_feedback |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Analyse root causes behind failed measurements and repeated waivers.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | project_feedback, onf_review_record |
| **Output** | root_cause_analysis |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

**AI participation — Normative framework steward**

- *Asked to:* Group failures by cause and distinguish a bad control from a bad process.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Decide which ONF elements to redesign in the next iteration.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | root_cause_analysis |
| **Output** | onf_backlog |
| **Mode** | Performed by a person |

---

## PR-APS-05 — Audit the ONF

Independent verification that the ONF exists, is used, and that applications comply with it. Conclusions are a human act; the agent assembles the pack and stops there.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Internal Auditor |
| **Trigger** | Audit programme schedule |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 0 |
| **Unattended steps** | 25% |

**Clauses discharged**

- ISO/IEC 27001:2022: 9.2
- iso42001: 9.2

**How this process is measured**

- Auditor independent of the ONF committee in 100% of audits

> No agent performs A3 or A4. An agent auditing the controls that bound agents is the clearest case where fluency would be mistaken for assurance.

### Procedure

#### A1. Establish the audit programme and confirm auditor competence and independence.

| | |
|---|---|
| **Who performs it** | Internal Auditor |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Output** | onf_audit_programme |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:9.2 |

#### A2. Assemble the audit pack: ONF elements, responsibility records, change history and prior findings.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | asc_library, asc_evidence |
| **Output** | onf_audit_pack |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Audit agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A3. Verify that the verification activities of each ONF sub-process were performed, and that applications comply with the ONF.

| | |
|---|---|
| **Who performs it** | Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | onf_audit_pack |
| **Output** | onf_audit_findings |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:9.2, iso42001:9.2 |
| **Records produced** | audit_working_paper |

#### A4. Record findings, root causes and agreed remediation with owners and dates.

| | |
|---|---|
| **Who performs it** | Internal Auditor |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | onf_audit_findings |
| **Output** | onf_audit_report, audit_findings |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:10.2 |

---

## PR-APS-06 — Specify application requirements and environment

Registers the application and fixes which contexts apply to it, which is what makes every later selection of controls defensible rather than arbitrary.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | A new application project starts, or an existing application enters the register |
| **Cadence** | event driven |
| **Autonomy tier** | L2 |
| **Human decision gates** | 0 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO/IEC 27001:2022: 8.1
- iso42001: 8.1, A.6.2.2

**How this process is measured**

- Zero applications in production without a register entry

> A4 is the single junction between ISO/IEC 27034 and ISO/IEC 42001. An AI-bearing application runs both tracks.

### Procedure

#### A1. Register the application with its owner, sourcing model, criticality and whether it carries an AI system.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Output** | application_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.9 |

#### A2. Select the business, regulatory and technological contexts that apply.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | onf_contexts, application_record |
| **Output** | selected_contexts |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Record actors, specifications and the information the application handles.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | application_record |
| **Output** | application_specification |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.12 |

**AI participation — Normative framework steward**

- *Asked to:* Draft the specification and classify the data elements it names.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Where the application carries an AI system, create the AI system register entry and hand off to the AI governance track.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | application_record |
| **Output** | ai_system_record |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.6.2.2 |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-APS-07 — Assess application security risk and set the targeted level of trust

Produces the one number the rest of the ASMP depends on. The owner approves it, which is what makes the control set a decision rather than a default.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Risk Officer |
| **Trigger** | Application requirements baselined, or a material change to the application or its contexts |
| **Cadence** | event driven |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO/IEC 27001:2022: 6.1.2, 8.2

**How this process is measured**

- Targeted level of trust approved by a named owner in 100% of projects

### Procedure

#### A1. Identify threats, vulnerabilities and impacts at the application level.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | application_specification, selected_contexts |
| **Output** | application_threat_set |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:6.1.2 |

**AI participation — Risk analysis agent**

- *Asked to:* Draft the threat and vulnerability set and cite the context that raises each.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A2. Analyse and evaluate the risks against the organisation's criteria.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | application_threat_set |
| **Output** | application_risk_assessment |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Risk analysis agent**

- *Asked to:* Propose inherent and residual scores with the reasoning for each.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A3. Derive security requirements and propose a targeted level of trust.

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | application_risk_assessment |
| **Output** | proposed_level_of_trust |
| **Mode** | AI-drafted, person owns the output |

#### A4. The application owner approves the targeted level of trust. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | proposed_level_of_trust |
| **Output** | targeted_level_of_trust |
| **Mode** | **Human decision required** |
| **Records produced** | level_of_trust_approval |

> **This step stops for a human decision** (`targeted_level_of_trust`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-APS-08 — Create and maintain the Application Normative Framework

Selects from the library exactly the controls the target requires, in the project's own stage vocabulary. Level-zero controls come with it and cannot be removed.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | Targeted level of trust approved, or a context or target change mid-project |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 60% |

**Clauses discharged**

- ISO/IEC 27001:2022: 6.1.3, 8.1
- iso42001: 8.1

**How this process is measured**

- Zero level-zero controls waived

> Carrying dead stages makes an ANF look complied-with when it is only inapplicable, which is why A3 removes them explicitly rather than leaving them unmeasured.

### Procedure

#### A1. Select every ASC required at the targeted level of trust, including all level-zero controls.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | targeted_level_of_trust, asc_library |
| **Output** | selected_asc_set |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:6.1.3 |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Translate each selected ASC into the project's own life cycle stage.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | selected_asc_set, lifecycle_stage_map |
| **Output** | staged_asc_set |
| **Mode** | Performed by the platform |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Derive the project life cycle by dropping stages the project does not use — an in-house build has no acquisition stage.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | staged_asc_set |
| **Output** | project_lifecycle |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Normative framework steward**

- *Asked to:* Propose which stages are inapplicable and say why for each.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Record any waiver of a non-level-zero ASC with its reason and approver.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | staged_asc_set |
| **Output** | asc_waivers |
| **Mode** | Performed by a person |
| **Records produced** | asc_waiver |

#### A5. Issue the ANF to the project and verification teams.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | staged_asc_set, project_lifecycle |
| **Output** | application_normative_framework |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-APS-09 — Provision and operate the application under its ANF

Performs the controls and measures them, with the two halves done by different actors. The database refuses a measurement recorded by whoever performed the activity, so the separation is not advisory.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Control Owner |
| **Trigger** | ANF issued |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 80% |

**Clauses discharged**

- ISO/IEC 27001:2022: 8.1, A.8.28, A.8.8
- iso42001: 8.1, 8.3

**How this process is measured**

- Zero measurements recorded by the actor that performed the activity
- Failed measurements escalated within the declared window

### Procedure

#### A1. Perform the security activity of each ASC at its mapped stage.

| | |
|---|---|
| **Who performs it** | Application security execution agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | application_normative_framework |
| **Output** | asc_activity_evidence |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.8.28, iso27001:A.8.8, iso27001:A.8.24 |
| **Records produced** | asc_activity |

**AI participation — Application security execution agent**

- *Escalates to a person below confidence:* 0.95
- *Accountable for this agent:* Control Owner

#### A2. Perform the verification measurement of each ASC. A different actor from the one that performed the activity, always.

| | |
|---|---|
| **Who performs it** | Verification measurement agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | asc_activity_evidence |
| **Output** | asc_measurement_evidence |
| **Mode** | Performed by the platform, owner notified |
| **Records produced** | asc_measurement |

**AI participation — Verification measurement agent**

- *Escalates to a person below confidence:* 0.95
- *Accountable for this agent:* Internal Auditor

#### A3. Escalate any failed measurement to the application owner within the declared window.

| | |
|---|---|
| **Who performs it** | Verification measurement agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | asc_measurement_evidence |
| **Output** | asc_escalations |
| **Mode** | Performed by the platform, owner notified |
| **Target** | Within 24 hours |

**AI participation — Verification measurement agent**

- *Escalates to a person below confidence:* 0.95
- *Accountable for this agent:* Internal Auditor

#### A4. Recompute the actual level of trust whenever a measurement is recorded.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | asc_measurement_evidence |
| **Output** | actual_level_of_trust |
| **Mode** | Performed by the platform |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A5. Release gate: refuse promotion while the actual level of trust sits below the target or a mandatory control lacks a passing measurement. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | actual_level_of_trust |
| **Output** | release_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso42001:A.6.2.5 |

> **This step stops for a human decision** (`application_release`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-APS-10 — Audit the security of the application

Determines the actual level of trust and puts it in front of the owner, who either accepts it or mandates adjustments. This is the step that makes the target mean something.

| | |
|---|---|
| **Domain** | APS |
| **Process owner** | Internal Auditor |
| **Trigger** | Release candidate ready, periodic schedule, or application owner request |
| **Cadence** | event driven |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 60% |

**Clauses discharged**

- ISO/IEC 27001:2022: 9.2
- iso42001: 9.2

**How this process is measured**

- Actual level of trust signed off by an auditor who performed no activity

### Procedure

#### A1. Assemble the audit pack: every ASC, its activity record, its measurement record and the supporting evidence.

| | |
|---|---|
| **Who performs it** | Audit agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | asc_evidence |
| **Output** | application_audit_pack |
| **Mode** | Performed by the platform, owner notified |

**AI participation — Audit agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Internal Auditor

#### A2. Verify every measurement in the ANF was performed and produced the expected result.

| | |
|---|---|
| **Who performs it** | Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | application_audit_pack |
| **Output** | verification_conclusions |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:9.2 |
| **Records produced** | audit_working_paper |

#### A3. Determine and record the actual level of trust.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Internal Auditor |
| **Who is accountable** | Internal Auditor |
| **When** | sequence |
| **Input** | verification_conclusions |
| **Output** | actual_level_of_trust |
| **Mode** | Performed by the platform |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A4. The application owner accepts the audit result, or mandates security adjustments. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | actual_level_of_trust, verification_conclusions |
| **Output** | application_audit_report |
| **Mode** | **Human decision required** |

> **This step stops for a human decision** (`application_security_acceptance`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Feed lessons back to the ONF improvement loop.

| | |
|---|---|
| **Who performs it** | Normative framework steward (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | application_audit_report |
| **Output** | project_feedback |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:10.1 |

**AI participation — Normative framework steward**

- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

---

## PR-AIG-01 — AI system inventory and risk classification

Maintains the inventory of AI systems the organisation builds or deploys, with a risk classification for each. This is the foundational record for AI governance and the first thing any AI regulator or customer assurance questionnaire asks for.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | New AI system or model; change of purpose; annual review |
| **Cadence** | quarterly |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.9, A.8.25
- UK GDPR: Art.22, Art.35

**How this process is measured**

- AI systems inventoried
- Systems with a current classification

> Scope deliberately includes this platform's own agents. A GRC system that automates compliance with AI and cannot evidence the governance of that AI is arguing against itself.

### Procedure

#### A1. Discover and record AI systems in use, including embedded and third-party models.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | system_inventory, supplier_register, model_gateway_config |
| **Output** | ai_inventory |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.5.9 |

**AI participation — Regulatory change agent**

- *Asked to:* Draft the inventory entry, including provider, model, purpose and data used.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Classify each system's risk and determine which obligations attach.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_inventory, obligation_register |
| **Output** | risk_classification, transparency_obligations |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.35 |

**AI participation — Regulatory change agent**

- *Asked to:* Present the classification the criteria point to and the obligations that would follow. Classification is a legal determination; present it, do not decide it.
- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A3. Approve the classification and the obligations accepted for each system. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | risk_classification |
| **Output** | approved_classification |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.9 |
| **Records produced** | ai_classification_record |

> **This step stops for a human decision** (`ai.risk_classification`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-02 — AI human oversight and decision accountability

Assures that every AI-influenced decision has a human accountable for it, that the person can understand and override the output, and that the record shows which is which.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | Continuous; on any new agent or autonomy change |
| **Cadence** | continuous |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.2, A.5.3, A.8.16
- UK GDPR: Art.22

**How this process is measured**

- AI outputs accepted without review
- Override rate by agent
- Low-confidence escalations honoured

### Procedure

#### A1. Record, for each agent, its scope, its autonomy tier and the person accountable.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | agent_registry |
| **Output** | oversight_register |
| **Mode** | Performed by a person |
| **Evidences** | iso27001:A.5.2 |
| **Records produced** | ai_oversight_register |

#### A2. Monitor acceptance and override rates per agent and per task class.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Continuous |
| **Input** | model_invocations, gate_decisions, audit_log |
| **Output** | oversight_metrics |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:A.8.16 |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A3. Detect rubber-stamping: an agent whose output is approved essentially always, or reviewed faster than it could be read.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | oversight_metrics |
| **Output** | oversight_findings |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.5.3, uk_gdpr:Art.22 |

**AI participation — Control assessment agent**

- *Asked to:* Flag where human review appears nominal. Oversight that is recorded but not exercised is the failure mode this control exists to catch.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Approve any change to an agent's autonomy tier or scope. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | oversight_findings, proposed_change |
| **Output** | autonomy_decisions |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.5.2 |
| **Records produced** | autonomy_change_record |

> **This step stops for a human decision** (`ai.autonomy_change`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-03 — AI performance monitoring and drift

Watches whether the AI is still doing what it was assessed as doing. Model versions change under the platform's feet, and a provider upgrade is a change to a control.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | Continuous; on model or prompt version change |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 50% |

**Clauses discharged**

- ISO/IEC 27001:2022: 9.1, A.8.16, A.8.32
- iso42001: 9.1

**How this process is measured**

- Confidence trend by task class
- Time from model change to revalidation

### Procedure

#### A1. Baseline output quality per agent and task class: confidence, override rate, correction rate.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | model_invocations, gate_decisions |
| **Output** | performance_baseline |
| **Mode** | Performed by the platform |
| **Evidences** | iso27001:9.1 |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A2. Detect drift against the baseline, and detect provider model or prompt version change.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | Continuous |
| **Input** | performance_baseline, model_invocations, config_versions |
| **Output** | drift_findings |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso27001:A.8.16, iso27001:A.8.32 |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A3. Revalidate the affected task classes against a held-out set before relying on them again.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | drift_findings, validation_set |
| **Output** | revalidation_record |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso27001:A.8.32 |
| **Records produced** | ai_revalidation_record |

**AI participation — Control assessment agent**

- *Asked to:* Compare current output against the reference set and report the delta.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A4. Approve continued reliance, or reduce autonomy until the shortfall is resolved. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | revalidation_record |
| **Output** | reliance_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso27001:A.8.32 |

> **This step stops for a human decision** (`ai.model_revalidation`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-04 — Establish and review the AI policy

Gives management direction on how AI is developed, bought and used, and keeps it current. The review is the part organisations skip, which is why the record of a review that changed nothing still has to exist.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | AIMS scope approved, annual review, or a material change in AI use or regulation |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 17% |

**Clauses discharged**

- iso42001: 4.3, 4.4, 5.2, A.2.2, A.2.3, A.2.4, A.9.3

**How this process is measured**

- AI policy reviewed within 12 months
- Every affected policy identified

### Procedure

#### A0. Define the AI management system scope, naming the AI systems in scope and the organisation's role for each — developer, provider, user, deployer or partner.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | context_analysis, ai_inventory |
| **Output** | aims_scope_statement |
| **Mode** | Performed by a person |
| **Evidences** | iso42001:4.3, iso42001:4.4 |
| **Records produced** | aims_scope |

#### A1. Draft the AI policy covering development, procurement and use of AI systems.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | context_analysis, ai_inventory |
| **Output** | draft_ai_policy |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.2.2 |

**AI participation — Regulatory change agent**

- *Asked to:* Draft the policy and cite the obligation behind each commitment it makes.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A2. Identify every other organisational policy the AI policy affects or is affected by.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_ai_policy, policy_set |
| **Output** | policy_impact_register |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.2.3 |

**AI participation — Control assessment agent**

- *Asked to:* Map overlaps and contradictions between the AI policy and existing policy.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Record the objectives that guide responsible use of AI systems.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_ai_policy |
| **Output** | responsible_use_objectives |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.9.3 |

#### A4. Approve and publish the AI policy. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_ai_policy, policy_impact_register |
| **Output** | ai_policy |
| **Mode** | **Human decision required** |
| **Records produced** | ai_policy_approval |

> **This step stops for a human decision** (`ai.policy_approval`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Run the scheduled review and record its outcome, including where the conclusion was that nothing needed to change.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_policy |
| **Output** | policy_review_record |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.2.4 |
| **Records produced** | ai_policy_review |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

---

## PR-AIG-05 — AI resource documentation and competence

Records what each AI system actually depends on — data, tooling, compute and people. Discovered from the live gateway configuration rather than from a spreadsheet, because an AI register maintained by memory is stale within two quarters.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | A new AI system, model, dataset, tool or provider is introduced or changed |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 50% |

**Clauses discharged**

- iso42001: 7.1, 7.2, A.4.2, A.4.3, A.4.4, A.4.5, A.4.6

**How this process is measured**

- Zero configured models absent from the resource register

### Procedure

#### A1. Discover configured providers, models and routes from the gateway and propose resource entries for each AI system.

| | |
|---|---|
| **Who performs it** | Data provenance agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | model_gateway_config |
| **Output** | proposed_ai_resources |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.4.2, iso42001:A.4.5 |

**AI participation — Data provenance agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A2. Document the data and tooling resources each AI system relies on.

| | |
|---|---|
| **Who performs it** | Data provenance agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | proposed_ai_resources, ai_inventory |
| **Output** | ai_resource_register |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.4.3, iso42001:A.4.4 |

**AI participation — Data provenance agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A3. Record the human resources and competences covering development, deployment, operation, change, maintenance, transfer, decommissioning, verification and integration.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_inventory |
| **Output** | ai_competence_matrix |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.4.6, iso42001:7.2 |
| **Records produced** | competence_record |

#### A4. Approve the resource entry before the AI system reaches production. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_resource_register, ai_competence_matrix |
| **Output** | approved_ai_resources |
| **Mode** | **Human decision required** |

> **This step stops for a human decision** (`ai.resource_approval`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-06 — AI risk assessment, treatment and Statement of Applicability

Assesses risk arising from AI on AI-specific criteria and produces the Statement of Applicability. Separate from the information security risk process on purpose: a security assessment does not ask whether a model treats people unfairly.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | Risk Officer |
| **Trigger** | New or materially changed AI system, planned interval, or an AI incident |
| **Cadence** | quarterly |
| **Autonomy tier** | L2 |
| **Human decision gates** | 2 |
| **Unattended steps** | 17% |

**Clauses discharged**

- iso42001: 6.1.1, 6.1.2, 6.1.3, 8.2, 8.3

**How this process is measured**

- Every AI system assessed within its review period
- Zero controls claiming satisfaction from more than one inbound mapping

> Over-mapping is how integrated management systems inflate readiness. A4 reports it rather than resolving it, because deciding which mapping is the real one is a judgement.

### Procedure

#### A1. Apply the AI risk criteria across the AI system life cycle.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | ai_inventory, ai_resource_register |
| **Output** | ai_risk_draft |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:6.1.2 |

**AI participation — Risk analysis agent**

- *Asked to:* Draft AI risks by life cycle stage, distinguishing them from security risks.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A2. Evaluate against the acceptance criteria and select treatment options.

| | |
|---|---|
| **Who performs it** | Risk analysis agent (AI agent), supervised by Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | ai_risk_draft |
| **Output** | ai_treatment_plan |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:6.1.3 |

**AI participation — Risk analysis agent**

- *Asked to:* Propose treatment options with the reasoning for each.
- *Escalates to a person below confidence:* 0.7
- *Accountable for this agent:* Risk Officer

#### A3. Determine the necessary controls and compare them against Annex A, generating a Statement of Applicability entry for every reference control with a justification, and a reason for every exclusion.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_treatment_plan |
| **Output** | draft_statement_of_applicability |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:6.1.3 |

**AI participation — Control assessment agent**

- *Asked to:* Draft applicability and justification per control; never mark one satisfied.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A4. Report over-mapping: any control claiming satisfaction from more than one inbound cross-framework mapping.

| | |
|---|---|
| **Who performs it** | Reporting agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | draft_statement_of_applicability |
| **Output** | over_mapping_report |
| **Mode** | Performed by the platform |

**AI participation — Reporting agent**

- *Escalates to a person below confidence:* 1.0
- *Accountable for this agent:* Platform Admin

#### A5. Accept residual AI risk, or record a time-bound exception. 🛑

| | |
|---|---|
| **Who performs it** | Risk Officer |
| **Who is accountable** | Risk Officer |
| **When** | sequence |
| **Input** | ai_treatment_plan |
| **Output** | ai_risk_register |
| **Mode** | **Human decision required** |
| **Records produced** | residual_acceptance |

> **This step stops for a human decision** (`ai.residual_risk_acceptance`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A6. Approve the Statement of Applicability. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | draft_statement_of_applicability, over_mapping_report |
| **Output** | statement_of_applicability |
| **Mode** | **Human decision required** |
| **Records produced** | soa_approval |

> **This step stops for a human decision** (`ai.soa_approval`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-07 — AI system impact assessment

Assesses what an AI system does to individuals, to groups and to society. The three dimensions are assessed and recorded separately so that answering two of three cannot look like a finished assessment.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | DPO |
| **Trigger** | New AI system, material change, periodic review, incident, or regulatory change |
| **Cadence** | event driven |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 20% |

**Clauses discharged**

- iso42001: 6.1.4, 8.4, A.5.2, A.5.3, A.5.4, A.5.5

**How this process is measured**

- Approved assessment predates deployment in 100% of cases
- Every approved assessment names a human approver

> A2 is the lowest-autonomy agent step in the repository. A model drafting an assessment of what an AI estate does to people — including the estate it belongs to — produces something fluent, complete-looking and unaccountable, so the database refuses an approved assessment that names no human approver.

### Procedure

#### A1. Assemble the inputs: intended use, affected parties, data provenance, evaluation results and prior incidents.

| | |
|---|---|
| **Who performs it** | AI impact assessment agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | ai_inventory, ai_data_provenance, incident_register |
| **Output** | impact_assessment_inputs |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.5.2 |

**AI participation — AI impact assessment agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A2. Draft the assessment across the individual, group and societal dimensions, with benefits and mitigations.

| | |
|---|---|
| **Who performs it** | AI impact assessment agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | impact_assessment_inputs |
| **Output** | draft_impact_assessment |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.5.4, iso42001:A.5.5 |

**AI participation — AI impact assessment agent**

- *Asked to:* Draft each impact dimension separately and say explicitly where the evidence does not support a conclusion.
- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A3. Review and complete the assessment, adding the judgements a model cannot make, with affected-party representation where relevant.

| | |
|---|---|
| **Who performs it** | DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | draft_impact_assessment |
| **Output** | completed_impact_assessment |
| **Mode** | Performed by a person |
| **Evidences** | iso42001:6.1.4 |

#### A4. Where personal data is involved, cross-reference the data protection impact assessment without treating either as satisfying the other.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | completed_impact_assessment, dpia_register |
| **Output** | dpia_cross_reference |
| **Mode** | AI-drafted, person owns the output |

**AI participation — Privacy operations agent**

- *Asked to:* Identify overlaps and, more importantly, what each assessment does not cover.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A5. Approve the assessment and set its retention period. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | completed_impact_assessment |
| **Output** | ai_impact_assessment |
| **Mode** | **Human decision required** |
| **Evidences** | iso42001:A.5.3, iso42001:8.4 |
| **Records produced** | ai_impact_approval |

> **This step stops for a human decision** (`ai.impact_assessment_approval`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## PR-AIG-08 — Data governance for AI systems

Records where the data came from, on what basis, at what quality and prepared how — for every dataset an AI system trains on or retrieves from.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | DPO |
| **Trigger** | A dataset is acquired, prepared, changed or retired |
| **Cadence** | continuous |
| **Autonomy tier** | L3 |
| **Human decision gates** | 0 |
| **Unattended steps** | 50% |

**Clauses discharged**

- iso42001: A.7.2, A.7.3, A.7.4, A.7.5, A.7.6

**How this process is measured**

- Zero datasets promoted without a provenance record and a quality result

> A6 exists because the provenance agent writes final records rather than proposals. Bounded autonomy needs a sampling review behind it, or it is just unattended writing.

### Procedure

#### A1. Record acquisition and selection details for each dataset.

| | |
|---|---|
| **Who performs it** | Data provenance agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | dataset_registry |
| **Output** | acquisition_records |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.7.3 |

**AI participation — Data provenance agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A2. Apply the data quality criteria and record the result.

| | |
|---|---|
| **Who performs it** | Data provenance agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | acquisition_records |
| **Output** | data_quality_results |
| **Mode** | Performed by the platform |
| **Evidences** | iso42001:A.7.4 |

**AI participation — Data provenance agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A3. Record provenance across the life cycles of the data and the AI system.

| | |
|---|---|
| **Who performs it** | Data provenance agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | acquisition_records, data_quality_results |
| **Output** | ai_data_provenance |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.7.5 |
| **Records produced** | provenance_record |

**AI participation — Data provenance agent**

- *Escalates to a person below confidence:* 0.9
- *Accountable for this agent:* DPO

#### A4. Record the preparation methods used and the criteria for choosing them.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | ai_data_provenance |
| **Output** | preparation_records |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.7.6, iso42001:A.7.2 |

#### A5. Where the dataset contains personal data, link it to the processing record and confirm the lawful basis.

| | |
|---|---|
| **Who performs it** | Privacy operations agent (AI agent), supervised by DPO |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | ai_data_provenance, processing_records |
| **Output** | lawful_basis_confirmation |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | uk_gdpr:Art.30 |

**AI participation — Privacy operations agent**

- *Asked to:* Identify datasets with personal data and no linked processing record.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

#### A6. Sample-review the provenance entries the agent recorded.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | DPO |
| **When** | sequence |
| **Input** | ai_data_provenance |
| **Output** | provenance_review |
| **Mode** | Performed by a person |

---

## PR-AIG-09 — Information for interested parties and AI incident communication

Gives users what they need to use the system within its intended use, gives outsiders a way to report harm, and makes sure both reach somebody when an AI incident occurs.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | System documentation change, an adverse impact report, or an AI incident |
| **Cadence** | continuous |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 0% |

**Clauses discharged**

- iso42001: 7.4, 7.5, A.8.2, A.8.3, A.8.4, A.8.5, A.3.3, A.6.2.7

**How this process is measured**

- Adverse impact reports acknowledged within the declared window

### Procedure

#### A1. Publish the information users need to operate the AI system within its intended use, and the technical documentation each interested-party category requires.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_inventory |
| **Output** | ai_user_documentation |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.8.2, iso42001:A.6.2.7, iso42001:7.5 |

**AI participation — Control assessment agent**

- *Asked to:* Draft user-facing documentation covering intended use and limitations.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A2. Operate an external channel through which interested parties can report adverse impacts, and a concerns channel that does not route through the owner of the system being questioned.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Output** | adverse_impact_channel |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.8.3, iso42001:A.3.3 |

#### A3. Classify an incoming report, link it to the AI system and harm type, and raise an incident.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | adverse_impact_channel |
| **Output** | ai_incident_link |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.8.4 |

**AI participation — Incident agent**

- *Asked to:* Classify the harm type and propose severity; do not close anything.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

#### A4. Execute the incident communication plan for users of the AI system. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_incident_link |
| **Output** | ai_incident_communications |
| **Mode** | **Human decision required** |
| **Evidences** | iso42001:A.8.4, iso42001:7.4 |

> **This step stops for a human decision** (`ai.external_communication`) because a legal duty attaches to the decision. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A5. Maintain the register of reporting obligations to interested parties and supervisory bodies.

| | |
|---|---|
| **Who performs it** | Regulatory change agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | obligation_register |
| **Output** | ai_reporting_obligations |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.8.5 |

**AI participation — Regulatory change agent**

- *Asked to:* Propose obligation entries with a retrievable source for each.
- *Escalates to a person below confidence:* 0.85
- *Accountable for this agent:* DPO

---

## PR-AIG-10 — Responsible use of AI systems and agent mandates

Governs how AI is actually used, including this platform's own agents. Every agent runs under an approved charter with a tier, tool grants, prohibited actions, a budget and a kill switch — enforced at the gateway, not requested in a prompt.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | CISO |
| **Trigger** | An agent charter is created or changed, or usage drifts from intended use |
| **Cadence** | continuous |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 33% |

**Clauses discharged**

- iso42001: 5.3, A.9.2, A.9.4, A.3.2, A.6.2.6, A.6.2.8

**How this process is measured**

- Zero agent identities enabled without a current approved charter
- Zero agents holding gate authority

> A3 is deliberately marked as an enforced control rather than an assisted one. Instructions inside a prompt are not a control; only enforcement outside the model counts as evidence here.

### Procedure

#### A1. Define the processes governing responsible use of AI systems.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_policy |
| **Output** | responsible_use_processes |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.9.2 |

#### A2. Approve an agent charter for every agent identity: purpose, autonomy tier, tool grants, prohibited actions, budgets and kill switch. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | agent_registry |
| **Output** | agent_charters |
| **Mode** | **Human decision required** |
| **Evidences** | iso42001:A.3.2, iso42001:A.9.2, iso42001:5.3 |
| **Records produced** | agent_charter_approval |

> **This step stops for a human decision** (`ai.agent_charter_approval`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A3. Enforce intended-use policy at the model gateway: provider routing, tool allowlists, output filters and token budgets.

| | |
|---|---|
| **Who performs it** | Platform Admin |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | agent_charters, model_gateway_config |
| **Output** | gateway_policy_evidence |
| **Mode** | Performed by the platform |
| **Evidences** | iso42001:A.9.4 |
| **Records produced** | gateway_policy_test |

#### A4. Enable event logging for the declared life cycle phases, at minimum while the system is in use.

| | |
|---|---|
| **Who performs it** | Platform Admin |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_inventory |
| **Output** | event_logging_configuration |
| **Mode** | Performed by the platform |
| **Evidences** | iso42001:A.6.2.8 |

#### A5. Detect and raise drift between recorded intended use and observed invocation patterns.

| | |
|---|---|
| **Who performs it** | Incident agent (AI agent), supervised by CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | model_invocations, ai_inventory |
| **Output** | drift_reports |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.6.2.6 |

**AI participation — Incident agent**

- *Asked to:* Describe how observed use diverges from recorded intended use.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* CISO

#### A6. Review agent budget ledgers, escalation counts and any disabled charters.

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | agent_charters |
| **Output** | agent_oversight_review |
| **Mode** | AI-drafted, person owns the output |
| **Records produced** | agent_oversight_record |

---

## PR-AIG-11 — AI third-party and customer relationships

Apportions responsibility across the AI supply chain and keeps the organisation accountable for the part it kept. Reuses the supplier register rather than creating a second one.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | Control Owner |
| **Trigger** | A new AI supplier, partner or customer relationship, or annual reassessment |
| **Cadence** | annual |
| **Autonomy tier** | L2 |
| **Human decision gates** | 1 |
| **Unattended steps** | 17% |

**Clauses discharged**

- ISO/IEC 27001:2022: A.5.19
- iso42001: A.10.2, A.10.3, A.10.4

**How this process is measured**

- Every AI supplier has a current assurance status

### Procedure

#### A1. Allocate life cycle responsibilities across the organisation, partners, suppliers, customers and other third parties.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_inventory, supplier_register |
| **Output** | ai_responsibility_allocation |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.10.2 |

#### A2. Assess whether supplier services, products or materials align with the organisation's responsible AI approach.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | supplier_register, ai_responsibility_allocation |
| **Output** | ai_supplier_findings |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.10.3, iso27001:A.5.19 |

**AI participation — Third-party risk agent**

- *Asked to:* Draft the assurance finding; do not set the assurance status.
- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

#### A3. Reflect the allocation in contractual terms: model change notification, evaluation access and incident reporting.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_responsibility_allocation |
| **Output** | ai_contract_terms |
| **Mode** | Performed by a person |
| **Evidences** | iso42001:A.10.2 |

#### A4. Capture customer expectations relating to AI and feed them into the responsible use objectives.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Output** | ai_customer_expectations |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.10.4 |

#### A5. Set the supplier assurance status, or record a time-bound exception. 🛑

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_supplier_findings |
| **Output** | ai_supplier_assurance |
| **Mode** | **Human decision required** |
| **Records produced** | supplier_assurance_decision |

> **This step stops for a human decision** (`ai.supplier_assurance`) because the exposure or value is material. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

#### A6. Reassess on schedule and on any supplier model or policy change.

| | |
|---|---|
| **Who performs it** | Third-party risk agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_supplier_assurance |
| **Output** | ai_supplier_reassessment |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.10.3 |

**AI participation — Third-party risk agent**

- *Escalates to a person below confidence:* 0.8
- *Accountable for this agent:* Control Owner

---

## PR-AIG-12 — Responsible AI system life cycle and deployment control

Governs an AI system from requirements through verification to deployment and operation, so that the impact assessment, the evaluation criteria and the logging configuration are all in place before anything reaches a user.

| | |
|---|---|
| **Domain** | AIG |
| **Process owner** | Control Owner |
| **Trigger** | An AI system enters design, or a release candidate is ready |
| **Cadence** | event driven |
| **Autonomy tier** | L3 |
| **Human decision gates** | 1 |
| **Unattended steps** | 20% |

**Clauses discharged**

- iso42001: 6.2, 6.3, 8.1, A.6.1.2, A.6.2.3, A.6.2.4, A.6.2.5

**How this process is measured**

- Zero deployments without an approved impact assessment predating them

### Procedure

#### A1. Record the objectives guiding responsible development and the measures taken to achieve them.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Output** | responsible_development_objectives |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.6.1.2, iso42001:6.2 |

#### A2. Document design and development against objectives, requirements and specification criteria.

| | |
|---|---|
| **Who performs it** | Control assessment agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | responsible_development_objectives |
| **Output** | ai_design_documentation |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.6.2.3 |

**AI participation — Control assessment agent**

- *Asked to:* Draft the design record and flag requirements with no design decision behind them.
- *Escalates to a person below confidence:* 0.75
- *Accountable for this agent:* Control Owner

#### A3. Run verification and validation against the declared criteria: accuracy, robustness, prompt injection resistance and refusal behaviour.

| | |
|---|---|
| **Who performs it** | Verification measurement agent (AI agent), supervised by Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | ai_design_documentation |
| **Output** | evaluation_report |
| **Mode** | Performed by the platform, owner notified |
| **Evidences** | iso42001:A.6.2.4 |
| **Records produced** | evaluation_report |

**AI participation — Verification measurement agent**

- *Escalates to a person below confidence:* 0.95
- *Accountable for this agent:* Internal Auditor

#### A4. Confirm the deployment prerequisites and record the deployment plan.

| | |
|---|---|
| **Who performs it** | Control Owner |
| **Who is accountable** | Control Owner |
| **When** | sequence |
| **Input** | evaluation_report, ai_impact_assessment |
| **Output** | ai_deployment_plan |
| **Mode** | AI-drafted, person owns the output |
| **Evidences** | iso42001:A.6.2.5, iso42001:6.3 |

#### A5. Deployment gate: approved impact assessment, evaluation criteria met, deployment plan recorded, event logging enabled. 🛑

| | |
|---|---|
| **Who performs it** | CISO |
| **Who is accountable** | CISO |
| **When** | sequence |
| **Input** | ai_deployment_plan |
| **Output** | ai_deployment_decision |
| **Mode** | **Human decision required** |
| **Evidences** | iso42001:A.6.2.5, iso42001:8.1 |
| **Records produced** | ai_deployment_approval |

> **This step stops for a human decision** (`ai.deployment_approval`) because the action cannot be undone. It cannot be performed by an agent, and it cannot be decided by whoever raised it.

---

## Clause coverage

Which process discharges which requirement. A clause with no process against it is a hole in the management system, and this table is how it is found rather than discovered during a certification audit.

### ISO 22301:2019

| Clause | Discharged by |
|---|---|
| 10.1 | `PR-GOV-05`, `PR-CMP-03` |
| 10.2 | `PR-GOV-05` |
| 4.1 | `PR-GOV-01` |
| 4.2 | `PR-GOV-01`, `PR-CMP-04` |
| 4.3 | `PR-GOV-01` |
| 4.4 | `PR-GOV-01` |
| 5.1 | `PR-GOV-01` |
| 5.2 | `PR-GOV-01` |
| 6.1 | `PR-RSK-01`, `PR-RSK-02` |
| 6.2 | `PR-GOV-02` |
| 7.2 | `PR-PPL-03` |
| 7.3 | `PR-PPL-03` |
| 8.1 | `PR-CMP-01`, `PR-CHG-01` |
| 8.2 | `PR-RSK-03`, `PR-RES-01` |
| 8.2.2 | `PR-RES-01` |
| 8.2.3 | `PR-RSK-01`, `PR-RES-01` |
| 8.3 | `PR-RSK-02`, `PR-TPR-01`, `PR-TPR-03`, `PR-RES-02` |
| 8.3.1 | `PR-RES-02` |
| 8.3.2 | `PR-RES-02` |
| 8.3.3 | `PR-RES-02` |
| 8.4 | `PR-SEC-01`, `PR-RES-02`, `PR-RES-04` |
| 8.4.1 | `PR-RES-02` |
| 8.4.2 | `PR-RES-02` |
| 8.4.3 | `PR-RES-04` |
| 8.4.4 | `PR-RES-04` |
| 8.4.5 | `PR-RES-04` |
| 8.5 | `PR-RES-03` |
| 9.1 | `PR-GOV-02`, `PR-RSK-03`, `PR-CMP-02`, `PR-RES-03` |
| 9.2 | `PR-GOV-03`, `PR-CMP-05` |
| 9.3 | `PR-GOV-04`, `PR-CMP-05` |

### ISO/IEC 27001:2022

| Clause | Discharged by |
|---|---|
| 10.1 | `PR-GOV-05`, `PR-CMP-03`, `PR-APS-04` |
| 10.2 | `PR-GOV-05`, `PR-CMP-03`, `PR-CMP-05`, `PR-APS-04` |
| 4.1 | `PR-GOV-01` |
| 4.2 | `PR-GOV-01`, `PR-CMP-04` |
| 4.3 | `PR-GOV-01` |
| 4.4 | `PR-GOV-01` |
| 5.1 | `PR-GOV-01` |
| 5.2 | `PR-GOV-01` |
| 6.1.1 | `PR-RSK-01` |
| 6.1.2 | `PR-RSK-01`, `PR-APS-07` |
| 6.1.3 | `PR-RSK-02`, `PR-CMP-03`, `PR-APS-01`, `PR-APS-08` |
| 6.1.3.d | `PR-RSK-02`, `PR-CMP-01` |
| 6.2 | `PR-GOV-02` |
| 7.2 | `PR-PPL-03`, `PR-APS-02` |
| 7.3 | `PR-PPL-03`, `PR-APS-02` |
| 8.1 | `PR-CHG-01`, `PR-APS-01`, `PR-APS-02`, `PR-APS-06`, `PR-APS-08`, `PR-APS-09` |
| 8.2 | `PR-RSK-01`, `PR-RSK-03`, `PR-APS-07` |
| 8.3 | `PR-RSK-02` |
| 9.1 | `PR-GOV-02`, `PR-RSK-03`, `PR-CMP-02`, `PR-AIG-03`, `PR-APS-03` |
| 9.2 | `PR-GOV-03`, `PR-CMP-05`, `PR-APS-05`, `PR-APS-10` |
| 9.2.1 | `PR-GOV-03` |
| 9.2.2 | `PR-GOV-03` |
| 9.3 | `PR-GOV-04`, `PR-CMP-05` |
| 9.3.1 | `PR-GOV-04` |
| 9.3.2 | `PR-GOV-04` |
| 9.3.3 | `PR-GOV-04` |
| A.5.14 | `PR-PRV-05` |
| A.5.16 | `PR-PPL-01`, `PR-PPL-02` |
| A.5.17 | `PR-PPL-01` |
| A.5.18 | `PR-PPL-01`, `PR-PPL-02` |
| A.5.19 | `PR-TPR-01`, `PR-TPR-02`, `PR-AIG-11` |
| A.5.2 | `PR-AIG-02` |
| A.5.20 | `PR-TPR-02` |
| A.5.21 | `PR-TPR-01`, `PR-TPR-02` |
| A.5.22 | `PR-TPR-02`, `PR-TPR-03` |
| A.5.23 | `PR-TPR-03` |
| A.5.24 | `PR-PRV-03`, `PR-SEC-01` |
| A.5.25 | `PR-SEC-01` |
| A.5.26 | `PR-PRV-03`, `PR-SEC-01` |
| A.5.27 | `PR-SEC-01` |
| A.5.28 | `PR-SEC-03` |
| A.5.29 | `PR-RES-01`, `PR-RES-03` |
| A.5.3 | `PR-AIG-02` |
| A.5.30 | `PR-RES-01`, `PR-RES-03` |
| A.5.31 | `PR-CMP-04` |
| A.5.34 | `PR-CMP-04`, `PR-PRV-01`, `PR-PRV-02` |
| A.5.35 | `PR-CMP-02` |
| A.5.36 | `PR-CMP-02` |
| A.5.9 | `PR-AIG-01` |
| A.6.1 | `PR-PPL-01` |
| A.6.2 | `PR-PPL-01` |
| A.6.3 | `PR-PPL-03` |
| A.6.5 | `PR-PPL-01` |
| A.6.8 | `PR-PRV-03`, `PR-SEC-01` |
| A.8.10 | `PR-PRV-05` |
| A.8.11 | `PR-PRV-01` |
| A.8.15 | `PR-SEC-03` |
| A.8.16 | `PR-SEC-03`, `PR-AIG-02`, `PR-AIG-03` |
| A.8.17 | `PR-SEC-03` |
| A.8.19 | `PR-SEC-02` |
| A.8.2 | `PR-PPL-02` |
| A.8.25 | `PR-PRV-04`, `PR-CHG-02`, `PR-AIG-01` |
| A.8.26 | `PR-CHG-02` |
| A.8.27 | `PR-PRV-04`, `PR-CHG-02` |
| A.8.28 | `PR-CHG-02`, `PR-APS-09` |
| A.8.29 | `PR-CHG-02` |
| A.8.31 | `PR-CHG-02` |
| A.8.32 | `PR-SEC-02`, `PR-CHG-01`, `PR-AIG-03` |
| A.8.8 | `PR-SEC-02`, `PR-APS-09` |
| A.8.9 | `PR-SEC-02`, `PR-CHG-01` |
| Annex A | `PR-CMP-01` |

### iso42001

| Clause | Discharged by |
|---|---|
| 10.1 | `PR-GOV-05`, `PR-CMP-03`, `PR-APS-04` |
| 10.2 | `PR-GOV-05`, `PR-CMP-03`, `PR-CMP-05`, `PR-APS-04` |
| 4.1 | `PR-GOV-01` |
| 4.2 | `PR-GOV-01`, `PR-CMP-04` |
| 4.3 | `PR-AIG-04` |
| 4.4 | `PR-GOV-01`, `PR-AIG-04` |
| 5.1 | `PR-GOV-01` |
| 5.2 | `PR-AIG-04` |
| 5.3 | `PR-AIG-10` |
| 6.1.1 | `PR-RSK-01`, `PR-AIG-06` |
| 6.1.2 | `PR-AIG-06` |
| 6.1.3 | `PR-AIG-06` |
| 6.1.4 | `PR-AIG-07` |
| 6.2 | `PR-GOV-02`, `PR-AIG-12` |
| 6.3 | `PR-AIG-12` |
| 7.1 | `PR-AIG-05` |
| 7.2 | `PR-PPL-03`, `PR-AIG-05`, `PR-APS-02` |
| 7.3 | `PR-PPL-03`, `PR-APS-02` |
| 7.4 | `PR-AIG-09` |
| 7.5 | `PR-AIG-09` |
| 8.1 | `PR-CMP-01`, `PR-CHG-01`, `PR-AIG-12`, `PR-APS-01`, `PR-APS-02`, `PR-APS-06`, `PR-APS-08`, `PR-APS-09` |
| 8.2 | `PR-AIG-06` |
| 8.3 | `PR-AIG-06`, `PR-APS-09` |
| 8.4 | `PR-AIG-07` |
| 9.1 | `PR-GOV-02`, `PR-RSK-03`, `PR-CMP-02`, `PR-RES-03`, `PR-AIG-03`, `PR-APS-03` |
| 9.2 | `PR-GOV-03`, `PR-CMP-05`, `PR-APS-05`, `PR-APS-10` |
| 9.3 | `PR-GOV-04`, `PR-CMP-05` |
| A.10.2 | `PR-AIG-11` |
| A.10.3 | `PR-AIG-11` |
| A.10.4 | `PR-AIG-11` |
| A.2.2 | `PR-AIG-04` |
| A.2.3 | `PR-AIG-04` |
| A.2.4 | `PR-AIG-04` |
| A.3.2 | `PR-AIG-10` |
| A.3.3 | `PR-AIG-09` |
| A.4.2 | `PR-AIG-05` |
| A.4.3 | `PR-AIG-05` |
| A.4.4 | `PR-AIG-05` |
| A.4.5 | `PR-AIG-05` |
| A.4.6 | `PR-AIG-05` |
| A.5.2 | `PR-AIG-07` |
| A.5.3 | `PR-AIG-07` |
| A.5.4 | `PR-AIG-07` |
| A.5.5 | `PR-AIG-07` |
| A.6.1.2 | `PR-AIG-12` |
| A.6.1.3 | `PR-APS-01` |
| A.6.2.2 | `PR-APS-06` |
| A.6.2.3 | `PR-AIG-12` |
| A.6.2.4 | `PR-AIG-12` |
| A.6.2.5 | `PR-AIG-12` |
| A.6.2.6 | `PR-AIG-10` |
| A.6.2.7 | `PR-AIG-09` |
| A.6.2.8 | `PR-AIG-10` |
| A.7.2 | `PR-AIG-08` |
| A.7.3 | `PR-AIG-08` |
| A.7.4 | `PR-AIG-08` |
| A.7.5 | `PR-AIG-08` |
| A.7.6 | `PR-AIG-08` |
| A.8.2 | `PR-AIG-09` |
| A.8.3 | `PR-AIG-09` |
| A.8.4 | `PR-AIG-09` |
| A.8.5 | `PR-AIG-09` |
| A.9.2 | `PR-AIG-10` |
| A.9.3 | `PR-AIG-04` |
| A.9.4 | `PR-AIG-10` |

### UK GDPR

| Clause | Discharged by |
|---|---|
| Art.12 | `PR-PRV-02` |
| Art.15 | `PR-PRV-02` |
| Art.16 | `PR-PRV-02` |
| Art.17 | `PR-PRV-02` |
| Art.18 | `PR-PRV-02` |
| Art.20 | `PR-PRV-02` |
| Art.21 | `PR-PRV-02` |
| Art.22 | `PR-AIG-01`, `PR-AIG-02` |
| Art.24 | `PR-GOV-01`, `PR-GOV-05`, `PR-RSK-01`, `PR-CMP-01`, `PR-CMP-04` |
| Art.25 | `PR-PRV-04`, `PR-CHG-01`, `PR-CHG-02` |
| Art.28 | `PR-TPR-01`, `PR-TPR-02`, `PR-TPR-03` |
| Art.30 | `PR-PRV-01` |
| Art.32 | `PR-RSK-01`, `PR-RSK-02`, `PR-CMP-01`, `PR-CMP-02`, `PR-SEC-01`, `PR-SEC-02`, `PR-SEC-03`, `PR-TPR-02`, `PR-PPL-01` |
| Art.33 | `PR-PRV-03`, `PR-SEC-01` |
| Art.34 | `PR-PRV-03` |
| Art.35 | `PR-RSK-02`, `PR-PRV-04`, `PR-CHG-01`, `PR-AIG-01` |
| Art.36 | `PR-PRV-04` |
| Art.39 | `PR-PPL-03` |
| Art.44 | `PR-PRV-05`, `PR-TPR-02` |
| Art.46 | `PR-PRV-05` |
| Art.49 | `PR-PRV-05` |
| Art.5 | `PR-GOV-01`, `PR-PRV-01`, `PR-PRV-03` |
| Art.5.1.e | `PR-PRV-05` |
| Art.6 | `PR-PRV-01` |
| Art.9 | `PR-PRV-01` |

---

## Appendix A — AI agents

Each agent is scoped to work it can do reliably, has a named person accountable for it, and declares what it refuses. None can approve anything.

### What every agent refuses, without exception

- Approving anything — every decision point returns a gate for a named person.
- Interpreting what a law or regulation requires of this organisation; that is a legal judgement.
- Accepting risk on the organisation's behalf, at any severity.
- Communicating with a regulator, an auditor, a customer or a data subject without human approval.
- Asserting that a control operates without an evidence record behind the claim.
- Inventing a clause reference, a citation, a date or a document name.

### Autonomy tiers

| Tier | Meaning |
|---|---|
| L1 | Observes and reports. Takes no action. |
| L2 | Drafts for a named person, who owns the output. |
| L3 | Acts on reversible things; anything irreversible raises a gate. |
| L4 | Acts unattended within a bounded, deterministic scope. |

An agent is tiered to the least deterministic thing it does. An L4 agent calls no model at all — acting without review on model output is precisely what the tiers exist to prevent.

### Orchestration agent (`orchestrator`)

Plans and sequences work across processes: starts runs on their trigger, routes activities to the right agent, tracks SLAs, chases what is late and escalates what is stuck. It does no compliance reasoning of its own.

| | |
|---|---|
| **Accountable role** | Platform Admin |
| **Autonomy tier** | L4 |
| **Escalates below confidence** | 0.9 |
| **Permissions** | `wf.execute`, `data.register.read`, `data.register.write`, `rpt.dashboard.view` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-CMP-01`, `PR-CMP-03`, `PR-PPL-01`, `PR-PPL-02`, `PR-PPL-03`, `PR-CHG-01` |

**Additionally refuses**

- Judging the substance of any assessment; it moves work, it does not evaluate it.

> L4 is justified because its actions are deterministic and reversible: scheduling, routing and notifying. It writes no conclusions.

### Evidence agent (`evidence`)

Collects, hashes, files and freshness-checks evidence, and runs automated control tests against source systems. The highest-volume and most reliably automated work in the platform.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L3 |
| **Escalates below confidence** | 0.75 |
| **Permissions** | `evidence.write`, `data.register.read`, `compliance.manage`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-CMP-02`, `PR-CMP-05`, `PR-GOV-03`, `PR-SEC-02`, `PR-SEC-03`, `PR-PPL-02` |

**Additionally refuses**

- Concluding that a control is effective; it reports what the evidence shows.
- Filling a gap in evidence with an inference about what probably happened.

> Collection and comparison are mechanical and run as AUTO in the processes that use them. Summarisation is marked ASSIST and read by a person. The agent is tiered to the latter.

### Control assessment agent (`control_assessor`)

Assesses control implementation against requirement, drafts gaps and remediation, and performs cause analysis. Produces the reasoning a control owner then owns.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.75 |
| **Permissions** | `compliance.manage`, `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-CMP-01`, `PR-CMP-02`, `PR-CMP-03`, `PR-GOV-02`, `PR-GOV-05`, `PR-CHG-01`, `PR-CHG-02` |

**Additionally refuses**

- Attesting a control; attestation is a personal statement by its owner.
- Closing a gap; closure requires verified evidence and a human decision.

### Risk analysis agent (`risk_analyst`)

Drafts risk statements, proposes inherent and residual scores with reasoning, maps controls to risks, and watches for signals that should move the register.

| | |
|---|---|
| **Accountable role** | Risk Officer |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.7 |
| **Permissions** | `risk.manage`, `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-RSK-01`, `PR-RSK-02`, `PR-RSK-03`, `PR-SEC-02` |

**Additionally refuses**

- Accepting residual risk, which is the single decision the register exists to record.
- Moving a risk on the register without a person confirming the movement.
- Reducing a residual score for a control that is claimed but not evidenced.

### Privacy operations agent (`privacy`)

Runs the mechanical parts of privacy: request classification and clock calculation, estate search, pack assembly with redaction proposals, processing-record drafting and drift detection.

| | |
|---|---|
| **Accountable role** | DPO |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.85 |
| **Permissions** | `data.register.read`, `data.register.write`, `data.pii.read`, `compliance.manage`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-PRV-01`, `PR-PRV-02`, `PR-PRV-03`, `PR-PRV-04`, `PR-PRV-05` |

**Additionally refuses**

- Releasing a subject access response; disclosure is irreversible and may expose a third party.
- Deciding whether to notify a supervisory authority or a data subject.
- Determining lawful basis or the adequacy of a transfer mechanism.
- Concluding that an incident is not a breach; uncertainty resolves towards the clock running.

> The highest escalation threshold in the registry apart from resilience, because privacy errors are statutory and usually irreversible. Over-escalation here costs a review; under-escalation costs a notifiable breach.

### Third-party risk agent (`third_party`)

Tiers engagements by inherent exposure, processes questionnaire responses, scores supplier domains against evidence, and monitors suppliers between assessments.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.8 |
| **Permissions** | `data.register.read`, `data.register.write`, `risk.manage`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-TPR-01`, `PR-TPR-02`, `PR-TPR-03` |

**Additionally refuses**

- Approving a supplier engagement or confirming a contract is adequate.
- Accepting a certificate whose scope it cannot verify covers the service being bought.

### Resilience agent (`resilience`)

Drafts business impact analyses and continuity plans, designs exercise scenarios, and analyses exercise results against stated objectives.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.75 |
| **Permissions** | `data.register.read`, `data.register.write`, `compliance.manage`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-RES-01`, `PR-RES-02`, `PR-RES-03`, `PR-RES-04` |

**Additionally refuses**

- Invoking continuity arrangements or declaring a crisis.
- Approving recovery objectives; the tolerance for disruption is a business decision.
- Recording an exercise as passed when the achieved recovery missed the objective.

> Drops to L1 during a live invocation: it records and informs, it does not act.

### Regulatory change agent (`regulatory_watch`)

Scans for change in law, regulation and standards, triages relevance to the scope, and maps a confirmed change to the controls, policies and records it touches.

| | |
|---|---|
| **Accountable role** | DPO |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.85 |
| **Permissions** | `data.register.read`, `data.register.write`, `compliance.manage`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-CMP-04`, `PR-GOV-01`, `PR-AIG-01` |

**Additionally refuses**

- Stating what a new obligation requires of this organisation.
- Concluding that a change does not apply; non-applicability is a legal position.
- Treating a proposal, a consultation or a political agreement as though it were in force.

> The distinction between agreed, adopted, published and in force is where this agent will fail if it is going to. It reports status and date, never a conclusion about applicability.

### Incident agent (`incident`)

Enriches security events with asset, owner and data context, proposes triage classification, and drafts timelines and cause analysis after the fact.

| | |
|---|---|
| **Accountable role** | CISO |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.8 |
| **Permissions** | `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-SEC-01`, `PR-PRV-03` |

**Additionally refuses**

- Taking containment action on a production system.
- Ruling out personal data involvement; that determination starts a statutory clock.

### Audit agent (`audit`)

Plans audit coverage, selects and documents samples, prepares working papers, and drafts observations and responses to external auditor requests.

| | |
|---|---|
| **Accountable role** | Internal Auditor |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.8 |
| **Permissions** | `audit.conduct`, `data.register.read`, `evidence.write`, `sec.auditlog.read`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-GOV-03`, `PR-CMP-05` |

**Additionally refuses**

- Forming the audit opinion; the conclusion and the independence behind it belong to the auditor.
- Validating its own work — an agent cannot provide assurance over a process it executed.
- Issuing anything to an external auditor.

> Segregation of duties applies to agents as well as people. Where this agent has drafted work in a process, its output cannot be the assurance over that same process.

### Reporting agent (`reporting`)

Computes and assembles: readiness figures, management review packs, objective performance, AI oversight metrics. Deterministic aggregation, not judgement.

| | |
|---|---|
| **Accountable role** | Platform Admin |
| **Autonomy tier** | L4 |
| **Escalates below confidence** | 1.0 |
| **Permissions** | `rpt.dashboard.view`, `data.register.read`, `compliance.manage`, `sec.auditlog.read` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-GOV-02`, `PR-GOV-04`, `PR-CMP-05`, `PR-AIG-02`, `PR-AIG-03` |

**Additionally refuses**

- Adjusting, smoothing or narrating a figure; it reports what the data says.
- Presenting a readiness figure without the evidence discount applied.

> L4 with no task classes at all: this agent runs queries and arithmetic. It calls no model, which is why its figures are reproducible.

### Normative framework steward (`onf_steward`)

Maintains the Application Security Control library and the Organization Normative Framework around it: drafts control definitions, selects the set a targeted level of trust requires, and translates each control into the delivery team's own stage vocabulary.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.75 |
| **Permissions** | `compliance.manage`, `data.register.read`, `data.register.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-APS-01`, `PR-APS-02`, `PR-APS-03`, `PR-APS-04`, `PR-APS-06`, `PR-APS-08`, `PR-APS-10` |

**Additionally refuses**

- Approving an ONF iteration or an ASC; the library is the committee's to authorise.
- Defining or changing level zero, which is the floor a project team cannot go below.
- Waiving any control, at any level of trust.

> Selecting controls for a level of trust is deterministic and could run unattended, and does — the process marks those steps AUTO. Designing a new control is judgement, so the agent as a whole sits at L2.

### Application security execution agent (`appsec`)

Runs the automatable security activities — static analysis, dependency and licence scanning, secret scanning, tenant isolation tests and vulnerability re-scans — and records the activity half of each Application Security Control.

| | |
|---|---|
| **Accountable role** | Control Owner |
| **Autonomy tier** | L3 |
| **Escalates below confidence** | 0.95 |
| **Permissions** | `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-APS-02`, `PR-APS-09` |

**Additionally refuses**

- Recording any verification measurement; it performs activities and nothing else.
- Changing a blocking severity threshold, which would let it grade its own work.
- Suppressing or dismissing a finding.

> A separate identity from the verification agent rather than a mode of one agent. The database separates duties by actor identity, so a single agent with two modes would defeat the trigger entirely.

### Verification measurement agent (`verification`)

Records the measurement half of an Application Security Control from independent tool output, runs AI system evaluation suites, and escalates every failure inside the declared window.

| | |
|---|---|
| **Accountable role** | Internal Auditor |
| **Autonomy tier** | L3 |
| **Escalates below confidence** | 0.95 |
| **Permissions** | `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-APS-09`, `PR-AIG-12` |

**Additionally refuses**

- Measuring any control marked as requiring a human verifier.
- Measuring a control whose security activity it performed.
- Amending an outcome once written; a correction is a new record with a reason.

> The database refuses both of the first two refusals independently. The refusal list states the intent; the trigger is what makes it true.

### Data provenance agent (`provenance`)

Discovers configured providers, models and compute from the live gateway, and records origin, acquisition basis, licence, quality result and preparation method for every dataset an AI system uses.

| | |
|---|---|
| **Accountable role** | DPO |
| **Autonomy tier** | L3 |
| **Escalates below confidence** | 0.9 |
| **Permissions** | `data.register.read`, `data.register.write`, `evidence.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-AIG-05`, `PR-AIG-08` |

**Additionally refuses**

- Determining a lawful basis for personal data, which is a legal judgement.
- Marking a dataset approved for training or retrieval.
- Recording provenance it cannot trace to a source record.

> Writes final records rather than proposals, which is why PR-AIG-08 carries a sampling review by the data owner behind it. Bounded autonomy without a review behind it is just unattended writing.

### AI impact assessment agent (`ai_impact`)

Assembles the inputs for an AI system impact assessment and drafts the individual, group and societal dimensions separately, saying explicitly where the evidence does not support a conclusion.

| | |
|---|---|
| **Accountable role** | DPO |
| **Autonomy tier** | L2 |
| **Escalates below confidence** | 0.9 |
| **Permissions** | `data.register.read`, `data.register.write`, `wf.execute` |
| **Holds approval authority** | No — structurally prevented |
| **Participates in** | `PR-AIG-07` |

**Additionally refuses**

- Setting a residual impact rating.
- Approving an assessment; the database refuses an approved record with no human approver.
- Assessing any AI system of which this agent forms a part.

> The lowest-trust agent in the estate by design. ISO/IEC 42001 A.5 asks what an AI system does to people; a model drafting that about its own estate is the clearest case where fluency would be mistaken for assurance, so the draft never becomes a record on its own.

---

*End of manual. Regenerate with `python -m docs.generate_sop` after any change to `app/processes` or `app/agents`, and the document will match what the platform executes.*
