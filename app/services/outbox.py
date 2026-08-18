"""Transactional outbox and webhook delivery.

Events are written to ``audit.outbox_event`` inside the same transaction as the
state change that caused them. Either both commit or neither does, so a
subscriber never hears about a gate decision that was rolled back, and a
committed decision is never silently unannounced.

A background relay reads undelivered events, fans them out to matching
subscriptions and signs each body with the subscription's own secret. Delivery
is at-least-once with exponential backoff, so consumers must deduplicate on the
event id — the delivery envelope carries it for exactly that reason.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import os
import socket
from dataclasses import dataclass
from datetime import timedelta

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import session_scope
from app.models.audit import OutboxEvent, WebhookDelivery, WebhookSubscription
from app.models.base import utcnow
from app.security.crypto import SecretUnavailable, canonical_json, sign_hmac, unseal

log = logging.getLogger(__name__)
_settings = get_settings()

MAX_ATTEMPTS = 6
FAILURE_SUSPEND_THRESHOLD = 10

# The published catalogue. Adding a topic is additive and namespaced by domain.
TOPICS: tuple[str, ...] = (
    "workflow.deployed",
    "run.started",
    "run.completed",
    "run.failed",
    "gate.raised",
    "gate.decided",
    "risk.raised",
    "risk.accepted",
    "incident.created",
    "breach.detected",
    "control.updated",
    "gap.raised",
    "gap.closed",
    "readiness.changed",
    "budget.threshold",
    "budget.capped",
    "config.activated",
    "rbac.changed",
    "audit.chain_broken",
)


def publish(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    topic: str,
    payload: dict,
    request_id: str | None = None,
) -> OutboxEvent:
    """Queue an event in the caller's transaction."""
    if topic not in TOPICS:
        log.warning("Publishing unregistered topic '%s'", topic)
    event = OutboxEvent(
        tenant_id=tenant_id,
        topic=topic,
        payload=payload,
        occurred_at=utcnow(),
        request_id=request_id,
    )
    db.add(event)
    db.flush()
    return event


def envelope(event: OutboxEvent) -> dict:
    return {
        "id": f"evt_{event.id.hex}",
        "type": event.topic,
        "occurred_at": event.occurred_at.isoformat(),
        "request_id": event.request_id,
        "tenant_id": str(event.tenant_id),
        "data": event.payload,
    }


def _matches(subscription: WebhookSubscription, topic: str) -> bool:
    for pattern in subscription.topics or []:
        if pattern == "*" or pattern == topic:
            return True
        if pattern.endswith(".*") and topic.startswith(pattern[:-1]):
            return True
    return False


# A claim older than this is treated as abandoned. It needs to comfortably
# exceed the HTTP timeout below, or a slow-but-working delivery would be
# reclaimed and sent twice — which is the exact failure this code exists to
# prevent.
RECLAIM_AFTER = timedelta(minutes=5)
DELIVERY_TIMEOUT_SECONDS = 15.0
BACKOFF_BASE_SECONDS = 30
BACKOFF_CAP_SECONDS = 3600


def _backoff(attempts: int) -> timedelta:
    """Exponential, capped at an hour, applied per event.

    Per event rather than per cycle: one unreachable subscriber should slow its
    own retries down, not everything queued behind it.
    """
    return timedelta(seconds=min(BACKOFF_BASE_SECONDS * (2 ** attempts), BACKOFF_CAP_SECONDS))


def claim_batch(db: Session, worker: str, limit: int = 50) -> list[uuid.UUID]:
    """Take exclusive ownership of a batch of due events.

    ``FOR UPDATE SKIP LOCKED`` is what makes more than one relay safe: two
    workers running this at the same instant walk past each other's locked rows
    instead of both selecting the same ones. Without it, every uvicorn worker
    delivers every event, and a subscriber that opens a ticket per event opens
    one per worker.

    The transaction here is deliberately tiny — a select and an update, no
    network — so nothing holds row locks while a remote server thinks about it.
    """
    now = utcnow()
    rows = db.execute(
        select(OutboxEvent)
        .where(
            OutboxEvent.delivered_at.is_(None),
            OutboxEvent.attempts < MAX_ATTEMPTS,
            OutboxEvent.next_attempt_at <= now,
            or_(
                OutboxEvent.claimed_at.is_(None),
                OutboxEvent.claimed_at < now - RECLAIM_AFTER,
            ),
        )
        .order_by(OutboxEvent.occurred_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    claimed: list[uuid.UUID] = []
    for event in rows:
        event.claimed_at = now
        event.claimed_by = worker
        claimed.append(event.id)
    return claimed


@dataclass
class _Attempt:
    event_id: uuid.UUID
    subscription_id: uuid.UUID | None
    tenant_id: uuid.UUID
    topic: str
    ok: bool
    status: int | None
    error: str | None


def _secret_for(subscription: WebhookSubscription) -> str | None:
    """Unseal the subscription's signing secret, or None if it cannot be read.

    An unreadable secret is a configuration fault, not a delivery fault: sending
    the body unsigned would be worse than not sending it, because a receiver
    that trusts the signature would have no way to tell.
    """
    try:
        return unseal(subscription.secret_ciphertext)
    except SecretUnavailable:
        log.error(
            "Webhook '%s' has an unreadable secret; deliveries are suspended. "
            "Has CRAFT_ENCRYPTION_KEY changed?",
            subscription.name,
        )
        return None


async def _post_signed(
    client: httpx.AsyncClient, url: str, secret: str | None, body: bytes
) -> tuple[bool, int | None, str | None]:
    """POST one signed delivery. Never raises — the caller records the outcome."""
    if secret is None:
        return False, None, "Signing secret could not be read"
    try:
        response = await client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Craft-Signature": sign_hmac(secret, body),
                "X-Craft-Delivery": uuid.uuid4().hex,
                "User-Agent": f"CRAFT/{_settings.version}",
            },
        )
    except httpx.TimeoutException:
        return False, None, f"Timed out after {DELIVERY_TIMEOUT_SECONDS:.0f}s"
    except httpx.HTTPError as exc:
        return False, None, f"{type(exc).__name__}: {str(exc)[:200]}"
    ok = 200 <= response.status_code < 300
    detail = None if ok else f"HTTP {response.status_code}: {response.text[:200]}"
    return ok, response.status_code, detail


async def deliver_batch(limit: int = 50, worker: str | None = None) -> int:
    """Deliver one batch of pending events. Returns the number processed.

    Three phases, with no transaction open across the network:

      1. claim the batch and commit, so no other relay can take it
      2. deliver over HTTP, holding nothing
      3. record the outcomes and release the claim

    If the process dies between phases the events stay claimed until the
    reclaim window passes, then another relay picks them up. That is
    at-least-once delivery, which is why every event carries a stable id for
    receivers to deduplicate on.
    """
    worker = worker or f"{socket.gethostname()}:{os.getpid()}"

    # Phase 1 — claim.
    # The relay drains every tenant's queue, so it is one of the few callers
    # that legitimately runs above tenant isolation.
    with session_scope(bypass_rls=True) as db:
        claimed_ids = claim_batch(db, worker, limit)
    if not claimed_ids:
        return 0

    # Read what we need for delivery, then let the connection go.
    with session_scope(bypass_rls=True) as db:
        events = list(
            db.execute(select(OutboxEvent).where(OutboxEvent.id.in_(claimed_ids)))
            .scalars()
            .all()
        )
        subscriptions = list(
            db.execute(
                select(WebhookSubscription).where(WebhookSubscription.is_active.is_(True))
            ).scalars().all()
        )
        work = [
            (
                event.id,
                event.tenant_id,
                event.topic,
                canonical_json(envelope(event)).encode("utf-8"),
                [
                    (s.id, s.url, _secret_for(s))
                    for s in subscriptions
                    if s.tenant_id == event.tenant_id and _matches(s, event.topic)
                ],
            )
            for event in events
        ]

    # Phase 2 — deliver. No transaction is open here.
    attempts: list[_Attempt] = []
    unsubscribed: list[uuid.UUID] = []
    async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
        for event_id, tenant_id, topic, body, targets in work:
            if not targets:
                unsubscribed.append(event_id)  # nobody is listening; done.
                continue
            for subscription_id, url, secret in targets:
                ok, status, error = await _post_signed(client, url, secret, body)
                attempts.append(
                    _Attempt(event_id, subscription_id, tenant_id, topic, ok, status, error)
                )

    # Phase 3 — record outcomes and release the claim.
    with session_scope(bypass_rls=True) as db:
        now = utcnow()
        by_event: dict[uuid.UUID, list[_Attempt]] = {}
        for attempt in attempts:
            by_event.setdefault(attempt.event_id, []).append(attempt)

        for event in db.execute(
            select(OutboxEvent).where(OutboxEvent.id.in_(claimed_ids))
        ).scalars().all():
            event.claimed_at = None
            event.claimed_by = None

            if event.id in unsubscribed:
                event.delivered_at = now
                continue

            results = by_event.get(event.id, [])
            if not results:
                continue

            event.attempts += 1
            for attempt in results:
                db.add(
                    WebhookDelivery(
                        tenant_id=attempt.tenant_id,
                        subscription_id=attempt.subscription_id,
                        event_id=attempt.event_id,
                        topic=attempt.topic,
                        status_code=attempt.status,
                        outcome="delivered" if attempt.ok else "failed",
                        attempts=event.attempts,
                        error=attempt.error,
                        created_at=now,
                    )
                )
            if all(a.ok for a in results):
                event.delivered_at = now
                event.last_error = None
            else:
                failures = [a for a in results if not a.ok]
                event.last_error = failures[0].error or "Delivery failed"
                event.next_attempt_at = now + _backoff(event.attempts)
                if event.attempts >= MAX_ATTEMPTS:
                    log.error(
                        "Outbox event %s (%s) dead-lettered after %s attempts: %s",
                        event.id, event.topic, event.attempts, event.last_error,
                    )

        # Subscription health is updated once per subscription, not once per
        # attempt, so a batch of ten failures counts as one failing cycle.
        for subscription_id, results in _group_by_subscription(attempts).items():
            subscription = db.get(WebhookSubscription, subscription_id)
            if subscription is None:
                continue
            if any(a.ok for a in results):
                subscription.last_delivery_at = now
                subscription.last_success_at = now
                subscription.consecutive_failures = 0
            else:
                subscription.consecutive_failures += 1
                if subscription.consecutive_failures >= FAILURE_SUSPEND_THRESHOLD:
                    subscription.is_active = False
                    log.error(
                        "Suspended webhook '%s' after %s consecutive failures",
                        subscription.name, subscription.consecutive_failures,
                    )
    return len(claimed_ids)


def _group_by_subscription(attempts: list[_Attempt]) -> dict[uuid.UUID, list[_Attempt]]:
    grouped: dict[uuid.UUID, list[_Attempt]] = {}
    for attempt in attempts:
        if attempt.subscription_id:
            grouped.setdefault(attempt.subscription_id, []).append(attempt)
    return grouped


async def relay_loop(stop: asyncio.Event) -> None:
    """Background relay. Backoff is applied per cycle, not per event, which is
    enough for a single-service deployment and keeps the loop simple."""
    idle_cycles = 0
    cycles = 0
    while not stop.is_set():
        try:
            processed = await deliver_batch()
            idle_cycles = 0 if processed else min(idle_cycles + 1, 6)
            cycles += 1
            # Housekeeping runs on the relay because it is the one process
            # guaranteed to exist and it already has a schedule. Expired cache
            # entries and spent idempotency keys are otherwise never collected,
            # and both tables grow forever.
            if cycles % HOUSEKEEPING_EVERY_CYCLES == 0:
                _housekeeping()
        except Exception:  # noqa: BLE001 - the relay must not die
            log.exception("Outbox relay cycle failed")
            idle_cycles = min(idle_cycles + 1, 6)
        delay = _settings.outbox_poll_seconds * (2**idle_cycles if idle_cycles else 1)
        try:
            await asyncio.wait_for(stop.wait(), timeout=min(delay, 300))
        except asyncio.TimeoutError:
            continue


HOUSEKEEPING_EVERY_CYCLES = 60


def _housekeeping() -> None:
    """Collect what has expired. Never allowed to disturb delivery."""
    from app.api.idempotency import sweep_expired as sweep_keys
    from app.services.llm.cache import sweep_expired as sweep_cache

    try:
        with session_scope(bypass_rls=True) as db:
            cache_rows = sweep_cache(db)
            key_rows = sweep_keys(db)
        if cache_rows or key_rows:
            log.info(
                "Housekeeping removed %s expired cache entries and %s spent "
                "idempotency keys",
                cache_rows, key_rows,
            )
    except Exception:  # noqa: BLE001 - housekeeping must never stop the relay
        log.exception("Housekeeping cycle failed")


def replay(db: Session, event_id: uuid.UUID) -> OutboxEvent:
    """Requeue a delivered or dead-lettered event."""
    event = db.get(OutboxEvent, event_id)
    if event is None:
        raise ValueError("Event not found")
    event.delivered_at = None
    event.attempts = 0
    event.last_error = None
    # Without these two the event would be requeued but not actually due, and
    # a stale claim would keep every relay from touching it.
    event.next_attempt_at = utcnow()
    event.claimed_at = None
    event.claimed_by = None
    db.flush()
    return event


def dead_letters(db: Session, tenant_id: uuid.UUID) -> list[OutboxEvent]:
    return list(
        db.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.tenant_id == tenant_id,
                OutboxEvent.delivered_at.is_(None),
                OutboxEvent.attempts >= MAX_ATTEMPTS,
            )
            .order_by(OutboxEvent.occurred_at.desc())
            .limit(200)
        ).scalars().all()
    )


def stale_pending(db: Session, older_than_minutes: int = 30) -> int:
    cutoff = utcnow() - timedelta(minutes=older_than_minutes)
    return int(
        db.execute(
            select(OutboxEvent).where(
                OutboxEvent.delivered_at.is_(None), OutboxEvent.occurred_at < cutoff
            )
        ).scalars().all().__len__()
    )
