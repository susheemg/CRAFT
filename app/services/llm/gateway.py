"""The model gateway.

Every model call in the platform goes through :func:`complete`. Nothing else
opens an HTTP connection to a provider. That single choke point is what makes
the following true at once:

  * models are configuration, never code — no agent hard-codes a vendor
  * every call is priced, metered and attributed to a run and a task class
  * budgets, rate limits and the kill switch are enforced before the spend
  * secrets and personal data are filtered out of prompts before they leave
  * caching is applied consistently rather than per caller
  * a failed provider falls back down a configured chain, and the fallback is
    recorded rather than hidden

Resolution order for one call:

    route lookup → policy check (kill switch, daily tokens, monthly cost)
    → redaction → exact-match cache → provider call (with native prefix cache)
    → ledger write → optional cache store
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import utcnow
from app.models.llm import (
    LlmModel,
    LlmPolicy,
    LlmProvider,
    LlmRoute,
    ModelInvocation,
    PromptTemplate,
)
from app.security.crypto import SecretUnavailable, resolve_vault_ref, sha256_hex, unseal
from app.services.llm import cache as prompt_cache
from app.services.llm.providers import ChatRequest, ChatResponse, ProviderError, build_adapter

log = logging.getLogger(__name__)
_settings = get_settings()


class GatewayError(RuntimeError):
    code = "llm_unavailable"


class BudgetExceeded(GatewayError):
    code = "llm_budget_exceeded"


class NoRouteConfigured(GatewayError):
    code = "llm_route_missing"


# --------------------------------------------------------------------------
# Redaction — applied to every prompt before it leaves the platform
# --------------------------------------------------------------------------
_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    # No \b before the "+": a word boundary needs a word character on one
    # side, and "+" is not one, so \b\+44 can never match. UK mobiles written
    # in international form were slipping through untouched.
    (re.compile(r"(?<![\w+])(?:\+44\s?|0)7\d{3}[\s-]?\d{6}(?!\d)"), "[PHONE]"),
    (re.compile(r"(?<![\w+])\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)"), "[PHONE]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[CARD]"),
    (re.compile(r"\b[A-Z]{2}\d{2}[ ]?[A-Z0-9]{4}[ ]?\d{4}[ ]?[A-Z0-9]{1,16}\b"), "[IBAN]"),
    (re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"), "[NINO]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"), "[SECRET]"),
    (re.compile(r"(?i)\b(api[_-]?key|bearer|password|secret)\s*[:=]\s*\S+"), r"\1: [SECRET]"),
)


def redact(text: str) -> tuple[str, int]:
    """Mask personal data and credential-shaped strings. Returns (text, count)."""
    if not text:
        return text, 0
    count = 0
    for pattern, replacement in _REDACTIONS:
        text, n = pattern.subn(replacement, text)
        count += n
    return text, count


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
@dataclass
class ResolvedRoute:
    route: LlmRoute
    chain: list[LlmModel]  # primary first, then fallbacks in order

    @property
    def task_class(self) -> str:
        return self.route.task_class


def resolve_route(
    db: Session, tenant_id: uuid.UUID, task_class: str, environment: str = "production"
) -> ResolvedRoute:
    route = db.execute(
        select(LlmRoute).where(
            LlmRoute.tenant_id == tenant_id,
            LlmRoute.task_class == task_class,
            LlmRoute.environment == environment,
            LlmRoute.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if route is None:
        route = db.execute(
            select(LlmRoute).where(
                LlmRoute.tenant_id == tenant_id,
                LlmRoute.task_class == "default",
                LlmRoute.environment == environment,
                LlmRoute.is_active.is_(True),
            )
        ).scalar_one_or_none()
    if route is None:
        raise NoRouteConfigured(
            f"No route is configured for task class '{task_class}'. "
            "Add one in Admin → LLM → Routing, or define a 'default' route."
        )

    chain: list[LlmModel] = []
    primary = db.get(LlmModel, route.model_id)
    if primary and primary.status == "active":
        chain.append(primary)
    for fid in route.fallback_model_ids or []:
        try:
            m = db.get(LlmModel, uuid.UUID(str(fid)))
        except (ValueError, TypeError):
            continue
        if m and m.status == "active" and m.id not in {c.id for c in chain}:
            chain.append(m)
    if not chain:
        raise NoRouteConfigured(
            f"Route '{route.task_class}' resolves to no active model. "
            "Check the model catalogue in Admin → LLM."
        )
    return ResolvedRoute(route=route, chain=chain)


def _credential_for(provider: LlmProvider) -> str:
    if provider.credential_vault_ref:
        return resolve_vault_ref(provider.credential_vault_ref)
    if provider.credential_ciphertext:
        return unseal(provider.credential_ciphertext)
    if provider.kind == "ollama":
        return ""  # self-hosted, no key
    raise SecretUnavailable(
        f"Provider '{provider.name}' has no credential configured."
    )


# --------------------------------------------------------------------------
# Policy enforcement
# --------------------------------------------------------------------------
@dataclass
class PolicyState:
    allowed: bool
    reason: str = ""
    tokens_today: int = 0
    cost_this_month: float = 0.0
    token_budget: int | None = None
    cost_cap: float | None = None
    threshold_breached: bool = False

    @property
    def token_utilisation(self) -> float:
        return self.tokens_today / self.token_budget if self.token_budget else 0.0

    @property
    def cost_utilisation(self) -> float:
        return self.cost_this_month / self.cost_cap if self.cost_cap else 0.0


def check_policy(
    db: Session, tenant_id: uuid.UUID, provider_id: uuid.UUID | None = None,
    route_id: uuid.UUID | None = None,
) -> PolicyState:
    """Evaluate the applicable policies, most specific last (route wins)."""
    scopes: list[tuple[str, uuid.UUID | None]] = [("global", None)]
    if provider_id:
        scopes.append(("provider", provider_id))
    if route_id:
        scopes.append(("route", route_id))

    policies: list[LlmPolicy] = []
    for scope, ref in scopes:
        stmt = select(LlmPolicy).where(
            LlmPolicy.tenant_id == tenant_id, LlmPolicy.scope == scope
        )
        stmt = stmt.where(LlmPolicy.scope_ref == ref) if ref else stmt.where(
            LlmPolicy.scope_ref.is_(None)
        )
        p = db.execute(stmt).scalar_one_or_none()
        if p:
            policies.append(p)

    if not policies:
        return PolicyState(allowed=True)

    for p in policies:
        if p.kill_switch:
            return PolicyState(
                allowed=False,
                reason=(
                    f"The {p.scope} kill switch is engaged"
                    + (f": {p.kill_switch_reason}" if p.kill_switch_reason else "")
                    + ". Reset it in Admin → LLM → Limits."
                ),
            )

    now = utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)

    tokens_today = db.execute(
        select(
            func.coalesce(
                func.sum(ModelInvocation.tokens_in + ModelInvocation.tokens_out), 0
            )
        ).where(
            ModelInvocation.tenant_id == tenant_id, ModelInvocation.created_at >= day_start
        )
    ).scalar_one()
    cost_month = float(
        db.execute(
            select(func.coalesce(func.sum(ModelInvocation.cost), 0)).where(
                ModelInvocation.tenant_id == tenant_id,
                ModelInvocation.created_at >= month_start,
            )
        ).scalar_one()
    )

    state = PolicyState(allowed=True, tokens_today=int(tokens_today), cost_this_month=cost_month)
    for p in policies:
        if p.token_budget_daily:
            state.token_budget = int(p.token_budget_daily)
            if tokens_today >= p.token_budget_daily:
                return PolicyState(
                    allowed=False,
                    reason=(
                        f"Daily token budget of {p.token_budget_daily:,} is spent "
                        f"({int(tokens_today):,} used). It resets at midnight UTC."
                    ),
                    tokens_today=int(tokens_today),
                    cost_this_month=cost_month,
                    token_budget=int(p.token_budget_daily),
                )
        if p.cost_cap_monthly:
            state.cost_cap = float(p.cost_cap_monthly)
            if cost_month >= float(p.cost_cap_monthly):
                return PolicyState(
                    allowed=False,
                    reason=(
                        f"Monthly cost cap of {p.cost_cap_monthly} is reached "
                        f"({cost_month:.2f} spent)."
                    ),
                    tokens_today=int(tokens_today),
                    cost_this_month=cost_month,
                    cost_cap=float(p.cost_cap_monthly),
                )
        threshold = float(p.alert_threshold or 0.8)
        if (state.token_budget and state.token_utilisation >= threshold) or (
            state.cost_cap and state.cost_utilisation >= threshold
        ):
            state.threshold_breached = True
    return state


def price(
    model: LlmModel, tokens_in: int, tokens_out: int,
    cache_read: int = 0, cache_write: int = 0,
) -> float:
    """Cost of one call. Cached input is priced at the model's cache-read rate."""
    fresh_in = max(tokens_in - cache_read, 0)
    total = (
        fresh_in / 1000 * float(model.in_cost_per_1k or 0)
        + tokens_out / 1000 * float(model.out_cost_per_1k or 0)
        + cache_read / 1000 * float(model.cache_read_cost_per_1k or 0)
        + cache_write / 1000 * float(model.cache_write_cost_per_1k or 0)
    )
    return round(total, 6)


# --------------------------------------------------------------------------
# Completion
# --------------------------------------------------------------------------
@dataclass
class CompletionResult:
    text: str
    model_key: str
    provider_kind: str
    task_class: str
    tokens_in: int = 0
    tokens_out: int = 0
    cache_status: str = "miss"
    cost: float = 0.0
    cost_saved: float = 0.0
    latency_ms: int = 0
    attempts: int = 1
    fell_back: bool = False
    redactions: int = 0
    notes: list[str] = field(default_factory=list)
    # The ledger row this call produced, so a caller that parses something the
    # gateway could not know — the model's stated confidence, for instance —
    # can attach it to the same record rather than a parallel one.
    invocation_id: uuid.UUID | None = None

    @property
    def from_cache(self) -> bool:
        return self.cache_status in ("local_hit", "provider_hit")


async def complete(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    task_class: str,
    prompt: str,
    system: str = "",
    cache_prefix: str = "",
    prompt_name: str | None = None,
    prompt_version: int | None = None,
    run_id: uuid.UUID | None = None,
    activity_run_id: uuid.UUID | None = None,
    actor_ref: str = "system",
    max_tokens: int | None = None,
    temperature: float | None = None,
    json_mode: bool = False,
    environment: str = "production",
    client: httpx.AsyncClient | None = None,
) -> CompletionResult:
    """Run one governed model call. Raises :class:`GatewayError` if it cannot."""
    resolved = resolve_route(db, tenant_id, task_class, environment)
    route = resolved.route
    effective_temp = route.temperature if temperature is None else temperature
    effective_max = max_tokens or route.max_tokens

    # 1. Redact before anything else touches the text.
    safe_prompt, r1 = redact(prompt)
    safe_system, r2 = redact(system or route.system_prompt or "")
    safe_prefix, r3 = redact(cache_prefix)
    redactions = r1 + r2 + r3
    prompt_digest = sha256_hex(safe_prefix + safe_system + safe_prompt)

    # 2. Exact-match cache, before any budget is consumed.
    cacheable = prompt_cache.is_cacheable(
        float(effective_temp), route.cache_enabled and _settings.llm_cache_enabled
    )
    primary = resolved.chain[0]
    cache_key = prompt_cache.build_key(
        model_key=primary.model_key,
        cache_prefix=safe_prefix,
        system=safe_system,
        prompt=safe_prompt,
        temperature=float(effective_temp),
        max_tokens=effective_max,
        json_mode=json_mode,
    )
    if cacheable:
        found = prompt_cache.lookup(db, tenant_id, cache_key)
        if found.hit:
            entry = found.entry
            saved = prompt_cache.record_hit(db, entry)
            _ledger(
                db, tenant_id=tenant_id, run_id=run_id, activity_run_id=activity_run_id,
                task_class=task_class, provider_kind="cache", model_key=entry.model_key,
                prompt_name=prompt_name, prompt_version=prompt_version,
                prompt_digest=prompt_digest, actor_ref=actor_ref,
                tokens_in=0, tokens_out=0, cache_read=0, cache_write=0,
                cache_status="local_hit", cost=0.0, cost_saved=saved,
                latency_ms=0, attempt=1, outcome="ok",
            )
            return CompletionResult(
                text=entry.response_text,
                model_key=entry.model_key,
                provider_kind="cache",
                task_class=task_class,
                tokens_in=entry.tokens_in,
                tokens_out=entry.tokens_out,
                cache_status="local_hit",
                cost=0.0,
                cost_saved=saved,
                redactions=redactions,
                notes=["Served from the response cache; no provider call was made."],
            )

    # 3. Budget and kill switch.
    policy = check_policy(db, tenant_id, provider_id=primary.provider_id, route_id=route.id)
    if not policy.allowed:
        _ledger(
            db, tenant_id=tenant_id, run_id=run_id, activity_run_id=activity_run_id,
            task_class=task_class, provider_kind="policy", model_key=primary.model_key,
            prompt_name=prompt_name, prompt_version=prompt_version,
            prompt_digest=prompt_digest, actor_ref=actor_ref,
            tokens_in=0, tokens_out=0, cache_read=0, cache_write=0,
            cache_status="bypass", cost=0.0, cost_saved=0.0, latency_ms=0,
            attempt=1, outcome="capped", error=policy.reason,
        )
        raise BudgetExceeded(policy.reason)

    # 4. Call the provider, walking the fallback chain on retryable failures.
    owns_client = client is None
    client = client or httpx.AsyncClient()
    errors: list[str] = []
    try:
        for attempt, model in enumerate(resolved.chain[: _settings.llm_max_fallback_attempts], 1):
            provider = db.get(LlmProvider, model.provider_id)
            if provider is None or provider.status != "active":
                errors.append(f"{model.model_key}: provider inactive")
                continue
            try:
                adapter = build_adapter(
                    provider.kind,
                    api_key=_credential_for(provider),
                    model_key=model.model_key,
                    base_url=provider.base_url,
                    region=provider.region,
                    api_version=provider.api_version,
                    extra_headers=provider.extra_headers or {},
                    timeout=_settings.llm_request_timeout_seconds,
                )
            except (ProviderError, SecretUnavailable) as exc:
                errors.append(f"{model.model_key}: {exc}")
                continue

            started = time.perf_counter()
            try:
                response: ChatResponse = await adapter.chat(
                    ChatRequest(
                        prompt=safe_prompt,
                        system=safe_system,
                        cache_prefix=safe_prefix,
                        max_tokens=effective_max,
                        temperature=float(effective_temp),
                        json_mode=json_mode,
                    ),
                    client,
                )
            except (ProviderError, httpx.HTTPError) as exc:
                latency = int((time.perf_counter() - started) * 1000)
                retryable = getattr(exc, "retryable", True)
                _ledger(
                    db, tenant_id=tenant_id, run_id=run_id, activity_run_id=activity_run_id,
                    task_class=task_class, provider_kind=provider.kind,
                    model_key=model.model_key, prompt_name=prompt_name,
                    prompt_version=prompt_version, prompt_digest=prompt_digest,
                    actor_ref=actor_ref, tokens_in=0, tokens_out=0, cache_read=0,
                    cache_write=0, cache_status="miss", cost=0.0, cost_saved=0.0,
                    latency_ms=latency, attempt=attempt, outcome="error",
                    error=str(exc)[:500],
                )
                errors.append(f"{model.model_key}: {exc}")
                if not retryable:
                    break
                continue

            latency = int((time.perf_counter() - started) * 1000)
            cost = price(
                model,
                response.tokens_in,
                response.tokens_out,
                response.cache_read_tokens,
                response.cache_write_tokens,
            )
            # What the same call would have cost with no cached prefix.
            uncached = price(model, response.tokens_in, response.tokens_out)
            saved = max(round(uncached - cost, 6), 0.0)
            cache_status = "provider_hit" if response.provider_cache_hit else "miss"

            invocation_id = _ledger(
                db, tenant_id=tenant_id, run_id=run_id, activity_run_id=activity_run_id,
                task_class=task_class, provider_kind=provider.kind,
                model_key=model.model_key, prompt_name=prompt_name,
                prompt_version=prompt_version, prompt_digest=prompt_digest,
                actor_ref=actor_ref, tokens_in=response.tokens_in,
                tokens_out=response.tokens_out, cache_read=response.cache_read_tokens,
                cache_write=response.cache_write_tokens, cache_status=cache_status,
                cost=cost, cost_saved=saved, latency_ms=latency, attempt=attempt,
                outcome="ok",
            )

            if cacheable and response.text:
                prompt_cache.store(
                    db,
                    tenant_id=tenant_id,
                    key=cache_key,
                    task_class=task_class,
                    model_key=model.model_key,
                    prompt_digest=prompt_digest,
                    response_text=response.text,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    cost=uncached,
                    ttl_seconds=route.cache_ttl_seconds or _settings.llm_cache_ttl_seconds,
                    meta={"provider": provider.kind, "finish": response.raw_finish_reason},
                )

            notes: list[str] = []
            if attempt > 1:
                notes.append(
                    f"Primary model unavailable; served by fallback {model.model_key}."
                )
            if response.provider_cache_hit:
                notes.append(
                    f"{response.cache_read_tokens:,} prompt tokens served from the "
                    "provider's prefix cache."
                )
            if policy.threshold_breached:
                notes.append("Budget alert threshold has been crossed for this scope.")

            return CompletionResult(
                text=response.text,
                model_key=model.model_key,
                provider_kind=provider.kind,
                task_class=task_class,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cache_status=cache_status,
                cost=cost,
                cost_saved=saved,
                latency_ms=latency,
                attempts=attempt,
                invocation_id=invocation_id,
                fell_back=attempt > 1,
                redactions=redactions,
                notes=notes,
            )
    finally:
        if owns_client:
            await client.aclose()

    raise GatewayError(
        "Every configured model for task class '"
        + task_class
        + "' failed. "
        + " | ".join(errors[:3])
    )


def _ledger(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    run_id: uuid.UUID | None,
    activity_run_id: uuid.UUID | None,
    task_class: str,
    provider_kind: str,
    model_key: str,
    prompt_name: str | None,
    prompt_version: int | None,
    prompt_digest: str,
    actor_ref: str,
    tokens_in: int,
    tokens_out: int,
    cache_read: int,
    cache_write: int,
    cache_status: str,
    cost: float,
    cost_saved: float,
    latency_ms: int,
    attempt: int,
    outcome: str,
    error: str | None = None,
    confidence: float | None = None,
) -> uuid.UUID:
    invocation = ModelInvocation(
        tenant_id=tenant_id,
        run_id=run_id,
        activity_run_id=activity_run_id,
        task_class=task_class,
        provider_kind=provider_kind,
        model_key=model_key,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        prompt_digest=prompt_digest,
        actor_ref=actor_ref,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        cache_status=cache_status,
        cost=cost,
        cost_saved=cost_saved,
        latency_ms=latency_ms,
        attempt=attempt,
        outcome=outcome,
        error=error,
        confidence=confidence,
        created_at=utcnow(),
    )
    db.add(invocation)
    db.flush()
    return invocation.id


def spend_summary(db: Session, tenant_id: uuid.UUID, days: int = 30) -> dict:
    """Token and cost spend by task class — the basis for right-sizing routes."""
    since = utcnow() - timedelta(days=days)
    rows = db.execute(
        select(
            ModelInvocation.task_class,
            ModelInvocation.model_key,
            func.count(ModelInvocation.id),
            func.coalesce(func.sum(ModelInvocation.tokens_in), 0),
            func.coalesce(func.sum(ModelInvocation.tokens_out), 0),
            func.coalesce(func.sum(ModelInvocation.cost), 0),
            func.coalesce(func.sum(ModelInvocation.cost_saved), 0),
            func.coalesce(func.avg(ModelInvocation.latency_ms), 0),
        )
        .where(ModelInvocation.tenant_id == tenant_id, ModelInvocation.created_at >= since)
        .group_by(ModelInvocation.task_class, ModelInvocation.model_key)
        .order_by(func.sum(ModelInvocation.cost).desc())
    ).all()
    return {
        "window_days": days,
        "rows": [
            {
                "task_class": r[0],
                "model_key": r[1],
                "calls": r[2],
                "tokens_in": int(r[3]),
                "tokens_out": int(r[4]),
                "cost": round(float(r[5]), 4),
                "saved": round(float(r[6]), 4),
                "avg_latency_ms": int(r[7]),
            }
            for r in rows
        ],
        "total_cost": round(sum(float(r[5]) for r in rows), 4),
        "total_saved": round(sum(float(r[6]) for r in rows), 4),
    }


def active_prompt(
    db: Session, tenant_id: uuid.UUID, name: str
) -> Optional[PromptTemplate]:
    return db.execute(
        select(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.name == name,
            PromptTemplate.is_active.is_(True),
        )
        .order_by(PromptTemplate.version.desc())
    ).scalars().first()
