#!/bin/sh
# Container entrypoint.
#
# Exists because of a deployment that failed with no error at all: uvicorn
# reported "Child process died" twice and exited, with nothing above it. Two
# things can produce that silence, and neither is diagnosable from the log:
#
#   * the application raised while *importing* — app.db calls get_settings() at
#     module scope, so a configuration error happens before uvicorn's lifespan
#     handler and before any logging is configured; and
#   * the worker was killed by the kernel out-of-memory killer, which by
#     definition writes nothing.
#
# So configuration is validated here, in the parent process, before uvicorn is
# ever started. Output from this script cannot be swallowed by a worker that
# dies, and the exit is explicit rather than a bare non-zero.

set -eu

echo "craft: preflight"

# Fail with a readable message rather than an import traceback from inside a
# worker nobody can see.
python -m app.preflight || {
    echo "craft: refusing to start — see the preflight output above." >&2
    exit 78   # EX_CONFIG
}

# Render, Fly and Heroku all publish the port to bind. Hard-coding 8000 works
# on Render only by coincidence.
PORT="${PORT:-8000}"

# Render sets WEB_CONCURRENCY from the instance's CPU allowance and memory. The
# previous CMD hard-coded --workers 2, which silently overrode it: on a 512 MB
# starter instance two workers, each with its own SQLAlchemy pool and its own
# outbox relay, is how a container gets OOM-killed with no message.
WORKERS="${WEB_CONCURRENCY:-1}"

if [ "${CRAFT_AUTO_MIGRATE:-false}" = "true" ]; then
    echo "craft: applying migrations"
    python -m app.migrate
else
    echo "craft: CRAFT_AUTO_MIGRATE is not true — assuming migrations ran in a pre-deploy step"
fi

echo "craft: starting uvicorn on 0.0.0.0:${PORT} with ${WORKERS} worker(s)"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --proxy-headers \
    --forwarded-allow-ips '*'
