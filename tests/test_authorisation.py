"""Authorisation: the rules that decide who may do what.

Three properties are tested, because each blocks a different failure:

  * an agent can never approve anything, so accountability for a decision
    always rests with a person
  * nobody approves their own request, which is the oldest control there is
  * segregation of duties is refused at the point of granting, not detected
    afterwards by a report nobody reads
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.db import session_scope
from app.models.base import ActorType
from app.models.iam import Role
from app.security.auth import Principal
from app.security.rbac import (
    AgentNotPermitted,
    PermissionDenied,
    SodViolation,
    assert_gate_authority,
    assert_human,
    resolve_access,
    validate_grant,
)


def _role_id(db, name: str) -> uuid.UUID:
    return db.execute(select(Role.id).where(Role.name == name)).scalar_one()


class TestAgentAccountability:
    def test_no_agent_role_carries_approval_authority(self, agent):
        """The seeded agent must hold no gate.* permission at all."""
        gates = {p for p in agent["permissions"] if p.startswith("gate.")}
        assert not gates, f"Agent holds approval authority: {sorted(gates)}"

    def test_granting_an_approval_role_to_an_agent_is_refused(self, tenant_id, agent, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            granting = Principal(
                id=people["security_admin"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="secadmin",
                permissions=frozenset({"*"}),
                roles=frozenset({"Security Admin"}),
            )
            with pytest.raises(AgentNotPermitted) as exc:
                validate_grant(
                    db,
                    granting_principal=granting,
                    target_principal_id=agent["id"],
                    target_principal_type=ActorType.AGENT,
                    role_id=_role_id(db, "DPO"),
                )
        assert "approval authority" in str(exc.value).lower()

    def test_agent_principal_cannot_pass_the_human_check(self, tenant_id, agent):
        principal = Principal(
            id=agent["id"],
            tenant_id=tenant_id,
            actor_type=ActorType.AGENT,
            display="compliance-analyst",
            permissions=frozenset({"gate.risk.approve"}),  # even if it somehow held it
            roles=frozenset({"AI Agent"}),
        )
        with pytest.raises(AgentNotPermitted) as exc:
            assert_human(principal)
        assert "cannot be delegated" in str(exc.value).lower()

    def test_a_role_marked_agent_eligible_never_carries_gates(self, tenant_id):
        """Structural check across the whole seeded role catalogue."""
        from app.models.iam import Permission, RolePermission

        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            offenders = db.execute(
                select(Role.name, Permission.code)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(Role.agent_eligible.is_(True), Permission.code.like("gate.%"))
            ).all()
        assert not offenders, f"Agent-eligible roles carrying gates: {offenders}"


class TestSeparationOfRequesterAndApprover:
    def test_the_requester_cannot_approve_their_own_request(self, tenant_id, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            access = resolve_access(db, people["officer"]["id"], tenant_id)
            principal = Principal(
                id=people["officer"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="risk officer",
                permissions=access.permissions,
                roles=access.role_names,
            )
            with pytest.raises(SodViolation) as exc:
                assert_gate_authority(
                    db,
                    principal,
                    "risk.residual_acceptance",
                    approver_role_id=None,
                    requested_by=principal.id,  # the same person raised it
                )
        assert "cannot approve" in str(exc.value).lower()

    def test_an_authorised_person_who_did_not_raise_it_may_approve(self, tenant_id, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            access = resolve_access(db, people["officer"]["id"], tenant_id)
            principal = Principal(
                id=people["officer"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="risk officer",
                permissions=access.permissions,
                roles=access.role_names,
            )
            assert_gate_authority(
                db,
                principal,
                "risk.residual_acceptance",
                approver_role_id=None,
                requested_by=uuid.uuid4(),
            )

    def test_a_role_without_the_authority_is_refused(self, tenant_id, people):
        """An operator can run the workflow but cannot decide its gate."""
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            access = resolve_access(db, people["operator"]["id"], tenant_id)
            principal = Principal(
                id=people["operator"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="operator",
                permissions=access.permissions,
                roles=access.role_names,
            )
            with pytest.raises(PermissionDenied):
                assert_gate_authority(
                    db, principal, "privacy.dsar_release",
                    approver_role_id=None, requested_by=uuid.uuid4(),
                )


class TestSegregationOfDuties:
    def test_mutually_exclusive_roles_are_refused_at_grant_time(self, tenant_id, people):
        """The auditor who tests the controls cannot also operate them."""
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            granting = Principal(
                id=people["security_admin"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="secadmin",
                permissions=frozenset({"*"}),
                roles=frozenset({"Security Admin"}),
            )
            with pytest.raises(SodViolation):
                validate_grant(
                    db,
                    granting_principal=granting,
                    target_principal_id=people["auditor"]["id"],
                    target_principal_type=ActorType.HUMAN,
                    role_id=_role_id(db, "Operator"),
                )

    def test_nobody_can_grant_beyond_their_own_authority(self, tenant_id, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            access = resolve_access(db, people["operator"]["id"], tenant_id)
            granting = Principal(
                id=people["operator"]["id"],
                tenant_id=tenant_id,
                actor_type=ActorType.HUMAN,
                display="operator",
                permissions=access.permissions,
                roles=access.role_names,
            )
            with pytest.raises(PermissionDenied) as exc:
                validate_grant(
                    db,
                    granting_principal=granting,
                    target_principal_id=people["operator"]["id"],
                    target_principal_type=ActorType.HUMAN,
                    role_id=_role_id(db, "CISO"),
                )
        assert "does not hold" in str(exc.value).lower()


class TestApiEnforcement:
    def test_an_endpoint_refuses_a_principal_without_the_permission(self, client, headers):
        response = client.post(
            "/v1/risks",
            headers=headers["operator"],
            json={"title": "An operator should not be able to file this",
                  "inherent_likelihood": 3, "inherent_impact": 3},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"

    def test_the_same_call_succeeds_for_a_principal_who_holds_it(self, client, headers):
        response = client.post(
            "/v1/risks",
            headers=headers["officer"],
            json={"title": "Supplier holds personal data without a processing agreement",
                  "category": "third_party", "inherent_likelihood": 4, "inherent_impact": 4},
        )
        assert response.status_code == 201, response.text
        assert response.json()["severity_band"] in {"high", "very_high"}

    def test_an_unauthenticated_request_is_refused(self):
        # A separate client, because the shared one carries a session cookie
        # from signing in and would not be anonymous.
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as anonymous:
            response = anonymous.get("/v1/risks")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"

    def test_a_forged_token_is_refused(self, client):
        response = client.get("/v1/risks", headers={"Authorization": "Bearer not.a.token"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
