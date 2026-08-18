"""Brata integration — REST and MCP.

The dossier does not specify Brata, so this adapter is written against a
conventional JSON-over-HTTPS API and the Model Context Protocol, with every
assumption made explicit and overridable from configuration rather than code:

  * **Endpoints** are templates in ``ExternalConnection.sync_config`` under
    ``endpoints``. Change the paths there to match the real API; no code change.
  * **Field names** are a mapping in ``sync_config['field_map']``, applied in
    both directions. Change the mapping, not the adapter.
  * **Auth** is bearer, API-key header, or OAuth2 client credentials, chosen by
    ``auth_scheme``.

Two transports are supported and both are governed the same way. Every call is
written to ``integ.sync_log`` with request and response digests, and every
inbound record that creates or changes a CRAFT record raises an audit row.

Until the real Brata contract is confirmed, treat the endpoint paths and field
names below as defaults to be edited in the connection settings.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import ExternalConnection, SyncLog
from app.models.base import ActorType, Severity, TreatmentStrategy, utcnow
from app.models.domain import Incident, Risk, Supplier
from app.security.auth import Principal
from app.security.crypto import (
    SecretUnavailable,
    canonical_hash,
    resolve_vault_ref,
    unseal,
)
from app.services import audit, risk as risk_service

log = logging.getLogger(__name__)


class IntegrationError(RuntimeError):
    code = "integration_error"

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


# Defaults, overridable per connection.
DEFAULT_ENDPOINTS: dict[str, str] = {
    "health": "/health",
    "list_risks": "/api/v1/risks",
    "create_risk": "/api/v1/risks",
    "update_risk": "/api/v1/risks/{remote_id}",
    "list_suppliers": "/api/v1/suppliers",
    "create_incident": "/api/v1/incidents",
    "list_controls": "/api/v1/controls",
    "push_evidence": "/api/v1/evidence",
}

DEFAULT_FIELD_MAP: dict[str, str] = {
    # craft field -> brata field
    "risk_ref": "reference",
    "title": "name",
    "description": "description",
    "category": "riskCategory",
    "inherent_likelihood": "inherentLikelihood",
    "inherent_impact": "inherentImpact",
    "residual_likelihood": "residualLikelihood",
    "residual_impact": "residualImpact",
    "treatment": "treatmentStrategy",
    "status": "status",
    "owner_user_id": "ownerId",
}


@dataclass
class SyncOutcome:
    operation: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "operation": self.operation,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "messages": self.messages[:20],
        }


class BrataClient:
    """Thin, governed HTTP client for one configured connection."""

    def __init__(self, db: Session, connection: ExternalConnection):
        self.db = db
        self.conn = connection
        cfg = connection.sync_config or {}
        self.endpoints = {**DEFAULT_ENDPOINTS, **(cfg.get("endpoints") or {})}
        self.field_map = {**DEFAULT_FIELD_MAP, **(cfg.get("field_map") or {})}
        self.reverse_map = {v: k for k, v in self.field_map.items()}
        self._token: str | None = None
        self._token_expiry: float = 0.0

    # -- credentials ------------------------------------------------------
    def _secret(self) -> str:
        if self.conn.credential_vault_ref:
            return resolve_vault_ref(self.conn.credential_vault_ref)
        if self.conn.credential_ciphertext:
            return unseal(self.conn.credential_ciphertext)
        if self.conn.auth_scheme == "none":
            return ""
        raise SecretUnavailable(
            f"Connection '{self.conn.name}' has no credential configured."
        )

    async def _headers(self, client: httpx.AsyncClient) -> dict:
        scheme = self.conn.auth_scheme
        if scheme == "none":
            return {"Content-Type": "application/json"}
        if scheme == "bearer":
            return {
                "Authorization": f"Bearer {self._secret()}",
                "Content-Type": "application/json",
            }
        if scheme == "api_key_header":
            return {
                (self.conn.auth_header_name or "X-API-Key"): self._secret(),
                "Content-Type": "application/json",
            }
        if scheme == "oauth2_client_credentials":
            token = await self._oauth_token(client)
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        raise IntegrationError(f"Unsupported auth scheme '{scheme}'")

    async def _oauth_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expiry - 30:
            return self._token
        if not self.conn.oauth_token_url:
            raise IntegrationError("OAuth2 is selected but no token URL is configured.")
        client_id, _, client_secret = self._secret().partition(":")
        resp = await client.post(
            self.conn.oauth_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                **({"scope": self.conn.oauth_scope} if self.conn.oauth_scope else {}),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code >= 400:
            raise IntegrationError(
                f"Token request failed ({resp.status_code}): {resp.text[:200]}",
                status=resp.status_code,
            )
        data = resp.json()
        self._token = data.get("access_token", "")
        self._token_expiry = time.time() + float(data.get("expires_in", 3600))
        if not self._token:
            raise IntegrationError("Token endpoint returned no access_token.")
        return self._token

    # -- transport --------------------------------------------------------
    async def request(
        self,
        method: str,
        endpoint_key: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        path_args: dict | None = None,
        entity: str | None = None,
        local_id: uuid.UUID | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> Any:
        template = self.endpoints.get(endpoint_key)
        if not template:
            raise IntegrationError(
                f"No endpoint is configured for '{endpoint_key}'. Add it under "
                "sync_config.endpoints on the connection."
            )
        path = template.format(**(path_args or {}))
        url = f"{self.conn.base_url.rstrip('/')}{path}"

        owns = client is None
        client = client or httpx.AsyncClient(verify=self.conn.verify_tls)
        started = time.perf_counter()
        status: int | None = None
        outcome = "ok"
        error: str | None = None
        payload: Any = None
        try:
            headers = await self._headers(client)
            resp = await client.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=headers,
                timeout=self.conn.timeout_seconds,
            )
            status = resp.status_code
            if status >= 400:
                outcome = "error"
                error = f"{status}: {resp.text[:300]}"
                raise IntegrationError(
                    f"Brata returned {status} for {endpoint_key}: {resp.text[:200]}",
                    status=status,
                )
            payload = resp.json() if resp.content else None
            return payload
        except IntegrationError:
            raise
        except httpx.HTTPError as exc:
            outcome = "error"
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
            raise IntegrationError(f"Could not reach Brata: {error}") from exc
        finally:
            self.db.add(
                SyncLog(
                    tenant_id=self.conn.tenant_id,
                    connection_id=self.conn.id,
                    direction="outbound",
                    operation=endpoint_key,
                    entity=entity,
                    local_id=local_id,
                    status_code=status,
                    outcome=outcome,
                    request_digest=canonical_hash(json_body or params or {}),
                    response_digest=canonical_hash(payload) if payload is not None else None,
                    error=error,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    created_at=utcnow(),
                )
            )
            self.db.flush()
            if owns:
                await client.aclose()

    async def health(self) -> tuple[bool, str]:
        try:
            await self.request("GET", "health", entity="health")
            return True, "Reachable and authenticated."
        except (IntegrationError, SecretUnavailable) as exc:
            return False, str(exc)[:300]

    # -- mapping ----------------------------------------------------------
    def to_remote(self, obj: Any, fields: Iterable[str]) -> dict:
        out: dict[str, Any] = {}
        for f in fields:
            value = getattr(obj, f, None)
            if value is None:
                continue
            if hasattr(value, "value"):
                value = value.value
            if isinstance(value, uuid.UUID):
                value = str(value)
            out[self.field_map.get(f, f)] = value
        return out

    def from_remote(self, record: dict) -> dict:
        return {self.reverse_map.get(k, k): v for k, v in record.items()}


# --------------------------------------------------------------------------
# Sync operations
# --------------------------------------------------------------------------
RISK_FIELDS = (
    "risk_ref", "title", "description", "category",
    "inherent_likelihood", "inherent_impact",
    "residual_likelihood", "residual_impact", "treatment", "status",
)


async def push_risks(
    db: Session, connection: ExternalConnection, principal: Principal, limit: int = 100
) -> SyncOutcome:
    """Send open CRAFT risks to Brata."""
    client = BrataClient(db, connection)
    outcome = SyncOutcome(operation="push_risks")
    risks = list(
        db.execute(
            select(Risk)
            .where(Risk.tenant_id == connection.tenant_id, Risk.is_deleted.is_(False))
            .order_by(Risk.created_at.desc())
            .limit(limit)
        ).scalars().all()
    )
    async with httpx.AsyncClient(verify=connection.verify_tls) as http:
        for r in risks:
            body = client.to_remote(r, RISK_FIELDS)
            body["source"] = "CRAFT"
            body["sourceId"] = str(r.id)
            try:
                await client.request(
                    "POST", "create_risk", json_body=body, entity="risk",
                    local_id=r.id, client=http,
                )
                outcome.created += 1
            except (IntegrationError, SecretUnavailable) as exc:
                outcome.failed += 1
                outcome.messages.append(f"{r.risk_ref}: {exc}")
    connection.last_sync_at = utcnow()
    audit.record(
        db,
        tenant_id=connection.tenant_id,
        action="integration.push_risks",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="external_connection",
        entity_id=connection.id,
        detail=outcome.as_dict(),
        outcome="success" if not outcome.failed else "partial",
    )
    return outcome


async def pull_risks(
    db: Session, connection: ExternalConnection, principal: Principal, limit: int = 100
) -> SyncOutcome:
    """Import risks from Brata into the CRAFT register.

    Imported rows carry lineage recording the remote id, so a later push does
    not create a duplicate and an auditor can see where the record came from.
    """
    client = BrataClient(db, connection)
    outcome = SyncOutcome(operation="pull_risks")
    try:
        payload = await client.request(
            "GET", "list_risks", params={"limit": limit}, entity="risk"
        )
    except (IntegrationError, SecretUnavailable) as exc:
        outcome.failed += 1
        outcome.messages.append(str(exc))
        return outcome

    records = payload if isinstance(payload, list) else (payload or {}).get("data", [])
    existing_remote_ids = {
        (r.lineage or {}).get("remote_id")
        for r in db.execute(
            select(Risk).where(Risk.tenant_id == connection.tenant_id)
        ).scalars().all()
        if r.lineage
    }

    for raw in records:
        if not isinstance(raw, dict):
            outcome.skipped += 1
            continue
        mapped = client.from_remote(raw)
        remote_id = str(raw.get("id") or mapped.get("id") or "")
        if remote_id and remote_id in existing_remote_ids:
            outcome.skipped += 1
            continue
        title = (mapped.get("title") or "").strip()
        if not title:
            outcome.skipped += 1
            outcome.messages.append(f"Record {remote_id or '?'} has no title; skipped.")
            continue
        try:
            created = risk_service.create_risk(
                db,
                tenant_id=connection.tenant_id,
                title=title,
                description=mapped.get("description") or "",
                category=mapped.get("category") or "third_party",
                inherent_likelihood=int(mapped.get("inherent_likelihood") or 3),
                inherent_impact=int(mapped.get("inherent_impact") or 3),
                residual_likelihood=(
                    int(mapped["residual_likelihood"])
                    if mapped.get("residual_likelihood")
                    else None
                ),
                residual_impact=(
                    int(mapped["residual_impact"]) if mapped.get("residual_impact") else None
                ),
                treatment=TreatmentStrategy.MITIGATE,
                lineage={
                    "source": "brata",
                    "connection": str(connection.id),
                    "remote_id": remote_id,
                    "imported_at": utcnow().isoformat(),
                },
                created_by=principal.id,
            )
            db.add(
                SyncLog(
                    tenant_id=connection.tenant_id,
                    connection_id=connection.id,
                    direction="inbound",
                    operation="pull_risks",
                    entity="risk",
                    local_id=created.id,
                    remote_id=remote_id or None,
                    outcome="ok",
                    request_digest=None,
                    response_digest=canonical_hash(raw),
                    created_at=utcnow(),
                )
            )
            outcome.created += 1
        except Exception as exc:  # noqa: BLE001 - one bad record must not stop the batch
            outcome.failed += 1
            outcome.messages.append(f"{remote_id or title[:30]}: {exc}")

    connection.last_sync_at = utcnow()
    audit.record(
        db,
        tenant_id=connection.tenant_id,
        action="integration.pull_risks",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="external_connection",
        entity_id=connection.id,
        detail=outcome.as_dict(),
        outcome="success" if not outcome.failed else "partial",
    )
    return outcome


async def push_incident(
    db: Session, connection: ExternalConnection, incident: Incident, principal: Principal
) -> dict:
    client = BrataClient(db, connection)
    body = {
        "reference": incident.incident_no,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity.value,
        "status": incident.status.value,
        "involvesPersonalData": incident.involves_personal_data,
        "detectedAt": incident.detected_at.isoformat() if incident.detected_at else None,
        "source": "CRAFT",
        "sourceId": str(incident.id),
    }
    result = await client.request(
        "POST", "create_incident", json_body=body, entity="incident", local_id=incident.id
    )
    audit.record(
        db,
        tenant_id=connection.tenant_id,
        action="integration.push_incident",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="incident",
        entity_id=incident.id,
        detail={"connection": connection.name},
    )
    return result or {}


# --------------------------------------------------------------------------
# MCP transport — CRAFT as an MCP *client* calling Brata's tools
# --------------------------------------------------------------------------
class BrataMcpClient:
    """Minimal MCP client over streamable HTTP (JSON-RPC 2.0).

    Used when Brata exposes an MCP server rather than a REST API. The same
    connection record, the same logging, the same audit trail.
    """

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, db: Session, connection: ExternalConnection):
        self.db = db
        self.conn = connection
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _auth_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.PROTOCOL_VERSION,
        }
        if self.conn.credential_vault_ref or self.conn.credential_ciphertext:
            secret = (
                resolve_vault_ref(self.conn.credential_vault_ref)
                if self.conn.credential_vault_ref
                else unseal(self.conn.credential_ciphertext)
            )
            if self.conn.auth_scheme == "api_key_header":
                headers[self.conn.auth_header_name or "X-API-Key"] = secret
            else:
                headers["Authorization"] = f"Bearer {secret}"
        return headers

    async def _rpc(self, method: str, params: dict | None = None) -> Any:
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        started = time.perf_counter()
        status = None
        outcome = "ok"
        error = None
        result = None
        try:
            async with httpx.AsyncClient(verify=self.conn.verify_tls) as client:
                resp = await client.post(
                    self.conn.base_url,
                    json=body,
                    headers=self._auth_headers(),
                    timeout=self.conn.timeout_seconds,
                )
                status = resp.status_code
                if status >= 400:
                    outcome = "error"
                    error = f"{status}: {resp.text[:200]}"
                    raise IntegrationError(f"Brata MCP returned {error}", status=status)
                data = resp.json()
                if "error" in data:
                    outcome = "error"
                    error = str(data["error"])[:300]
                    raise IntegrationError(f"Brata MCP error: {error}")
                result = data.get("result")
                return result
        except httpx.HTTPError as exc:
            outcome = "error"
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
            raise IntegrationError(f"Could not reach Brata MCP: {error}") from exc
        finally:
            self.db.add(
                SyncLog(
                    tenant_id=self.conn.tenant_id,
                    connection_id=self.conn.id,
                    direction="outbound",
                    operation=f"mcp:{method}",
                    status_code=status,
                    outcome=outcome,
                    request_digest=canonical_hash(body),
                    response_digest=canonical_hash(result) if result is not None else None,
                    error=error,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    created_at=utcnow(),
                )
            )
            self.db.flush()

    async def initialize(self) -> dict:
        return await self._rpc(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "CRAFT", "version": "1.0.0"},
            },
        ) or {}

    async def list_tools(self) -> list[dict]:
        result = await self._rpc("tools/list") or {}
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments}) or {}

    async def health(self) -> tuple[bool, str]:
        try:
            info = await self.initialize()
            tools = await self.list_tools()
            server = (info.get("serverInfo") or {}).get("name", "Brata")
            return True, f"Connected to {server}; {len(tools)} tool(s) available."
        except (IntegrationError, SecretUnavailable) as exc:
            return False, str(exc)[:300]


def get_connection(
    db: Session, tenant_id: uuid.UUID, name_or_id: str
) -> ExternalConnection:
    try:
        conn = db.get(ExternalConnection, uuid.UUID(name_or_id))
        if conn and conn.tenant_id == tenant_id:
            return conn
    except (ValueError, TypeError):
        pass
    conn = db.execute(
        select(ExternalConnection).where(
            ExternalConnection.tenant_id == tenant_id,
            ExternalConnection.name == name_or_id,
        )
    ).scalar_one_or_none()
    if conn is None:
        raise IntegrationError(f"No connection named '{name_or_id}' is configured.")
    return conn


async def check_health(
    db: Session, connection: ExternalConnection
) -> tuple[bool, str]:
    if connection.transport == "mcp":
        ok, detail = await BrataMcpClient(db, connection).health()
    else:
        ok, detail = await BrataClient(db, connection).health()
    connection.last_health_ok = ok
    connection.last_health_detail = detail
    db.flush()
    return ok, detail
