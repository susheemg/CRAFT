"""CRAFT as an MCP server.

Speaks JSON-RPC 2.0 over HTTP POST — the streamable HTTP transport — so any MCP
client, Brata included, can discover and call the tools in
:mod:`app.mcp.tools`.

Authentication is the same bearer token used everywhere else, and every call
runs through the same permission checks and the same audit log. The protocol
gives external agents a convenient shape to work in; it does not give them a
different set of rules.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.deps import CurrentPrincipal, DbSession
from app.config import get_settings
from app.mcp import tools as tool_registry
from app.mcp.tools import ToolError

log = logging.getLogger(__name__)
_settings = get_settings()

PROTOCOL_VERSION = "2025-06-18"

router = APIRouter(prefix="/mcp", tags=["MCP"])

# JSON-RPC 2.0 reserved codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _result(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str, data: dict | None = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message}
    if data:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


@router.get("/manifest", summary="Tool manifest (plain HTTP convenience)")
def manifest(principal: CurrentPrincipal) -> dict:
    """A non-JSON-RPC view of the same manifest, for humans and simple clients."""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {"name": "craft-grc", "version": _settings.version},
        "tools": tool_registry.manifests(principal),
        "principal": {
            "type": principal.actor_type.value,
            "display": principal.display,
            "permissions": sorted(principal.permissions),
        },
    }


@router.post("", summary="MCP JSON-RPC endpoint")
async def rpc(request: Request, db: DbSession, principal: CurrentPrincipal) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            _error(None, PARSE_ERROR, "Request body is not valid JSON."), status_code=400
        )

    if isinstance(body, list):
        # Batched calls: each is handled independently; notifications drop out.
        responses = [await _dispatch(db, principal, item) for item in body]
        return JSONResponse([r for r in responses if r is not None])

    response = await _dispatch(db, principal, body)
    if response is None:
        return JSONResponse({}, status_code=202)  # notification, nothing to return
    return JSONResponse(response)


async def _dispatch(db, principal, message: dict) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Expected a JSON-RPC 2.0 message.")

    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    is_notification = "id" not in message

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "logging": {}},
                "serverInfo": {"name": "craft-grc", "version": _settings.version},
                "instructions": (
                    "CRAFT is a governance, risk and compliance platform. Read tools "
                    "expose the risk register, control positions, gaps and readiness. "
                    "Write tools record risks, gaps, evidence and incidents. No tool "
                    "can approve anything: decisions that need approval raise a gate "
                    "for an authorised person and return its identifier."
                ),
            }
        elif method in {"notifications/initialized", "initialized"}:
            return None
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tool_registry.manifests(principal)}
        elif method == "tools/call":
            name = params.get("name")
            if not name:
                return None if is_notification else _error(
                    request_id, INVALID_PARAMS, "A tool name is required."
                )
            arguments = params.get("arguments") or {}
            try:
                payload = tool_registry.invoke(db, principal, name, arguments)
                db.commit()
                result = {
                    "content": [{"type": "text", "text": _as_text(payload)}],
                    "structuredContent": payload,
                    "isError": False,
                }
            except ToolError as exc:
                db.rollback()
                # A tool-level failure is a result, not a protocol error: the
                # client should see the reason and be able to act on it.
                result = {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                }
            except Exception as exc:  # pragma: no cover - unexpected
                db.rollback()
                log.exception("MCP tool %s failed", name)
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": f"The tool failed: {type(exc).__name__}. "
                            "The failure has been logged.",
                        }
                    ],
                    "isError": True,
                }
        elif method in {"resources/list", "prompts/list"}:
            # Declared for well-behaved clients that probe capabilities.
            result = {"resources": []} if method.startswith("resources") else {"prompts": []}
        else:
            return None if is_notification else _error(
                request_id, METHOD_NOT_FOUND, f"Method '{method}' is not supported."
            )
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        log.exception("MCP dispatch failed for %s", method)
        return None if is_notification else _error(
            request_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}"
        )

    return None if is_notification else _result(request_id, result)


def _as_text(payload: dict) -> str:
    """A readable rendering for clients that only display text content."""
    import json

    return json.dumps(payload, indent=2, default=str)
