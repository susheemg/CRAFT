# Release notes — application security and AI management

**CRAFT 1.1 · ISO/IEC 27034-1:2011 / -2:2015 and ISO/IEC 42001:2023**

---

## What this release adds

Two standards that the previous build did not model, integrated into the
existing engine rather than bolted alongside it.

**ISO/IEC 27034 — application security.** An Organization Normative Framework
built iteratively, an Application Security Control library where every control
has both a security activity and an independent verification measurement, four
levels of trust with a floor a project team cannot remove, and a per-application
Application Normative Framework whose actual level of trust is computed from
measurement records rather than asserted.

**ISO/IEC 42001 — AI management.** All 27 clauses and all 38 Annex A controls
across nine objectives, an AI system inventory discovered from the live model
gateway, AI system impact assessments that cannot be approved without a named
human, data provenance per dataset, and agent charters that make a bounded
mandate a database record rather than a property of the code.

### Numbers

| | Before | After |
|---|---|---|
| Tests | 142 | **198** |
| Processes | 36 | **55** |
| Activities | — | 243 (32.9% unattended) |
| Domains | 10 | **11** (added `APS`) |
| Agents | 11 | **16** |
| Frameworks | 3 | **4** |
| Catalogue controls | 182 | **247** |
| Tables | 51 | **74** |
| Migrations | 0005 | **0006** |

The unattended automation rate moved from 32.4% to 32.9% and remains inside the
15–45% band the suite asserts. It is derived by classifying each activity; ASSIST
is still not counted as automation.

---

## Defects found and fixed in the existing build

Three, all pre-existing, all surfaced by standing the build up against a real
split-credential PostgreSQL before any new code was written.

**1. Reference-catalogue seeding could not work with separated credentials.**
`ref` is `SELECT`-only for the serving role, by design and by migration 0003 —
but the seeder wrote the framework catalogue on that connection. This works on a
single-credential managed Postgres and fails immediately in the split-credential
configuration the code itself recommends. Added `owner_session_scope()` in
`app/db.py` and routed reference seeding, including the new life cycle reference
model, through the owning credential.

**2. A test fixture named an agent that no longer existed.** `tests/conftest.py`
selected the agent identity `compliance-analyst`, which is not in the registry.
Every test in `TestAgentAccountability` therefore *errored* during setup rather
than running — a control test that had silently stopped being one. The fixture
is now keyed off `AGENT_BY_KEY` with an assertion, so a future rename fails
loudly instead of quietly disabling the checks.

**3. Production had no guardrail on the database URL.** Found by a Render deploy
that crash-looped against `localhost:5432`. The immediate cause was an unset
`CRAFT_DATABASE_URL`, which is configuration — but `get_settings()` guards
`CRAFT_SECRET_KEY` and `CRAFT_ENCRYPTION_KEY` in production and did not guard
the database URL, the one setting whose default is silently *plausible*. The
service fell back to the development default and failed two hundred traceback
lines away from its cause. Production now refuses to start on the development
default, with a message naming the variable and the likely Render cause, and
`lifespan` logs the host it tried before re-raising. The guard catches an unset
variable rather than forbidding a host, so a sidecar or socket-proxy deployment
against localhost still works.

The first version of that guard was itself wrong, and the live logs proved it:
it was gated on `CRAFT_ENVIRONMENT == "production"`, but `CRAFT_ENVIRONMENT` is
one of the variables that goes missing when a service is misconfigured, so the
settings fell back to `"development"` and the guard stayed silent through the
exact failure it was written for. A guard against misconfiguration cannot depend
on a variable that is part of the misconfiguration. It now keys off the hosting
platform's own variables — `RENDER`, `DYNO`, `KUBERNETES_SERVICE_HOST` and
similar — which no developer sets by hand. See
`docs/Render_Deployment_Troubleshooting.md`.

**4. An invented permission name.** The first draft of the new router guarded
its endpoints with `compliance.read`, which does not exist in the permission
catalogue. Caught by the endpoint tests: the endpoints would have been
unreachable for every role. Corrected to `compliance.manage`.

---

## Defects found in the new work, by the new tests

Worth listing separately, because they are the reason the tests exist.

**A level-zero application was reporting level three.** The level-of-trust
computation started every level optimistic and only marked a level unsatisfied
when a control in the ANF failed. An ANF built at level zero contains no
level-three controls, so nothing could fail them — an absence of evidence read
as evidence of assurance. Fixed by capping the actual level at the highest level
whose mandatory controls are actually present in the ANF.

**Level one required nothing level zero did not.** Found when the corrected
computation still reported level one for a level-zero framework, which turned
out to be correct: every control level one requires is also a level-zero
control, so the two levels are indistinguishable. The arithmetic was right and
the level design was wrong. Rather than adjust the assertion, added
`onf_level_design_issues()`, surfaced it on `GET /v1/appsec/onf`, and left a
test that will start failing when the seed is corrected — with a comment saying
to remove it then. PR-APS-04 owns closing it.

**Three instances of over-mapping.** `PR-APS-07` claimed ISO/IEC 42001 6.1.2 and
8.2; `PR-APS-01` and `PR-APS-08` claimed 6.1.3. An application security risk
assessment asks what an attacker could do; an AI risk assessment asks what the
system could do to people, and the ASC library is not the AI Statement of
Applicability. All three claims removed, and
`test_ai_specific_clauses_are_never_inherited_from_another_standard` now fails
if they come back.

**Four uncovered ISO/IEC 42001 clauses.** 4.3, 4.4, 5.3 and 7.5 were discharged
by no process. Closed at source with a new scope-definition activity on
`PR-AIG-04` and clause claims on `PR-AIG-09` and `PR-AIG-10`, not by relaxing
the coverage test.

---

## What is enforced where

The distinction matters: a control implemented only in a service method is one
refactor from gone.

**Database — cannot be bypassed by application code**

| Rule | Mechanism |
|---|---|
| A measurement cannot be recorded by whoever performed the activity | `compliance.enforce_asc_sod` trigger |
| An agent cannot measure a control marked human-verifier-only | same trigger |
| An agent-written record cannot claim human attestation | `ck_asc_evidence_agent_not_attested` |
| A level-zero control cannot be waived | `ck_anf_asc_level_zero_locked` |
| Exactly one level zero per ONF iteration | `uq_trust_level_one_zero` partial index |
| An impact assessment cannot be approved without a named human | `ck_ai_impact_human_approval` |
| An agent-drafted assessment must be labelled as such | `ck_ai_impact_agent_draft_labelled` |
| A Statement of Applicability exclusion needs a reason | `ck_soa_exclusion_reasoned` |
| Tenant isolation on all 22 new tenant tables | RLS with `FORCE`, matching migration 0002 |

**Repository validators — fail at import, not at run time**

Agents assigned to unknown processes or unrouted task classes; an L4 agent that
routes to a model; an agent named as accountable; a gate performed by an agent.

**Process — requires a human**

Every gate. `PR-APS-05` A3 and A4, `PR-APS-10` A2, and `PR-AIG-07` A3 are
explicitly performed by people: an agent auditing the controls that bound agents
is the clearest case where fluency would be mistaken for assurance.

---

## The two standards meet in exactly one place

`PR-APS-06` activity A4. An application flagged `is_ai_system` creates the AI
system register entry and hands off to the AI governance track, and runs both.
It does not run one and claim the other.

The failure mode that junction exists to catch is an AI system with no owning
application: no ANF, so no control set, so nothing measuring it.
`GET /v1/ai/systems` reports those in an `unowned` list rather than leaving them
to be noticed.

---

## Shared clause reuse

ISO 22301, ISO/IEC 27001 and ISO/IEC 42001 share the Annex SL structure, so
`_inherit_shared_clauses` in `app/processes/__init__.py` extends coverage across
them for 19 genuinely common clauses. Eight are on a `NEVER_INHERITED` list with
a reason each — 4.3 because an AI scope that does not name the AI systems draws
a nonconformity however well 4.1 is evidenced; 5.2 because the AI policy is not
the information security policy; 6.1.2, 6.1.3, 6.1.4, 8.2, 8.3 and 8.4 because
the risk questions are different questions.

Inheritance never manufactures coverage the source lacked. ISO/IEC 27001 5.3,
6.3, 7.1, 7.4 and 7.5 are discharged by no process in this build — a
pre-existing gap tracked in `Coverage_Improvement_Plan.md` — and nothing
inherited them. There is a test asserting exactly that.

---

## Known limitations, stated plainly

**Certification against ISO/IEC 42001 is blocked, deliberately.** Every
catalogue entry for it is a CRAFT paraphrase. `RECONCILED` in
`app/seed/catalogue_iso42001.py` is `False`,
`GET /v1/ai/certification-block` reports the block with its reason, and a test
asserts the flag stays false. Certifying against a paraphrase is not
certification. Reconcile line by line against a licensed copy, record the
attestation, then flip the flag.

**Level one of the shipped ONF is indistinguishable from level zero.** Reported
by the API and covered by a test that will fail once fixed.

**Three task classes still have no prompt template** — `classification`,
`dpia_drafting` and `policy_drafting`. Pre-existing; the two new classes
(`asc_design`, `impact_assessment`) ship with templates.

**No agent charters are seeded yet.** `config.agent_charter`,
`agent_tool_grant` and `agent_budget_ledger` exist and are enforced by
`PR-AIG-10`'s gate, but populating them from the registry, and wiring the kill
switch and budget ledger into the gateway's per-call path, is the next piece of
work. Until then the charter table is a schema, not a running control.

---

## Upgrading

```bash
python -m app.migrate          # applies 0006, idempotent
python -m pytest               # 198 tests
python docs/generate_sop.py > docs/SOP_Manual.md
```

Migration 0006 is additive: no table is altered or dropped. It applies cleanly
twice, verified.
