"""Configuration preflight.

Run before the server starts, in the parent process, so its output cannot be
lost when a worker dies. Exists because of a deploy that produced this and
nothing else:

    INFO:     Waiting for child process [26]
    INFO:     Child process [26] died

``app.db`` calls ``get_settings()`` at module scope, so a configuration error
raises during *import* of the application — before uvicorn's lifespan handler,
before logging is configured, and inside a worker process whose stderr is not
reliably drained when it dies during bootstrap. The result is a silent exit.

This module makes that impossible: every check runs here first, prints a line
per check, and exits non-zero with a message a person can act on.

    python -m app.preflight

It never prints a secret. Credentials are reported as present or absent, and
the database URL is shown with its password stripped.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit, urlunsplit


def _redact(url: str) -> str:
    """The URL with the password removed, so it is safe in a build log."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<unparseable>"
    if parts.password:
        netloc = f"{parts.username or ''}:***@{parts.hostname or ''}"
        if parts.port:
            netloc += f":{parts.port}"
        parts = parts._replace(netloc=netloc)
    return urlunsplit(parts)


def _line(ok: bool, label: str, detail: str = "") -> None:
    mark = "  ok  " if ok else " FAIL "
    print(f"[{mark}] {label}{': ' + detail if detail else ''}", flush=True)


# Variables the service cannot start without once it is running on a platform,
# with what each is for. Kept here rather than derived from the Settings model
# because this list has to be readable when the Settings model is what failed.
REQUIRED_WHEN_DEPLOYED: tuple[tuple[str, str], ...] = (
    ("CRAFT_DATABASE_URL", "the database to serve from"),
    ("CRAFT_SECRET_KEY", "session and token signing"),
    ("CRAFT_ENCRYPTION_KEY", "sealing stored provider credentials"),
)

RECOMMENDED_WHEN_DEPLOYED: tuple[tuple[str, str], ...] = (
    ("CRAFT_ENVIRONMENT", "should be 'production'; unset means the whole variable set is missing"),
    ("CRAFT_MIGRATION_DATABASE_URL", "the owning credential, needed to seed the ref catalogue"),
    ("CRAFT_BASE_URL", "absolute links in notifications and webhooks"),
)


def _report_all_missing() -> None:
    """Enumerate every unset variable, not only the one that raised first."""
    missing = [(n, why) for n, why in REQUIRED_WHEN_DEPLOYED if not os.environ.get(n)]
    absent = [(n, why) for n, why in RECOMMENDED_WHEN_DEPLOYED if not os.environ.get(n)]

    if missing:
        print("Required and not set:", file=sys.stderr, flush=True)
        for name, why in missing:
            print(f"  * {name} — {why}", file=sys.stderr, flush=True)
    if absent:
        print("\nAlso not set:", file=sys.stderr, flush=True)
        for name, why in absent:
            print(f"  * {name} — {why}", file=sys.stderr, flush=True)
    if len(missing) + len(absent) >= 4:
        print(
            "\nAlmost nothing is set, which points at the service rather than at "
            "any one variable: it was very likely created by hand instead of from "
            "render.yaml. Re-applying the blueprint sets all of these at once.",
            file=sys.stderr,
            flush=True,
        )
    print(
        "\nGenerate an encryption key with:\n"
        '  python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"',
        file=sys.stderr,
        flush=True,
    )


def main() -> int:
    problems: list[str] = []

    # Importing the settings is itself the first check: this is where the
    # configuration guards raise, and doing it here rather than inside a worker
    # is the whole point of this module.
    try:
        from app.config import LOCAL_DEV_DATABASE_URL, get_settings, is_deployed

        settings = get_settings()
    except Exception as exc:  # configuration errors are RuntimeError by design
        # get_settings() raises on the first problem it meets, which would send
        # an operator round the loop once per missing variable: fix one, wait for
        # a redeploy, discover the next. Fall through to a direct read of the
        # environment and report everything that is wrong in one pass.
        print("[ FAIL ] configuration could not be loaded", flush=True)
        print(f"\n{exc}\n", file=sys.stderr, flush=True)
        _report_all_missing()
        return 1

    _line(True, "settings loaded", f"environment={settings.environment}")

    deployed = is_deployed()
    _line(
        True,
        "hosting platform",
        "detected" if deployed else "none — treating this as local development",
    )

    # Database ------------------------------------------------------------
    url = settings.database_url
    parsed = urlsplit(url)
    on_default = url == LOCAL_DEV_DATABASE_URL
    _line(not (deployed and on_default), "CRAFT_DATABASE_URL", _redact(url))
    if deployed and on_default:
        problems.append(
            "CRAFT_DATABASE_URL is not set. The service is using the local "
            "development default, and nothing listens on localhost inside a "
            "container. On Render, add the craft-db Internal Database URL as "
            "CRAFT_DATABASE_URL, or re-apply render.yaml as a Blueprint."
        )

    owner_set = bool(settings.migration_database_url)
    _line(
        True,
        "CRAFT_MIGRATION_DATABASE_URL",
        _redact(settings.migration_database_url) if owner_set
        else "unset — falling back to the serving credential",
    )
    if deployed and not owner_set:
        # Not fatal on single-credential managed Postgres, but it is the cause
        # of "permission denied for table framework" during seeding, so it is
        # worth naming before it happens rather than after.
        print(
            "         note: reference-catalogue seeding writes to the ref schema, "
            "which the serving credential may only read. If seeding fails with a "
            "permission error, set this to the owning credential.",
            flush=True,
        )

    # Secrets -------------------------------------------------------------
    if settings.is_production or deployed:
        for name, value, hint in (
            ("CRAFT_SECRET_KEY", settings.secret_key, "session and token signing"),
            ("CRAFT_ENCRYPTION_KEY", settings.encryption_key, "provider credential sealing"),
        ):
            supplied = bool(value) and not value.startswith("dev-only")
            _line(supplied, name, "set" if supplied else f"missing — needed for {hint}")
            if not supplied:
                problems.append(f"{name} must be set. It is used for {hint}.")

    # Concurrency ---------------------------------------------------------
    workers = os.environ.get("WEB_CONCURRENCY")
    _line(True, "WEB_CONCURRENCY", workers or "unset — defaulting to 1 worker")
    if workers and workers.isdigit() and int(workers) > 1:
        print(
            "         note: each worker holds its own connection pool "
            f"({settings.db_pool_size} + {settings.db_max_overflow} overflow) and its "
            "own outbox relay. Confirm the instance has memory for that before "
            "raising this.",
            flush=True,
        )

    # Migrations ----------------------------------------------------------
    _line(
        True,
        "CRAFT_AUTO_MIGRATE",
        "true — migrations run at start-up"
        if settings.auto_migrate
        else "false — a pre-deploy step must run 'python -m app.migrate'",
    )

    if problems:
        print("\ncraft: configuration is not usable\n", file=sys.stderr, flush=True)
        for problem in problems:
            print(f"  * {problem}\n", file=sys.stderr, flush=True)
        return 1

    print("craft: preflight passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
