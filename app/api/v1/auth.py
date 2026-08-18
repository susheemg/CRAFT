"""Authentication endpoints."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import CurrentPrincipal, DbSession, RequestId, requires
from app.api.schemas import (
    ApiTokenRequest,
    ApiTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
)
from app.config import get_settings
from app.db import identity_lookup, set_session_context
from app.models.base import ActorType, utcnow
from app.models.iam import AgentIdentity, ApiToken, Tenant, UserAccount
from app.security.auth import (
    TokenInvalid,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.security.crypto import new_api_token
from app.security.rbac import resolve_access
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Authentication"])
_settings = get_settings()


@router.post("/login", response_model=TokenResponse, summary="Sign in with local credentials")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    request_id: RequestId,
) -> TokenResponse:
    """Local sign-in for the bootstrap and non-federated accounts.

    Where an identity provider is configured, users sign in through it instead;
    this route exists so the platform can be stood up before federation and can
    be disabled with ``CRAFT_ALLOW_LOCAL_LOGIN=false``.
    """
    if not _settings.allow_local_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "local_login_disabled",
                    "message": "Sign in through your organisation's identity provider.",
                }
            },
        )

    # Matching an email address means searching every tenant, because which
    # tenant the address belongs to is precisely what is being established.
    with identity_lookup(db):
        user = db.execute(
            select(UserAccount).where(UserAccount.email == payload.email.lower())
        ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        # One message for both cases: do not reveal which accounts exist.
        if user is not None:
            set_session_context(db, user.tenant_id, f"human:{user.email}")
            audit.record(
                db,
                tenant_id=user.tenant_id,
                action="auth.login",
                outcome="failure",
                actor_type=ActorType.HUMAN,
                actor_ref=f"human:{user.email}",
                actor_id=user.id,
                entity="user_account",
                entity_id=user.id,
                request_id=request_id,
                ip_address=request.client.host if request.client else None,
                detail={"reason": "invalid_credentials"},
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "invalid_credentials",
                    "message": "That email address and password did not match.",
                    "request_id": request_id,
                }
            },
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "account_inactive", "message": "This account is not active."}},
        )

    set_session_context(db, user.tenant_id, f"human:{user.email}")
    access = resolve_access(db, user.id, user.tenant_id)
    token = create_access_token(
        user.id, user.tenant_id, ActorType.HUMAN, user.email, sorted(access.permissions)
    )
    refresh = create_refresh_token(user.id, user.tenant_id)
    user.last_login_at = utcnow()

    audit.record(
        db,
        tenant_id=user.tenant_id,
        action="auth.login",
        actor_type=ActorType.HUMAN,
        actor_ref=f"human:{user.email}",
        actor_id=user.id,
        entity="user_account",
        entity_id=user.id,
        request_id=request_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:300],
        detail={"roles": list(access.role_names)},
    )
    db.commit()

    response.set_cookie(
        "craft_session",
        token,
        max_age=_settings.access_token_minutes * 60,
        httponly=True,
        secure=_settings.is_production,
        samesite="lax",
        path="/",
    )
    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        expires_in=_settings.access_token_minutes * 60,
        principal={
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "tenant_id": str(user.tenant_id),
            "roles": list(access.role_names),
            "permissions": sorted(access.permissions),
        },
    )


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token")
def refresh_token(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except TokenInvalid as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_token", "message": str(exc)}},
        ) from exc
    if claims.get("kind") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_token", "message": "Not a refresh token."}},
        )
    user_id, tenant_id = uuid.UUID(claims["sub"]), uuid.UUID(claims["tid"])
    with identity_lookup(db):
        user = db.get(UserAccount, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "account_inactive", "message": "This account is not active."}},
        )
    set_session_context(db, tenant_id, f"human:{user.email}")
    access = resolve_access(db, user_id, tenant_id)
    return TokenResponse(
        access_token=create_access_token(
            user_id, tenant_id, ActorType.HUMAN, user.email, sorted(access.permissions)
        ),
        refresh_token=create_refresh_token(user_id, tenant_id),
        expires_in=_settings.access_token_minutes * 60,
        principal={"id": str(user_id), "email": user.email, "roles": list(access.role_names)},
    )


@router.post("/logout", summary="Sign out")
def logout(response: Response) -> dict:
    response.delete_cookie("craft_session", path="/")
    return {"signed_out": True}


@router.get("/me", summary="Describe the current principal")
def whoami(principal: CurrentPrincipal) -> dict:
    return {
        "id": str(principal.id),
        "tenant_id": str(principal.tenant_id),
        "type": principal.actor_type.value,
        "display": principal.display,
        "is_human": principal.is_human,
        "roles": list(principal.roles),
        "permissions": sorted(principal.permissions),
    }


@router.post(
    "/tokens",
    response_model=ApiTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue an API token for a service or agent",
)
def create_token(
    payload: ApiTokenRequest,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("sec.identity.manage")),
) -> ApiTokenResponse:
    """The token is returned once and stored only as a SHA-256 hash.

    A token can never carry more than the principal behind it holds: scopes are
    intersected with the principal's effective permissions at every request.
    """
    target_id = payload.principal_id or principal.id
    target_type = ActorType(payload.principal_type)
    if target_type == ActorType.AGENT:
        if db.get(AgentIdentity, target_id) is None:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "not_found", "message": "No such agent identity."}},
            )
    elif db.get(UserAccount, target_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "No such user account."}},
        )

    raw, token_hash, token_hint = new_api_token()
    expires = utcnow() + timedelta(days=payload.expires_days)
    row = ApiToken(
        tenant_id=principal.tenant_id,
        name=payload.name,
        principal_id=target_id,
        principal_type=target_type,
        token_hash=token_hash,
        token_hint=token_hint,
        scopes=payload.scopes or None,
        expires_at=expires,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="auth.token_issued",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="api_token",
        entity_id=row.id,
        request_id=request_id,
        detail={
            "name": payload.name,
            "principal_type": target_type.value,
            "scopes": payload.scopes,
            "expires_at": expires.isoformat(),
        },
    )
    db.commit()
    return ApiTokenResponse(
        id=row.id, name=row.name, token=raw, hint=token_hint, expires_at=expires
    )


@router.delete("/tokens/{token_id}", summary="Revoke an API token")
def revoke_token(
    token_id: uuid.UUID,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("sec.identity.manage")),
) -> dict:
    row = db.get(ApiToken, token_id)
    if row is None or row.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such token."}}
        )
    row.revoked_at = utcnow()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="auth.token_revoked",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="api_token",
        entity_id=row.id,
        request_id=request_id,
    )
    db.commit()
    return {"revoked": True, "id": str(token_id)}


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
)
def create_user(
    payload: UserCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("sec.identity.manage")),
) -> dict:
    existing = db.execute(
        select(UserAccount).where(
            UserAccount.tenant_id == principal.tenant_id,
            UserAccount.email == payload.email.lower(),
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "conflict",
                    "message": "An account with that email address already exists.",
                }
            },
        )
    user = UserAccount(
        tenant_id=principal.tenant_id,
        email=payload.email.lower(),
        display_name=payload.display_name,
        status="active",
        idp_subject=payload.idp_subject,
        password_hash=hash_password(payload.password) if payload.password else None,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="identity.user_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="user_account",
        entity_id=user.id,
        after_state={"email": user.email, "display_name": user.display_name},
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "has_password": bool(user.password_hash),
    }


@router.get("/users", summary="List user accounts")
def list_users(db: DbSession, principal=Depends(requires("sec.identity.manage"))) -> dict:
    users = db.execute(
        select(UserAccount).where(UserAccount.tenant_id == principal.tenant_id)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "status": u.status,
                "roles": list(resolve_access(db, u.id, u.tenant_id).role_names),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ]
    }
