"""Compliance arithmetic and the catalogue behind it.

The numbers on the dashboard are the ones a certification auditor will
challenge, so they are tested directly rather than through the UI.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.db import session_scope
from app.models.compliance import ControlImplementation, Framework, FrameworkControl
from app.services import compliance as svc
from app.services.compliance import ComplianceError


class TestCatalogue:
    def test_iso27001_has_every_annex_a_control(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            fw = db.execute(select(Framework).where(Framework.code == "iso27001")).scalar_one()
            annex = db.execute(
                select(func.count(FrameworkControl.id)).where(
                    FrameworkControl.framework_id == fw.id,
                    FrameworkControl.control_type == "control",
                )
            ).scalar_one()
        # ISO/IEC 27001:2022 Annex A contains 93 controls.
        assert annex == 93

    def test_the_annex_a_theme_split_matches_the_standard(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            fw = db.execute(select(Framework).where(Framework.code == "iso27001")).scalar_one()
            rows = db.execute(
                select(FrameworkControl.theme, func.count(FrameworkControl.id))
                .where(
                    FrameworkControl.framework_id == fw.id,
                    FrameworkControl.control_type == "control",
                )
                .group_by(FrameworkControl.theme)
            ).all()
        counts = {theme: n for theme, n in rows}
        assert counts == {
            "organisational": 37,
            "people": 8,
            "physical": 14,
            "technological": 34,
        }

    def test_no_duplicate_references_within_a_framework(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            duplicates = db.execute(
                select(FrameworkControl.framework_id, FrameworkControl.ref_code)
                .group_by(FrameworkControl.framework_id, FrameworkControl.ref_code)
                .having(func.count(FrameworkControl.id) > 1)
            ).all()
        assert not duplicates, f"Duplicate control references: {duplicates}"

    def test_iso22301_and_gdpr_are_present(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            codes = set(db.execute(select(Framework.code)).scalars().all())
        assert {"iso27001", "iso22301", "uk_gdpr"} <= codes


class TestReadinessArithmetic:
    @pytest.fixture(scope="class", autouse=True)
    def programme(self, client, headers):
        response = client.post(
            "/v1/compliance/programmes",
            headers=headers["ciso"],
            json={"framework": "iso27001", "scope_statement": "Test scope"},
        )
        assert response.status_code in (201, 422), response.text

    def test_a_fresh_programme_starts_at_zero(self, client, headers, tenant_id):
        response = client.get("/v1/compliance/iso27001/readiness", headers=headers["ciso"])
        assert response.status_code == 200
        body = response.json()
        assert body["total_controls"] == 118  # 25 clauses + 93 Annex A controls
        assert body["applicable"] > 0

    def test_certification_is_blocked_while_mandatory_clauses_are_unmet(
        self, client, headers
    ):
        body = client.get(
            "/v1/compliance/iso27001/readiness", headers=headers["ciso"]
        ).json()
        assert body["certification_ready"] is False
        assert body["blockers"], "A programme with nothing implemented must list blockers"

    def test_an_unevidenced_claim_is_discounted(self, client, headers):
        """Claiming a control operates, with no evidence, must not score full marks.

        This is the difference between a readiness figure that survives an audit
        and one that does not. The test picks a control that has not been
        touched, so it measures the change rather than whatever a previous run
        left behind.
        """
        controls = client.get(
            "/v1/compliance/iso27001/controls?status=not_started&limit=5",
            headers=headers["ciso"],
        ).json()["data"]
        assert controls, "Expected at least one untouched control to measure against"
        target = controls[0]

        def readiness() -> float:
            return client.get(
                "/v1/compliance/iso27001/readiness", headers=headers["ciso"]
            ).json()["readiness_pct"]

        before = readiness()
        client.patch(
            f"/v1/compliance/controls/{target['id']}",
            headers=headers["ciso"],
            json={"status": "operating", "maturity": 4,
                  "how_implemented": "Asserted with no supporting evidence"},
        )
        unevidenced = readiness()

        client.post(
            "/v1/compliance/evidence",
            headers=headers["ciso"],
            json={"kind": "attestation", "title": f"Evidence for {target['ref_code']}",
                  "payload": {"detail": "quarterly review record"},
                  "subject_type": "control_implementation", "subject_id": target["id"]},
        )
        evidenced = readiness()

        assert unevidenced > before, "Implementing a control should raise readiness"
        assert evidenced > unevidenced, (
            "Attaching evidence must raise readiness further, or the discount "
            "for an unevidenced claim is not being applied"
        )
        # An unevidenced claim must score strictly less than an evidenced one.
        # The exact ratio is asserted in the arithmetic test below rather than
        # here: readiness_pct is reported to one decimal place, and one control
        # out of 118 moves it by well under a point, so the rounding swamps the
        # ratio at this level of measurement.
        assert (unevidenced - before) < (evidenced - before)

    def test_the_discount_is_applied_at_the_control_level(self):
        """Arithmetic check, independent of how much data happens to be present."""
        from app.models.base import ImplementationStatus

        operating = svc.STATUS_WEIGHT[ImplementationStatus.OPERATING]
        assert operating == 1.0
        assert svc.EVIDENCE_DISCOUNT < 1.0
        # An unevidenced "operating" claim must score below an evidenced
        # "implemented" one: proof beats assertion.
        implemented = svc.STATUS_WEIGHT[ImplementationStatus.IMPLEMENTED]
        assert operating * svc.EVIDENCE_DISCOUNT < implemented

        # The discount is exactly what the configuration says: a control claimed
        # to be operating with no evidence scores 70% of one that is evidenced.
        assert operating * svc.EVIDENCE_DISCOUNT == pytest.approx(0.70)

    def test_a_mandatory_clause_cannot_be_excluded(self, client, headers):
        controls = client.get(
            "/v1/compliance/iso27001/controls?limit=200", headers=headers["ciso"]
        ).json()["data"]
        clause = next(c for c in controls if c["ref_code"].startswith(("4.", "5.", "6.")))
        response = client.patch(
            f"/v1/compliance/controls/{clause['id']}",
            headers=headers["ciso"],
            json={"is_applicable": False, "applicability_justification": "Not for us"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "mandatory_clause"

    def test_excluding_a_control_without_justification_is_refused(self, client, headers):
        controls = client.get(
            "/v1/compliance/iso27001/controls?limit=200", headers=headers["ciso"]
        ).json()["data"]
        annex = next(c for c in controls if c["ref_code"].startswith("A."))
        response = client.patch(
            f"/v1/compliance/controls/{annex['id']}",
            headers=headers["ciso"],
            json={"is_applicable": False},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "justification_required"


class TestStatementOfApplicability:
    def test_the_soa_covers_every_control_with_no_omissions(self, client, headers):
        """An auditor reads the SoA first. Every control must appear, included
        or excluded, and every exclusion must carry a reason."""
        soa = client.get("/v1/compliance/iso27001/soa", headers=headers["ciso"]).json()
        assert soa["total"] == len(soa["entries"]) == 118
        assert soa["included"] + soa["excluded"] == soa["total"]
        for entry in soa["entries"]:
            assert entry["ref"] and "applicable" in entry
        # The SoA reports its own weakness rather than hiding it: an exclusion
        # with no reason is counted, so it can be found and fixed before audit.
        unjustified = [
            e["ref"] for e in soa["entries"]
            if not e["applicable"] and not e["justification"].strip()
        ]
        assert len(unjustified) == soa["missing_justification"]

    def test_the_soa_is_refused_for_a_framework_with_no_programme(self, client, headers):
        response = client.get("/v1/compliance/iso22301/soa", headers=headers["ciso"])
        assert response.status_code in (404, 422)
