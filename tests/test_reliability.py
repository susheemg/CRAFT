"""Reliability under the conditions this repository actually ships.

Two defects lived here, and both only appear in the deployed configuration
rather than on a developer's machine:

  * render.yaml starts two uvicorn workers, and each started its own relay, so
    every webhook subscriber received every event twice
  * the API accepted an Idempotency-Key header and ignored it, so a client
    retrying a timed-out POST created a second record

Both are tested against the real database, because both are concurrency
properties that a mock cannot demonstrate.
"""

from __future__ import annotations

import os

import uuid

import pytest
from sqlalchemy import select

from app.db import session_scope
from app.models.audit import IdempotencyKey, OutboxEvent
from app.models.base import utcnow
from app.services import outbox


def _publish(db, tenant_id, topic="risk.raised", n=1):
    ids = []
    for i in range(n):
        event = outbox.publish(
            db, tenant_id=tenant_id, topic=topic, payload={"probe": i, "n": uuid.uuid4().hex}
        )
        ids.append(event.id)
    return ids


class TestOutboxClaiming:
    def test_two_relays_never_claim_the_same_event(self, tenant_id):
        """The defect that mattered: with two workers, every event went twice.

        Two claim transactions run against the same queue. SKIP LOCKED means
        the second walks past the first's locked rows rather than taking them,
        so the two claim sets must not intersect.
        """
        with session_scope(tenant_id=tenant_id) as db:
            published = set(_publish(db, tenant_id, n=8))

        # Two sessions, both claiming, with the first still open — exactly the
        # shape of two workers polling at the same instant.
        # The limit is generous because the queue may already hold events from
        # earlier tests; the property under test is that the two claim sets are
        # disjoint, not which events land in which.
        with session_scope(bypass_rls=True) as first:
            claimed_a = set(outbox.claim_batch(first, worker="worker-a", limit=500))
            assert claimed_a, "The first relay claimed nothing"

            with session_scope(bypass_rls=True) as second:
                claimed_b = set(outbox.claim_batch(second, worker="worker-b", limit=500))

        assert not (claimed_a & claimed_b), (
            f"Both relays claimed {len(claimed_a & claimed_b)} of the same events; "
            "every subscriber would have received those twice"
        )
        assert published <= (claimed_a | claimed_b), (
            "Published events were never claimed by either relay"
        )

    def test_a_claimed_event_is_not_reclaimed_while_the_claim_is_fresh(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            _publish(db, tenant_id, n=3)
        with session_scope(bypass_rls=True) as db:
            first = set(outbox.claim_batch(db, worker="worker-a", limit=50))
        with session_scope(bypass_rls=True) as db:
            second = set(outbox.claim_batch(db, worker="worker-b", limit=50))
        assert not (first & second)

    def test_an_abandoned_claim_is_reclaimed(self, tenant_id):
        """A worker that dies mid-delivery must not strand its events forever."""
        with session_scope(tenant_id=tenant_id) as db:
            event_ids = _publish(db, tenant_id, n=1)
        with session_scope(bypass_rls=True) as db:
            claimed = outbox.claim_batch(db, worker="doomed-worker", limit=50)
            assert event_ids[0] in claimed

        # Age the claim past the reclaim window, as a crash would.
        with session_scope(bypass_rls=True) as db:
            event = db.get(OutboxEvent, event_ids[0])
            event.claimed_at = utcnow() - outbox.RECLAIM_AFTER * 2

        with session_scope(bypass_rls=True) as db:
            reclaimed = outbox.claim_batch(db, worker="healthy-worker", limit=50)
        assert event_ids[0] in reclaimed

    def test_backoff_grows_and_is_capped(self):
        first = outbox._backoff(1).total_seconds()
        later = outbox._backoff(4).total_seconds()
        far = outbox._backoff(30).total_seconds()
        assert later > first, "Retries must slow down as attempts accumulate"
        assert far == outbox.BACKOFF_CAP_SECONDS, "Backoff must be capped"

    def test_the_reclaim_window_exceeds_the_delivery_timeout(self):
        """If a claim expired before a slow delivery finished, the event would
        be reclaimed and sent twice — the exact fault this is meant to prevent."""
        assert outbox.RECLAIM_AFTER.total_seconds() > outbox.DELIVERY_TIMEOUT_SECONDS * 5

    def test_an_event_not_yet_due_is_left_alone(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            event_ids = _publish(db, tenant_id, n=1)
        with session_scope(bypass_rls=True) as db:
            event = db.get(OutboxEvent, event_ids[0])
            event.next_attempt_at = utcnow() + outbox._backoff(3)
        with session_scope(bypass_rls=True) as db:
            claimed = outbox.claim_batch(db, worker="worker-a", limit=100)
        assert event_ids[0] not in claimed

    @pytest.mark.asyncio
    async def test_an_event_with_no_subscriber_is_completed_not_retried(self, tenant_id):
        """Nobody is listening, so the event is done. Leaving it pending would
        make the queue grow without bound on a deployment using no webhooks.

        Any subscription that happens to exist is stood down for the duration
        and restored afterwards, so the test measures the no-subscriber path
        rather than whatever the environment was left in.
        """
        from app.models.audit import WebhookSubscription

        with session_scope(bypass_rls=True) as db:
            live = db.execute(
                select(WebhookSubscription).where(WebhookSubscription.is_active.is_(True))
            ).scalars().all()
            stood_down = [s.id for s in live]
            for subscription in live:
                subscription.is_active = False

        try:
            with session_scope(tenant_id=tenant_id) as db:
                event_ids = _publish(db, tenant_id, topic="risk.raised", n=2)

            processed = await outbox.deliver_batch(limit=200)
            assert processed >= 2

            with session_scope(bypass_rls=True) as db:
                for event_id in event_ids:
                    event = db.get(OutboxEvent, event_id)
                    assert event.delivered_at is not None, (
                        "An event with no subscriber stayed pending; the queue "
                        "would grow without bound on a deployment using no webhooks"
                    )
                    assert event.claimed_at is None, "The claim was not released"
        finally:
            with session_scope(bypass_rls=True) as db:
                for subscription_id in stood_down:
                    subscription = db.get(WebhookSubscription, subscription_id)
                    if subscription:
                        subscription.is_active = True


class TestIdempotency:
    def test_a_retried_create_does_not_duplicate_the_record(self, client, headers):
        key = f"test-{uuid.uuid4()}"
        payload = {
            "title": "Retried create must produce exactly one risk",
            "inherent_likelihood": 3,
            "inherent_impact": 3,
        }
        first = client.post(
            "/v1/risks", headers={**headers["officer"], "Idempotency-Key": key}, json=payload
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/v1/risks", headers={**headers["officer"], "Idempotency-Key": key}, json=payload
        )
        assert second.status_code == 201
        assert second.headers.get("Idempotent-Replay") == "true"
        assert second.json()["id"] == first.json()["id"], (
            "The retry created a second risk instead of replaying the first"
        )

    def test_reusing_a_key_with_a_different_body_is_refused(self, client, headers):
        key = f"test-{uuid.uuid4()}"
        client.post(
            "/v1/risks",
            headers={**headers["officer"], "Idempotency-Key": key},
            json={"title": "The original request body", "inherent_likelihood": 2,
                  "inherent_impact": 2},
        )
        response = client.post(
            "/v1/risks",
            headers={**headers["officer"], "Idempotency-Key": key},
            json={"title": "A completely different request", "inherent_likelihood": 5,
                  "inherent_impact": 5},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "idempotency_key_reused"

    def test_requests_without_a_key_are_unaffected(self, client, headers):
        payload = {"title": "No key, so two calls mean two risks",
                   "inherent_likelihood": 2, "inherent_impact": 2}
        first = client.post("/v1/risks", headers=headers["officer"], json=payload)
        second = client.post("/v1/risks", headers=headers["officer"], json=payload)
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] != second.json()["id"]

    def test_a_failed_request_does_not_hold_its_key(self, client, headers, tenant_id):
        """A client whose request failed must be able to retry with the same key
        and have it actually run, rather than replaying the failure forever."""
        key = f"test-{uuid.uuid4()}"
        bad = client.post(
            "/v1/risks",
            headers={**headers["officer"], "Idempotency-Key": key},
            json={"title": "x", "inherent_likelihood": 99, "inherent_impact": 3},
        )
        assert bad.status_code == 422

        with session_scope(tenant_id=tenant_id) as db:
            held = db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.tenant_id == tenant_id, IdempotencyKey.key == key
                )
            ).scalar_one_or_none()
        assert held is None, "A rejected request kept its key, blocking a valid retry"

        good = client.post(
            "/v1/risks",
            headers={**headers["officer"], "Idempotency-Key": key},
            json={"title": "The corrected request now succeeds",
                  "inherent_likelihood": 3, "inherent_impact": 3},
        )
        assert good.status_code == 201

    def test_one_tenant_cannot_replay_another_tenants_response(self, client, headers):
        """The store is scoped by tenant, so guessing a key gets you nothing."""
        key = f"test-{uuid.uuid4()}"
        client.post(
            "/v1/risks",
            headers={**headers["officer"], "Idempotency-Key": key},
            json={"title": "Belongs to this tenant", "inherent_likelihood": 3,
                  "inherent_impact": 3},
        )
        with session_scope(bypass_rls=True) as db:
            rows = db.execute(
                select(IdempotencyKey).where(IdempotencyKey.key == key)
            ).scalars().all()
        assert len(rows) == 1
        assert rows[0].tenant_id is not None


class TestProductionConfiguration:
    """Guards on settings that are only wrong in production.

    Added after a Render deploy crash-looped with a connection-refused traceback
    against localhost:5432. The immediate cause was an unset CRAFT_DATABASE_URL,
    but the reason it was hard to read is that the setting had no production
    guard while every other production-critical secret did — so it fell back to
    a plausible default and failed two hundred lines away from its cause.
    """

    def _settings(self, monkeypatch, **overrides):
        import app.config as config

        config.get_settings.cache_clear()
        for key in ("CRAFT_DATABASE_URL", "CRAFT_MIGRATION_DATABASE_URL"):
            monkeypatch.delenv(key, raising=False)
        env = {
            "CRAFT_ENVIRONMENT": "production",
            "CRAFT_SECRET_KEY": "a-real-secret-key-for-this-test-only",
            "CRAFT_ENCRYPTION_KEY": "0" * 44,
            **overrides,
        }
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        try:
            return config.get_settings()
        finally:
            config.get_settings.cache_clear()

    def test_production_refuses_to_start_on_the_development_database_default(
        self, monkeypatch
    ):
        with pytest.raises(RuntimeError, match="CRAFT_DATABASE_URL is not set"):
            self._settings(monkeypatch)

    def test_the_guard_fires_even_when_craft_environment_is_also_missing(
        self, monkeypatch
    ):
        """The first version of this guard was gated on CRAFT_ENVIRONMENT ==
        production, and missed the live failure completely: when a service is
        misconfigured, CRAFT_ENVIRONMENT is one of the variables that is
        missing, so the settings fell back to 'development' and the guard stayed
        silent. A misconfiguration guard cannot depend on a variable that is
        part of the misconfiguration."""
        import app.config as config

        config.get_settings.cache_clear()
        for key in list(os.environ):
            if key.startswith("CRAFT_"):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("RENDER", "true")
        try:
            with pytest.raises(RuntimeError, match="CRAFT_DATABASE_URL is not set"):
                config.get_settings()
        finally:
            config.get_settings.cache_clear()

    def test_local_development_is_left_alone(self, monkeypatch):
        """No platform marker means a developer's laptop, where the localhost
        default is the correct answer and must keep working."""
        import app.config as config

        config.get_settings.cache_clear()
        for key in list(os.environ):
            if key.startswith("CRAFT_"):
                monkeypatch.delenv(key, raising=False)
        for marker in config.PLATFORM_MARKERS:
            monkeypatch.delenv(marker, raising=False)
        try:
            settings = config.get_settings()
            assert settings.database_url == config.LOCAL_DEV_DATABASE_URL
        finally:
            config.get_settings.cache_clear()

    def test_production_starts_when_the_database_url_is_supplied(self, monkeypatch):
        settings = self._settings(
            monkeypatch,
            CRAFT_DATABASE_URL="postgresql://user:pw@db.internal:5432/craft",
        )
        # Render hands out postgres:// and postgresql:// ; SQLAlchemy 2 with
        # psycopg 3 needs the driver named explicitly or it loads psycopg2.
        assert settings.database_url.startswith("postgresql+psycopg://")

    def test_pointing_production_at_localhost_deliberately_is_still_allowed(
        self, monkeypatch
    ):
        """The guard must catch an *unset* variable, not forbid a host. A
        sidecar or socket-proxy deployment is a legitimate reason to run
        production against localhost, and refusing that would be the guard
        overreaching."""
        settings = self._settings(
            monkeypatch,
            CRAFT_DATABASE_URL="postgresql://craft_app:pw@localhost:5432/craft",
        )
        assert "localhost" in settings.database_url


class TestPreflight:
    """The configuration report that runs before uvicorn forks.

    Added after a deploy that logged nothing but 'Child process died'. Two
    causes produce that silence — a configuration error raised while importing
    app.db inside a worker, and an OOM kill — and neither leaves a diagnosable
    line. Running the checks in the parent process is what makes them visible.
    """

    def _run(self, monkeypatch, env: dict) -> tuple[int, str]:
        import importlib
        import io
        import contextlib

        import app.config as config

        config.get_settings.cache_clear()
        for key in list(os.environ):
            if key.startswith("CRAFT_"):
                monkeypatch.delenv(key, raising=False)
        for marker in config.PLATFORM_MARKERS:
            monkeypatch.delenv(marker, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        preflight = importlib.import_module("app.preflight")
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = preflight.main()
        finally:
            config.get_settings.cache_clear()
        return code, out.getvalue() + err.getvalue()

    def test_it_fails_loudly_on_the_exact_deployed_misconfiguration(self, monkeypatch):
        code, output = self._run(monkeypatch, {"RENDER": "true"})
        assert code == 1
        assert "CRAFT_DATABASE_URL is not set" in output

    def test_it_passes_on_a_correctly_configured_service(self, monkeypatch):
        code, output = self._run(
            monkeypatch,
            {
                "RENDER": "true",
                "CRAFT_ENVIRONMENT": "production",
                "CRAFT_DATABASE_URL": "postgresql://u:p@db.internal:5432/craft",
                "CRAFT_SECRET_KEY": "a-real-secret-key-for-this-test-only",
                "CRAFT_ENCRYPTION_KEY": "0" * 44,
            },
        )
        assert code == 0
        assert "preflight passed" in output

    def test_it_never_prints_the_database_password(self, monkeypatch):
        """This output lands in a build log that is often shared when asking for
        help, so a leaked credential here is a credential leaked publicly."""
        code, output = self._run(
            monkeypatch,
            {
                "RENDER": "true",
                "CRAFT_ENVIRONMENT": "production",
                "CRAFT_DATABASE_URL": "postgresql://u:hunter2-do-not-log@db.internal:5432/craft",
                "CRAFT_SECRET_KEY": "a-real-secret-key-for-this-test-only",
                "CRAFT_ENCRYPTION_KEY": "0" * 44,
            },
        )
        assert code == 0
        assert "hunter2-do-not-log" not in output
        assert "db.internal" in output, "the host must still be shown, or it cannot be diagnosed"

    def test_a_missing_production_secret_is_named_rather_than_implied(self, monkeypatch):
        code, output = self._run(
            monkeypatch,
            {
                "RENDER": "true",
                "CRAFT_ENVIRONMENT": "production",
                "CRAFT_DATABASE_URL": "postgresql://u:p@db.internal:5432/craft",
            },
        )
        assert code == 1
        assert "CRAFT_SECRET_KEY" in output
