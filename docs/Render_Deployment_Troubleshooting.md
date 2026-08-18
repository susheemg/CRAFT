# Deploying to Render: the failure that keeps happening

If the service exits at startup with `connection to server at "127.0.0.1", port
5432 failed: Connection refused`, the cause is almost never the database. It is
that **`CRAFT_DATABASE_URL` is not reaching the container**, so the application
falls back to the local development default, and nothing listens on localhost
inside a container.

## Confirming it in ten seconds

In the Render dashboard, open the service → **Environment**. If
`CRAFT_DATABASE_URL` is missing, that is the whole problem. If
`CRAFT_ENVIRONMENT` is *also* missing, the service was created by hand rather
than from `render.yaml`, and none of the other settings are present either.

## Fixing it

> **If the service is a Docker service, `render.yaml` does not apply to it
> unless the service was created from the blueprint.** The `envVars` block is a
> property of the blueprint, not of the repository, so a hand-created Docker
> service starts with no configuration at all — which is exactly the failure
> above. `render.yaml` now declares `runtime: docker` so re-applying it produces
> the service you are actually running.


**Option A — re-apply the blueprint (preferred).** This is what `render.yaml`
exists for, and it wires the database link, the pre-deploy migration, the health
check and the generated secrets in one step.

1. Dashboard → **Blueprints** → **New Blueprint Instance**.
2. Point it at this repository on the `main` branch.
3. Set the three variables marked `sync: false` when prompted:
   `CRAFT_ENCRYPTION_KEY`, `CRAFT_BOOTSTRAP_ADMIN_EMAIL`, `CRAFT_BASE_URL`.
   Generate the encryption key with:
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Back it up outside Render. Losing it makes every stored provider credential
   unreadable.
4. Leave `CRAFT_BOOTSTRAP_ADMIN_PASSWORD` unset and read the generated password
   from the first boot's logs.

**Option B — repair the existing service.** Faster, and the right choice if you
want to keep the service you already have. You must add by hand everything the
blueprint would have set. The minimum to get off the ground is five variables:

| Variable | Value |
|---|---|
| `CRAFT_DATABASE_URL` | the **Internal** Database URL from the `craft-db` page |
| `CRAFT_ENVIRONMENT` | `production` |
| `CRAFT_SECRET_KEY` | any long random string |
| `CRAFT_ENCRYPTION_KEY` | a Fernet key — see the command below; back it up |
| `CRAFT_AUTO_MIGRATE` | `true`, unless you set a Pre-Deploy Command instead |

`CRAFT_AUTO_MIGRATE=true` is the pragmatic choice on a hand-created Docker
service: the entrypoint applies migrations before serving, the runner is
forward-only and idempotent, and with a single worker there is nothing to race.
Prefer a Pre-Deploy Command once you run more than one instance.

The full set follows.

1. Service → **Environment** → **Add Environment Variable**.
2. `CRAFT_DATABASE_URL` = the **Internal Database URL** from the `craft-db`
   database page. Use the internal URL, not the external one: the external URL
   goes over the public internet and `ipAllowList: []` blocks it.
3. Add `CRAFT_MIGRATION_DATABASE_URL` with the same value.
4. Add `CRAFT_ENVIRONMENT=production`, `CRAFT_AUTO_MIGRATE=false`,
   `CRAFT_AUTO_SEED=true`, `CRAFT_ENABLE_OUTBOX_RELAY=true`,
   `CRAFT_ALLOW_LOCAL_LOGIN=true`.
5. Add `CRAFT_SECRET_KEY` and `CRAFT_ENCRYPTION_KEY` — the service refuses to
   start in production without them, by design.
6. Settings → **Pre-Deploy Command** → `python -m app.migrate`. Without this the
   schema is never created, and the first request fails on a missing table
   instead of at boot.

## The second failure: no error message at all

```
INFO:     Waiting for child process [26]
INFO:     Child process [26] died
```

Nothing above it, no traceback. Two causes produce exactly this, and the log
cannot distinguish them:

**The worker was killed by the kernel out-of-memory killer.** An OOM kill writes
nothing by definition. The Dockerfile originally hard-coded `--workers 2`, which
silently overrode the `WEB_CONCURRENCY=1` Render sets from the instance's
memory. Two workers, each with a SQLAlchemy pool of 5 connections plus 10
overflow and its own outbox relay, on a 512 MB starter instance, is how that
happens. The entrypoint now takes its worker count from `WEB_CONCURRENCY` and
defaults to 1.

**The application raised while being imported.** `app/db.py` calls
`get_settings()` at module scope, so a configuration error happens before
uvicorn's lifespan handler, before logging is configured, and inside a worker
whose stderr is not reliably drained when it dies during bootstrap.

Both are now caught by `python -m app.preflight`, which the entrypoint runs in
the parent process before uvicorn forks. Its output cannot be lost, it names
every unset variable in one pass rather than one per redeploy, and it redacts
the database password so the report is safe to paste when asking for help.

Run it against any environment file directly:

```
docker run --rm --env-file .env craft python -m app.preflight
```

## Things that look like this but are not

| Symptom | Actual cause |
|---|---|
| Connection refused on a **non**-localhost host | The database is in a different region from the service. The private network does not cross regions; both must be `frankfurt`, or both whatever you changed it to. |
| `password authentication failed for user "craft_app"` | Migration 0003 created the `craft_app` role with `CRAFT_APP_DB_PASSWORD`, and that value changed between the pre-deploy and the service. Set it explicitly rather than with `generateValue`. |
| `permission denied for table framework` | `CRAFT_DATABASE_URL` points at the `craft_app` role but `CRAFT_MIGRATION_DATABASE_URL` is unset, so reference seeding runs on the credential that may only read `ref`. Set both. |
| Starts, then `no such table` on first request | Pre-deploy command missing and `CRAFT_AUTO_MIGRATE=false`. Set one or the other. |
| `Child process died`, nothing else, on a Docker deploy | Worker count or import-time configuration error. Run the preflight; see the section above. |
| Health check fails but the app is up | `HEALTHCHECK` and the bind port disagree. The entrypoint binds `$PORT`; older images hard-coded 8000. |

## What the application now tells you

Two guards were added after this failure, because the first report of it was two
hundred lines of SQLAlchemy traceback whose only useful sentence was on the last
line.

`app/config.py` refuses to start when the database URL is the development
default *and* a hosting platform is detected. It keys off the platform's own
variables — `RENDER`, `DYNO`, `KUBERNETES_SERVICE_HOST` and similar — rather
than off `CRAFT_ENVIRONMENT`. That distinction matters: the first version of
this guard was gated on `CRAFT_ENVIRONMENT == production` and missed the live
failure entirely, because `CRAFT_ENVIRONMENT` is one of the variables that goes
missing when a service is misconfigured. A guard against misconfiguration cannot
depend on a variable that is part of the misconfiguration.

`app/main.py` logs the host it tried and the variable that chose it before
re-raising, so the first line of the failure names the problem.

A developer's machine has no platform marker, so the localhost default keeps
working locally. There is a test asserting that too.
