"""Twelve-factor configuration. All settings come from the environment.

No secret material is ever hard-coded. CRAFT_ENCRYPTION_KEY is the local
key-encryption key used to seal provider credentials at rest; in a managed
deployment it should be sourced from a KMS/vault and injected as an env var.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# The local development fallback. Named rather than inlined so the production
# guard in get_settings() can tell "nobody configured this" apart from "somebody
# deliberately pointed production at localhost".
LOCAL_DEV_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/craft"

# Environment variables the hosting platform sets itself, which no developer
# sets by hand. These are the only reliable signal that the process is deployed
# rather than local, because CRAFT_ENVIRONMENT is one of the variables that goes
# missing when a service is misconfigured — gating a misconfiguration guard on a
# variable that is itself part of the misconfiguration is how the guard misses
# the case it exists for.
PLATFORM_MARKERS: tuple[str, ...] = (
    "RENDER",                  # Render
    "RENDER_SERVICE_ID",
    "DYNO",                    # Heroku
    "FLY_APP_NAME",            # Fly.io
    "KUBERNETES_SERVICE_HOST", # Kubernetes
    "WEBSITE_INSTANCE_ID",     # Azure App Service
    "ECS_CONTAINER_METADATA_URI_V4",  # AWS ECS
)


def is_deployed() -> bool:
    """True when a hosting platform is running this process."""
    return any(os.environ.get(marker) for marker in PLATFORM_MARKERS)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRAFT_", env_file=".env", extra="ignore", case_sensitive=False
    )

    # --- Identity of the deployment -------------------------------------
    app_name: str = "CRAFT"
    version: str = "1.0.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=list)

    # --- Start-up behaviour ---------------------------------------------
    # Both are idempotent, so leaving them on means a deploy or a restart
    # converges on the right state without an operator running anything.
    auto_migrate: bool = True
    auto_seed: bool = True

    # --- Data tier -------------------------------------------------------
    # The credential that serves requests. It must not be a superuser and must
    # not own the tables, or PostgreSQL will exempt it from row-level security
    # and tenant isolation will silently not apply.
    database_url: str = LOCAL_DEV_DATABASE_URL
    # The credential that owns the schema and runs migrations. Defaults to
    # database_url for single-credential deployments such as Render's managed
    # Postgres; set both where the roles can be separated.
    migration_database_url: str = ""
    app_db_password: str = "craft_app_local_dev"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_statement_timeout_ms: int = 30_000

    # --- Cryptography / sessions ----------------------------------------
    secret_key: str = Field(default="dev-only-change-me-in-production")
    encryption_key: str = Field(default="")  # Fernet key; generated on boot in dev
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    # --- Authentication --------------------------------------------------
    # Local credentials exist so the platform can be bootstrapped before an
    # IdP is federated. In production, set oidc_* and disable local login.
    allow_local_login: bool = True
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    bootstrap_admin_email: str = "admin@craft.local"
    bootstrap_admin_password: str = ""  # if empty, a password is generated and logged once

    # --- LLM gateway -----------------------------------------------------
    llm_cache_enabled: bool = True
    llm_cache_ttl_seconds: int = 86_400
    llm_request_timeout_seconds: float = 60.0
    llm_max_fallback_attempts: int = 3

    # --- Outbound integration (Brata) ------------------------------------
    brata_base_url: str = ""
    brata_api_key: str = ""
    brata_mcp_url: str = ""
    brata_verify_tls: bool = True

    # --- Background workers ---------------------------------------------
    enable_background_workers: bool = True
    enable_outbox_relay: bool = True
    outbox_poll_seconds: float = 5.0
    audit_verify_interval_seconds: int = 3600

    # --- Multi-tenancy ---------------------------------------------------
    default_tenant_name: str = "Primary"
    default_tenant_region: str = "uk"

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        if not v:
            return v
        # Render supplies postgres:// ; SQLAlchemy 2 + psycopg3 needs a driver.
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def owner_database_url(self) -> str:
        """Where DDL runs. Falls back to the serving credential when only one
        credential is available, which is the common managed-Postgres case."""
        return self.migration_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    if not s.encryption_key:
        from cryptography.fernet import Fernet

        generated = Fernet.generate_key().decode()
        if s.is_production:
            raise RuntimeError(
                "CRAFT_ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet;"
                "print(Fernet.generate_key().decode())\""
            )
        os.environ["CRAFT_ENCRYPTION_KEY"] = generated
        s.encryption_key = generated
    if s.is_production and s.secret_key.startswith("dev-only"):
        raise RuntimeError("CRAFT_SECRET_KEY must be set in production.")

    # Every other production-critical secret is checked above. The database URL
    # was not, and it is the one whose default is silently *plausible*: an unset
    # CRAFT_DATABASE_URL leaves the service pointing at localhost, where nothing
    # is listening, and the failure arrives as a connection-refused traceback
    # rather than as the configuration error it actually is. Same shape as the
    # row-level security defect: a setting that appears configured, is not, and
    # fails somewhere far from its cause.
    if (s.is_production or is_deployed()) and s.database_url == LOCAL_DEV_DATABASE_URL:
        detail = (
            "CRAFT_ENVIRONMENT is also unset (it defaults to 'development'), "
            "which means none of this service's environment variables are "
            "reaching the container. "
            if not s.is_production
            else ""
        )
        raise RuntimeError(
            "CRAFT_DATABASE_URL is not set, so this service is using the local "
            "development database default (localhost:5432). Nothing listens on "
            f"localhost inside a container, so it cannot start. {detail}"
            "On Render this almost always means the service was not created "
            "from render.yaml, or the 'fromDatabase' link to craft-db was "
            "removed. Fix it by adding an environment variable CRAFT_DATABASE_URL "
            "pointing at the craft-db Internal Database URL, or by re-applying "
            "the blueprint."
        )
    return s
