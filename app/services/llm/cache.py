"""Prompt caching — two layers, both measured.

**Layer 1: exact-match response cache (this module).**
Keyed on SHA-256 of the model, the system prefix, the rendered prompt and the
sampling parameters. A hit returns the stored completion with no provider call
at all. This is the large saving: assessing the same control against the same
policy text, re-running a supplier questionnaire, regenerating a report that
has not changed — all common in compliance work, all fully deterministic when
temperature is 0.

Only deterministic calls are cached. A route with a non-zero temperature is
never served from cache, because reproducing a sampled answer would be
misleading rather than economical.

**Layer 2: provider-native prefix caching (handled in the adapters).**
When the exact-match cache misses, the request still carries a stable,
cacheable prefix in front of the variable part, so Anthropic and OpenAI charge
the discounted cached rate for the shared head. The adapters report
``cache_read_tokens`` and the gateway prices them at the model's cache-read
rate.

Both layers write to the same ledger, so the console can answer "what did
caching save us this month?" with a number rather than an assertion.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.llm import ModelInvocation, PromptCacheEntry
from app.security.crypto import sha256_hex

log = logging.getLogger(__name__)


@dataclass
class CacheLookup:
    key: str
    entry: PromptCacheEntry | None

    @property
    def hit(self) -> bool:
        return self.entry is not None


def build_key(
    *,
    model_key: str,
    cache_prefix: str,
    system: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> str:
    """Deterministic cache key. Any change to any input yields a different key."""
    material = "\u0000".join(
        [
            model_key,
            cache_prefix or "",
            system or "",
            prompt,
            f"{temperature:.3f}",
            str(max_tokens),
            "json" if json_mode else "text",
        ]
    )
    return sha256_hex(material)


def is_cacheable(temperature: float, cache_enabled: bool) -> bool:
    """Cache only what can be reproduced exactly."""
    return bool(cache_enabled) and temperature <= 0.0001


def lookup(db: Session, tenant_id: uuid.UUID, key: str) -> CacheLookup:
    entry = db.execute(
        select(PromptCacheEntry).where(
            PromptCacheEntry.tenant_id == tenant_id,
            PromptCacheEntry.cache_key == key,
            PromptCacheEntry.expires_at > utcnow(),
        )
    ).scalar_one_or_none()
    return CacheLookup(key=key, entry=entry)


def record_hit(db: Session, entry: PromptCacheEntry) -> float:
    """Register a hit and return the cost avoided by not making the call."""
    saved = float(entry.original_cost or 0)
    entry.hit_count += 1
    entry.last_hit_at = utcnow()
    entry.saved_cost = float(entry.saved_cost or 0) + saved
    db.flush()
    return saved


def store(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    key: str,
    task_class: str,
    model_key: str,
    prompt_digest: str,
    response_text: str,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    ttl_seconds: int,
    meta: dict | None = None,
) -> PromptCacheEntry:
    now = utcnow()
    existing = db.execute(
        select(PromptCacheEntry).where(
            PromptCacheEntry.tenant_id == tenant_id, PromptCacheEntry.cache_key == key
        )
    ).scalar_one_or_none()
    if existing:
        existing.response_text = response_text
        existing.response_meta = meta
        existing.tokens_in = tokens_in
        existing.tokens_out = tokens_out
        existing.original_cost = cost
        existing.expires_at = now + timedelta(seconds=ttl_seconds)
        db.flush()
        return existing

    entry = PromptCacheEntry(
        tenant_id=tenant_id,
        cache_key=key,
        task_class=task_class,
        model_key=model_key,
        prompt_digest=prompt_digest,
        response_text=response_text,
        response_meta=meta,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        original_cost=cost,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(entry)
    db.flush()
    return entry


def sweep_expired(db: Session, limit: int = 5000) -> int:
    """Remove expired entries. Safe to run on a schedule."""
    result = db.execute(
        delete(PromptCacheEntry).where(
            PromptCacheEntry.id.in_(
                select(PromptCacheEntry.id)
                .where(PromptCacheEntry.expires_at <= utcnow())
                .limit(limit)
            )
        )
    )
    return result.rowcount or 0


def invalidate(
    db: Session, tenant_id: uuid.UUID, task_class: str | None = None
) -> int:
    """Drop cached answers after a prompt or knowledge change.

    Call this whenever a prompt template version is activated or a policy
    document is superseded — a stale cached assessment is worse than an
    expensive fresh one.
    """
    stmt = delete(PromptCacheEntry).where(PromptCacheEntry.tenant_id == tenant_id)
    if task_class:
        stmt = stmt.where(PromptCacheEntry.task_class == task_class)
    result = db.execute(stmt)
    return result.rowcount or 0


def statistics(db: Session, tenant_id: uuid.UUID, days: int = 30) -> dict:
    """Cache effectiveness, computed from the invocation ledger."""
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(
            ModelInvocation.cache_status,
            func.count(ModelInvocation.id),
            func.coalesce(func.sum(ModelInvocation.cost), 0),
            func.coalesce(func.sum(ModelInvocation.cost_saved), 0),
            func.coalesce(func.sum(ModelInvocation.tokens_in), 0),
            func.coalesce(func.sum(ModelInvocation.cache_read_tokens), 0),
        )
        .where(
            ModelInvocation.tenant_id == tenant_id,
            ModelInvocation.created_at >= since,
            ModelInvocation.outcome == "ok",
        )
        .group_by(ModelInvocation.cache_status)
    ).all()

    by_status = {
        r[0]: {
            "calls": r[1],
            "cost": float(r[2]),
            "saved": float(r[3]),
            "tokens_in": int(r[4]),
            "cache_read_tokens": int(r[5]),
        }
        for r in rows
    }
    total_calls = sum(v["calls"] for v in by_status.values())
    local_hits = by_status.get("local_hit", {}).get("calls", 0)
    provider_hits = by_status.get("provider_hit", {}).get("calls", 0)
    spend = sum(v["cost"] for v in by_status.values())
    saved = sum(v["saved"] for v in by_status.values())

    entries = db.execute(
        select(
            func.count(PromptCacheEntry.id),
            func.coalesce(func.sum(PromptCacheEntry.hit_count), 0),
        ).where(
            PromptCacheEntry.tenant_id == tenant_id,
            PromptCacheEntry.expires_at > utcnow(),
        )
    ).one()

    return {
        "window_days": days,
        "total_calls": total_calls,
        "local_hits": local_hits,
        "provider_hits": provider_hits,
        "hit_rate": round((local_hits + provider_hits) / total_calls, 4) if total_calls else 0.0,
        "local_hit_rate": round(local_hits / total_calls, 4) if total_calls else 0.0,
        "spend": round(spend, 4),
        "saved": round(saved, 4),
        "saving_rate": round(saved / (spend + saved), 4) if (spend + saved) else 0.0,
        "live_entries": int(entries[0]),
        "lifetime_entry_hits": int(entries[1]),
        "by_status": by_status,
    }
