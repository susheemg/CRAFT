# CRAFT

An AI-native governance, risk and compliance platform. It runs the ISO 27001,
ISO 22301 and UK GDPR compliance journeys end to end — controls, evidence,
gaps, risk, incidents, continuity and subject requests — with an immutable audit
trail, human approval gates on the decisions that need them, and a governed
gateway for whichever AI providers you choose to connect.

- **API**: `/docs` (OpenAPI), 82 endpoints under `/v1`
- **Console**: server-rendered, no build step
- **MCP server**: `/mcp` (JSON-RPC 2.0), for Brata or any other MCP client
- **Health**: `/healthz` liveness, `/readyz` readiness

---

## Documentation

| Document | For |
|---|---|
| `docs/SOP_Manual.md` | The 36 processes, generated from `app/processes` so it cannot drift from what executes |
| `docs/Technical_Manual.md` | Deploying, operating, configuring, troubleshooting |
| `docs/System_Architecture_Design.md` | Why the system is shaped this way, and what it deliberately does not do |
| `docs/Coverage_Improvement_Plan.md` | The 20 uncovered clauses, and the nine processes that close them |
| `docs/ISO42001_Design_Requirements.md` | Specification for adding ISO/IEC 42001 as a fourth certifiable framework |
| `docs/Functional_Technical_Design_R2.md` | Build specification for release 2.0 — hand this to the development team |

---

## Three properties worth knowing before you build on it

**The audit log cannot be edited.** Entries are hash-chained per tenant, and the
database refuses `UPDATE`, `DELETE` and `TRUNCATE` on the table. Those are two
independent defences, because they fail differently: the trigger stops the
ordinary mistake and the ordinary insider; the hash chain catches alteration
*even by someone who can disable the trigger*. `GET /v1/audit/verify` recomputes
the chain and names the exact sequence number of any break. The test suite
proves this by disabling the trigger, rewriting a row as the database owner, and
confirming the verifier still finds it.

**Retries are safe.** Send an `Idempotency-Key` header on any mutating request
and the same key with the same body returns the original response without
re-running the handler; the same key with a *different* body is refused rather
than replayed. Two simultaneous identical requests race on a unique constraint
and one is told the work is in flight. Failed requests release their key, so a
client can correct the payload and retry with the same one.

**Approvals belong to people.** Agent principals structurally cannot hold
approval authority — refused at role definition, at grant time, and again at the
gate. Nobody approves their own request. An action that needs a decision returns
`202` with a gate identifier rather than proceeding. No MCP tool can approve
anything, and there is no tool that could.

**Readiness is not a self-assessment score.** A control claimed to be operating
with no current evidence scores 70% of one that is evidenced, because an auditor
will not accept an unevidenced claim either. Certification readiness is judged
separately and more strictly: one unimplemented mandatory clause, one open
high-severity gap, or one exclusion without a justification blocks it, whatever
the headline percentage says.

---

## Deploying to Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository. `render.yaml`
   provisions the web service and a PostgreSQL 16 database together.
3. Set `CRAFT_ENCRYPTION_KEY` before the first deploy:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   **Back this up outside Render.** Every stored AI provider credential is sealed
   with it. Lose it and those credentials become unreadable and must be
   re-entered by hand.
4. Deploy. Migrations run in `preDeployCommand`, before any instance takes
   traffic, so a schema change cannot race a starting instance.
5. Read the first-boot log for the generated bootstrap password. It is printed
   once and never again. Sign in at `/login` and change it.

### The one thing to fix after it is running

Render's managed PostgreSQL issues a single database user, and that user owns
the schema. Migration 0002 sets `FORCE ROW LEVEL SECURITY`, so tenant isolation
does apply to an owner — but that owner can still alter the schema and disable
triggers, which is more authority than a request handler needs.

Migration 0003 creates a `craft_app` login role that is `NOSUPERUSER
NOBYPASSRLS`, owns nothing, cannot change the schema, and holds only
`SELECT, INSERT` on the audit log. To use it, set:

```
CRAFT_DATABASE_URL          = postgresql+psycopg://craft_app:<CRAFT_APP_DB_PASSWORD>@<host>/craft
CRAFT_MIGRATION_DATABASE_URL = <the owner connection string Render gave you>
```

This is worth doing. It is the difference between "the application is not
supposed to read across tenants" and "the application cannot read across
tenants."

### Anywhere else

```bash
docker build -t craft .
docker run --rm --env-file .env craft python -m app.migrate   # as the owner
docker run -p 8000:8000 --env-file .env craft
```

---

## Running locally

```bash
createdb craft && psql craft -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;'
pip install -r requirements-dev.txt
cp .env.example .env          # then edit it
python -m app.migrate
uvicorn app.main:app --reload
pytest -q                     # 142 tests
```

---

## Connecting an AI provider

The platform works with no provider connected — registers, workflows, gates,
evidence and reporting all function. A provider adds the drafting and assessment
steps.

Seven provider types are supported: Anthropic, OpenAI, Azure OpenAI, Google,
Bedrock (through an OpenAI-compatible gateway), Ollama, and any other
OpenAI-shaped endpoint. Configure through `/v1/admin/llm/providers` or the **AI**
page in the console.

Credentials go in and never come out. A key is sealed with Fernet on receipt and
only the last four characters are ever returned, so an operator can confirm
which key is in place without being able to read it. Prefer `vault_ref` where you
have a secret manager: `env:ANTHROPIC_API_KEY` or `file:/run/secrets/api-key`
keeps the secret out of the database entirely.

Changing production routing raises a gate for a second approver. The person who
proposes a configuration cannot activate it — that combination determines what
data leaves your estate and what it costs.

### Token economy

Two layers of caching, both measured rather than estimated. Every figure on the
AI console comes from the invocation ledger.

*Prefix caching.* Prompt templates are split into a stable `cache_prefix` — the
assessor's standing instructions, the scoring rubric, the output contract — and a
variable tail carrying the specific control. The prefix is byte-identical on
every call in a task class, which is what lets Anthropic's explicit
`cache_control` breakpoints and OpenAI's automatic prefix cache engage. On a
93-control ISO 27001 assessment run, the rubric is sent once and read from cache
92 times.

*Housekeeping.* Expired cache entries and spent idempotency keys are collected
by the relay on a schedule; neither table grows without bound.

*Response caching.* An exact-match cache keyed on model, prefix, system prompt,
prompt, temperature, max tokens and JSON mode. It only stores calls made at
temperature zero: a sampled answer is not reproducible, and replaying one as
though it were would misrepresent what the model actually said. Changing the
model behind a task class invalidates its cached answers, so a superseded model's
conclusions are never served as current.

---

## Integrating with Brata

**Brata does not appear anywhere in the design dossier.** I have assumed it is an
external system of yours and built an adapter against conventional REST and MCP
patterns, with every endpoint path and field name in configuration rather than
code. Aligning it to Brata's real contract is a configuration change, not a
release.

Both directions are supported:

*CRAFT calling Brata.* Create a connection at
`POST /v1/integrations/connections` with `transport: rest` or `transport: mcp`.
Four auth schemes: bearer, API key header, OAuth2 client credentials, or none.
Override the defaults in `sync_config`:

```json
{
  "endpoints": { "risks": "/api/v2/risk-items" },
  "field_map": { "title": "riskName", "residual_score": "netScore" }
}
```

Pulled records are deduplicated by lineage, so re-running a pull updates what is
already here rather than creating a second copy. Every call is written to
`integ.sync_log`.

*Brata calling CRAFT.* Point an MCP client at `/mcp` with a bearer token from
`POST /v1/auth/tokens`. Thirteen tools; each declares the permission it requires,
and the manifest only advertises tools the caller could actually use. A token
never carries more authority than the principal behind it.

Webhooks are the third option — 19 topics, signed with HMAC-SHA256 over the raw
body. Verify the signature before trusting a payload.

---

## Declared deviations from the dossier

Each of these is a deliberate choice, not an omission. Say the word and any of
them can be reversed.

**The stack.** The dossier specifies React + NestJS + Python + Kafka +
Kubernetes. That is not deployable on Render, which you asked for. This is a
single FastAPI service with a server-rendered console, a transactional outbox in
place of Kafka, and optional Redis. The control design is preserved intact; the
runtime topology is not. If you would rather have the original stack, the
Render requirement has to go.

**Migrations.** A purpose-built forward-only runner rather than Alembic. The
schema needs triggers, RLS policies, roles and grants, which Alembic expresses
awkwardly. Applied files are checksummed; if one changes after being applied the
runner refuses to continue.

**Local password login** is retained alongside OIDC hooks, so the platform can be
stood up before an identity provider is federated. Disable it with
`CRAFT_ALLOW_LOCAL_LOGIN=false` once yours is.

**No pgvector or RAG.** Scoped out to control the build. The schema leaves room.

**Bedrock** is reached through an OpenAI-compatible gateway rather than native
SigV4 signing.

**Email validation is deliberately permissive.** Strict RFC validators reject
reserved top-level domains such as `.local` and `.internal`, which is exactly
what on-premise deployments use for internal accounts.

**Readiness is reported to one decimal place.** With 118 controls, a single
control moves the figure by well under a point, so the displayed percentage
rounds. The underlying weighting is exact; only the display rounds.

---

## What the tests actually prove

142 tests against a real PostgreSQL instance — not SQLite, not mocks. The
properties most worth testing here are database behaviour: row-level security,
append-only triggers, native enums, the advisory lock behind audit sequencing. A
suite that swapped the engine out would prove nothing about what ships.

The suite connects as `craft_app`, not as the owner. This matters: run it as a
superuser and every isolation test passes while proving nothing, because
PostgreSQL exempts superusers from row-level security. CI asserts that
`craft_app` holds neither `rolsuper` nor `rolbypassrls` before the tests run.

Covered: audit immutability and tamper detection under a bypassed trigger; tenant
isolation on read and on write; agent non-accountability; requester–approver
separation; segregation of duties at grant time; the ISO 27001 catalogue
(93 Annex A controls, split 37/8/14/34) and Statement of Applicability
completeness; the evidence discount; prompt-cache key separation and hit
accounting; redaction; MCP authorisation; idempotent retries; and concurrent
outbox claiming.

Every endpoint is also called at least once by a smoke test, with a principal
holding every role so authorisation cannot mask a broken handler. That test
exists because three faults reached an earlier build purely by never having been
executed — a model attribute that did not exist, a column that was never
created, and a renamed field. All three were one-line mistakes that any single
call would have caught, and none were caught by tests exercising the services
underneath.

### Known limitations, stated plainly

- **Live provider calls are untested.** Adapters are written against each
  provider's documented API and exercised through the gateway, but no test in
  this suite makes a real billed call. Use `POST /v1/admin/llm/providers/{id}:test`
  after connecting one — it makes a genuine minimal call, which is the only way
  to know the credential, endpoint and model name are all correct together.
- **The Brata contract is assumed**, as described above.
- **Single-region.** No multi-region failover, and no load testing at scale.
  Concurrent relays are safe (see below), but the throughput ceiling is
  unmeasured.
- **The workflow engine ships six starter workflows**, not the dossier's 28. The
  engine is general and the remaining workflows are data, not code.
