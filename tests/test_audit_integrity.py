"""The audit log must be trustworthy, or nothing else in the platform is.

Two independent defences are tested here, because they fail differently:

  * the database refuses UPDATE and DELETE on the log, which stops the ordinary
    mistake and the ordinary insider
  * the hash chain detects alteration even when the trigger is bypassed, which
    is the only defence that survives someone with database-owner rights

The second is the one that matters under audit. A control that only works while
nobody has privileged access is not a control.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError, InternalError, ProgrammingError

from app.config import get_settings
from app.db import session_scope, set_session_context

# Trigger and policy manipulation needs the owning credential; that is the
# point of these tests — they simulate someone who *has* that access.
engine = create_engine(get_settings().owner_database_url, future=True)
from app.models.audit import AuditLog
from app.models.base import ActorType, utcnow
from app.models.domain import Risk
from app.models.iam import Tenant
from app.services import audit


def _write(db, tenant_id, n=5, prefix="test"):
    for i in range(n):
        audit.record(
            db,
            tenant_id=tenant_id,
            action=f"{prefix}.event.{i}",
            actor_type=ActorType.HUMAN,
            actor_ref="human:pytest",
            entity="test_entity",
            detail={"index": i},
        )


class TestImmutability:
    def test_update_is_refused_by_the_database(self, tenant_db, tenant_id):
        _write(tenant_db, tenant_id, 2, prefix="upd")
        tenant_db.commit()
        with engine.begin() as conn:
            with pytest.raises((ProgrammingError, InternalError, DBAPIError)) as exc:
                conn.execute(
                    text("UPDATE audit.audit_log SET action = 'tampered' WHERE seq = 1")
                )
        assert "append-only" in str(exc.value).lower()

    def test_delete_is_refused_by_the_database(self, tenant_db, tenant_id):
        _write(tenant_db, tenant_id, 2, prefix="del")
        tenant_db.commit()
        with engine.begin() as conn:
            with pytest.raises((ProgrammingError, InternalError, DBAPIError)) as exc:
                conn.execute(text("DELETE FROM audit.audit_log WHERE seq = 1"))
        assert "append-only" in str(exc.value).lower()

    def test_truncate_is_refused(self, tenant_db, tenant_id):
        with engine.begin() as conn:
            with pytest.raises((ProgrammingError, InternalError, DBAPIError)):
                conn.execute(text("TRUNCATE audit.audit_log"))


class TestHashChain:
    def test_chain_is_intact_after_ordinary_writes(self, tenant_db, tenant_id):
        _write(tenant_db, tenant_id, 6, prefix="chain")
        tenant_db.commit()
        report = audit.verify_chain(tenant_db, tenant_id)
        assert report.is_intact
        assert report.rows_checked > 0
        assert report.first_broken_seq is None

    def test_each_entry_links_to_its_predecessor(self, tenant_db, tenant_id):
        _write(tenant_db, tenant_id, 4, prefix="link")
        tenant_db.commit()
        rows = tenant_db.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.seq.desc())
            .limit(4)
        ).scalars().all()
        rows = list(reversed(rows))
        for earlier, later in zip(rows, rows[1:]):
            assert later.prev_hash == earlier.row_hash

    def test_content_tampering_is_detected_when_the_trigger_is_bypassed(
        self, tenant_db, tenant_id
    ):
        """The scenario that matters: someone with database-owner rights edits
        history, disabling the trigger to do it. The chain still gives them away."""
        _write(tenant_db, tenant_id, 5, prefix="tamper")
        tenant_db.commit()
        target = tenant_db.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.action.like("tamper.%"))
            .order_by(AuditLog.seq)
        ).scalars().all()[2]
        original_action = target.action

        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE audit.audit_log DISABLE TRIGGER trg_audit_log_immutable")
            )
            conn.execute(
                text("UPDATE audit.audit_log SET action = :a WHERE seq = :s"),
                {"a": "quietly.rewritten", "s": target.seq},
            )
            conn.execute(
                text("ALTER TABLE audit.audit_log ENABLE TRIGGER trg_audit_log_immutable")
            )

        with session_scope() as fresh:
            set_session_context(fresh, tenant_id, "human:test")
            report = audit.verify_chain(fresh, tenant_id)
        assert not report.is_intact
        assert report.first_broken_seq == target.seq
        assert "hash" in (report.reason or "").lower()

        with engine.begin() as conn:  # restore, so later tests see a sound chain
            conn.execute(
                text("ALTER TABLE audit.audit_log DISABLE TRIGGER trg_audit_log_immutable")
            )
            conn.execute(
                text("UPDATE audit.audit_log SET action = :a WHERE seq = :s"),
                {"a": original_action, "s": target.seq},
            )
            conn.execute(
                text("ALTER TABLE audit.audit_log ENABLE TRIGGER trg_audit_log_immutable")
            )
        with session_scope() as fresh:
            set_session_context(fresh, tenant_id, "human:test")
            assert audit.verify_chain(fresh, tenant_id).is_intact

    def test_deletion_is_detected_as_a_broken_link(self, tenant_db, tenant_id):
        _write(tenant_db, tenant_id, 5, prefix="splice")
        tenant_db.commit()
        rows = tenant_db.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.action.like("splice.%"))
            .order_by(AuditLog.seq)
        ).scalars().all()
        victim = rows[2]
        from psycopg.types.json import Jsonb

        json_columns = {
            "before_state", "after_state", "detail", "sources",
        }
        saved = {
            c.name: (
                Jsonb(getattr(victim, c.name))
                if c.name in json_columns and getattr(victim, c.name) is not None
                else getattr(victim, c.name)
            )
            for c in AuditLog.__table__.columns
        }

        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE audit.audit_log DISABLE TRIGGER trg_audit_log_immutable")
            )
            conn.execute(
                text("DELETE FROM audit.audit_log WHERE seq = :s"), {"s": victim.seq}
            )
            conn.execute(
                text("ALTER TABLE audit.audit_log ENABLE TRIGGER trg_audit_log_immutable")
            )

        with session_scope() as fresh:
            set_session_context(fresh, tenant_id, "human:test")
            report = audit.verify_chain(fresh, tenant_id)
        # Removing an entry orphans the one that pointed at it.
        assert not report.is_intact

        with engine.begin() as conn:
            conn.execute(text("SELECT set_config('app.bypass_rls', 'on', true)"))
            columns = ", ".join(saved)
            placeholders = ", ".join(f":{k}" for k in saved)
            conn.execute(
                text("ALTER TABLE audit.audit_log DISABLE TRIGGER trg_audit_log_immutable")
            )
            conn.execute(
                text(f"INSERT INTO audit.audit_log ({columns}) VALUES ({placeholders})"),
                saved,
            )
            conn.execute(
                text("ALTER TABLE audit.audit_log ENABLE TRIGGER trg_audit_log_immutable")
            )
        with session_scope() as fresh:
            set_session_context(fresh, tenant_id, "human:test")
            assert audit.verify_chain(fresh, tenant_id).is_intact

    def test_verification_is_exposed_through_the_api(self, client, headers):
        response = client.get("/v1/audit/verify", headers=headers["security_admin"])
        assert response.status_code == 200
        body = response.json()
        assert body["intact"] is True
        assert body["rows_checked"] > 0
        assert "hashes to its recorded value" in body["interpretation"]

    def test_reading_the_log_requires_the_permission(self, client, headers):
        assert client.get("/v1/audit/log", headers=headers["operator"]).status_code == 403
        assert client.get("/v1/audit/log", headers=headers["auditor"]).status_code == 200


class TestTenantIsolation:
    def test_row_level_security_hides_another_tenant_completely(self, tenant_id):
        """Set up a second tenant with its own risk, then confirm a session bound
        to the first cannot see it — not filtered in the query, but invisible."""
        with session_scope() as db:
            other = Tenant(name=f"Isolation-{uuid.uuid4().hex[:8]}", region="uk",
                           status="active", created_at=utcnow())
            db.add(other)
            db.flush()
            other_id = other.id
            ref = f"OTHER-{uuid.uuid4().hex[:6].upper()}"
            set_session_context(db, other_id, "human:other")
            db.add(
                Risk(
                    tenant_id=other_id,
                    risk_ref=ref,
                    title="A risk belonging to the other tenant",
                    category="information_security",
                    inherent_likelihood=3,
                    inherent_impact=3,
                    inherent_score=9,
                    severity_band="medium",
                    created_at=utcnow(),
                )
            )

        with session_scope() as db:
            set_session_context(db, other_id, "human:other")
            assert db.execute(
                select(Risk).where(Risk.risk_ref == ref)
            ).scalar_one_or_none() is not None

        with session_scope() as db:
            set_session_context(db, tenant_id, "human:test")
            leaked = db.execute(
                select(Risk).where(Risk.risk_ref == ref)
            ).scalar_one_or_none()
        assert leaked is None, (
            "A risk from another tenant was visible. Row-level security is not "
            "being applied on this connection."
        )

    def test_audit_sequence_is_per_tenant(self, tenant_id):
        """Two tenants each get their own chain, so activity in one cannot
        perturb the other's sequence or hashes."""
        with session_scope() as db:
            other = Tenant(name=f"Seq-{uuid.uuid4().hex[:8]}", region="uk",
                           status="active", created_at=utcnow())
            db.add(other)
            db.flush()
            other_id = other.id
            set_session_context(db, other_id, "human:other")
            _write(db, other_id, 3, prefix="othertenant")

        with session_scope() as db:
            set_session_context(db, other_id, "human:other")
            seq, _ = audit.head(db, other_id)
            assert seq == 3, "A new tenant's chain should start at one"
            assert audit.verify_chain(db, other_id).is_intact
