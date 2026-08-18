# For anywhere that is not Render. The image runs as a non-root user and holds
# no secrets: everything comes from the environment at run time.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libpq for psycopg, curl for the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY db ./db
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN useradd --create-home --uid 10001 craft \
    && chown -R craft:craft /app
USER craft

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/readyz" || exit 1

# The entrypoint validates configuration before uvicorn forks, binds $PORT
# rather than assuming 8000, and takes its worker count from WEB_CONCURRENCY.
#
# The previous CMD hard-coded --workers 2 and port 8000. Both were wrong on a
# platform: the port assumption survives only because Render happens to use
# 8000, and the worker count silently overrode the WEB_CONCURRENCY the platform
# sets from the instance's memory — which is how two workers get started on a
# 512 MB instance and killed by the OOM killer with no log line at all.
#
# Migrations still do not run here by default. Run them in a pre-deploy step
# with the owning credential, or set CRAFT_AUTO_MIGRATE=true to have the
# entrypoint apply them before serving:
#   docker run --rm --env-file .env craft python -m app.migrate
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
