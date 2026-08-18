"""Request-scoped dependencies.

Authorization happens in two layers, deliberately:

  * the token layer, here, checks the bearer token is valid and resolves the
    principal's effective permissions from the database rather than trusting
    the scope claim alone — so revoking a role takes effect immediately rather
    than when the token expires
  * the service layer checks the fine-grained permission, resource scope and
    segregation of duties before any state change

Every authenticated request also binds ``app.tenant_id`` on the database
session, which is what the row-level security policies read.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Callable, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, identity_lookup, set_session_context
from app.models.base import ActorType, utcnow
from app.models.iam import AgentIdentity, ApiToken, UserAccount
from app.security.auth import Principal, TokenInvalid, decode_token, principal_from_claims
from app.security.crypto import sha256_hex
from app.security.rbac import AuthorizationError, resolve_access

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _unauthenticated(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "unauthenticated", "message": detail}},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_api_token(db: Session, raw: str) -> Principal | None:
    row = db.execute(
        select(ApiToken).where(ApiToken.token_hash == sha256_hex(raw))
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.revoked_at or (row.expires_at and row.expires_at < utcnow()):
        raise _unauthenticated("This API token has expired or been revoked.")
    row.last_used_at = utcnow()

    access = resolve_access(db, row.principal_id, row.tenant_id)
    granted = set(access.permissions)
    if row.scopes:
        # A token can never exceed the permissions of the principal behind it.
        granted &= set(row.scopes)
    display = "token"
    if row.principal_type == ActorType.AGENT:
        agent = db.get(AgentIdentity, row.principal_id)
        display = agent.agent_key if agent else "agent"
    else:
        user = db.get(UserAccount, row.principal_id)
        display = user.email if user else "user"
    return Principal(
        id=row.principal_id,
        tenant_id=row.tenant_id,
        actor_type=row.principal_type,
        display=display,
        permissions=frozenset(granted),
        roles=access.role_names,
        token_id=str(row.id),
    )


def get_principal(
    request: Request,
    db: DbSession,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
    session_token: Annotated[Optional[str], Cookie(alias="craft_session")] = None,
) -> Principal:
    """Resolve the acting principal from a bearer token, API token or session cookie."""
    raw = credentials.credentials if credentials else session_token
    if not raw:
        raise _unauthenticated("Sign in or present a bearer token to continue.")

    principal: Principal | None = None
    # Resolving a token or an account means searching before the tenant is
    # known, so this one step runs cross-tenant. set_session_context below
    # closes the window as soon as the tenant is established.
    with identity_lookup(db):
        if raw.startswith("craft_"):
            principal = _resolve_api_token(db, raw)
            if principal is None:
                raise _unauthenticated("This API token is not recognised.")
        else:
            try:
                claims = decode_token(raw)
            except TokenInvalid as exc:
                raise _unauthenticated(f"Token rejected: {exc}") from exc
            if claims.get("kind") == "refresh":
                raise _unauthenticated("A refresh token cannot be used to call the API.")
            base = principal_from_claims(claims)
            # Re-resolve permissions so a revoked grant takes effect at once,
            # rather than when the token happens to expire.
            access = resolve_access(db, base.id, base.tenant_id)
            principal = Principal(
                id=base.id,
                tenant_id=base.tenant_id,
                actor_type=base.actor_type,
                display=base.display,
                permissions=access.permissions,
                roles=access.role_names,
                token_id=base.token_id,
            )

        if principal.actor_type == ActorType.HUMAN:
            user = db.get(UserAccount, principal.id)
            if user is None or user.status != "active":
                raise _unauthenticated("This account is not active.")
        elif principal.actor_type == ActorType.AGENT:
            agent = db.get(AgentIdentity, principal.id)
            if agent is None or agent.status != "active":
                raise _unauthenticated("This agent identity is not active.")

    set_session_context(db, principal.tenant_id, principal.actor_ref)
    request.state.principal = principal
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def requires(*permissions: str) -> Callable:
    """Endpoint guard. Declares the permission an endpoint needs; default deny."""

    def guard(principal: CurrentPrincipal) -> Principal:
        if "*" in principal.permissions:
            return principal
        missing = [p for p in permissions if p not in principal.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "permission_denied",
                        "message": f"This action requires: {', '.join(missing)}",
                        "request_id": None,
                    }
                },
            )
        return principal

    return guard


def requires_any(*permissions: str) -> Callable:
    def guard(principal: CurrentPrincipal) -> Principal:
        if "*" in principal.permissions or any(
            p in principal.permissions for p in permissions
        ):
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "permission_denied",
                    "message": f"This action requires one of: {', '.join(permissions)}",
                }
            },
        )

    return guard


def authz_exception(exc: AuthorizationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": exc.code, "message": str(exc)}},
    )


def request_id(
    x_request_id: Annotated[Optional[str], Header(alias="X-Request-Id")] = None,
) -> str:
    return x_request_id or uuid.uuid4().hex


RequestId = Annotated[str, Depends(request_id)]
IdempotencyKey = Annotated[Optional[str], Header(alias="Idempotency-Key")]
