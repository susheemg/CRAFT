# System Architecture Design Document

**CRAFT — AI-native Governance, Risk and Compliance Platform**
**Version 1.0 · August 2026**

---

## 1. What this system is for

An organisation pursuing ISO 27001, ISO 22301 and UK GDPR compliance has to do
three things continuously: run the processes the standards require, evidence
that it ran them, and be able to prove both to a hostile reader. Most GRC tools
are repositories — they store what you tell them. This one executes the
processes and produces the evidence as a by-product of execution.

The design problem is therefore not "how do we store compliance data" but "how
do we make a system whose records an auditor will believe, while automating
enough of the work to be worth deploying."

Those two goals pull against each other, and most of what follows is about
where the tension was resolved and why.

---

## 2. The four decisions everything else follows from

### 2.1 The audit log is the foundation, not a feature

Every claim the platform makes rests on its records being trustworthy. So the
audit log gets two independent defences, chosen because they fail differently:

**Database-level immutability.** `UPDATE`, `DELETE` and `TRUNCATE` on
`audit.audit_log` raise `insufficient_privilege`. The serving credential holds
only `SELECT, INSERT` regardless of what the triggers do.

**A per-tenant hash chain.** Each entry hashes its canonical content plus its
predecessor's hash. This catches alteration by someone who *can* disable the
trigger — a database owner, a compromised operator, a cloud provider's support
engineer.

Only the second survives privileged access, and privileged access is exactly
the threat model that matters for an audit trail. A control that works only
while nobody has database rights is not a control.

*Rejected:* append-only via application logic alone (defeated by direct
database access); external immutable storage such as a ledger database
(operationally heavy, and the failure mode becomes "the platform and the ledger
disagree", which is worse than either).

### 2.2 Accountability never rests with an agent

The platform is agent-driven. Eleven agents draft assessments, score risks,
process questionnaires and collect evidence. None can approve anything.

This is enforced at four independent points, because a single check is a single
point of failure:

1. The agent registry **refuses to construct** an agent holding a `gate.*`
   permission.
2. Role definition refuses to make an agent-eligible role carry approval authority.
3. Grant-time validation refuses to give an agent an approving role.
4. The gate check refuses a non-human principal regardless of permissions held.

Four checks for one property looks like over-engineering until you consider
what the failure looks like: an AI system that approved its own residual risk
acceptance, discovered during a certification audit. The cost of the redundancy
is a few hundred lines; the cost of the failure is the certification.

The same principle appears in the process repository: validation rejects any
activity naming an agent as accountable, and any gate assigned to an agent.

### 2.3 Automation is bounded by what the evidence supports

Current practice puts reliable agentic automation of repetitive compliance work
at roughly 20–40%, with the boundary set by governance rather than capability.
The categories that do not automate reliably are consistent across sources:
regulatory interpretation, risk acceptance, material stakeholder communication,
contextually complex exceptions, and final sign-off.

The repository was classified activity by activity against that boundary and
lands at **32.4% unattended**. A test asserts it stays within 15–45% and fails
if anyone starts counting AI-drafted steps as automated — which is the specific
dishonesty this metric invites, and the reason vendor automation claims are
usually implausible.

Three automation modes, and the distinction between the middle two is the whole
argument:

| Mode | Meaning | Counted as automated |
|---|---|---|
| `AUTO` / `AUTO_NOTIFY` | The platform completes it unaided | Yes |
| `ASSIST` | AI drafts, a named person owns the output | **No** — a draft still has to be read |
| `GATE` | Stops for a human decision | No |

### 2.4 The process repository is code, not documentation

The 36 processes live in `app/processes` as typed Python data. The engine
executes them, the SOP manual is generated from them, and clause coverage is a
query over them.

This is the decision that makes the rest cohere. A written procedure manual and
the system that executes the procedure drift apart within a quarter, and the
manual is the one an auditor believes. Generating the manual from the
definitions means the documented procedure and the executed procedure are the
same object viewed two ways — they *cannot* disagree.

It also makes structural defects findable. The validator caught four
inconsistencies in the author's own design on first run, including two agents
tiered to act unattended while also routing to a model, which is precisely what
autonomy tiers exist to prevent.

*Rejected:* processes as database rows edited through a UI (no version control,
no code review, no CI validation, and the definitions become undiscoverable);
processes as BPMN (expressive, but the tooling burden exceeds the benefit for
36 linear processes with gates).

---

## 3. Structure

```
                      ┌──────────────────────────────────┐
   Browser ──────────▶│  Console (Jinja2, server-side)   │
                      ├──────────────────────────────────┤
   API client ───────▶│  REST /v1 — 82 endpoints         │
                      ├──────────────────────────────────┤
   MCP client ───────▶│  MCP /mcp — 13 governed tools    │
   (Brata, agents)    └───────────────┬──────────────────┘
                                      │
                      ┌───────────────▼──────────────────┐
                      │  Middleware                      │
                      │  request context · idempotency   │
                      ├──────────────────────────────────┤
                      │  Authorisation                   │
                      │  principal · RBAC · SoD · gates  │
                      ├──────────────────────────────────┤
                      │  Services                        │
                      │  engine · risk · compliance      │
                      │  audit · outbox · brata          │
                      ├──────────────────────────────────┤
                      │  Model gateway                   │
                      │  routing · redaction · budget    │
                      │  two-layer prompt cache          │
                      └───────────────┬──────────────────┘
                                      │
                      ┌───────────────▼──────────────────┐
                      │  PostgreSQL 16                   │
                      │  8 schemas · 51 tables           │
                      │  RLS (forced) · immutable audit  │
                      └──────────────────────────────────┘

   Specification (executed, not described):
     app/processes    36 processes · 148 activities · 30 gates
     app/agents       11 agents · scopes · tiers · refusals
```

Every model call in the platform passes through **one** gateway. That is what
makes redaction, budget, caching and provider governance enforceable rather
than aspirational — there is no second path to a provider.

---

## 4. The data model

Eight schemas, chosen so that access can be granted per schema rather than per
table:

| Schema | Holds | Notable property |
|---|---|---|
| `iam` | Tenants, users, agents, roles, grants, SoD, gate authority | The only schema whose root table has no `tenant_id` |
| `ref` | Framework catalogues | Read-only to the application |
| `core` | Workflows, activities, runs, gates, evidence | Evidence is append-only |
| `domain` | Risks, assets, suppliers, incidents, breaches, DSARs, BIAs, plans | |
| `compliance` | Programmes, implementations, gaps, readiness snapshots | |
| `config` | Providers, models, routes, policies, prompts, invocations | Credentials sealed |
| `audit` | Audit log, chain checks, outbox | `SELECT, INSERT` only for the app |
| `integ` | Connections, webhooks, sync log, idempotency keys | |

### Tenant isolation

Row-level security on 36 tables, **forced**, with `WITH CHECK` so a session
cannot write a row stamped with another tenant's id.

The subtlety that cost the most to get right: PostgreSQL exempts superusers and
table owners from RLS. `FORCE ROW LEVEL SECURITY` closes the owner case;
nothing closes the superuser case except not being one. Hence a dedicated
`craft_app` login role that is `NOSUPERUSER NOBYPASSRLS` and owns nothing, with
DDL running under a separate credential.

Policies are **fail-closed**: an unbound session reads nothing. The earlier
design treated an unset tenant as "match everything", which meant any code path
that forgot to bind read the whole database. There are exactly two legitimate
cross-tenant operations — migrations/seeding, and identity resolution where an
email or token must be matched before its tenant is known — and both go through
a single explicitly named escape hatch.

### One further subtlety

Transaction-local settings are discarded by `COMMIT`, and most handlers commit
mid-request. The tenant binding is therefore held on the session and re-applied
by an `after_begin` listener, with a pool `checkin` hook scrubbing connections
on return. Without the scrub, a session-scoped setting outlives its request and
the next borrower inherits another tenant's context — a cross-tenant read caused
purely by connection reuse.

---

## 5. Authorisation

Four layers, each catching what the others cannot:

**Authentication** resolves a principal from a JWT, an API token or a session
cookie. Permissions are re-resolved from the database on every request rather
than trusted from the token claim, so revoking a role takes effect immediately
rather than at token expiry.

**Permission** — 30 permissions, 11 human roles plus one scoped role per agent.
Default deny; every endpoint declares what it needs.

**Segregation of duties** — mutually exclusive role pairs refused at grant time,
not detected afterwards by a report. Adding a constraint that existing grants
already violate is refused, because a rule that is unenforced from the day it is
written is worse than no rule.

**Gate authority** — deciding a gate requires being human, holding the gate
permission, holding an authorised role, and not having raised the request.

Agents get **one role each** rather than sharing a broad "AI Agent" role. If the
privacy agent is misconfigured, its reach is the privacy agent's reach, not the
audit agent's.

---

## 6. The model gateway

Every call passes through it, in this order:

```
prompt → redact → cache lookup → policy check → provider → ledger
```

**Redaction first**, before the cache key is computed, so a secret cannot reach
a provider *or* be stored locally. Deliberately conservative on the other side:
a rubric full of `[REDACTED]` produces a useless assessment, so ordinary
compliance text is left alone.

**Caching in two layers.** Prompt templates split into a stable `cache_prefix`
(standing instructions, rubric, output contract) and a variable tail. The prefix
is byte-identical across a task class, which is what makes provider prefix
caching engage — on a 93-control ISO 27001 run the rubric is sent once and read
from cache 92 times. Above that sits an exact-match response cache, which
**only stores temperature-zero calls**: a sampled answer is not reproducible,
and replaying one as though it were would misrepresent what the model said.

**Configuration is change-controlled.** Provider, model and routing determine
what data leaves the estate and what it costs. Changing them raises a gate for
a second approver, and the proposer cannot approve.

**Credentials go in and never come out.** Sealed with Fernet, or held as a
vault reference. Only the last four characters are ever returned.

---

## 7. Agent architecture

Eleven agents. Each declares a scope, a named accountable person, an autonomy
tier, the permissions its work needs, and an explicit refusal list.

| Tier | Meaning | Agents |
|---|---|---|
| L1 | Observes and reports | (contextual — resilience drops to L1 during live invocation) |
| L2 | Drafts; a person owns the output | 8 |
| L3 | Acts on reversible things; irreversible raises a gate | 1 |
| L4 | Acts unattended in a bounded, deterministic scope | 2 |

**An agent is tiered to the least deterministic thing it does.** The evidence
agent collects and hashes deterministically but also summarises for reviewers,
which is a judgement — so it is L3, not L4. **An L4 agent calls no model at
all**; the orchestrator routes work according to the process definition and the
reporting agent runs queries and arithmetic. Their outputs are reproducible,
which is why they can run unreviewed.

Escalation thresholds vary by consequence. Privacy escalates below 0.85 and
resilience below 0.90, against 0.75 for ordinary control assessment. Over-
escalation in privacy costs a review; under-escalation costs a notifiable
breach.

Segregation of duties applies to agents too: where the audit agent has drafted
work in a process, its output cannot be the assurance over that same process.

---

## 8. AI governance

A platform that automates compliance with AI and cannot evidence the governance
of that AI is arguing against itself. So the repository includes an AI
governance domain covering the platform's own agents: inventory and risk
classification, human oversight, and performance drift.

**Oversight measurement is the part that matters.** A control test asking "is
there an approval step?" cannot detect the real failure, which is approval that
happens without review. `/v1/ai-oversight` flags a 100% approval rate over a
meaningful sample, and decisions taken within a minute of the gate being raised
— less time than the material takes to read.

**Drift matters because model versions change underneath you.** A provider
upgrading a model is a change to a control. Confidence is baselined per task
class, and a shift triggers revalidation before continued reliance.

### Regulatory context

The EU AI Act position changed materially in the weeks before this version. The
Digital Omnibus on AI (Regulation (EU) 2026/1744) entered into force on 27 July
2026, deferring standalone Annex III high-risk obligations to 2 December 2027
and embedded Annex I systems to 2 August 2028. **Article 50 transparency
obligations were not deferred and took effect on 2 August 2026.**

Two design consequences: the deferral is breathing room for conformity
assessment and human-oversight design rather than a reason to stand down, and
the transparency duties are live now. Whether a given deployment of this
platform is in scope of any of it is a legal determination, which is why the
regulatory watch agent presents status and dates and never concludes
applicability.

---

## 9. Reliability

**Transactional outbox instead of Kafka.** Events publish inside the
transaction that caused them, so an event cannot exist for a change that rolled
back. Delivery is a three-phase relay: claim with `FOR UPDATE SKIP LOCKED` and
commit, deliver holding no transaction, record outcomes.

`SKIP LOCKED` is what makes concurrent relays safe — and the deployment runs two
uvicorn workers, so it is not hypothetical. Holding a transaction across
outbound HTTP was the other half of the same defect: one slow endpoint held row
locks and blocked vacuum for as long as the remote server took.

Delivery is **at-least-once**. Every event carries a stable id; receivers
deduplicate. Exactly-once across a network boundary is not available, and
claiming it would be dishonest.

**Idempotency** as middleware rather than per-endpoint, so a new endpoint cannot
forget to opt in. Failed requests release their key, so a client can correct the
payload and retry with the same one.

---

## 10. Declared deviations from the design dossier

Each is deliberate and reversible on request.

| Deviation | Reason |
|---|---|
| Single FastAPI service, not React + NestJS + Python + Kafka + Kubernetes | The dossier stack is not deployable on Render, which was a stated requirement. The control design is preserved; the runtime topology is not. |
| Transactional outbox instead of Kafka | One fewer system to operate, and the ordering guarantee needed is per-tenant, which the outbox provides. |
| Purpose-built migration runner, not Alembic | The schema needs triggers, RLS policies, roles and grants. Applied files are checksummed and cannot be edited. |
| Local password login alongside OIDC hooks | The platform must be able to bootstrap before an identity provider is federated. Disable with `CRAFT_ALLOW_LOCAL_LOGIN=false`. |
| No pgvector or RAG | Scoped out to control the build. The schema leaves room. |
| Bedrock via an OpenAI-compatible gateway, not native SigV4 | Avoids an AWS-specific signing path in the provider layer. |
| Permissive email validation | Strict RFC validators reject `.local` and `.internal`, which on-premise deployments use for internal accounts. |
| Brata contract assumed | Brata appears nowhere in the 117-page dossier. Endpoints and field names are configuration, not code. |

---

## 11. What this architecture does not do

Stated plainly, because an architecture document that lists only strengths is
not useful.

- **Continuous control monitoring needs connectors.** PR-CMP-02 defines the
  process and the platform runs it, but making a control machine-testable
  requires a connector to the source system, and those are per-environment work.
  Without them the process degrades to attestation, which is honest but not the
  point.
- **No live provider call is tested.** Adapters are written against documented
  APIs and exercised through the gateway, but nothing in the suite makes a
  billed call.
- **Single-region, single-database.** No multi-region failover, and the
  throughput ceiling is unmeasured. For a single-tenant compliance platform this
  is proportionate; for a multi-tenant SaaS it would not be.
- **The control catalogue paraphrases.** Titles are not reproduced verbatim from
  the licensed standards. A `source_note` flags where reconciliation against
  licensed copies is required before certification use.
- **Agent tool execution is specified, not implemented.** The registry defines
  each agent's tools and scope, and the gateway routes their model calls, but
  the autonomous execution loop that would let an agent chain tools unattended
  is future work. Current agents act within workflow activities, one step at a
  time. This is a deliberate sequencing choice: the governance around agent
  action was built first, because building it afterwards means retrofitting
  controls onto a system that already acts.

---

## 12. Evidence that the architecture holds

137 tests against real PostgreSQL, connecting as the non-superuser application
role. The properties above are asserted, not described:

- The audit chain detects tampering **performed by a database owner with the
  trigger disabled**
- A second tenant's data is invisible on read and rejected on write
- The registry **refuses to construct** an approving agent
- Two concurrent relays never claim the same event
- Unattended automation stays within the band the evidence supports
- Every endpoint executes — added after four production faults reached earlier
  builds purely by never having been called
