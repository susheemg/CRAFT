"""Every endpoint is called at least once.

Two production faults reached the previous build because their endpoints had
never been executed: one read a model attribute that did not exist, the other a
column that had never been created. Both were one-line mistakes that any single
call would have surfaced, and neither was caught by tests that exercised the
services underneath.

So this walks the OpenAPI document and calls everything. It asserts only that
nothing returns 5xx: a 403 or a 404 is a considered answer, but a 500 means the
handler cannot run at all.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import session_scope
from app.main import app
from app.models.iam import UserAccount, Role, RoleGrant
from app.models.base import ActorType, utcnow


@pytest.fixture(scope="module")
def omniscient(client, tenant_id):
    """A principal holding every role, so authorisation cannot mask a fault.

    A 403 would hide a broken handler just as well as a 200 would reveal it,
    which is exactly how the two faults above survived.
    """
    email = "smoke.everything@test.local"
    with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
        from app.security.auth import hash_password

        user = db.execute(
            select(UserAccount).where(UserAccount.email == email)
        ).scalar_one_or_none()
        if user is None:
            user = UserAccount(
                tenant_id=tenant_id, email=email, display_name="Smoke",
                status="active", password_hash=hash_password("smoke-password-2026"),
                created_at=utcnow(),
            )
            db.add(user)
            db.flush()
        held = {
            g.role_id for g in db.execute(
                select(RoleGrant).where(RoleGrant.principal_id == user.id)
            ).scalars().all()
        }
        for role in db.execute(select(Role)).scalars().all():
            if role.agent_eligible or role.id in held:
                continue
            db.add(
                RoleGrant(
                    tenant_id=tenant_id, principal_id=user.id,
                    principal_type=ActorType.HUMAN, role_id=role.id, scope="all",
                    granted_at=utcnow(), justification="smoke test fixture",
                )
            )
    response = client.post(
        "/v1/auth/login", json={"email": email, "password": "smoke-password-2026"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _collection_paths() -> list[str]:
    """Every GET that needs no path parameter."""
    return sorted(
        path
        for path, operations in app.openapi()["paths"].items()
        if "get" in operations and "{" not in path
    )


@pytest.mark.parametrize("path", _collection_paths())
def test_every_collection_endpoint_runs(client, omniscient, path):
    response = client.get(path, headers=omniscient)
    assert response.status_code < 500, (
        f"GET {path} returned {response.status_code}. A handler that cannot run "
        f"is a fault regardless of what the services beneath it do.\n"
        f"{response.text[:400]}"
    )


def test_the_console_pages_all_render(client, omniscient):
    """The console is server-rendered, so a template fault is a runtime fault.

    Rendering is where a renamed field or a wrong dictionary key shows up, and
    it will not show up anywhere else.
    """
    client.post(
        "/login",
        data={"email": "smoke.everything@test.local", "password": "smoke-password-2026"},
        follow_redirects=False,
    )
    for page in (
        "/", "/compliance", "/compliance/iso27001", "/risks",
        "/approvals", "/operations", "/audit", "/admin/ai",
    ):
        response = client.get(page)
        assert response.status_code == 200, (
            f"{page} returned {response.status_code}: {response.text[:300]}"
        )
        assert "<html" in response.text.lower()


def test_the_stylesheet_is_served(client):
    """The static mount resolves from the package, not the working directory.

    It previously used a relative path inside a suppressed exception, so
    starting the service from anywhere but the repository root produced an
    unstyled console and no error to explain it.
    """
    response = client.get("/static/craft.css")
    assert response.status_code == 200
    assert "--navy" in response.text


def test_openapi_generates(client):
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    assert len(spec.json()["paths"]) > 60
