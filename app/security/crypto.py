"""Credential sealing, hashing and HMAC signing.

Provider API keys, webhook secrets and outbound integration credentials are
sealed with Fernet (AES-128-CBC + HMAC-SHA256) using a key held outside the
database. Two storage modes are supported and the choice is per record:

  * ``credential_vault_ref`` — a pointer into an external KMS/vault. Preferred
    in production; the platform resolves it at call time and never persists
    the material.
  * ``credential_ciphertext`` — sealed locally with CRAFT_ENCRYPTION_KEY, for
    deployments without a vault. The database alone is never sufficient to
    recover a key.

Nothing here ever returns a decrypted secret to an API response. The only
consumer of :func:`unseal` is the outbound HTTP client.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class SecretUnavailable(RuntimeError):
    """Raised when a credential cannot be resolved or decrypted."""


def _fernet() -> Fernet:
    key = get_settings().encryption_key
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:  # pragma: no cover - misconfiguration
        raise SecretUnavailable(
            "CRAFT_ENCRYPTION_KEY is not a valid Fernet key. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        ) from exc


def seal(plaintext: str) -> str:
    """Encrypt a secret for storage. Returns URL-safe ciphertext."""
    if not plaintext:
        raise ValueError("Refusing to seal an empty secret")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def unseal(ciphertext: str) -> str:
    """Decrypt a stored secret. Only the outbound HTTP client should call this."""
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise SecretUnavailable(
            "Stored credential could not be decrypted. The encryption key has "
            "probably changed; re-enter the credential."
        ) from exc


def resolve_vault_ref(ref: str) -> str:
    """Resolve an external vault reference to secret material.

    Two forms are supported out of the box:
      ``env:NAME``    read from the process environment (Render secret files
                      and env groups land here)
      ``file:/path``  read from a mounted secret file

    Extend this function to reach a real vault (AWS Secrets Manager, Azure Key
    Vault, HashiCorp Vault) without touching any caller.
    """
    if ref.startswith("env:"):
        value = os.environ.get(ref[4:], "")
        if not value:
            raise SecretUnavailable(f"Environment variable {ref[4:]} is not set")
        return value
    if ref.startswith("file:"):
        path = ref[5:]
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError as exc:
            raise SecretUnavailable(f"Secret file {path} is not readable") from exc
    raise SecretUnavailable(
        f"Unsupported vault reference '{ref[:12]}…'. Use env:NAME or file:/path."
    )


def hint(secret: str) -> str:
    """A recognisable, non-reversible tail for the console (never the key)."""
    return f"…{secret[-4:]}" if len(secret) >= 8 else "…"


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(payload: Any) -> str:
    """Deterministic JSON — the basis of every hash in the platform."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(payload: Any) -> str:
    return sha256_hex(canonical_json(payload))


def sign_hmac(secret: str, body: bytes) -> str:
    """Webhook signature: ``sha256=<hex>`` over the exact delivered bytes."""
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify_hmac(secret: str, body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_hmac(secret, body), signature)


def new_api_token() -> tuple[str, str, str]:
    """Return (token, sha256_hash, hint). The token is shown exactly once."""
    raw = "craft_" + base64.urlsafe_b64encode(secrets.token_bytes(30)).decode().rstrip("=")
    return raw, sha256_hex(raw), hint(raw)
