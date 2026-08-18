"""Forward-only, versioned schema migration.

Two stages run in order, both idempotent, both recorded:

  1. Schemas and tables are created from the SQLAlchemy metadata.
  2. Numbered SQL files in ``db/migrations`` apply everything the ORM cannot
     express — the audit immutability trigger, row-level security policies,
     database roles and grants, and partial indexes.

Applied files are recorded in ``audit.schema_migration`` with a checksum. If a
file changes after it has been applied the runner refuses to continue: forward
only, no silent edits to history.
"""

from __future__ import annotations

import hashlib
import logging
import pathlib

from sqlalchemy import text

from sqlalchemy import create_engine

from app.config import get_settings
from app.models import SCHEMAS, Base

_settings = get_settings()

# Migrations connect as the schema owner, which is a different credential from
# the one that serves requests wherever the two can be separated.
engine = create_engine(_settings.owner_database_url, pool_pre_ping=True, future=True)

log = logging.getLogger(__name__)

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "db" / "migrations"

_TRACKER_DDL = """
CREATE SCHEMA IF NOT EXISTS audit;
CREATE TABLE IF NOT EXISTS audit.schema_migration (
    filename   text PRIMARY KEY,
    checksum   text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
"""


def _checksum(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def create_schemas() -> None:
    with engine.begin() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def apply_sql_migrations() -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        conn.execute(text(_TRACKER_DDL))
        rows = conn.execute(text("SELECT filename, checksum FROM audit.schema_migration")).all()
        seen = {r[0]: r[1] for r in rows}

    if not MIGRATIONS_DIR.exists():
        return applied

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        body = path.read_text(encoding="utf-8")
        digest = _checksum(body)
        if path.name in seen:
            if seen[path.name] != digest:
                raise RuntimeError(
                    f"Migration {path.name} changed after it was applied. "
                    "Migrations are forward-only — add a new file instead."
                )
            continue
        log.info("Applying migration %s", path.name)
        with engine.begin() as conn:
            # 0003 reads this to set the application role's password without
            # ever writing the secret into a migration file.
            conn.execute(
                text("SELECT set_config('craft.app_password', :pw, false)"),
                {"pw": _settings.app_db_password},
            )
            conn.execute(text(body))
            conn.execute(
                text(
                    "INSERT INTO audit.schema_migration (filename, checksum) "
                    "VALUES (:f, :c)"
                ),
                {"f": path.name, "c": digest},
            )
        applied.append(path.name)
    return applied


def run() -> list[str]:
    create_schemas()
    create_tables()
    return apply_sql_migrations()


if __name__ == "__main__":  # pragma: no cover - operational entry point
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    done = run()
    print(f"Schema up to date. Applied {len(done)} new migration(s): {done or 'none'}")
