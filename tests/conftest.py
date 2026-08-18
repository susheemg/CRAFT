"""Shared fixtures.

Tests run against a real PostgreSQL database, not a mock or SQLite. That is
deliberate: the properties most worth testing here — row-level security, the
append-only triggers, native enums, the advisory lock behind audit sequencing —
are all database behaviour. A test suite that swapped the engine out would
prove nothing about the thing being shipped.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("CRAFT_ENVIRONMENT", "test")
# Tests run against the same non-superuser role the application uses. Running
# them as the owner would silently disable row-level security and make the
# isolation tests meaningless.
os.environ.setdefault(
    "CRAFT_DATABASE_URL",
    "postgresql+psycopg://craft_app:craft_app_local_dev@127.0.0.1:5432/craft",
)
os.environ.setdefault(
    "CRAFT_MIGRATION_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/craft",
)
os.environ.setdefault("CRAFT_AUTO_SEED", "true")
os.environ.setdefault("CRAFT_ENABLE_OUTBOX_RELAY", "false")
os.environ.setdefault("CRAFT_BOOTSTRAP_ADMIN_PASSWORD", "test-bootstrap-pw-2026")

from app.db import session_scope, set_session_context  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import ActorType, AutonomyTier, utcnow  # noqa: E402
from app.models.iam import AgentIdentity, Role, RoleGrant, Tenant, UserAccount  # noqa: E402
from app.security.auth import Principal, hash_password  # noqa: E402
from app.security.rbac import resolve_access  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def tenant_id(client) -> uuid.UUID:
    """The seeded tenant, selected by name rather than by arbitrary order.

    ``iam.tenant`` is the one table with no tenant_id of its own, so it carries
    no isolation policy; taking whichever row came back first would silently
    bind the whole suite to a leftover tenant from another test.
    """
    from app.config import get_settings

    name = get_settings().default_tenant_name
    with session_scope(bypass_rls=True) as db:
        tenant = db.execute(select(Tenant).where(Tenant.name == name)).scalar_one()
        return tenant.id


def _make_user(db, tenant_id: uuid.UUID, email: str, roles: list[str]) -> UserAccount:
    user = db.execute(select(UserAccount).where(UserAccount.email == email)).scalar_one_or_none()
    if user is None:
        user = UserAccount(
            tenant_id=tenant_id,
            email=email,
            display_name=email.split("@")[0],
            status="active",
            password_hash=hash_password("test-password-2026"),
            created_at=utcnow(),
        )
        db.add(user)
        db.flush()
    for name in roles:
        role = db.execute(select(Role).where(Role.name == name)).scalar_one()
        exists = db.execute(
            select(RoleGrant).where(
                RoleGrant.principal_id == user.id, RoleGrant.role_id == role.id
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                RoleGrant(
                    tenant_id=tenant_id,
                    principal_id=user.id,
                    principal_type=ActorType.HUMAN,
                    role_id=role.id,
                    scope="all",
                    granted_at=utcnow(),
                    justification="test fixture",
                )
            )
    db.flush()
    return user


def _principal_for(db, user: UserAccount) -> Principal:
    access = resolve_access(db, user.id, user.tenant_id)
    return Principal(
        id=user.id,
        tenant_id=user.tenant_id,
        actor_type=ActorType.HUMAN,
        display=user.email,
        permissions=access.permissions,
        roles=access.role_names,
    )


@pytest.fixture(scope="session")
def people(client, tenant_id) -> dict:
    """A cast with genuinely different authority, so authorisation is testable.

    ``officer`` can manage risk and accept it; ``operator`` can run workflows but
    decides nothing; ``ciso`` holds security approval authority.
    """
    specs = {
        "officer": ("risk.officer@test.local", ["Risk Officer"]),
        "operator": ("operator@test.local", ["Operator"]),
        "ciso": ("ciso@test.local", ["CISO"]),
        "dpo": ("dpo@test.local", ["DPO"]),
        "security_admin": ("secadmin@test.local", ["Security Admin"]),
        "auditor": ("auditor@test.local", ["Internal Auditor"]),
    }
    out = {}
    with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
        for key, (email, roles) in specs.items():
            user = _make_user(db, tenant_id, email, roles)
            out[key] = {"id": user.id, "email": email}
    return out


def token_for(client, email: str) -> str:
    response = client.post(
        "/v1/auth/login", json={"email": email, "password": "test-password-2026"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def headers(client, people) -> dict:
    return {
        key: {"Authorization": f"Bearer {token_for(client, spec['email'])}"}
        for key, spec in people.items()
    }


@pytest.fixture(scope="session")
def agent(client, tenant_id) -> dict:
    with session_scope(tenant_id=tenant_id) as db:
        # Keyed off the registry rather than a hard-coded string: the fixture
        # named an agent that no longer exists, which made every agent
        # accountability test error out instead of run — the failure mode where
        # a control test silently stops being a control test.
        from app.agents.registry import AGENT_BY_KEY

        key = "risk_analyst"
        assert key in AGENT_BY_KEY, f"registry no longer defines '{key}'"
        identity = db.execute(
            select(AgentIdentity).where(AgentIdentity.agent_key == key)
        ).scalar_one()
        access = resolve_access(db, identity.id, tenant_id)
        return {
            "id": identity.id,
            "key": identity.agent_key,
            "permissions": set(access.permissions),
            "roles": set(access.role_names),
        }


@pytest.fixture
def db():
    with session_scope() as session:
        yield session


@pytest.fixture
def tenant_db(tenant_id):
    """A session already bound to the tenant, as a request would be."""
    with session_scope() as session:
        set_session_context(session, tenant_id, "human:test")
        yield session
