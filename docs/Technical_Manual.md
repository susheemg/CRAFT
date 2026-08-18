# CRAFT Technical Manual

**Version 1.0 · August 2026**

For the people who deploy, operate and extend the platform. The System
Architecture Design Document explains *why* the system is shaped as it is; this
explains how to run it.

---

## 1. What you are deploying

A single Python 3.12 FastAPI service backed by PostgreSQL 16. One process, one
database, no message broker, no separate frontend build. It serves:

| Surface | Path | Purpose |
|---|---|---|
| REST API | `/v1` | 82 endpoints, OpenAPI at `/docs` |
| Console | `/` | Server-rendered, seven pages |
| MCP server | `/mcp` | JSON-RPC 2.0, 13 governed tools |
| Health | `/healthz`, `/readyz` | Liveness and readiness |

Run it with two uvicorn workers on a 512 MB instance. That is sufficient for a
single-tenant deployment and is what `render.yaml` specifies.

---

## 2. The database credentials, and why there are two

This is the single most consequential configuration decision, and getting it
wrong disables tenant isolation silently.

PostgreSQL exempts **superusers** and **table owners** from row-level security.
A platform that connects as either has RLS policies that are never consulted.
Nothing errors; the policies simply do not apply, and the console reports
isolation as enabled while it is not.

So there are two credentials:

| Variable | Role | Rights |
|---|---|---|
| `CRAFT_DATABASE_URL` | Serves requests | `craft_app`: not a superuser, not an owner. Cannot alter schema, disable triggers, or `UPDATE`/`DELETE` the audit log. |
| `CRAFT_MIGRATION_DATABASE_URL` | Runs DDL | The schema owner. Used by `python -m app.migrate` only. |

Migration `0003_app_role.sql` creates `craft_app` with the password in
`CRAFT_APP_DB_PASSWORD`. Where your provider gives you only one credential,
`CRAFT_MIGRATION_DATABASE_URL` falls back to `CRAFT_DATABASE_URL` and the
platform still works — but the serving credential can then alter the schema,
which is more authority than a request handler needs. Separate them if you can.

**Verify it took effect:**

```sql
SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = 'craft_app';
-- must return f
```

CI asserts this before the test suite runs, because a suite run as the owner
passes every isolation test while proving nothing.

---

## 3. Configuration

All settings take the `CRAFT_` prefix and come from the environment or `.env`.

### Required in production

| Variable | Notes |
|---|---|
| `CRAFT_SECRET_KEY` | JWT signing. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CRAFT_ENCRYPTION_KEY` | Fernet key sealing provider credentials. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `CRAFT_DATABASE_URL` | The serving credential. See section 2. |

The application refuses to start in production with development defaults for
either secret. That refusal is deliberate: a platform holding sealed API
credentials that boots with a known key is worse than one that will not boot.

**Back up `CRAFT_ENCRYPTION_KEY` outside your hosting provider.** Losing it
makes every stored AI provider credential unreadable, and they must be
re-entered by hand.

### Behaviour

| Variable | Default | Effect |
|---|---|---|
| `CRAFT_AUTO_MIGRATE` | `true` | Migrate at start-up. Set `false` on Render, where `preDeployCommand` owns it. |
| `CRAFT_AUTO_SEED` | `true` | Load reference data and the process repository. Idempotent; safe to leave on. |
| `CRAFT_ENABLE_OUTBOX_RELAY` | `true` | Webhook delivery and housekeeping. Safe with multiple workers. |
| `CRAFT_ALLOW_LOCAL_LOGIN` | `true` | Set `false` once an identity provider is federated. |
| `CRAFT_LLM_CACHE_ENABLED` | `true` | Response caching for deterministic calls. |

---

## 4. First boot

1. `python -m app.migrate` with the owning credential.
2. Start the service. Seeding runs automatically and is idempotent.
3. **Read the log for the generated bootstrap password.** It is printed once
   and never again. Sign in at `/login` and change it.

Seeding creates: 30 permissions, 11 human roles, the segregation-of-duties
constraints, the gate authority map, three framework catalogues (182 controls),
36 workflows from the process repository, and 11 agent principals each with its
own scoped role.

The bootstrap account holds Platform Admin and Security Admin only. It
deliberately carries **no business gate authority** — it configures the
platform, it does not approve anything within it.

---

## 5. Migrations

A purpose-built forward-only runner, not Alembic. The schema needs triggers,
RLS policies, roles and grants, which Alembic expresses awkwardly.

```bash
python -m app.migrate
```

`SQLAlchemy create_all` runs first (idempotent), then numbered SQL files from
`db/migrations/` in order. Each applied file is checksummed into
`audit.schema_migration`; **if an applied file changes, the runner refuses to
continue** rather than leaving environments silently divergent.

| Migration | What it does |
|---|---|
| `0001_controls` | Audit immutability triggers, RLS policies, four database roles, grants |
| `0002_rls_hardening` | `FORCE ROW LEVEL SECURITY`, fail-closed policies with `WITH CHECK`, `TRUNCATE` block, evidence immutability |
| `0003_app_role` | The `craft_app` login role and least-privilege grants |
| `0004_outbox_concurrency` | Claim columns and per-event backoff for concurrent relays |
| `0005_invocation_confidence` | Model confidence as a first-class measurement for AI oversight and drift |

To add one: create `db/migrations/00NN_name.sql`, make it idempotent
(`IF NOT EXISTS`), and run the runner. Never edit an applied file.

---

## 6. The audit log

Two independent defences, because they fail differently.

**The database refuses mutation.** `UPDATE`, `DELETE` and `TRUNCATE` on
`audit.audit_log` raise `insufficient_privilege`, and `craft_app` holds only
`SELECT, INSERT` regardless. This stops the ordinary mistake and the ordinary
insider.

**The hash chain detects it anyway.** Each entry hashes its content plus its
predecessor's hash, per tenant. This catches alteration by someone who *can*
disable the trigger — which is the only defence that survives database-owner
access, and the one that matters under audit.

```bash
curl -H "Authorization: Bearer $TOKEN" https://your-host/v1/audit/verify
```

An intact result means nothing has been altered, deleted or spliced since it
was written. A break names the exact sequence number: entries before it remain
sound, everything from it is unverified, and you are investigating direct
database access.

The test suite proves this by disabling the trigger, rewriting a row as the
owner, and confirming the verifier still finds it.

---

## 7. Connecting an AI provider

The platform works with none connected. Registers, workflows, gates, evidence
and reporting all function; a provider adds drafting and assessment.

Seven provider types: Anthropic, OpenAI, Azure OpenAI, Google, Bedrock (through
an OpenAI-compatible gateway), Ollama, and any other OpenAI-shaped endpoint.

```bash
POST /v1/admin/llm/providers
{ "name": "Anthropic", "kind": "anthropic", "vault_ref": "env:ANTHROPIC_API_KEY" }
```

Prefer `vault_ref` (`env:NAME` or `file:/path`) where you have a secret manager;
it keeps the credential out of the database entirely. Otherwise `api_key` is
sealed with Fernet on receipt. **Credentials never come back out** — only the
last four characters are ever returned, so an operator can confirm which key is
in place without being able to read it.

Then add a model, point a route at it, and test:

```bash
POST /v1/admin/llm/providers/{id}:test
```

That makes a real minimal call. It is the only way to know the credential,
endpoint and model name are all correct *together*.

### Two-person configuration control

`POST /v1/admin/llm/versions` captures the live configuration and raises a gate
for a second approver. The proposer cannot approve. That combination determines
what data leaves your estate and what it costs, so no one person changes it
alone.

### Token economy

Two layers, both measured from the invocation ledger rather than estimated.

*Prefix caching.* Prompt templates split into a stable `cache_prefix` — standing
instructions, scoring rubric, output contract — and a variable tail. The prefix
is byte-identical across a task class, which is what lets Anthropic's explicit
`cache_control` breakpoints and OpenAI's automatic prefix cache engage. On a
93-control ISO 27001 run the rubric is sent once and read from cache 92 times.

*Response caching.* Exact-match on model, prefix, system, prompt, temperature,
max tokens and JSON mode. **Only temperature-zero calls are cached** — a sampled
answer is not reproducible, and replaying one as though it were would
misrepresent what the model said. Changing the model behind a task class
invalidates its cached answers.

Monitor at `GET /v1/admin/llm/cache` and `/spend`.

---

## 8. Operating the outbox

Events are published inside the transaction that caused them, then delivered by
a relay. Three phases, with no transaction held across the network:

1. **Claim** with `FOR UPDATE SKIP LOCKED`, commit.
2. **Deliver** over HTTP, holding nothing.
3. **Record** outcomes, release the claim.

`SKIP LOCKED` is what makes multiple relays safe — two uvicorn workers step past
each other's locked rows rather than both delivering. Without it, every
subscriber receives every event once per worker.

Delivery is **at-least-once**. Every event carries a stable id; receivers should
deduplicate on it.

| Situation | Behaviour |
|---|---|
| Delivery fails | Per-event exponential backoff, 30s doubling to 1h |
| 10 consecutive failures on a subscription | Suspended, logged |
| Worker dies mid-delivery | Claim expires after 5 minutes, another relay takes it |
| 10 delivery attempts | Dead-lettered |

Inspect with `GET /v1/integrations/outbox`; requeue with
`POST /v1/integrations/outbox/{id}:replay`.

The relay also runs housekeeping every 60 cycles: expired cache entries and
spent idempotency keys. Both tables otherwise grow forever.

---

## 9. Idempotency

Send `Idempotency-Key` on any mutating request.

| Case | Result |
|---|---|
| Same key, same body | Original response replayed, `Idempotent-Replay: true` |
| Same key, different body | `422 idempotency_key_reused` |
| Two simultaneous identical requests | One runs, the other gets `409 idempotency_in_progress` |
| Request failed | Key released, so a corrected retry with the same key runs |

Keys are scoped by tenant and retained 24 hours. Implemented as middleware, so
a new endpoint cannot forget to opt in.

---

## 10. The process repository

The 36 processes in `app/processes` are the specification the engine executes,
not a document about it.

```
app/processes/__init__.py    Domain, Process, Activity types; validation; coverage
app/processes/governance.py  GOV, RSK, CMP
app/processes/operations.py  PRV, SEC, TPR, RES, PPL, CHG, AIG
app/agents/registry.py       11 agents with scopes, tiers, refusals
app/seed/repository.py       Materialises both into the database
```

### Changing a process

1. Edit the definition.
2. Run `python -c "from app.processes import validate; print(validate())"` —
   must be empty.
3. Restart, or run the seeder. A changed definition **supersedes** its
   predecessor and gets a new version rather than being edited in place, because
   runs already executed against the old definition and an auditor will ask which.
4. Regenerate the manual: `python -m docs.generate_sop > docs/SOP_Manual.md`.

The loader **refuses to load a repository that does not validate**. A workflow
referencing an agent that cannot perform it would otherwise fail at the moment
someone depends on it.

### What validation enforces

- No activity makes an agent accountable
- No gate is assigned to an agent
- Every agent-assisted step names an agent that exists and is routed for its task class
- Every process discharges at least one clause
- L4 (unattended) agents call no model

---

## 11. AI governance

`GET /v1/ai-oversight` answers the question an AI regulator or assurance
questionnaire actually asks: is human oversight real, or nominal?

It flags two things a control test that merely checks "is there an approval
step?" would miss:

- **A 100% approval rate** over a meaningful sample. Review that never rejects
  anything is usually review that is not happening.
- **Decisions taken within a minute** of the gate being raised — less time than
  the material takes to read.

`GET /v1/ai-oversight/decisions` gives the per-decision record: model, prompt
version, sources cited, stated confidence, and the named person who owned the
outcome.

Model confidence is a column on `config.model_invocation`, not a JSON field,
because two controls depend on it: PR-AIG-02 escalates below an agent's floor,
and PR-AIG-03 baselines it per task class to detect drift when a provider
changes a model underneath you.

---

## 12. Integrating with Brata

**Brata is not mentioned anywhere in the design dossier.** The adapter is built
against conventional REST and MCP patterns with every endpoint path and field
name in configuration. Aligning it to the real contract is a config change.

*Outbound:*

```json
POST /v1/integrations/connections
{
  "name": "Brata", "kind": "brata", "transport": "rest",
  "base_url": "https://brata.example.com",
  "auth_scheme": "oauth2_client_credentials",
  "sync_config": {
    "endpoints": { "risks": "/api/v2/risk-items" },
    "field_map": { "title": "riskName", "residual_score": "netScore" }
  }
}
```

Pulled records deduplicate by lineage. Every call lands in `integ.sync_log`.

*Inbound:* point an MCP client at `/mcp` with a token from
`POST /v1/auth/tokens`. Thirteen tools, each declaring its required permission;
the manifest only advertises what the caller could use. **No tool can approve
anything, and there is no tool that could.**

*Webhooks:* 19 topics, HMAC-SHA256 over the raw body in `X-Craft-Signature`.
Verify before trusting a payload.

---

## 13. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `/readyz` returns 503 with `tables < 40` | Migrations have not run |
| Queries return nothing for a valid tenant | Session not bound. All reads go through `set_session_context`; policies are fail-closed by design |
| Console renders unstyled | Static mount failed. It resolves from the package, so this means a packaging fault |
| `503 no_route_configured` | No AI provider connected. Everything except drafting still works |
| Webhook subscriber receives duplicates | Expected: delivery is at-least-once. Deduplicate on event id |
| Migration runner refuses to start | An applied file was edited. Restore it and add a new migration instead |
| Every provider call fails after a redeploy | `CRAFT_ENCRYPTION_KEY` changed. Sealed credentials are unreadable; re-enter them |

**Logs to watch:** slow requests over 3s, `Suspended webhook`, `Outbox event
dead-lettered`, `Housekeeping cycle failed`, and any `Audit chain integrity
failure`. The last is the only one that is an emergency.

---

## 14. Testing

```bash
pytest -q     # 137 tests
```

Against real PostgreSQL, connecting as `craft_app`. Not SQLite, not mocks: the
properties most worth testing are database behaviour, and a suite that swapped
the engine out would prove nothing about what ships.

| File | Covers |
|---|---|
| `test_audit_integrity.py` | Immutability, tamper detection under a bypassed trigger, tenant isolation |
| `test_authorisation.py` | Agent non-accountability, requester–approver separation, SoD at grant time |
| `test_compliance.py` | Catalogue completeness, readiness arithmetic, SoA, evidence discount |
| `test_gateway_and_mcp.py` | Redaction, cache keys, budget, MCP authorisation |
| `test_reliability.py` | Concurrent outbox claiming, idempotent retries |
| `test_process_repository.py` | Repository and registry integrity, honest automation claims |
| `test_endpoint_smoke.py` | Every endpoint executed at least once |

The smoke test exists because **four production faults reached earlier builds
purely by never having been executed**. It walks the OpenAPI document with a
principal holding every role, so authorisation cannot mask a broken handler.

---

## 15. Known limitations

- **No test makes a real billed provider call.** Adapters are written against
  documented APIs. Use the provider test endpoint after connecting one.
- **The Brata contract is assumed.**
- **Single-region.** No multi-region failover; throughput ceiling unmeasured.
- **Continuous control monitoring needs connectors.** PR-CMP-02 defines the
  process and the platform runs it, but the source-system connectors that make
  a control machine-testable are per-environment work.
- **Readiness displays to one decimal place.** With 118 controls, one control
  moves it by well under a point. The weighting is exact; only the display rounds.
