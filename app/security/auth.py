"""Authentication and the acting principal.

Three ways to authenticate, all resolving to the same :class:`Principal`:

  * an interactive session cookie or bearer JWT held by a human
  * a bearer JWT issued to a service or AI agent (client-credentials style)
  * a long-lived API token, stored only as a hash, used by integrations

The principal carries its type. That single field is what stops an AI agent
deciding a human approval gate: the gate endpoint asserts ``is_human`` before
anything else, and no permission grant can override it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import base64
import hashlib

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.models.base import ActorType

_settings = get_settings()

ALGORITHM = "HS256"
BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 12


# --------------------------------------------------------------------------
# Passwords (bootstrap and non-federated accounts only)
# --------------------------------------------------------------------------
def _prepare(password: str) -> bytes:
    """bcrypt silently truncates above 72 bytes, so pre-hash first.

    SHA-256 then base64 gives a fixed 44-byte input, which means a long
    passphrase keeps all of its entropy instead of being cut short.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("ascii"))
    except (ValueError, TypeError):  # pragma: no cover - malformed stored hash
        return False


# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Principal:
    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_type: ActorType
    display: str
    permissions: frozenset[str] = field(default_factory=frozenset)
    roles: tuple[str, ...] = ()
    token_id: Optional[str] = None

    @property
    def is_human(self) -> bool:
        return self.actor_type == ActorType.HUMAN

    @property
    def is_agent(self) -> bool:
        return self.actor_type == ActorType.AGENT

    @property
    def actor_ref(self) -> str:
        return f"{self.actor_type.value}:{self.display}"

    def has(self, permission: str) -> bool:
        return permission in self.permissions


SYSTEM_PRINCIPAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def system_principal(tenant_id: uuid.UUID) -> Principal:
    """Used by schedulers and the seeder. Not reachable over the network."""
    return Principal(
        id=SYSTEM_PRINCIPAL_ID,
        tenant_id=tenant_id,
        actor_type=ActorType.SYSTEM,
        display="scheduler",
        permissions=frozenset({"*"}),
    )


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------
def create_access_token(
    principal_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_type: ActorType,
    display: str,
    scopes: list[str],
    minutes: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=minutes or _settings.access_token_minutes)
    payload = {
        "sub": str(principal_id),
        "tid": str(tenant_id),
        "typ": actor_type.value,
        "name": display,
        "scope": " ".join(sorted(scopes)),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": _settings.base_url,
        "aud": "craft",
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(principal_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(principal_id),
        "tid": str(tenant_id),
        "kind": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=_settings.refresh_token_days)).timestamp()),
        "iss": _settings.base_url,
        "aud": "craft",
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _settings.secret_key, algorithm=ALGORITHM)


class TokenInvalid(Exception):
    """Raised when a token fails signature, audience, expiry or shape checks."""


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _settings.secret_key,
            algorithms=[ALGORITHM],
            audience="craft",
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError as exc:
        raise TokenInvalid(str(exc)) from exc


def principal_from_claims(claims: dict) -> Principal:
    try:
        return Principal(
            id=uuid.UUID(claims["sub"]),
            tenant_id=uuid.UUID(claims["tid"]),
            actor_type=ActorType(claims.get("typ", "human")),
            display=claims.get("name", "unknown"),
            permissions=frozenset(claims.get("scope", "").split()),
            token_id=claims.get("jti"),
        )
    except (KeyError, ValueError) as exc:
        raise TokenInvalid("Token is missing required claims") from exc
