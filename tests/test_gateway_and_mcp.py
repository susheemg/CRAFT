"""The model gateway and the MCP server.

The gateway is the single point where prompts leave the estate, so redaction,
caching and budget enforcement are tested here directly. The MCP tests exist to
confirm that speaking a different protocol does not buy a caller different
authority.
"""

from __future__ import annotations

import uuid

import pytest

from app.db import session_scope
from app.mcp import tools as mcp_tools
from app.mcp.tools import ToolError
from app.models.base import ActorType
from app.security.auth import Principal
from app.security.rbac import resolve_access
from app.services.llm import cache as prompt_cache
from app.services.llm import gateway


class TestRedaction:
    """Redaction runs before anything else touches the text, including the cache
    key, so a secret cannot reach a provider or be stored locally."""

    @pytest.mark.parametrize(
        "text, must_not_contain",
        [
            ("Contact jane.doe@acme.co.uk about the finding", "jane.doe@acme.co.uk"),
            ("Card 4111 1111 1111 1111 was used", "4111"),
            ("api_key=sk-ant-abcdefghijklmnopqrstuvwxyz123456", "sk-ant-abcdefghij"),
            ("Call the DPO on +44 7700 900123 today", "7700 900123"),
        ],
    )
    def test_identifiers_are_removed_before_the_prompt_leaves(self, text, must_not_contain):
        redacted, count = gateway.redact(text)
        assert count >= 1, f"Nothing was redacted from: {text}"
        assert must_not_contain not in redacted

    def test_ordinary_compliance_text_is_left_alone(self):
        """Over-redaction would be its own failure: a rubric full of [REDACTED]
        produces a useless assessment."""
        text = (
            "Control A.5.15 requires access control rules to be established "
            "based on business and information security requirements."
        )
        redacted, count = gateway.redact(text)
        assert count == 0
        assert redacted == text


class TestPromptCache:
    def test_only_deterministic_calls_are_cacheable(self):
        """A sampled answer is not reproducible, so replaying one as though it
        were would misrepresent what the model actually said."""
        assert prompt_cache.is_cacheable(0.0, cache_enabled=True) is True
        assert prompt_cache.is_cacheable(0.7, cache_enabled=True) is False
        assert prompt_cache.is_cacheable(0.0, cache_enabled=False) is False

    def test_the_key_separates_calls_that_must_not_share_an_answer(self):
        base = dict(
            cache_prefix="RUBRIC", system="sys", prompt="Assess A.5.1",
            temperature=0.0, max_tokens=1000, json_mode=False,
        )
        key = prompt_cache.build_key(model_key="model-a", **base)

        assert key == prompt_cache.build_key(model_key="model-a", **base), (
            "An identical call must produce an identical key, or caching never hits"
        )
        # Each of these changes the meaning of the call, so each must miss.
        assert prompt_cache.build_key(model_key="model-b", **base) != key
        assert prompt_cache.build_key(
            model_key="model-a", **{**base, "prompt": "Assess A.5.2"}
        ) != key
        assert prompt_cache.build_key(
            model_key="model-a", **{**base, "cache_prefix": "DIFFERENT RUBRIC"}
        ) != key
        assert prompt_cache.build_key(
            model_key="model-a", **{**base, "max_tokens": 2000}
        ) != key
        assert prompt_cache.build_key(
            model_key="model-a", **{**base, "json_mode": True}
        ) != key

    def test_a_stored_answer_is_returned_and_the_saving_is_recorded(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            key = prompt_cache.build_key(
                model_key="test-model", cache_prefix="P", system="",
                prompt=f"unique-{uuid.uuid4()}", temperature=0.0, max_tokens=100,
                json_mode=False,
            )
            assert prompt_cache.lookup(db, tenant_id, key).hit is False

            prompt_cache.store(
                db, tenant_id=tenant_id, key=key, task_class="control_assessment",
                model_key="test-model", prompt_digest="d" * 64,
                response_text="A cached assessment", tokens_in=1200, tokens_out=300,
                cost=0.0450, ttl_seconds=600,
            )
            db.commit()

            found = prompt_cache.lookup(db, tenant_id, key)
            assert found.hit is True
            assert found.entry.response_text == "A cached assessment"

            saved = prompt_cache.record_hit(db, found.entry)
            db.commit()
            assert saved == pytest.approx(0.0450)
            assert found.entry.hit_count == 1

    def test_statistics_are_computed_from_the_ledger(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            stats = prompt_cache.statistics(db, tenant_id, days=30)
        for field in ("hit_rate", "total_calls", "saved", "spend", "live_entries"):
            assert field in stats, f"statistics() is missing {field}"
        assert 0.0 <= stats["hit_rate"] <= 1.0
        assert 0.0 <= stats["saving_rate"] <= 1.0


class TestGatewayGovernance:
    def test_a_call_with_no_route_configured_is_refused_clearly(self, tenant_id):
        """A fresh deployment has no provider. The refusal must say what to do
        rather than fail with a stack trace."""
        with session_scope(tenant_id=tenant_id) as db:
            with pytest.raises(gateway.NoRouteConfigured) as exc:
                gateway.resolve_route(db, tenant_id, "control_assessment")
        assert "admin" in str(exc.value).lower()

    def test_budget_state_is_reported_even_before_any_spend(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            state = gateway.check_policy(db, tenant_id)
        assert state.allowed is True
        assert state.tokens_today == 0
        assert state.token_budget is not None, "The seeder should set a default budget"


class TestMcpAuthorisation:
    def _principal(self, db, tenant_id, principal_id, actor_type=ActorType.HUMAN):
        access = resolve_access(db, principal_id, tenant_id)
        return Principal(
            id=principal_id, tenant_id=tenant_id, actor_type=actor_type,
            display="test", permissions=access.permissions, roles=access.role_names,
        )

    def test_no_tool_can_decide_a_gate(self):
        """The structural guarantee: there is no approval tool to call."""
        approving = [
            name for name in mcp_tools.TOOLS
            if any(word in name for word in ("approve", "decide", "sign_off", "authorise"))
        ]
        assert not approving, f"MCP exposes an approval tool: {approving}"

    def test_every_tool_declares_a_permission(self):
        for name, tool in mcp_tools.TOOLS.items():
            assert tool.permission, f"{name} declares no required permission"
            assert tool.permission != "*", f"{name} demands wildcard authority"

    def test_the_manifest_hides_tools_the_caller_cannot_use(self, tenant_id, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            operator = self._principal(db, tenant_id, people["operator"]["id"])
            officer = self._principal(db, tenant_id, people["officer"]["id"])
        operator_tools = {t["name"] for t in mcp_tools.manifests(operator)}
        officer_tools = {t["name"] for t in mcp_tools.manifests(officer)}

        assert "craft_create_risk" not in operator_tools
        assert "craft_create_risk" in officer_tools
        assert "craft_verify_audit_chain" not in operator_tools

    def test_calling_a_tool_without_the_permission_is_refused(self, tenant_id, people):
        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            operator = self._principal(db, tenant_id, people["operator"]["id"])
            with pytest.raises(ToolError) as exc:
                mcp_tools.invoke(db, operator, "craft_create_risk", {
                    "title": "Should never be recorded",
                    "inherent_likelihood": 3, "inherent_impact": 3,
                })
        assert "permission" in str(exc.value).lower()

    def test_an_agent_principal_gets_no_approval_tools(self, tenant_id, agent):
        principal = Principal(
            id=agent["id"], tenant_id=tenant_id, actor_type=ActorType.AGENT,
            display=agent["key"], permissions=frozenset(agent["permissions"]),
            roles=frozenset(agent["roles"]),
        )
        names = {t["name"] for t in mcp_tools.manifests(principal)}
        assert "craft_create_risk" in names, "The agent should still be able to work"
        for tool_name in names:
            assert not mcp_tools.TOOLS[tool_name].permission.startswith("gate.")

    def test_a_tool_call_is_written_to_the_audit_log(self, tenant_id, people):
        from sqlalchemy import select

        from app.models.audit import AuditLog

        with session_scope(tenant_id=tenant_id, bypass_rls=True) as db:
            officer = self._principal(db, tenant_id, people["officer"]["id"])
            result = mcp_tools.invoke(db, officer, "craft_risk_summary", {})
            db.commit()
            assert "summary" in result

            entry = db.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_id,
                       AuditLog.action == "mcp.craft_risk_summary")
                .order_by(AuditLog.seq.desc())
            ).scalars().first()
        assert entry is not None, "An MCP call left no audit trail"
        assert entry.actor_ref


class TestMcpProtocol:
    def test_initialize_advertises_the_server(self, client, headers):
        response = client.post(
            "/mcp", headers=headers["officer"],
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["serverInfo"]["name"] == "craft-grc"
        assert "no tool can approve" in result["instructions"].lower()

    def test_tools_list_returns_schemas(self, client, headers):
        response = client.post(
            "/mcp", headers=headers["officer"],
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        tools = response.json()["result"]["tools"]
        assert tools
        for tool in tools:
            assert tool["inputSchema"]["type"] == "object"
            assert tool["annotations"]["requiredScope"]

    def test_a_tool_failure_is_a_result_not_a_protocol_error(self, client, headers):
        """The client should see why it failed and be able to act, rather than
        receiving a transport-level error it cannot interpret."""
        response = client.post(
            "/mcp", headers=headers["officer"],
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "craft_list_controls",
                             "arguments": {"framework": "not_a_framework"}}},
        )
        assert response.status_code == 200
        body = response.json()
        assert "error" not in body
        assert body["result"]["isError"] is True

    def test_an_unknown_method_returns_the_standard_code(self, client, headers):
        response = client.post(
            "/mcp", headers=headers["officer"],
            json={"jsonrpc": "2.0", "id": 4, "method": "does/not/exist"},
        )
        assert response.json()["error"]["code"] == -32601

    def test_mcp_requires_authentication(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as anonymous:
            response = anonymous.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 5, "method": "tools/list"}
            )
        assert response.status_code == 401
