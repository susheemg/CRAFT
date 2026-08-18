"""Administration of the model gateway.

This is where an administrator connects the platform to whichever AI providers
the organisation has approved. Three principles shape the design:

  * **Credentials go in and never come out.** A key is sealed on receipt and
    only the last four characters are ever returned, so the console can show
    the operator which key is in place without being able to read it back.
  * **Changing production configuration is a two-person act.** Editing a route
    or activating a configuration version raises a gate for a second approver.
    An administrator configures; an approver decides.
  * **Spend is measured, not estimated.** Every figure on the console comes
    from the invocation ledger.
"""

from __future__ import annotations

import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, requires
from app.api.schemas import (
    CompletionRequest,
    ModelCreate,
    PolicyUpsert,
    ProviderCreate,
    ProviderOut,
    ProviderUpdate,
    RouteUpsert,
)
from app.models.base import GateReason, utcnow
from app.models.core import Workflow
from app.models.llm import (
    LlmConfigVersion,
    LlmModel,
    LlmPolicy,
    LlmProvider,
    LlmRoute,
    PromptTemplate,
)
from app.security.crypto import canonical_hash, resolve_vault_ref, seal
from app.services import audit
from app.services.llm import cache as prompt_cache
from app.services.llm import gateway
from app.services.llm.providers import build_adapter

router = APIRouter(prefix="/admin/llm", tags=["Admin — AI providers"])

PROVIDER_DEFAULTS: dict[str, dict] = {
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "supports_prompt_cache": True,
        "note": "Explicit cache breakpoints. Best token economics for repeated rubrics.",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "supports_prompt_cache": True,
        "note": "Automatic prefix caching above the provider's minimum prefix length.",
    },
    "azure_openai": {
        "base_url": None,
        "supports_prompt_cache": True,
        "note": "Set base_url to your resource endpoint and api_version to the deployment API version.",
    },
    "openai_compatible": {
        "base_url": None,
        "supports_prompt_cache": False,
        "note": "Any OpenAI-shaped endpoint: vLLM, Together, Groq, OpenRouter, LiteLLM.",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "supports_prompt_cache": False,
        "note": "Self-hosted. No credential needed; keeps prompts inside your network.",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "supports_prompt_cache": True,
        "note": "Gemini. Implicit context caching on longer prompts.",
    },
    "bedrock": {
        "base_url": None,
        "supports_prompt_cache": True,
        "note": (
            "Reached through an OpenAI-compatible gateway rather than native SigV4. "
            "Point base_url at your Bedrock access gateway."
        ),
    },
}


# ==========================================================================
# Providers
# ==========================================================================
@router.get("/provider-kinds", summary="The provider types this build supports")
def provider_kinds(_=Depends(requires("admin.llm.view"))) -> dict:
    return {
        "data": [
            {
                "kind": kind,
                "default_base_url": spec["base_url"],
                "supports_prompt_cache": spec["supports_prompt_cache"],
                "note": spec["note"],
            }
            for kind, spec in PROVIDER_DEFAULTS.items()
        ]
    }


@router.get("/providers", summary="List configured providers")
def list_providers(db: DbSession, principal=Depends(requires("admin.llm.view"))) -> dict:
    rows = db.execute(
        select(LlmProvider)
        .where(LlmProvider.tenant_id == principal.tenant_id)
        .order_by(LlmProvider.name)
    ).scalars().all()
    counts = dict(
        db.execute(
            select(LlmModel.provider_id, func.count(LlmModel.id))
            .where(LlmModel.tenant_id == principal.tenant_id)
            .group_by(LlmModel.provider_id)
        ).all()
    )
    return {
        "data": [
            ProviderOut(
                id=p.id,
                name=p.name,
                kind=p.kind,
                base_url=p.base_url,
                region=p.region,
                status=p.status,
                is_default=p.is_default,
                credential_hint=p.credential_hint,
                credential_source=(
                    "vault"
                    if p.credential_vault_ref
                    else "sealed" if p.credential_ciphertext else "none"
                ),
                supports_prompt_cache=p.supports_prompt_cache,
                model_count=counts.get(p.id, 0),
                last_health_ok=p.last_health_ok,
                last_health_at=p.last_health_at,
                last_health_detail=p.last_health_detail,
            ).model_dump(mode="json")
            for p in rows
        ]
    }


@router.post("/providers", status_code=201, summary="Connect a provider")
def create_provider(
    payload: ProviderCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    if payload.kind not in PROVIDER_DEFAULTS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "unsupported_provider",
                    "message": f"'{payload.kind}' is not a provider type this build supports.",
                }
            },
        )
    spec = PROVIDER_DEFAULTS[payload.kind]
    base_url = payload.base_url or spec["base_url"]
    if base_url is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "base_url_required",
                    "message": f"A base URL is required for {payload.kind}. {spec['note']}",
                }
            },
        )
    if payload.api_key and payload.vault_ref:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "ambiguous_credential",
                    "message": "Supply either an API key or a vault reference, not both.",
                }
            },
        )
    if not payload.api_key and not payload.vault_ref and payload.kind != "ollama":
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "credential_required",
                    "message": f"{payload.kind} needs a credential. Provide api_key or vault_ref.",
                }
            },
        )
    if payload.vault_ref:
        try:
            resolve_vault_ref(payload.vault_ref)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "vault_ref_unresolvable",
                        "message": (
                            f"'{payload.vault_ref}' could not be resolved on this host: {exc}"
                        ),
                    }
                },
            ) from exc

    if payload.is_default:
        for other in db.execute(
            select(LlmProvider).where(
                LlmProvider.tenant_id == principal.tenant_id, LlmProvider.is_default.is_(True)
            )
        ).scalars().all():
            other.is_default = False

    provider = LlmProvider(
        tenant_id=principal.tenant_id,
        name=payload.name,
        kind=payload.kind,
        base_url=base_url,
        region=payload.region,
        api_version=payload.api_version,
        credential_ciphertext=seal(payload.api_key) if payload.api_key else None,
        credential_vault_ref=payload.vault_ref,
        credential_hint=payload.api_key[-4:] if payload.api_key else None,
        credential_rotated_at=utcnow() if payload.api_key else None,
        extra_headers=payload.extra_headers or None,
        supports_prompt_cache=spec["supports_prompt_cache"],
        status="active",
        is_default=payload.is_default,
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(provider)
    db.flush()

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.provider_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_provider",
        entity_id=provider.id,
        # The credential itself is never written to the log — only its shape.
        after_state={
            "name": provider.name,
            "kind": provider.kind,
            "base_url": provider.base_url,
            "credential_source": "vault" if payload.vault_ref else "sealed",
            "credential_hint": provider.credential_hint,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(provider.id),
        "name": provider.name,
        "kind": provider.kind,
        "credential_hint": provider.credential_hint,
        "next_step": "Add at least one model, then point a route at it.",
    }


@router.patch("/providers/{provider_id}", summary="Update a provider or rotate its key")
def update_provider(
    provider_id: uuid.UUID,
    payload: ProviderUpdate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    provider = _provider(db, principal.tenant_id, provider_id)
    before = {"status": provider.status, "base_url": provider.base_url}
    data = payload.model_dump(exclude_unset=True)
    rotated = False
    if data.get("api_key"):
        provider.credential_ciphertext = seal(data["api_key"])
        provider.credential_vault_ref = None
        provider.credential_hint = data["api_key"][-4:]
        provider.credential_rotated_at = utcnow()
        rotated = True
    if data.get("vault_ref"):
        provider.credential_vault_ref = data["vault_ref"]
        provider.credential_ciphertext = None
        provider.credential_hint = None
        provider.credential_rotated_at = utcnow()
        rotated = True
    for field in ("base_url", "region", "api_version", "status"):
        if data.get(field) is not None:
            setattr(provider, field, data[field])
    if data.get("is_default"):
        for other in db.execute(
            select(LlmProvider).where(
                LlmProvider.tenant_id == principal.tenant_id,
                LlmProvider.is_default.is_(True),
                LlmProvider.id != provider.id,
            )
        ).scalars().all():
            other.is_default = False
        provider.is_default = True
    provider.updated_at = utcnow()
    provider.updated_by = principal.id

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.provider_updated",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_provider",
        entity_id=provider.id,
        before_state=before,
        after_state={
            "status": provider.status,
            "base_url": provider.base_url,
            "credential_rotated": rotated,
            "credential_hint": provider.credential_hint,
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(provider.id), "credential_rotated": rotated, "status": provider.status}


@router.post("/providers/{provider_id}:test", summary="Check the provider answers")
async def test_provider(
    provider_id: uuid.UUID,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    """A live, minimal call against a real model — the only way to know the
    credential, endpoint and model name are all correct together."""
    provider = _provider(db, principal.tenant_id, provider_id)
    model = db.execute(
        select(LlmModel).where(
            LlmModel.provider_id == provider.id, LlmModel.status == "active"
        ).order_by(LlmModel.in_cost_per_1k)
    ).scalars().first()
    if model is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "no_model",
                    "message": "Add a model to this provider before testing it.",
                }
            },
        )
    try:
        credential = gateway._credential_for(provider)
        adapter = build_adapter(provider, credential)
    except Exception as exc:
        provider.last_health_ok = False
        provider.last_health_at = utcnow()
        provider.last_health_detail = str(exc)[:500]
        db.commit()
        return {"ok": False, "detail": str(exc)[:500], "model": model.model_key}

    ok, detail = False, ""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await adapter.complete(
                client,
                model_key=model.model_key,
                system="Reply with the single word: ready.",
                prompt="ready?",
                cache_prefix="",
                max_tokens=16,
                temperature=0.0,
                json_mode=False,
            )
        ok = True
        detail = (
            f"{model.model_key} answered in {response.latency_ms}ms "
            f"({response.tokens_in} in / {response.tokens_out} out)."
        )
    except Exception as exc:
        detail = f"{type(exc).__name__}: {str(exc)[:400]}"

    provider.last_health_ok = ok
    provider.last_health_at = utcnow()
    provider.last_health_detail = detail
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.provider_tested",
        outcome="success" if ok else "failure",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_provider",
        entity_id=provider.id,
        detail={"model": model.model_key, "result": detail},
        request_id=request_id,
    )
    db.commit()
    return {"ok": ok, "detail": detail, "model": model.model_key}


# ==========================================================================
# Models
# ==========================================================================
@router.get("/models", summary="List the model catalogue")
def list_models(db: DbSession, principal=Depends(requires("admin.llm.view"))) -> dict:
    rows = db.execute(
        select(LlmModel, LlmProvider)
        .join(LlmProvider, LlmProvider.id == LlmModel.provider_id)
        .where(LlmModel.tenant_id == principal.tenant_id)
        .order_by(LlmProvider.name, LlmModel.model_key)
    ).all()
    return {
        "data": [
            {
                "id": str(m.id),
                "provider": p.name,
                "provider_kind": p.kind,
                "model_key": m.model_key,
                "display_name": m.display_name,
                "capability": m.capability,
                "context_window": m.context_window,
                "in_cost_per_1k": float(m.in_cost_per_1k),
                "out_cost_per_1k": float(m.out_cost_per_1k),
                "cache_read_cost_per_1k": float(m.cache_read_cost_per_1k),
                "supports_native_cache": m.supports_native_cache,
                "status": m.status,
            }
            for m, p in rows
        ]
    }


@router.post("/models", status_code=201, summary="Add a model to the catalogue")
def create_model(
    payload: ModelCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    provider = _provider(db, principal.tenant_id, payload.provider_id)
    if payload.cache_read_cost_per_1k > payload.in_cost_per_1k:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "implausible_pricing",
                    "message": (
                        "A cached read costs less than a fresh input token on every "
                        "provider. Check the figures before saving."
                    ),
                }
            },
        )
    model = LlmModel(
        tenant_id=principal.tenant_id,
        provider_id=provider.id,
        model_key=payload.model_key,
        display_name=payload.display_name or payload.model_key,
        capability=payload.capability,
        context_window=payload.context_window,
        max_output=payload.max_output,
        in_cost_per_1k=payload.in_cost_per_1k,
        out_cost_per_1k=payload.out_cost_per_1k,
        cache_write_cost_per_1k=payload.cache_write_cost_per_1k,
        cache_read_cost_per_1k=payload.cache_read_cost_per_1k,
        supports_native_cache=payload.supports_native_cache and provider.supports_prompt_cache,
        status="active",
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(model)
    db.flush()
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.model_created",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_model",
        entity_id=model.id,
        after_state={
            "provider": provider.name,
            "model_key": model.model_key,
            "in_cost_per_1k": float(model.in_cost_per_1k),
            "out_cost_per_1k": float(model.out_cost_per_1k),
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(model.id), "model_key": model.model_key, "provider": provider.name}


# ==========================================================================
# Routes
# ==========================================================================
@router.get("/routes", summary="List task-class routing")
def list_routes(db: DbSession, principal=Depends(requires("admin.llm.view"))) -> dict:
    rows = db.execute(
        select(LlmRoute)
        .where(LlmRoute.tenant_id == principal.tenant_id)
        .order_by(LlmRoute.task_class)
    ).scalars().all()
    models = {
        m.id: m
        for m in db.execute(
            select(LlmModel).where(LlmModel.tenant_id == principal.tenant_id)
        ).scalars().all()
    }

    def name_of(mid) -> str | None:
        try:
            m = models.get(uuid.UUID(str(mid)))
        except (ValueError, TypeError):
            return None
        return m.model_key if m else None

    return {
        "data": [
            {
                "id": str(r.id),
                "task_class": r.task_class,
                "description": r.description,
                "environment": r.environment,
                "model": name_of(r.model_id),
                "fallbacks": [
                    n for n in (name_of(f) for f in (r.fallback_model_ids or [])) if n
                ],
                "temperature": float(r.temperature),
                "max_tokens": r.max_tokens,
                "cache_enabled": r.cache_enabled,
                "cache_ttl_seconds": r.cache_ttl_seconds,
                "is_active": r.is_active,
            }
            for r in rows
        ],
        "unrouted_task_classes": _unrouted(db, principal.tenant_id, rows),
    }


def _unrouted(db, tenant_id: uuid.UUID, routes) -> list[str]:
    """Task classes the workflows and prompts need but no route serves."""
    routed = {r.task_class for r in routes if r.is_active}
    needed: set[str] = {
        t.task_class
        for t in db.execute(
            select(PromptTemplate).where(PromptTemplate.tenant_id == tenant_id)
        ).scalars().all()
    }
    for wf in db.execute(
        select(Workflow).where(Workflow.tenant_id == tenant_id)
    ).scalars().all():
        for act in (wf.definition or {}).get("activities", []):
            if act.get("task_class"):
                needed.add(act["task_class"])
    return sorted(needed - routed)


@router.put("/routes/{task_class}", summary="Set the route for a task class")
def upsert_route(
    task_class: str,
    payload: RouteUpsert,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    model = db.get(LlmModel, payload.model_id)
    if model is None or model.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "invalid_model", "message": "No such model."}},
        )
    for fid in payload.fallback_model_ids:
        fb = db.get(LlmModel, fid)
        if fb is None or fb.tenant_id != principal.tenant_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "invalid_fallback",
                        "message": f"Fallback model {fid} does not exist.",
                    }
                },
            )
        if fb.provider_id == model.provider_id:
            # Not fatal, but worth saying: a same-provider fallback does not
            # protect against the outage most likely to matter.
            pass

    route = db.execute(
        select(LlmRoute).where(
            LlmRoute.tenant_id == principal.tenant_id,
            LlmRoute.task_class == task_class,
            LlmRoute.environment == payload.environment,
        )
    ).scalar_one_or_none()
    before = (
        None
        if route is None
        else {
            "model_id": str(route.model_id),
            "temperature": float(route.temperature),
            "cache_enabled": route.cache_enabled,
            "is_active": route.is_active,
        }
    )
    if route is None:
        route = LlmRoute(
            tenant_id=principal.tenant_id,
            task_class=task_class,
            environment=payload.environment,
            created_at=utcnow(),
            created_by=principal.id,
        )
        db.add(route)
    route.model_id = payload.model_id
    route.fallback_model_ids = [str(f) for f in payload.fallback_model_ids] or None
    route.description = payload.description or route.description
    route.temperature = payload.temperature
    route.max_tokens = payload.max_tokens
    route.cache_enabled = payload.cache_enabled
    route.cache_ttl_seconds = payload.cache_ttl_seconds
    route.system_prompt = payload.system_prompt
    route.is_active = payload.is_active
    route.updated_at = utcnow()
    route.updated_by = principal.id
    db.flush()

    # Changing the model behind a task class invalidates answers cached under
    # the old one; leaving them would serve a superseded model's conclusions.
    invalidated = 0
    if before and before["model_id"] != str(payload.model_id):
        invalidated = prompt_cache.invalidate(db, principal.tenant_id, task_class=task_class)

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.route_changed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_route",
        entity_id=route.id,
        before_state=before,
        after_state={
            "model_id": str(route.model_id),
            "model_key": model.model_key,
            "temperature": float(route.temperature),
            "cache_enabled": route.cache_enabled,
            "is_active": route.is_active,
        },
        detail={"cache_entries_invalidated": invalidated},
        request_id=request_id,
    )
    db.commit()
    return {
        "task_class": task_class,
        "model": model.model_key,
        "cache_entries_invalidated": invalidated,
    }


# ==========================================================================
# Policy, spend and cache
# ==========================================================================
@router.get("/policy", summary="Budget and kill-switch state")
def get_policy(db: DbSession, principal=Depends(requires("admin.llm.view"))) -> dict:
    state = gateway.check_policy(db, principal.tenant_id)
    rows = db.execute(
        select(LlmPolicy).where(LlmPolicy.tenant_id == principal.tenant_id)
    ).scalars().all()
    return {
        "effective": {
            "allowed": state.allowed,
            "reason": state.reason,
            "tokens_today": state.tokens_today,
            "token_budget": state.token_budget,
            "token_utilisation": round(state.token_utilisation, 3),
            "cost_this_month": round(state.cost_this_month, 4),
            "cost_cap": state.cost_cap,
            "cost_utilisation": round(state.cost_utilisation, 3),
            "threshold_breached": state.threshold_breached,
        },
        "policies": [
            {
                "id": str(p.id),
                "scope": p.scope,
                "scope_ref": str(p.scope_ref) if p.scope_ref else None,
                "rate_rpm": p.rate_rpm,
                "token_budget_daily": p.token_budget_daily,
                "cost_cap_monthly": float(p.cost_cap_monthly) if p.cost_cap_monthly else None,
                "alert_threshold": float(p.alert_threshold),
                "kill_switch": p.kill_switch,
                "kill_switch_reason": p.kill_switch_reason,
            }
            for p in rows
        ],
    }


@router.put("/policy", summary="Set a budget policy or throw the kill switch")
def upsert_policy(
    payload: PolicyUpsert,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    """The kill switch stops every model call for the tenant at once.

    It requires a reason, because an operator finding the platform mute at
    03:00 needs to know why and who to call.
    """
    if payload.kill_switch and not payload.kill_switch_reason:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "reason_required",
                    "message": "Engaging the kill switch requires a reason.",
                }
            },
        )
    stmt = select(LlmPolicy).where(
        LlmPolicy.tenant_id == principal.tenant_id, LlmPolicy.scope == payload.scope
    )
    stmt = (
        stmt.where(LlmPolicy.scope_ref == payload.scope_ref)
        if payload.scope_ref
        else stmt.where(LlmPolicy.scope_ref.is_(None))
    )
    policy = db.execute(stmt).scalar_one_or_none()
    before = (
        None
        if policy is None
        else {
            "kill_switch": policy.kill_switch,
            "token_budget_daily": policy.token_budget_daily,
            "cost_cap_monthly": float(policy.cost_cap_monthly)
            if policy.cost_cap_monthly
            else None,
        }
    )
    if policy is None:
        policy = LlmPolicy(
            tenant_id=principal.tenant_id,
            scope=payload.scope,
            scope_ref=payload.scope_ref,
            created_at=utcnow(),
            created_by=principal.id,
        )
        db.add(policy)
    was_on = bool(policy.kill_switch)
    policy.rate_rpm = payload.rate_rpm
    policy.token_budget_daily = payload.token_budget_daily
    policy.cost_cap_monthly = payload.cost_cap_monthly
    policy.alert_threshold = payload.alert_threshold
    policy.kill_switch = payload.kill_switch
    policy.kill_switch_reason = payload.kill_switch_reason
    if payload.kill_switch and not was_on:
        policy.kill_switch_at = utcnow()
    policy.updated_at = utcnow()
    policy.updated_by = principal.id
    db.flush()

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.kill_switch" if payload.kill_switch != was_on else "admin.policy_changed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_policy",
        entity_id=policy.id,
        before_state=before,
        after_state={
            "kill_switch": policy.kill_switch,
            "reason": policy.kill_switch_reason,
            "token_budget_daily": policy.token_budget_daily,
            "cost_cap_monthly": float(policy.cost_cap_monthly)
            if policy.cost_cap_monthly
            else None,
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(policy.id), "scope": policy.scope, "kill_switch": policy.kill_switch}


@router.get("/spend", summary="Spend by task class and model")
def spend(
    db: DbSession,
    days: int = Query(default=30, ge=1, le=365),
    principal=Depends(requires("admin.llm.view")),
) -> dict:
    return gateway.spend_summary(db, principal.tenant_id, days)


@router.get("/cache", summary="Prompt-cache effectiveness")
def cache_stats(
    db: DbSession,
    days: int = Query(default=30, ge=1, le=365),
    principal=Depends(requires("admin.llm.view")),
) -> dict:
    """Hit rate and money saved, computed from the ledger rather than modelled."""
    return prompt_cache.statistics(db, principal.tenant_id, days)


@router.post("/cache:sweep", summary="Remove expired cache entries")
def sweep_cache(db: DbSession, principal=Depends(requires("admin.llm.manage"))) -> dict:
    removed = prompt_cache.sweep_expired(db)
    db.commit()
    return {"removed": removed}


@router.delete("/cache", summary="Invalidate cached responses")
def clear_cache(
    db: DbSession,
    request_id: RequestId,
    task_class: Optional[str] = None,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    removed = prompt_cache.invalidate(db, principal.tenant_id, task_class=task_class)
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.cache_invalidated",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="prompt_cache",
        detail={"task_class": task_class or "all", "removed": removed},
        request_id=request_id,
    )
    db.commit()
    return {"removed": removed, "task_class": task_class or "all"}


@router.post("/complete", summary="Run a governed completion (console test)")
async def complete(
    payload: CompletionRequest,
    db: DbSession,
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    try:
        result = await gateway.complete(
            db,
            tenant_id=principal.tenant_id,
            task_class=payload.task_class,
            prompt=payload.prompt,
            system=payload.system,
            actor_ref=principal.actor_ref,
            max_tokens=payload.max_tokens,
            json_mode=payload.json_mode,
        )
    except gateway.GatewayError as exc:
        raise HTTPException(
            status_code=503, detail={"error": {"code": exc.code, "message": str(exc)}}
        ) from exc
    db.commit()
    return {
        "text": result.text,
        "model": result.model_key,
        "provider": result.provider_kind,
        "cache_status": result.cache_status,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost": result.cost,
        "cost_saved": result.cost_saved,
        "latency_ms": result.latency_ms,
        "redactions": result.redactions,
        "notes": result.notes,
    }


# ==========================================================================
# Configuration versions — the two-person rule
# ==========================================================================
def _snapshot(db, tenant_id: uuid.UUID) -> dict:
    providers = db.execute(
        select(LlmProvider).where(LlmProvider.tenant_id == tenant_id)
    ).scalars().all()
    models = db.execute(
        select(LlmModel).where(LlmModel.tenant_id == tenant_id)
    ).scalars().all()
    routes = db.execute(
        select(LlmRoute).where(LlmRoute.tenant_id == tenant_id)
    ).scalars().all()
    policies = db.execute(
        select(LlmPolicy).where(LlmPolicy.tenant_id == tenant_id)
    ).scalars().all()
    return {
        # Deliberately excludes every credential field.
        "providers": [
            {
                "name": p.name, "kind": p.kind, "base_url": p.base_url,
                "status": p.status, "credential_hint": p.credential_hint,
            }
            for p in providers
        ],
        "models": [
            {
                "model_key": m.model_key, "capability": m.capability,
                "in_cost_per_1k": float(m.in_cost_per_1k),
                "out_cost_per_1k": float(m.out_cost_per_1k), "status": m.status,
            }
            for m in models
        ],
        "routes": [
            {
                "task_class": r.task_class, "environment": r.environment,
                "model_id": str(r.model_id), "temperature": float(r.temperature),
                "max_tokens": r.max_tokens, "cache_enabled": r.cache_enabled,
                "is_active": r.is_active,
            }
            for r in routes
        ],
        "policies": [
            {
                "scope": p.scope, "token_budget_daily": p.token_budget_daily,
                "cost_cap_monthly": float(p.cost_cap_monthly)
                if p.cost_cap_monthly
                else None,
                "kill_switch": p.kill_switch,
            }
            for p in policies
        ],
    }


@router.get("/versions", summary="Configuration change history")
def list_versions(db: DbSession, principal=Depends(requires("admin.llm.view"))) -> dict:
    rows = db.execute(
        select(LlmConfigVersion)
        .where(LlmConfigVersion.tenant_id == principal.tenant_id)
        .order_by(LlmConfigVersion.version_no.desc())
        .limit(50)
    ).scalars().all()
    return {
        "data": [
            {
                "id": str(v.id),
                "version_no": v.version_no,
                "status": v.status,
                "note": v.note,
                "snapshot_hash": v.snapshot_hash[:16],
                "proposed_at": v.proposed_at.isoformat() if v.proposed_at else None,
                "approved_at": v.approved_at.isoformat() if v.approved_at else None,
                "activated_at": v.activated_at.isoformat() if v.activated_at else None,
            }
            for v in rows
        ]
    }


@router.post("/versions", status_code=201, summary="Propose the current configuration")
def propose_version(
    db: DbSession,
    request_id: RequestId,
    note: str = Query(default="", max_length=1000),
    principal=Depends(requires("admin.llm.manage")),
) -> dict:
    """Captures the live configuration and raises a gate for a second person.

    The administrator who proposes cannot approve. That is the point: the
    combination of provider, model and routing determines what data leaves the
    estate and what it costs, and no one person should be able to change it
    alone.
    """
    from app.services import engine
    from app.models.core import Run

    snapshot = _snapshot(db, principal.tenant_id)
    digest = canonical_hash(snapshot)
    last = db.execute(
        select(LlmConfigVersion)
        .where(LlmConfigVersion.tenant_id == principal.tenant_id)
        .order_by(LlmConfigVersion.version_no.desc())
    ).scalars().first()
    if last and last.snapshot_hash == digest and last.status in {"proposed", "active"}:
        return {
            "unchanged": True,
            "version_no": last.version_no,
            "message": "The live configuration is identical to the last version.",
        }

    version = LlmConfigVersion(
        tenant_id=principal.tenant_id,
        version_no=(last.version_no + 1) if last else 1,
        snapshot=snapshot,
        snapshot_hash=digest,
        note=note or None,
        status="proposed",
        proposed_by=principal.id,
        proposed_at=utcnow(),
    )
    db.add(version)
    db.flush()

    workflow = db.execute(
        select(Workflow).where(
            Workflow.tenant_id == principal.tenant_id, Workflow.wf_code == "WF-26"
        )
    ).scalars().first()
    gate_id = None
    if workflow:
        run = Run(
            tenant_id=principal.tenant_id,
            workflow_id=workflow.id,
            wf_version=1,
            trigger_source=f"llm_config:v{version.version_no}",
            initiated_by=principal.id,
            started_at=utcnow(),
            created_at=utcnow(),
            context={"config_version_id": str(version.id)},
        )
        db.add(run)
        db.flush()
        gate = engine.raise_gate(
            db,
            run=run,
            activity_run=None,
            gate_type="config.llm_activation",
            reason=GateReason.IRREVERSIBLE,
            summary=f"Activate AI configuration version {version.version_no}",
            context={
                "config_version_id": str(version.id),
                "version_no": version.version_no,
                "snapshot_hash": digest,
                "note": note,
            },
            requested_by=principal.id,
            due_hours=48,
        )
        gate_id = str(gate.id)

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="admin.config_proposed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="llm_config_version",
        entity_id=version.id,
        after_state={"version_no": version.version_no, "hash": digest},
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(version.id),
        "version_no": version.version_no,
        "snapshot_hash": digest[:16],
        "gate_id": gate_id,
        "message": (
            "The configuration has been captured and sent for second approval. "
            "You cannot approve your own proposal."
        ),
    }


def _provider(db, tenant_id: uuid.UUID, provider_id: uuid.UUID) -> LlmProvider:
    provider = db.get(LlmProvider, provider_id)
    if provider is None or provider.tenant_id != tenant_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "No such provider."}},
        )
    return provider
