# Functional and Technical Design — CRAFT Release 2.0

**Coverage closure across ISO 27001, ISO 22301 and UK GDPR, plus ISO/IEC 42001**

**Version 1.0 · August 2026 · For the development team**

---

## 1. Purpose and audience

A build specification. It states what to build, how it must fit the existing
codebase, and what must be true before each piece is done.

Read sections 2 and 3 before writing any code. Section 3 describes conventions
that are not obvious from the source and that this codebase enforces in CI — a
change that ignores them will fail the build rather than merge quietly.

**Scope of this release**

| Work package | Delivers | Est. |
|---|---|---|
| WP0 | Two defects that must be fixed before anything is built on top | 3d |
| WP1 | Management-system processes — closes 13 clauses across 27001 and 22301 | 5d |
| WP2 | Privacy processes — closes 7 GDPR articles | 6d |
| WP3 | Continuity processes — closes 3 ISO 22301 clauses | 3d |
| WP4 | Extensions to existing processes — closes 3 clauses | 1d |
| WP5 | ISO 42001 catalogue and schema | 6d |
| WP6 | ISO 42001 process domain | 8d |
| WP7 | Agent constraints and self-assessment prohibition | 3d |
| WP8 | AI system inventory, impact assessment and dataset API | 7d |
| WP9 | Console and cross-framework mapping | 5d |
| WP10 | Test and documentation completion | 4d |
| | | **51d** |

Estimates assume one developer already familiar with the codebase. Add
onboarding for anyone who is not: the data-driven design in section 3 takes
about two days to internalise and saves considerably more than that afterwards.

**Out of scope:** model evaluation harnesses, bias testing tooling, EU AI Act
conformity assessment, source-system connectors for continuous control
monitoring. Connectors are the highest-value next release and are specified
separately.

---

## 2. Current state

Release 1.0, in the attached repository.

| | |
|---|---|
| Service | Single FastAPI (Python 3.12) + PostgreSQL 16 |
| API | 82 endpoints under `/v1`, OpenAPI at `/docs` |
| Console | Server-rendered Jinja2, seven pages |
| MCP | JSON-RPC 2.0 at `/mcp`, 13 governed tools |
| Schemas | 8, 51 tables, RLS forced on 36 |
| Processes | 36 across 10 domains, 148 activities, 30 gates |
| Agents | 11, none with approval authority |
| Catalogue | ISO 27001 (118), ISO 22301 (33), UK GDPR (31) |
| Tests | 142, against real PostgreSQL |
| Migrations | 0001–0005, forward-only, checksummed |

Coverage today: ISO 27001 95.8%, ISO 22301 75.8%, UK GDPR 77.4%.

---

## 3. Conventions you must follow

This codebase is data-driven in a way that is easy to fight if you have not
read this section.

### 3.1 Processes are code, not configuration rows

The 36 processes live in `app/processes/*.py` as frozen dataclasses. **The
engine executes them and the SOP manual is generated from them.** Do not add a
process by inserting database rows; add it to the repository module and let the
loader materialise it.

```python
Process(
    code="PR-GOV-06",
    name="Documented information control",
    domain="GOV",
    purpose="...",                       # one paragraph, says why it exists
    owner_role="CISO",                   # must match a seeded role name exactly
    trigger="...",
    cadence=Cadence.QUARTERLY,
    clauses={"iso27001": ("7.5",), "iso22301": ("7.5",)},
    activities=( ... ),
)
```

**After any change:**

```bash
python -c "from app.processes import validate; print(validate())"   # must be []
python -c "from app.agents.registry import validate; print(validate())"
python -m docs.generate_sop > docs/SOP_Manual.md
pytest -q
```

### 3.2 What validation enforces

`app/processes/validate()` will reject your change if:

- an activity names an agent as `accountable` — accountability is always a person
- a `GATE` activity names an agent
- an agent-assisted activity has an `ai_role` but no `task_class` to route it
- a process discharges no clause
- a domain lists a process that does not exist, or vice versa
- an activity code is duplicated within a process

`app/agents/registry.validate()` will reject your change if:

- an agent claims a process that does not exist
- an L4 (unattended) agent declares any `task_class` — unattended work must be
  deterministic
- an activity routes to a task class its agent does not hold

**These are not style rules.** Each corresponds to a failure that would only
surface when someone depended on it in production.

### 3.3 Clause references must resolve

WP0 adds a validator rule making this a build failure. Every string in
`control_refs` and every key in `clauses` must resolve to a `ref_code` in the
shipped catalogue. Check the catalogue before inventing a reference:

```python
from app.seed.catalogue import CONTROLS_BY_FRAMEWORK
{c["ref_code"] for c in CONTROLS_BY_FRAMEWORK["iso27001"]()}
```

### 3.4 Migrations are forward-only and checksummed

Add `db/migrations/00NN_name.sql`. Make it idempotent (`IF NOT EXISTS`).
**Never edit an applied file** — the runner checksums applied migrations and
refuses to continue if one changes, which is deliberate.

Every new table needs, without exception:

```sql
-- tenant_id column, then in the same migration:
ALTER TABLE <schema>.<table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <schema>.<table> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <schema>.<table>
    USING (tenant_id::text = current_setting('app.tenant_id', true)
           OR current_setting('app.bypass_rls', true) = 'on')
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true)
           OR current_setting('app.bypass_rls', true) = 'on');
GRANT SELECT, INSERT, UPDATE, DELETE ON <schema>.<table> TO craft_app;
```

`FORCE` is not optional: PostgreSQL exempts the table owner from RLS without
it, and on single-credential deployments the application *is* the owner.
`WITH CHECK` is not optional either — without it a session can write a row
stamped with another tenant's id.

### 3.5 Every state change writes an audit entry

```python
audit.record(
    db, tenant_id=principal.tenant_id, action="ai.system_registered",
    actor_type=principal.actor_type, actor_ref=principal.actor_ref,
    actor_id=principal.id, entity="ai_system", entity_id=row.id,
    before_state={...}, after_state={...}, request_id=request_id,
)
```

Where a model contributed, also pass `model`, `prompt_version` and `sources`.
The AI decision record at `/v1/ai-oversight/decisions` reads these, and an
entry without them is invisible to it.

### 3.6 Error envelope

One shape, everywhere:

```json
{"error": {"code": "snake_case_code", "message": "A sentence a person can act on.", "request_id": "..."}}
```

Raise `HTTPException` with that structure as `detail`, or a bare string — the
handler in `app/main.py` normalises both.

### 3.7 Naming and tone

Endpoint actions use a colon suffix (`POST /v1/risks/{id}:accept`). Error
messages say what to do, not what went wrong. Comments explain *why*, never
*what* — the code already says what.

---

## 4. WP0 — Defects to fix first

Both were found while specifying this release. Build nothing on top of them.

### 4.1 Sixteen gate types have no authority mapping

**Finding.** The repository defines 30 distinct gate types. `GATE_AUTHORITY` in
`app/seed/__init__.py` maps 14. The unmapped 16 include
`governance.management_review`, `compliance.soa_approval`,
`audit.report_issue`, `privacy.subject_notification`,
`risk.treatment_approval` and all three `ai.*` gates.

**Consequence.** `engine.raise_gate()` takes `approver_role_id` as a parameter
defaulting to `None` and does not consult the authority table. A gate raised
without it is decidable by anyone holding the permission derived from the gate
type prefix. The role restriction the authority table exists to express is not
applied.

This is a control weakness, not an outage: the permission check and the
requester-cannot-approve check both still operate. But `compliance.soa_approval`
is currently decidable by anyone with `compliance.attest`, when it should be
reserved to the CISO.

**Fix.**

1. Extend `GATE_AUTHORITY` to cover all 30 gate types. Proposed mapping:

| Gate type | Role |
|---|---|
| `governance.scope_approval` | CISO |
| `governance.objectives_approval` | CISO |
| `governance.management_review` | CISO |
| `compliance.soa_approval` | CISO |
| `compliance.control_attestation` | Control Owner |
| `compliance.gap_closure` | Control Owner |
| `risk.treatment_approval` | Risk Officer |
| `audit.report_issue` | Internal Auditor |
| `audit.external_response` | CISO |
| `privacy.subject_notification` | DPO |
| `privacy.disposal_authorisation` | DPO |
| `security.vulnerability_exception` | CISO |
| `resilience.stand_down` | CISO |
| `ai.risk_classification` | CISO |
| `ai.autonomy_change` | CISO |
| `ai.model_revalidation` | CISO |

2. Change `engine.raise_gate()` to resolve `approver_role_id` from
   `iam.gate_authority` when the caller does not supply one. Where more than
   one role is authorised, leave `approver_role_id` null and rely on the
   permission check — the table still documents who may decide.

3. **Add a test that fails when a repository gate type has no mapping.** This
   is the durable fix; the table will otherwise fall behind the repository
   again the next time someone adds a process.

```python
def test_every_repository_gate_type_has_an_authority_mapping():
    from app.processes import PROCESSES
    from app.seed import GATE_AUTHORITY
    mapped = {g for g, _ in GATE_AUTHORITY}
    unmapped = {a.gate_type for p in PROCESSES for a in p.gates} - mapped
    assert not unmapped, f"Gate types with no authorised role: {sorted(unmapped)}"
```

**Effort: 2d.**

### 4.2 Clause references do not all resolve

**Finding.** Twelve references in the repository match no catalogue entry: the
repository claims `9.2.1` where the catalogue holds `9.2`, and `8.2` where the
catalogue holds `8.2.2`/`8.2.3`.

**Consequence.** None today — every affected clause is covered by another claim
at the catalogue's own granularity. But an unresolvable reference is a silent
no-op, so the next one to appear will hide a real gap.

**Fix.** Add to `app/processes/validate()`, resolving against the catalogue:

```python
def validate_against_catalogue(catalogue: dict[str, set[str]]) -> list[str]:
    """Every claimed reference must name a real catalogue entry.

    Deliberately not prefix-matching. 'Art.5.1.e' (storage limitation) would
    prefix-match 'Art.5(2)' (accountability) and report a clause as discharged
    by a process with nothing to do with it. Manufacturing coverage is worse
    than under-reporting it, so unknown references are an error and aliases are
    declared explicitly.
    """
```

Maintain `CLAUSE_ALIASES: dict[str, dict[str, str]]` for legitimate cases
(`{"iso27001": {"9.2.1": "9.2", "9.2.2": "9.2", ...}}`). Correct the twelve
references to canonical form. Wire the check into CI.

**Do not implement prefix resolution.** It is the obvious approach and it
manufactures phantom coverage.

**Effort: 1d.**

---

## 5. WP1 — Management-system processes

Closes ISO 27001 5.3, 6.3, 7.1, 7.4, 7.5 and ISO 22301 5.3, 6.3, 7.1, 7.4, 7.5.

### 5.1 Functional design

**`PR-GOV-06` Documented information control** — governs the lifecycle of
policies, procedures and records: creation, review, approval, version,
distribution, retention, disposal.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Maintain the document register: every controlled document, its owner, version, approval date and review date | `AUTO` | `evidence` |
| A2 | Detect documents past their review date or superseded but still distributed | `AUTO_NOTIFY` | `evidence` |
| A3 | Draft the revision for a document falling due | `ASSIST` | `control_assessor` |
| A4 | Approve and issue the revision | `GATE` `governance.document_approval` — irreversible | — |
| A5 | Withdraw superseded versions and record the disposal | `AUTO` | `evidence` |

*Design note for the team:* A2 is the clause's real content. Auditors test 7.5
by asking for a document and checking whether the copy in circulation is the
approved version. Detecting that divergence automatically is the whole value.

**`PR-GOV-07` Communication planning and delivery** — what is communicated
about the management systems, to whom, by whom, on what trigger.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Maintain the communication matrix: topic, audience, channel, frequency, owner | `ASSIST` | `control_assessor` |
| A2 | Detect communications due or missed against the matrix | `AUTO_NOTIFY` | `orchestrator` |
| A3 | Draft the communication | `ASSIST` | `control_assessor` |
| A4 | Approve external communication | `GATE` `governance.external_communication` — irreversible | — |
| A5 | Record delivery and, where required, acknowledgement | `AUTO` | `evidence` |

*A4 is gated because external communication cannot be retracted, and because
the universal agent refusal list already forbids an agent communicating with a
regulator, auditor, customer or data subject.*

**`PR-GOV-08` Roles, authorities and resourcing** — assigns management-system
roles and authorities, determines the resources each needs, reviews both.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Derive the required roles and authorities from the process repository | `AUTO` | `reporting` |
| A2 | Reconcile required roles against actual grants and report unfilled or unclear assignments | `AUTO_NOTIFY` | `evidence` |
| A3 | Determine the resources each role needs to discharge its authority | `ASSIST` | `control_assessor` |
| A4 | Approve the assignment and the resourcing | `GATE` `governance.roles_and_resources` — high risk | — |

*A1 is genuinely automatable and worth doing well: the repository already knows
every `owner_role` and every `accountable` role, so the required role set is a
query. A2 then finds the roles nobody holds — which is how an organisation
discovers that thirteen gates route to a DPO it never designated.*

**`PR-PRV-09` DPO designation, position and independence** — closes GDPR
Art.37 and Art.38.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Record the designation: identity, contact, publication, notification to the supervisory authority | `MANUAL` | — |
| A2 | Record the reporting line, resourcing and the tasks the DPO also performs | `ASSIST` | `privacy` |
| A3 | Assess conflict of interest across the DPO's other duties | `ASSIST` | `privacy` |
| A4 | Confirm designation and independence annually | `GATE` `privacy.dpo_designation` — statutory | — |

*A3 must be `ASSIST` and never `AUTO`. Whether a DPO's other duties create a
conflict is a judgement about organisational reality, and the agent's job is to
surface the facts.*

### 5.2 Technical design

New file `app/processes/management_system.py` exporting
`MANAGEMENT_SYSTEM: tuple[Process, ...]`. Register in `app/processes/_load()`.
Add the four codes to the `GOV` and `PRV` domain tuples in `DOMAINS`.

Four new gate types — add to `GATE_AUTHORITY` per WP0, and confirm
`gate_permission_for()` derives an existing permission for each. Both
`governance.*` gates derive `gate.config.approve`; if the derivation is wrong
for these, add permissions rather than bending the gate names.

No schema change. No API change — the existing `/v1/processes` endpoints expose
new processes automatically.

**Effort: 5d.**

---

## 6. WP2 — Privacy processes

Closes GDPR Art.7, 13, 14, 26.

### 6.1 `PR-PRV-06` Transparency and privacy information

The strongest automation case in this release.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Maintain the notice register: each notice, the processing it covers, version, publication location | `AUTO` | `evidence` |
| A2 | **Reconcile notices against the Article 30 register and report processing with no covering notice** | `AUTO_NOTIFY` | `privacy` |
| A3 | Determine whether collection is direct (Art.13) or indirect (Art.14) and which disclosures are required | `ASSIST` | `privacy` |
| A4 | Draft or revise the notice | `ASSIST` | `privacy` |
| A5 | Approve and publish | `GATE` `privacy.notice_publication` — irreversible | — |
| A6 | Record the version served and when | `AUTO` | `evidence` |

*A2 is the reason to build this. Notice drift is invisible without it: a new
processing activity is added to the Article 30 register, no one updates the
notice, and nothing detects the divergence until a complaint. This is a set
difference over two registers the platform already holds.*

*A3 must handle the indirect case explicitly. Art.14 is the harder half and the
one usually missed, so the agent should call it out rather than defaulting to
Art.13.*

### 6.2 `PR-PRV-07` Consent lifecycle

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Record the consent: purpose, scope, wording presented, version, timestamp, method | `AUTO` | `evidence` |
| A2 | Assess whether the consent as captured meets the conditions — freely given, specific, informed, unambiguous | `ASSIST` | `privacy` |
| A3 | Detect consents that are stale, or whose purpose has drifted from what was consented to | `AUTO_NOTIFY` | `privacy` |
| A4 | Process a withdrawal and propagate it to every downstream recipient | `AUTO` | `orchestrator` |
| A5 | Confirm the withdrawal took effect everywhere | `ASSIST` | `evidence` |

*A4 is where consent implementations usually fail. Withdrawal must be as easy
as giving, and it must reach downstream processors. Propagation is a real
workflow, not a flag update, so model it as one.*

### 6.3 `PR-PRV-08` Controller relationships and joint controllership

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Determine controller, processor or joint status per processing activity | `ASSIST` | `privacy` |
| A2 | Record the Article 26 arrangement, including who discharges which duty | `MANUAL` | — |
| A3 | Detect activities whose status is undetermined or inconsistent with the supplier record | `AUTO_NOTIFY` | `privacy` |
| A4 | Approve the determination and the arrangement | `GATE` `privacy.controller_determination` — statutory | — |

*A1 proposes; it does not conclude. Controller status is a legal determination
and the universal refusal list already covers it.*

### 6.4 Technical design

New file `app/processes/privacy_extended.py`. Register in `_load()`; add codes
to the `PRV` domain tuple.

Three new tables — see section 9.1 for DDL: `domain.privacy_notice`,
`domain.consent_record`, `domain.controller_arrangement`.

New endpoints under `/v1/privacy/`: `notices`, `consents`,
`controller-arrangements`, each following the existing router pattern in
`app/api/v1/operations.py`.

**Effort: 6d.**

---

## 7. WP3 and WP4 — Continuity and extensions

### 7.1 `PR-RES-05` Continuity documentation and capability evaluation

Closes ISO 22301 8.6, which is distinct from 8.5 exercising: 8.5 asks whether
the plan works, 8.6 asks whether it still describes the business.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Detect divergence between plans and the current estate — dependencies, suppliers, systems that changed since approval | `AUTO_NOTIFY` | `resilience` |
| A2 | Evaluate whether documented capability still meets the approved objectives | `ASSIST` | `resilience` |
| A3 | Raise gaps where documentation or capability has fallen behind | `AUTO_NOTIFY` | `control_assessor` |
| A4 | Confirm the evaluation | `GATE` `resilience.capability_evaluation` — high risk | — |

### 7.2 Extend `PR-RES-02`

Add two activities and claim ISO 22301 8.3.4 and 8.3.5. The process already
produces `resource_requirements`; formalise it as an activity and add
implementation governance.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A5 | Specify the resources the selected strategy requires — people, premises, technology, information, suppliers | `ASSIST` | `resilience` |
| A6 | Confirm the solution is implemented and operable before the plan is relied on | `ASSIST` | `evidence` |

### 7.3 WP4 — Claim extensions

| Change | Closes |
|---|---|
| `PR-GOV-01` — add an activity governing planned change to the management system itself, and claim `6.3` on both standards | 27001 6.3, 22301 6.3 |
| `PR-GOV-04` — add `"uk_gdpr": ("Art.5(2)",)` to `clauses` | GDPR Art.5(2) |
| `PR-CMP-05` — add `"uk_gdpr": ("Art.5(2)",)` to `clauses` | GDPR Art.5(2) |

*Art.5(2) is the duty to demonstrate compliance, and it is demonstrated jointly
by the management review record and the evidence pack. Two processes claiming
one clause is correct here and the coverage model supports it.*

**Effort: WP3 3d, WP4 1d.**

---

## 8. WP5–WP9 — ISO/IEC 42001

Implements the design requirements in `docs/ISO42001_Design_Requirements.md`.
That document is normative; this section says how to build it.

### 8.1 WP5 — Catalogue and schema

New file `app/seed/catalogue_iso42001.py` following the existing pattern:

```python
def iso42001_controls() -> list[dict]:
    """ISO/IEC 42001:2023.

    Titles are PARAPHRASED, not reproduced. Each entry carries a source_note
    recording that reconciliation against a licensed copy is outstanding, and
    certification readiness stays blocked until it is done (DR-0).
    """
```

- Clauses 4–10: `control_type="requirement"`, `is_mandatory=True`
- Annex A: `control_type="control"`, `theme` set to the objective (`A.2`–`A.10`)
- Every entry: `source_note="paraphrased; reconcile against licensed copy"` and
  a populated `evidence_hint`

Register in `FRAMEWORKS` and `CONTROLS_BY_FRAMEWORK` in `app/seed/catalogue.py`.

**Certification blocker.** Extend `compliance.compute_readiness()` so an
unreconciled `source_note` on any applicable control adds a blocker to
`ReadinessResult.blockers` and forces `certification_ready = False`. Do not
special-case ISO 42001 — apply the rule to every framework, which also makes it
visible for the existing three.

Migration `0006_ai_management.sql` — see section 9.2.

**Effort: 6d.**

### 8.2 WP6 — Process domain

New domain `AIM`. **Re-home the three existing `AIG` processes into it rather
than duplicating them** (DR-8): rename `PR-AIG-01/02/03` to `PR-AIM-02/06/07`,
extend them, and remove the `AIG` domain. Because the loader supersedes a
changed definition rather than editing it, the rename creates new workflows;
retire the old ones by setting `status = "retired"` in a data migration so run
history stays intact.

Ten processes per DR-9. The two needing most care:

**`PR-AIM-03` AI system impact assessment** — the control with no ISO 27001
analogue.

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Describe the system, its intended purpose and its deployment context | `ASSIST` | `privacy` |
| A2 | Identify affected individuals and groups, including those who are not users | `ASSIST` | `privacy` |
| A3 | Assess impact per group across rights, safety, fairness, environmental and societal categories | `ASSIST` | `privacy` |
| A4 | Determine mitigations and the residual position | `ASSIST` | `privacy` |
| A5 | Approve, where residual impact remains material | `GATE` `ai.impact_acceptance` — irreversible | — |

*A2 is the activity that distinguishes this from a DPIA. A DPIA concerns data
subjects; an impact assessment concerns everyone the system affects, including
people who never interact with it and about whom no personal data is held. Do
not let this collapse into the DPIA — DR-17 requires a separate table for the
same reason.*

**`PR-AIM-05` Data for AI systems**

| # | Activity | Mode | Agent |
|---|---|---|---|
| A1 | Record dataset provenance, collection method and licence basis | `ASSIST` | `privacy` |
| A2 | Record preparation steps and known limitations | `ASSIST` | `control_assessor` |
| A3 | Assess quality and representativeness against the intended purpose | `ASSIST` | `control_assessor` |
| A4 | Detect datasets in use with no provenance record | `AUTO_NOTIFY` | `evidence` |
| A5 | Approve the dataset for the stated purpose | `GATE` `ai.dataset_approval` — high risk | — |

**Effort: 8d.**

### 8.3 WP7 — Agent constraints

**No new agent** (DR-12). Impact assessment work goes to `privacy` (which
already holds `dpia_drafting`) and `regulatory_watch`.

**Self-assessment prohibition** (DR-13) — a new validator rule and the most
interesting piece of work in this package:

```python
def _validate_no_self_assessment(problems: list[str]) -> None:
    """An agent may not assess an AI system that includes itself.

    Every registered agent is an AI system in scope of PR-AIM-02. Letting the
    privacy agent perform the impact assessment of the privacy agent is the
    circularity ISO 42001 exists to prevent, and it would not be visible in
    any output — the assessment would simply be favourable.
    """
```

Implement as: any activity in `PR-AIM-03`, `PR-AIM-06` or `PR-AIM-07` whose
subject may be an agent must either be `MANUAL`/`GATE`, or be performed by an
agent that is excluded from the assessed set. Enforce at runtime too — the
service performing an impact assessment must refuse when
`ai_system.agent_key == acting_principal.agent_key`.

Add to `UNIVERSAL_REFUSALS` (DR-15):

```python
"Determining whether an AI system is high-risk under any regulation, or "
"whether its impact on individuals is acceptable.",
```

*Note: `test_every_agent_declines_the_five_things_that_must_not_be_automated`
asserts required tokens appear in each agent's refusal list. Adding to the
universal list satisfies it automatically; check the test still passes.*

**Inventory self-population** (DR-14): extend `app/seed/repository.py` to create
an `ai_system` row per registered agent, so the inventory cannot fall behind the
registry. Add a test asserting the two sets match.

**Effort: 3d.**

### 8.4 WP8 — API

New router `app/api/v1/ai_systems.py`:

| Method | Path | Permission | Notes |
|---|---|---|---|
| `GET` | `/v1/ai-systems` | `data.register.read` | Filter by classification, lifecycle stage, owner |
| `POST` | `/v1/ai-systems` | `compliance.manage` | |
| `GET` | `/v1/ai-systems/{id}` | `data.register.read` | Includes assessments, datasets, invocation volume |
| `PATCH` | `/v1/ai-systems/{id}` | `compliance.manage` | |
| `POST` | `/v1/ai-systems/{id}/impact-assessments` | `compliance.manage` | Creates draft |
| `POST` | `/v1/ai-impact-assessments/{id}:approve` | — | Raises `ai.impact_acceptance`; returns `202` + gate id |
| `GET` | `/v1/ai-systems/{id}/datasets` | `data.register.read` | |
| `POST` | `/v1/ai-systems/{id}/datasets` | `compliance.manage` | |

Extend `/v1/ai-oversight` rather than adding a parallel surface (DR-23).

**Effort: 7d.**

### 8.5 WP9 — Mapping and console

**Cross-framework mapping** (DR-5, DR-6, DR-7). Add entries to
`CONTROL_MAPPINGS`. Map clauses 4–10 to their ISO 27001 equivalents; map A.7 to
27001 A.8.10–A.8.12 and GDPR Art.5; map A.10 to 27001 A.5.19–A.5.22; map A.9 to
GDPR Art.22.

**Do not map A.5 to anything.** An ISO 27001 risk assessment addresses risk to
the organisation; A.5 addresses impact on individuals. A mapping would let a
real gap pass certification, and this is the specific failure DR-7 exists to
prevent.

**Console.** One page at `/ai-management`: inventory by classification, impact
assessments due or overdue, oversight metrics, drift findings. Follow
`app/web/templates/compliance.html` for structure and use the existing palette
— no new CSS variables.

**Effort: 5d.**

---

## 9. Data model

### 9.1 Privacy tables (WP2)

```sql
-- 0006_privacy_extended.sql

CREATE TABLE IF NOT EXISTS domain.privacy_notice (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    name            text NOT NULL,
    audience        text NOT NULL,              -- customers, employees, applicants
    collection_type text NOT NULL,              -- direct (Art.13) | indirect (Art.14)
    version         integer NOT NULL DEFAULT 1,
    body_uri        text,
    published_at    timestamptz,
    published_url   text,
    superseded_at   timestamptz,
    -- The processing activities this notice covers. The reconciliation in
    -- PR-PRV-06/A2 is a set difference between this and the Article 30
    -- register, which is how notice drift becomes detectable.
    covers_processing uuid[] NOT NULL DEFAULT '{}',
    owner_user_id   uuid REFERENCES iam.user_account(id),
    next_review_at  timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      uuid,
    updated_at      timestamptz,
    updated_by      uuid,
    is_deleted      boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS domain.consent_record (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    subject_ref       text NOT NULL,
    processing_record_id uuid REFERENCES domain.processing_record(id),
    purpose           text NOT NULL,
    -- The exact wording presented, not a reference to it. Art.7(1) requires
    -- demonstrating what the subject agreed to, and a pointer to a document
    -- that has since changed does not demonstrate anything.
    wording_presented text NOT NULL,
    notice_version    integer,
    method            text NOT NULL,            -- web_form, verbal, paper, api
    given_at          timestamptz NOT NULL,
    expires_at        timestamptz,
    withdrawn_at      timestamptz,
    withdrawal_method text,
    propagated_at     timestamptz,              -- when downstream recipients were told
    propagation_status jsonb,
    evidence_hash     bytea,
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        uuid
);

CREATE TABLE IF NOT EXISTS domain.controller_arrangement (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    processing_record_id uuid NOT NULL REFERENCES domain.processing_record(id),
    our_role             text NOT NULL,         -- controller | processor | joint_controller
    counterparty         text NOT NULL,
    supplier_id          uuid REFERENCES domain.supplier(id),
    duty_allocation      jsonb NOT NULL DEFAULT '{}',   -- which party discharges which duty
    arrangement_uri      text,
    essence_published_at timestamptz,           -- Art.26(2)
    determined_by        uuid REFERENCES iam.user_account(id),
    determined_at        timestamptz,
    approval_gate_id     uuid REFERENCES core.approval_gate(id),
    created_at           timestamptz NOT NULL DEFAULT now(),
    created_by           uuid,
    is_deleted           boolean NOT NULL DEFAULT false
);
```

Apply the RLS and grant block from section 3.4 to all three.

### 9.2 AI management tables (WP5)

```sql
-- 0007_ai_management.sql

CREATE TABLE IF NOT EXISTS compliance.ai_system (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    system_ref        text NOT NULL,
    name              text NOT NULL,
    purpose           text NOT NULL,
    intended_use      text NOT NULL,
    deployment_context text,
    -- Set where the system is one of this platform's own agents. The loader
    -- populates one row per registry entry, so the inventory cannot fall
    -- behind the registry (DR-14).
    agent_key         text,
    provider_id       uuid REFERENCES config.llm_provider(id),
    model_id          uuid REFERENCES config.llm_model(id),
    data_categories   text[] NOT NULL DEFAULT '{}',
    autonomy_tier     autonomy_tier,
    lifecycle_stage   text NOT NULL DEFAULT 'design',
    classification    text,                     -- as determined by PR-AIM-02
    classification_at timestamptz,
    owner_user_id     uuid REFERENCES iam.user_account(id),
    accountable_role_id uuid REFERENCES iam.role(id),
    status            text NOT NULL DEFAULT 'active',
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        uuid,
    updated_at        timestamptz,
    updated_by        uuid,
    is_deleted        boolean NOT NULL DEFAULT false,
    CONSTRAINT uq_ai_system_ref UNIQUE (tenant_id, system_ref)
);

CREATE TABLE IF NOT EXISTS compliance.ai_impact_assessment (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    ai_system_id     uuid NOT NULL REFERENCES compliance.ai_system(id),
    -- Deliberately NOT a flag on domain.dpia. A DPIA concerns data subjects;
    -- this concerns everyone the system affects, including people about whom
    -- no personal data is held. Conflating them means one is done badly.
    affected_groups  jsonb NOT NULL DEFAULT '[]',
    impacts          jsonb NOT NULL DEFAULT '[]',   -- per group: category, likelihood, severity
    mitigations      jsonb NOT NULL DEFAULT '[]',
    residual_position text,
    residual_material boolean NOT NULL DEFAULT false,
    assessed_by      uuid REFERENCES iam.user_account(id),
    assessed_at      timestamptz,
    approval_gate_id uuid REFERENCES core.approval_gate(id),
    approved_at      timestamptz,
    next_review_at   timestamptz,
    ai_assessment    jsonb,                    -- the model's draft, never the decision
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       uuid,
    is_deleted       boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS compliance.ai_dataset (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         uuid NOT NULL REFERENCES iam.tenant(id) ON DELETE RESTRICT,
    name              text NOT NULL,
    ai_system_id      uuid REFERENCES compliance.ai_system(id),
    provenance        text NOT NULL,
    collection_method text,
    licence_basis     text,
    preparation_steps jsonb NOT NULL DEFAULT '[]',
    known_limitations text,
    bias_assessment   text,
    quality_assessment text,
    retention_rule    text,
    approved_at       timestamptz,
    approval_gate_id  uuid REFERENCES core.approval_gate(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        uuid,
    is_deleted        boolean NOT NULL DEFAULT false
);

-- Every model call becomes attributable to an inventoried system (DR-19).
ALTER TABLE config.model_invocation
    ADD COLUMN IF NOT EXISTS ai_system_id uuid REFERENCES compliance.ai_system(id);

CREATE INDEX IF NOT EXISTS ix_model_invocation_system
    ON config.model_invocation (tenant_id, ai_system_id, created_at);
```

Apply the RLS and grant block to all three new tables.

---

## 10. Non-functional requirements

| # | Requirement |
|---|---|
| NFR-1 | Every new table has `tenant_id`, RLS enabled **and forced**, a policy with `USING` and `WITH CHECK`, and a grant to `craft_app` |
| NFR-2 | Every state-changing endpoint writes an audit entry with before and after state |
| NFR-3 | Every mutating endpoint works correctly under retry — the idempotency middleware covers this automatically; do not bypass it |
| NFR-4 | No new endpoint may be decidable by an agent principal where it represents an approval |
| NFR-5 | New list endpoints paginate at 200 and support a cursor |
| NFR-6 | No secret is ever returned by an API response, including in error messages |
| NFR-7 | AI-generated content is stored in an `ai_*` column and never written directly to a status or decision field |
| NFR-8 | New model-backed activities declare `min_confidence` or inherit their agent's floor |
| NFR-9 | p95 response under 500ms for list endpoints at 10k rows per tenant |
| NFR-10 | The SOP manual regenerates with no change to `docs/generate_sop.py` |

NFR-10 is a real constraint on your design: if a new process needs the generator
changed to render properly, the process is using the repository model in a way
it was not designed for. Reconsider the process before changing the generator.

---

## 11. Test requirements

Every work package ships with tests. Minimum bar per package:

| WP | Must prove |
|---|---|
| WP0 | Every repository gate type has an authority mapping; every clause reference resolves; prefix resolution is *not* used |
| WP1–WP4 | Repository validates; coverage reaches the stated percentage; new gates are human-only; manual regenerates with the new activity count |
| WP5 | Catalogue counts and theme split; unreconciled `source_note` blocks certification readiness on **every** framework |
| WP6 | Impact assessment gate is `irreversible`; retired `AIG` workflows keep their run history |
| WP7 | An agent cannot assess itself — assert at both validator and service level; inventory matches the registry exactly |
| WP8 | Endpoint smoke test covers the new routes; approval returns `202` with a gate id, never `200` |
| WP9 | A.5 is **not** mapped to any ISO 27001 control; console pages render |

**Do not weaken an existing test to make a change pass.** Two in particular:

- `test_unattended_automation_sits_in_the_evidenced_band` — asserts unattended
  automation stays between 15% and 45%. New processes will move it. If it goes
  out of band, the classification is wrong, not the test.
- `test_every_activity_appears` — asserts the manual documents exactly as many
  activities as the platform executes.

---

## 12. Sequencing

```
WP0 ──┬── WP1 ──┬── WP4
      ├── WP2 ──┤
      ├── WP3 ──┘
      └── WP5 ── WP6 ── WP7 ── WP8 ── WP9 ── WP10
```

WP0 blocks everything. WP1–WP4 are independent of WP5–WP9 and can run in
parallel with a second developer. WP7 must land before WP8, because the
self-assessment prohibition changes what the API is allowed to accept.

**Coverage after each phase:**

| After | 27001 | 22301 | GDPR | 42001 |
|---|---|---|---|---|
| WP0 | 95.8% | 75.8% | 77.4% | — |
| WP4 | 99.2% | 78.8% | 80.6% | — |
| WP1 | **100%** | 90.9% | 83.9% | — |
| WP2 | 100% | 90.9% | **100%** | — |
| WP3 | 100% | **100%** | 100% | — |
| WP9 | 100% | 100% | 100% | **100%** |

---

## 13. Definition of done

A work package is done when all of the following hold. Not most of them.

1. `pytest -q` passes, with new tests covering the package's own bar in §11
2. `app.processes.validate()` and `app.agents.registry.validate()` return `[]`
3. `python -m docs.generate_sop > docs/SOP_Manual.md` produces a manual whose
   activity count matches the repository, committed with the change
4. Migrations apply cleanly to a fresh database **and** to a database at the
   previous release
5. The seeder is idempotent — a second run reports zero created and zero
   versioned
6. CI's RLS guard passes: `craft_app` holds neither `rolsuper` nor
   `rolbypassrls`
7. `GET /readyz` returns ready and the endpoint smoke test covers every new route
8. Coverage moves to the figure in §12, verified by
   `GET /v1/processes/coverage`
9. No existing test was weakened or skipped to make it pass

---

## 14. Open questions for the business

Answer before WP5 starts.

1. **Is ISO 42001 certification actually being pursued, or is the AIMS for
   internal assurance and customer questionnaires?** If certification, DR-0
   reconciliation needs a licensed copy purchased now — it is on the critical
   path and cannot be engineered around.
2. **Who is the accountable owner of the AI management system?** The design
   assumes the CISO. If it should be a separate AI governance owner, the role
   must be seeded and the SoD constraints reviewed, because that role would hold
   authority over systems the CISO also owns.
3. **Which agents, if any, are in scope of EU AI Act Article 50 transparency?**
   Those duties took effect on 2 August 2026 and were not deferred. This is a
   legal determination and the platform will not make it.
4. **Does the organisation act as a joint controller anywhere today?** WP2
   builds the machinery either way, but the answer sets whether Art.26 is a
   live gap or a precaution.
5. **What is the connector budget for the next release?** Ten well-chosen
   connectors would move real assurance further than closing the last twenty
   clauses, and the two compete for the same engineering time.
