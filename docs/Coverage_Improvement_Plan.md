# Coverage Improvement Plan

**ISO/IEC 27001:2022 · ISO 22301:2019 · UK GDPR**
**Version 1.0 · August 2026**

Derived from `GET /v1/processes/coverage`, not from judgement. Every gap below
is a clause in the shipped catalogue that no process in the repository claims.

| Framework | Covered | Catalogue | Gap |
|---|---|---|---|
| ISO/IEC 27001:2022 | 113 | 118 | **5** |
| ISO 22301:2019 | 25 | 33 | **8** |
| UK GDPR | 24 | 31 | **7** |
| | | | **20 clauses** |

Closing all twenty needs **nine new processes and four extensions**. None of it
is speculative: each item below names the clauses it closes.

---

## 1. First, a defect that is not a coverage gap

Twelve clause references in the repository do not match any catalogue entry:

| Framework | Claimed | Catalogue actually holds |
|---|---|---|
| ISO 27001 | `6.1.3.d`, `9.2.1`, `9.2.2`, `9.3.1`, `9.3.2`, `9.3.3` | `6.1.3`, `9.2`, `9.3` — the repository is **finer** than the catalogue |
| ISO 22301 | `8.2`, `8.3`, `8.3.1`, `8.4`, `8.4.1` | `8.2.2`, `8.3.2`, `8.4.2` … — the repository is **coarser** |
| UK GDPR | `Art.5.1.e` | `Art.5`, `Art.5(2)` — a formatting difference |

**This does not change the coverage figures above.** In every case another
claim already covers the clause at the catalogue's own granularity, so nothing
is silently uncovered today.

It is still worth fixing, because it will eventually mask a real gap. Two
options, and the obvious one is wrong:

- ❌ **Resolve references by prefix.** Tempting and mechanical, but it
  manufactures phantom coverage. `Art.5.1.e` (storage limitation) would
  prefix-match `Art.5(2)` (accountability) and report a clause as discharged by
  a process that has nothing to do with it. Over-reporting coverage is worse
  than under-reporting it.
- ✅ **Make the repository speak the catalogue's vocabulary, and fail CI when
  it does not.** Add a validator rule: every `control_refs` entry must resolve
  to a catalogue `ref_code`, with an explicit alias table for the handful of
  legitimate cases. Unknown references become a build failure rather than a
  silent no-op.

**Effort: small. Do it first**, because it makes every later coverage
measurement trustworthy.

---

## 2. ISO/IEC 27001:2022 — 5 clauses

All five sit in Leadership and Support, and they share a cause: the repository
was built outward from operational compliance work and the management-system
scaffolding around it was left thin.

| Clause | Requirement | Currently |
|---|---|---|
| 5.3 | Organisational roles, responsibilities and authorities | Implied by the RBAC model; no process assigns or reviews them |
| 6.3 | Planning of changes | `PR-CHG-01` governs change to *systems*, not to the management system |
| 7.1 | Resources | Nothing determines or provides them |
| 7.4 | Communication | Nothing plans what is communicated, to whom, by whom, when |
| 7.5 | Documented information | Nothing governs document lifecycle, version, approval or retention |

**7.5 is the one that hurts.** A platform that produces evidence and has no
process governing its own documented information is a visible inconsistency,
and it is a clause certification auditors examine early because it is easy to
test.

---

## 3. ISO 22301:2019 — 8 clauses

The same five management-system clauses, plus three specific to the BCMS:

| Clause | Requirement | Currently |
|---|---|---|
| 5.3, 6.3, 7.1, 7.4, 7.5 | As above | Shared with ISO 27001 — one set of processes closes both |
| 8.3.4 | Resource requirements for continuity solutions | `PR-RES-02` already **produces** `resource_requirements` but does not claim the clause |
| 8.3.5 | Implementation of continuity solutions | Not addressed — the repository plans and exercises but does not govern implementation |
| 8.6 | Evaluation of continuity documentation and capabilities | Distinct from 8.5 exercising: a periodic review of whether the documentation and capability remain adequate |

**8.3.4 is nearly free** — a claim correction, not new work. 8.6 is genuinely
missing and is the clause that catches plans which are exercised but never
reassessed for whether they still describe the business.

---

## 4. UK GDPR — 7 articles

These are the most substantive gaps, because each is a real operational duty
with no home:

| Article | Requirement | Why it matters |
|---|---|---|
| Art.13 | Information where data is collected from the subject | Privacy notices are a live obligation with no owning process |
| Art.14 | Information where data is obtained elsewhere | The harder half — indirect collection is where notices are usually missed |
| Art.7 | Conditions for consent | Where consent is the basis, it must be demonstrable and withdrawable as easily as given. `PR-PRV-01` records that consent *is* the basis but nothing evidences it |
| Art.26 | Joint controllers | No process determines controller status or records the arrangement |
| Art.37 | Designation of the DPO | The role is used throughout the repository as an approver but never formally designated |
| Art.38 | Position of the DPO | Independence, resourcing and no-conflict are testable and untested |
| Art.5(2) | Accountability | The obligation to *demonstrate* compliance, not merely achieve it |

**Art.37/38 is an awkward one to leave open.** Thirteen gates in the repository
resolve to the DPO. A management system that routes statutory decisions to a
role it never formally designated, and whose independence it never assures, has
a hole an auditor will find quickly.

---

## 5. What to build

Nine new processes and four extensions. Grouped so that one piece of work
closes clauses across more than one standard wherever the requirement is
genuinely the same.

### Tier 1 — closes 13 clauses across all three standards

| ID | Process | Domain | Closes |
|---|---|---|---|
| `PR-GOV-06` | **Documented information control** — creation, review, approval, version, distribution, retention and disposal of policies, procedures and records | GOV | 27001 7.5 · 22301 7.5 |
| `PR-GOV-07` | **Communication planning and delivery** — what is communicated about the management systems, to whom, by whom, on what trigger, including regulator and customer channels | GOV | 27001 7.4 · 22301 7.4 |
| `PR-GOV-08` | **Roles, authorities and resourcing** — assigns management-system roles and authorities, determines the resources each needs, and reviews both on a cycle | GOV | 27001 5.3, 7.1 · 22301 5.3, 7.1 |
| `PR-PRV-09` | **DPO designation, position and independence** — designation, published contact, reporting line, resourcing, conflict-of-interest assurance | PRV | GDPR Art.37, Art.38 |

Tier 1 is deliberately management-system scaffolding. It is the least
interesting work in this plan and the most likely to be sampled in a stage 1
audit.

### Tier 2 — closes 4 privacy obligations

| ID | Process | Domain | Closes |
|---|---|---|---|
| `PR-PRV-06` | **Transparency and privacy information** — maintains notices against the Article 30 record, detects processing with no corresponding notice, governs notice change and republication | PRV | GDPR Art.13, Art.14 |
| `PR-PRV-07` | **Consent lifecycle** — capture with evidence, granularity, refresh, withdrawal, and downstream propagation of a withdrawal | PRV | GDPR Art.7 |
| `PR-PRV-08` | **Controller relationships and joint controllership** — determines controller/processor/joint status per activity and records the Article 26 arrangement | PRV | GDPR Art.26 |

`PR-PRV-06` has the strongest automation case in this plan: reconciling notices
against the Article 30 register is exactly the kind of mechanical comparison the
evidence agent already does well, and notice drift is invisible without it.

### Tier 3 — closes 3 continuity clauses

| ID | Process | Domain | Closes |
|---|---|---|---|
| `PR-RES-05` | **Continuity documentation and capability evaluation** — periodic review of whether plans still describe the business and whether capability still meets the objectives | RES | 22301 8.6 |
| *extend* `PR-RES-02` | Add activities for resource specification and solution implementation | RES | 22301 8.3.4, 8.3.5 |

### Tier 4 — extensions to existing processes

| Change | Closes |
|---|---|
| `PR-GOV-01` — add an activity governing planned change to the management system itself | 27001 6.3 · 22301 6.3 |
| `PR-GOV-04` — claim the accountability obligation; the management review record is how compliance is demonstrated | GDPR Art.5(2) |
| `PR-CMP-05` — claim Art.5(2) jointly; the evidence pack is the other half of demonstrating accountability | GDPR Art.5(2) |

---

## 6. Sequence

| Step | Work | Result |
|---|---|---|
| 1 | Reference normalisation and the CI validator rule | Coverage measurement becomes trustworthy |
| 2 | Tier 4 extensions | 27001 → **99.2%**, 22301 → 78.8% |
| 3 | Tier 1 | 27001 → **100%**, 22301 → 90.9%, GDPR → 83.9% |
| 4 | Tier 2 | GDPR → **100%** |
| 5 | Tier 3 | 22301 → **100%** |

Steps 2 and 4 give the most coverage per unit of work. Step 1 is not optional
even though it moves no number — everything after it depends on the measurement
being right.

---

## 7. Coverage is not the same as compliance

Reaching 100% on this plan means every clause has a process against it. It does
not mean the organisation is compliant, and the platform should not imply that
it does.

Three things matter more than the last few percentage points:

**Connectors are the real constraint.** `PR-CMP-02` defines continuous control
monitoring and the platform runs it, but a control is only machine-testable if
something connects to the source system. Without connectors the process
degrades to attestation — which is honest, and still weaker than a test. Ten
well-chosen connectors (identity provider, cloud posture, endpoint, backup,
logging, ticketing) would move real assurance further than closing all twenty
clauses.

**A control test library.** Each control needs a defined expected state before
drift means anything. This is per-environment work the repository cannot do for
you.

**The evidence discount is already telling you this.** Readiness is discounted
30% where an implementation claim has no current evidence. That gap between
claimed and evidenced readiness is a more useful number than clause coverage,
and it will not move because a clause acquired a process.
