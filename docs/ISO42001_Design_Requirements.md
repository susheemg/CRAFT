# Design Requirements — ISO/IEC 42001:2023

**Artificial Intelligence Management System (AIMS)**
**Version 1.0 · August 2026**

A specification for adding ISO/IEC 42001 as a fourth certifiable framework. It
states what must be built, what must be true when it is, and what is
deliberately out of scope.

---

## 1. Why this standard, and why now

Three reasons, in order of weight.

**The platform cannot credibly omit it.** CRAFT automates compliance using
eleven AI agents. A GRC system that governs everything except its own AI is
arguing against itself, and any competent assessor will notice. The AI
governance domain added in v1.0 (`PR-AIG-01/02/03`) was a partial answer;
ISO 42001 is the complete one, and it is certifiable.

**It is the natural companion to what already exists.** ISO 42001 shares the
Annex SL high-level structure with ISO 27001 and ISO 22301 — clauses 4 to 10 are
structurally the same management-system requirements. An organisation already
running those two absorbs a third at materially lower cost than the clause count
suggests, and the platform's existing cross-framework mapping is built for
exactly this.

**It gives the EU AI Act deferral a purpose.** Regulation (EU) 2026/1744 moved
standalone Annex III high-risk obligations to 2 December 2027 and embedded
Annex I systems to 2 August 2028. Article 50 transparency duties were *not*
deferred and took effect on 2 August 2026. The deferral is time to build a
management system rather than a reason to stand down, and ISO 42001 is the
recognised structure for doing so.

**Note on legal effect:** ISO 42001 certification is not a presumption of
conformity with the AI Act. The harmonised standards under the Act are separate
work. The platform must never imply otherwise.

---

## 2. What the standard requires

### 2.1 Management system clauses (4–10)

Structurally identical to ISO 27001 and ISO 22301: context, leadership,
planning, support, operation, performance evaluation, improvement. The
substance differs — the risk being managed is risk *from and to* AI systems,
including risk to individuals and society rather than only to the organisation.

### 2.2 Annex A controls

Approximately 38 controls grouped under nine objectives:

| Objective | Concerns |
|---|---|
| A.2 | Policies for AI |
| A.3 | Internal organisation — roles, responsibilities, reporting of concerns |
| A.4 | Resources for AI systems — data, tooling, compute, human competence |
| A.5 | Assessing impacts of AI systems, including impacts on individuals and society |
| A.6 | AI system lifecycle — objectives, design, verification, deployment, operation |
| A.7 | Data for AI systems — provenance, quality, preparation |
| A.8 | Information for interested parties |
| A.9 | Use of AI systems — responsible use, intended purpose, human oversight |
| A.10 | Third-party and customer relationships |

> **DR-0 — Reconcile before certification.** The control titles and structure
> above are paraphrased from memory of the published standard and must be
> reconciled against a licensed copy before any certification use. This follows
> the `source_note` mechanism already used for the ISO 27001 and ISO 22301
> catalogues: titles are paraphrased rather than reproduced, and each entry
> carries a flag recording that reconciliation is outstanding. **The platform
> must not report certification readiness against an unreconciled catalogue.**

### 2.3 The distinguishing requirement

Clause A.5 — **AI system impact assessment** — is the control with no analogue
in ISO 27001. It requires assessing consequences for individuals and groups,
not merely for the organisation. It is closest in spirit to a DPIA, and the
platform's existing DPIA machinery is the right foundation, but the scope is
wider: a DPIA concerns personal data, an AI impact assessment concerns effects
including those with no personal data involved at all.

---

## 3. Design requirements

### 3.1 Catalogue

**DR-1** — Add framework `iso42001` to the catalogue with `certifiable = true`,
edition `2023`, issuer `ISO/IEC`.

**DR-2** — Load clauses 4–10 as `control_type = "requirement"` with
`is_mandatory = true`, matching the treatment of the other management-system
standards. A mandatory clause must remain non-excludable in the Statement of
Applicability.

**DR-3** — Load the Annex A controls as `control_type = "control"`, excludable
with justification, each carrying `theme` set to its objective (A.2–A.10) so
that section-level readiness reports the way the standard is structured.

**DR-4** — Every entry carries `source_note` recording that the title is
paraphrased and reconciliation is outstanding, and `evidence_hint` describing
what good looks like for that control.

### 3.2 Cross-framework mapping

**DR-5** — Map ISO 42001 clauses 4–10 to their ISO 27001 equivalents. An
organisation satisfying 27001 clause 7.5 largely satisfies 42001 clause 7.5;
the platform must show that so the same evidence serves both and the second
certification does not duplicate the first.

**DR-6** — Map the Annex A controls with genuine overlap, and **only** those.
A.7 (data for AI) overlaps 27001 A.8.10–A.8.12 and GDPR Art.5. A.10
(third-party) overlaps 27001 A.5.19–A.5.22. A.9 (responsible use) overlaps GDPR
Art.22.

**DR-7** — Do not map where the overlap is superficial. A mapping that lets an
organisation claim A.5 impact assessment is satisfied by an ISO 27001 risk
assessment would be actively harmful: it addresses risk to the organisation,
not to the individuals the AI affects, and asserting otherwise would let a real
gap pass certification.

### 3.3 Process repository

**DR-8** — Add domain `AIM` — *AI management system* — owned by a named role. The
existing `AIG` domain (three processes covering inventory, oversight and drift)
is subsumed: its processes are re-homed into `AIM` and extended rather than
duplicated, so there is one set of AI processes rather than two competing ones.

**DR-9** — The domain must include, at minimum:

| Process | Purpose | Principal clauses |
|---|---|---|
| `PR-AIM-01` | AI policy, scope and objectives | 4.1–4.4, 5.2, 6.2, A.2 |
| `PR-AIM-02` | AI system inventory and classification *(extends `PR-AIG-01`)* | A.6, A.9 |
| `PR-AIM-03` | **AI system impact assessment** | 6.1, A.5 |
| `PR-AIM-04` | AI lifecycle governance — objectives, design, verification, release | A.6 |
| `PR-AIM-05` | Data for AI — provenance, quality, preparation, retention | A.7 |
| `PR-AIM-06` | Human oversight and decision accountability *(extends `PR-AIG-02`)* | A.9, 8.1 |
| `PR-AIM-07` | Performance monitoring, drift and revalidation *(extends `PR-AIG-03`)* | 9.1, A.6 |
| `PR-AIM-08` | Information for interested parties — transparency, disclosure, incident communication | A.8 |
| `PR-AIM-09` | Third-party AI and model supply chain *(extends `PR-TPR-02`)* | A.10 |
| `PR-AIM-10` | AI incident, misuse and concern reporting | A.3, 10.2 |

**DR-10** — `PR-AIM-03` must carry a **statutory-or-irreversible gate** on
approving an assessment where residual impact on individuals remains material.
The four exception tests apply as everywhere else, and this is the process where
they bite hardest.

**DR-11** — `PR-AIM-10` must provide a route for a person to raise a concern
about an AI system, including anonymously. A.3 expects it, and a reporting
channel that only accepts named complaints will not surface the concerns that
matter most.

### 3.4 Agent implications

**DR-12** — No new agent. The impact-assessment work belongs to the existing
`privacy` agent (which already runs `dpia_drafting`) and the `regulatory_watch`
agent. Adding an "AI governance agent" that assesses AI systems would create the
circularity the standard exists to prevent.

**DR-13** — Agents must be **prohibited from assessing themselves**. The
existing rule that the audit agent cannot assure a process it executed extends
to this: no agent may perform the impact assessment, oversight review or drift
revalidation of an AI system that includes itself. The process validator must
enforce this, not a convention.

**DR-14** — Every agent in `app/agents/registry.py` is an AI system in scope of
`PR-AIM-02`. The loader must create an inventory entry per registered agent
automatically, so the inventory cannot fall behind the registry.

**DR-15** — Add to the universal refusal list: *"Determining whether an AI
system is high-risk under any regulation, or whether its impact on individuals
is acceptable."* Both are determinations with legal consequence.

### 3.5 Data model

**DR-16** — New table `compliance.ai_system`: identity, owner, purpose,
intended use, deployment context, provider and model where applicable, data
categories used, autonomy level, lifecycle stage, classification, and links to
the agent registry key where the system is one of the platform's own.

**DR-17** — New table `compliance.ai_impact_assessment`: the assessed system,
affected groups, impact categories (rights, safety, fairness, environmental,
societal), likelihood and severity per group, mitigations, residual position,
assessor, approver, approval gate, and review date. It must be a distinct table
from `dpia`, not a flag on it: the scopes differ, and conflating them means one
is done badly.

**DR-18** — New table `compliance.ai_dataset`: provenance, licence basis,
collection method, preparation steps, known limitations and bias assessment,
retention. A.7 is unsatisfiable without it.

**DR-19** — Extend `config.model_invocation` with the AI system identifier so
that every model call is attributable to an inventoried system. The
`confidence` column added in migration 0005 already supports A.6 and A.9
monitoring.

**DR-20** — All new tables carry `tenant_id`, RLS with `FORCE` and `WITH CHECK`,
and the standard timestamp and soft-delete mixins. No exceptions to the
isolation model.

### 3.6 Interface

**DR-21** — Extend `GET /v1/compliance/frameworks` and the readiness, SoA and
coverage endpoints to include `iso42001` with no special-casing. If the
framework needs bespoke handling in those endpoints, the catalogue model is
wrong.

**DR-22** — New endpoints: `/v1/ai-systems` (inventory CRUD),
`/v1/ai-systems/{id}/impact-assessment`, `/v1/ai-systems/{id}/datasets`.

**DR-23** — Extend the existing `/v1/ai-oversight` rather than adding a parallel
surface. It already measures the thing A.9 cares about — whether human oversight
is real or nominal.

**DR-24** — Console: one AI management page showing inventory by classification,
impact assessments due or overdue, oversight metrics, and drift findings. One
page, one decision per view, consistent with the existing console.

### 3.7 Evidence

**DR-25** — The following must be produced as hashed evidence records by process
execution, not assembled by hand at audit time: the AI system inventory
snapshot, each approved impact assessment, oversight metrics per period, drift
and revalidation records, dataset provenance records, and third-party AI
assessments.

**DR-26** — Readiness must apply the same 30% evidence discount as the other
frameworks. There must be no route by which AI governance scores better for
being newer.

---

## 4. Acceptance criteria

The work is done when all of the following hold:

1. `GET /v1/compliance/iso42001/readiness` returns a figure computed the same
   way as the other three frameworks, with the evidence discount applied.
2. `GET /v1/processes/coverage?framework=iso42001` reports **100%**, with every
   claimed reference resolving to a catalogue entry.
3. The Statement of Applicability lists every Annex A control, and every
   exclusion carries a justification.
4. Every agent in the registry appears in the AI system inventory, created by
   the loader rather than by hand.
5. `app.processes.validate()` and `app.agents.registry.validate()` both return
   empty, including the new self-assessment prohibition (DR-13).
6. No agent holds approval authority over any AI governance gate — verified by
   the existing structural tests, extended to the new gate types.
7. The SOP manual regenerates to include the `AIM` domain with no code change to
   the generator.
8. Certification readiness reports **blocked** while any catalogue entry remains
   unreconciled against a licensed copy (DR-0).
9. Tests: catalogue completeness and theme split, impact-assessment gate
   behaviour, self-assessment prohibition, inventory-to-registry consistency,
   and the endpoint smoke test extended to the new routes.

---

## 5. Out of scope

Stated so that the boundary is a decision rather than an omission.

- **Model evaluation and benchmarking.** The platform records that validation
  happened and what it concluded. It does not run the evaluation. Building an
  evaluation harness is a different product.
- **Bias and fairness testing.** Same reasoning: the process requires the
  assessment and records its outcome; the statistical testing belongs in the ML
  toolchain.
- **EU AI Act conformity assessment.** ISO 42001 is a management system
  standard. Conformity assessment under the Act is a distinct exercise against
  different criteria, and conflating them would mislead.
- **Governance of AI embedded in third-party SaaS the organisation merely uses.**
  In scope for the inventory (A.10), out of scope for lifecycle controls the
  organisation cannot exercise.

---

## 6. Risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Catalogue paraphrasing diverges from the standard | Certification fails on a control the platform reported as met | DR-0 blocks certification readiness until reconciled |
| Over-eager mapping to ISO 27001 | A real AI-specific gap passes as covered by existing evidence | DR-7 — map only genuine overlap; A.5 explicitly unmapped |
| Impact assessment collapses into the DPIA | Non-personal-data impacts on individuals go unassessed | DR-17 — separate table, separate process, separate gate |
| Agents assess themselves | The circularity the standard exists to prevent | DR-13 — enforced by the validator |
| The framework is treated as a documentation exercise | Certification achieved, oversight still nominal | DR-23 and DR-26 — oversight measured, discount applied |

---

## 7. Sequencing

| Phase | Work | Outcome |
|---|---|---|
| 1 | DR-1 to DR-4, DR-16 to DR-20 | Catalogue and schema exist; readiness computes at 0% |
| 2 | DR-8 to DR-11 | Processes defined; SOP manual regenerates |
| 3 | DR-12 to DR-15 | Agent constraints enforced; inventory self-populates |
| 4 | DR-21 to DR-24 | API and console |
| 5 | DR-5 to DR-7, DR-25, DR-26 | Mapping and evidence; readiness becomes meaningful |
| 6 | Reconcile catalogue against a licensed copy | Certification readiness unblocks |

Phases 1 to 3 are the substance. Phase 6 is not optional, and it is the one that
needs a purchased copy of the standard rather than engineering time.
