"""Application security (ISO/IEC 27034) and AI management (ISO/IEC 42001).

The tests worth having here are the ones that prove a control *refuses*
something. A control that has only ever been observed permitting things has not
been tested; it has been used.

So the emphasis is on the refusals: the separation of duties between performing
a security activity and verifying it, the controls an agent may never attest to,
the floor a project team cannot remove, and the impact assessment that cannot be
approved without a human behind it. Each is enforced in the database, so each is
tested against the database rather than against the service that calls it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.db import session_scope
from app.models.aims import AiImpactAssessment, AiSystem
from app.models.appsec import (
    Anf,
    AnfAsc,
    Application,
    Asc,
    AscEvidence,
    AslcrmStage,
    LifecycleStageMap,
    Onf,
    SoaEntry,
    TrustLevel,
)
from app.models.base import utcnow
from app.models.compliance import Framework, FrameworkControl
from app.models.iam import AgentIdentity, UserAccount
from app.services import appsec as svc
from app.services.appsec import AppSecError


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _application(db, tenant_id, **kwargs) -> Application:
    app = Application(
        tenant_id=tenant_id,
        code=_unique("APP"),
        name="Test application",
        created_at=utcnow(),
        **kwargs,
    )
    db.add(app)
    db.flush()
    return app


def _two_actors(db, tenant_id) -> tuple[UserAccount, AgentIdentity]:
    user = db.execute(
        select(UserAccount).where(UserAccount.tenant_id == tenant_id).limit(1)
    ).scalars().first()
    agent = db.execute(
        select(AgentIdentity).where(AgentIdentity.agent_key == "appsec")
    ).scalars().first()
    return user, agent


# ==========================================================================
# The catalogue
# ==========================================================================
class TestIso42001Catalogue:
    def test_annex_a_carries_thirty_eight_controls(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            fw = db.execute(select(Framework).where(Framework.code == "iso42001")).scalar_one()
            annex = db.execute(
                select(func.count(FrameworkControl.id)).where(
                    FrameworkControl.framework_id == fw.id,
                    FrameworkControl.control_type == "control",
                )
            ).scalar_one()
        assert annex == 38

    def test_annex_a_spans_nine_control_objectives(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            fw = db.execute(select(Framework).where(Framework.code == "iso42001")).scalar_one()
            sections = db.execute(
                select(func.count(func.distinct(FrameworkControl.section))).where(
                    FrameworkControl.framework_id == fw.id,
                    FrameworkControl.control_type == "control",
                )
            ).scalar_one()
        assert sections == 9

    def test_the_management_system_clauses_are_mandatory(self, tenant_id):
        """A clause an organisation may exclude is not a clause. Only Annex A is
        selectable; clauses 4 to 10 are not."""
        with session_scope(tenant_id=tenant_id) as db:
            fw = db.execute(select(Framework).where(Framework.code == "iso42001")).scalar_one()
            optional_clauses = db.execute(
                select(func.count(FrameworkControl.id)).where(
                    FrameworkControl.framework_id == fw.id,
                    FrameworkControl.control_type == "requirement",
                    FrameworkControl.is_mandatory.is_(False),
                )
            ).scalar_one()
        assert optional_clauses == 0

    def test_certification_is_blocked_while_the_catalogue_is_a_paraphrase(self):
        """The block is a property of the catalogue, not a policy someone has to
        remember on the day."""
        block = svc.certification_block("iso42001")
        assert block is not None
        assert "reconcil" in block.lower()
        # Other frameworks ship published clause names and are not blocked.
        assert svc.certification_block("iso27001") is None


# ==========================================================================
# The Organization Normative Framework
# ==========================================================================
class TestOrganizationNormativeFramework:
    def test_the_onf_seeds_with_a_full_asc_library(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            ascs = db.execute(
                select(func.count(Asc.id)).where(Asc.onf_id == onf.id)
            ).scalar_one()
        assert ascs == 27

    def test_every_asc_specifies_both_halves_of_the_control(self, tenant_id):
        """An ASC with an activity and no measurement is a checklist item. The
        separation between doing and verifying is the whole point."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            ascs = list(db.execute(select(Asc).where(Asc.onf_id == onf.id)).scalars())
        incomplete = [
            a.asc_uid for a in ascs if not a.activity_spec or not a.measurement_spec
        ]
        assert incomplete == []

    def test_exactly_one_level_zero_exists(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            zeros = db.execute(
                select(func.count(TrustLevel.id)).where(
                    TrustLevel.onf_id == onf.id, TrustLevel.is_level_zero.is_(True)
                )
            ).scalar_one()
        assert zeros == 1

    def test_a_second_level_zero_is_refused_by_the_database(self, tenant_id):
        """Two floors means no floor."""
        with pytest.raises(Exception) as exc:
            with session_scope(tenant_id=tenant_id) as db:
                onf = svc.current_onf(db, tenant_id)
                db.add(
                    TrustLevel(
                        tenant_id=tenant_id,
                        onf_id=onf.id,
                        level_no=99,
                        label="Second floor",
                        is_level_zero=True,
                        created_at=utcnow(),
                    )
                )
                db.flush()
        assert "uq_trust_level_one_zero" in str(exc.value)

    def test_every_reference_stage_has_a_local_stage_mapped_to_it(self, tenant_id):
        """An ASC placed at a reference stage with no local equivalent can never
        be scheduled, so the gap is a defect rather than a detail."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            reference = {s.code for s in db.execute(select(AslcrmStage)).scalars()}
            mapped = {
                m.aslcrm_stage_code
                for m in db.execute(
                    select(LifecycleStageMap).where(LifecycleStageMap.onf_id == onf.id)
                ).scalars()
            }
        assert reference - mapped == set()

    def test_controls_that_govern_agents_require_a_human_verifier(self, tenant_id):
        """An agent attesting to the controls that bound agents is the clearest
        case where fluency would be mistaken for assurance."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            for uid in ("ASC-AI-AGENTMANDATE", "ASC-BLD-REVIEW", "ASC-AUD-INDEPENDENT"):
                asc = db.execute(
                    select(Asc).where(Asc.onf_id == onf.id, Asc.asc_uid == uid)
                ).scalar_one()
                assert asc.measurement_requires_human, uid


# ==========================================================================
# Building an Application Normative Framework
# ==========================================================================
class TestApplicationNormativeFramework:
    def test_an_anf_at_level_two_inherits_the_level_zero_floor(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            level_two = db.execute(
                select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.level_no == 2)
            ).scalar_one()
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, level_two)

            floor = db.execute(
                select(func.count(AnfAsc.id)).where(
                    AnfAsc.anf_id == anf.id, AnfAsc.is_level_zero.is_(True)
                )
            ).scalar_one()
            total = db.execute(
                select(func.count(AnfAsc.id)).where(AnfAsc.anf_id == anf.id)
            ).scalar_one()

        assert floor > 0, "a level-two ANF that omits the floor is not an ANF"
        assert total > floor, "level two should require more than the floor alone"

    def test_a_level_zero_control_cannot_be_waived(self, tenant_id):
        with pytest.raises(Exception) as exc:
            with session_scope(tenant_id=tenant_id) as db:
                onf = svc.current_onf(db, tenant_id)
                zero = svc.level_zero(db, onf)
                app = _application(db, tenant_id)
                anf = svc.build_anf(db, app, zero)
                selection = db.execute(
                    select(AnfAsc).where(
                        AnfAsc.anf_id == anf.id, AnfAsc.is_level_zero.is_(True)
                    ).limit(1)
                ).scalars().first()
                selection.waived_at = utcnow()
                selection.waiver_reason = "project deadline"
                db.flush()
        assert "ck_anf_asc_level_zero_locked" in str(exc.value)

    def test_building_a_new_version_supersedes_the_previous_one(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            level_one = db.execute(
                select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.level_no == 1)
            ).scalar_one()
            app = _application(db, tenant_id)
            first = svc.build_anf(db, app, level_one)
            second = svc.build_anf(db, app, level_one)
            db.flush()
            db.refresh(first)

        assert first.status == "superseded"
        assert second.version == first.version + 1


# ==========================================================================
# Separation of duties — the control this release exists to add
# ==========================================================================
class TestSeparationOfDuties:
    def _selection(self, db, tenant_id, *, human_only: bool):
        onf = svc.current_onf(db, tenant_id)
        level = db.execute(
            select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.level_no == 3)
        ).scalar_one()
        app = _application(db, tenant_id)
        anf = svc.build_anf(db, app, level)
        uid = "ASC-AI-AGENTMANDATE" if human_only else "ASC-BLD-SAST"
        asc = db.execute(
            select(Asc).where(Asc.onf_id == onf.id, Asc.asc_uid == uid)
        ).scalar_one()
        return db.execute(
            select(AnfAsc).where(AnfAsc.anf_id == anf.id, AnfAsc.asc_id == asc.id)
        ).scalar_one()

    def test_an_agent_may_perform_a_security_activity(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            _user, agent = _two_actors(db, tenant_id)
            selection = self._selection(db, tenant_id, human_only=False)
            row = svc.record_evidence(
                db, selection, kind="activity", actor_type="agent",
                actor_agent_id=agent.id, outcome="pass",
            )
            assert row.provenance == "tool_output"

    def test_the_same_agent_cannot_then_verify_its_own_work(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            _user, agent = _two_actors(db, tenant_id)
            selection = self._selection(db, tenant_id, human_only=False)
            svc.record_evidence(
                db, selection, kind="activity", actor_type="agent",
                actor_agent_id=agent.id, outcome="pass",
            )
            with pytest.raises(AppSecError, match="cannot record its verification"):
                svc.record_evidence(
                    db, selection, kind="measurement", actor_type="agent",
                    actor_agent_id=agent.id, outcome="pass",
                )

    def test_a_different_actor_may_verify(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            user, agent = _two_actors(db, tenant_id)
            selection = self._selection(db, tenant_id, human_only=False)
            svc.record_evidence(
                db, selection, kind="activity", actor_type="agent",
                actor_agent_id=agent.id, outcome="pass",
            )
            row = svc.record_evidence(
                db, selection, kind="measurement", actor_type="human",
                actor_user_id=user.id, outcome="pass",
            )
            assert row.provenance == "human_attested"

    def test_a_human_only_control_refuses_an_agent_measurement(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            _user, agent = _two_actors(db, tenant_id)
            selection = self._selection(db, tenant_id, human_only=True)
            with pytest.raises(AppSecError, match="human verifier"):
                svc.record_evidence(
                    db, selection, kind="measurement", actor_type="agent",
                    actor_agent_id=agent.id, outcome="pass",
                )

    def test_agent_output_cannot_be_labelled_as_human_attestation(self, tenant_id):
        """The provenance label is what lets an auditor filter the evidence base.
        An agent record claiming human attestation would make the label useless."""
        with session_scope(tenant_id=tenant_id) as db:
            _user, agent = _two_actors(db, tenant_id)
            selection = self._selection(db, tenant_id, human_only=False)
            with pytest.raises(Exception) as exc:
                svc.record_evidence(
                    db, selection, kind="activity", actor_type="agent",
                    actor_agent_id=agent.id, provenance="human_attested",
                )
            assert "ck_asc_evidence_agent_not_attested" in str(exc.value)


# ==========================================================================
# Level of trust and the release gate
# ==========================================================================
class TestLevelOfTrust:
    def test_an_unmeasured_application_does_not_meet_its_target(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            level_two = db.execute(
                select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.level_no == 2)
            ).scalar_one()
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, level_two, approved_by=uuid.uuid4())
            decision = svc.release_decision(db, anf)

        assert decision["allowed"] is False
        assert decision["passing"] == 0
        assert decision["blocking"], "a blocked release must name what is blocking it"

    def test_the_gate_names_the_controls_responsible(self, tenant_id):
        """A bare refusal makes the gate an obstacle. Naming the controls makes
        it a work list."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            level_one = db.execute(
                select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.level_no == 1)
            ).scalar_one()
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, level_one, approved_by=uuid.uuid4())
            decision = svc.release_decision(db, anf)

        assert "reason" in decision
        assert any(uid.startswith("ASC-") for uid in decision["blocking"])

    def test_an_activity_record_alone_does_not_satisfy_a_control(self, tenant_id):
        """The two-part control exists so that somebody independent confirms the
        activity worked. Counting the activity would erase that."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            zero = svc.level_zero(db, onf)
            _user, agent = _two_actors(db, tenant_id)
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, zero, approved_by=uuid.uuid4())
            for selection in db.execute(
                select(AnfAsc).where(AnfAsc.anf_id == anf.id)
            ).scalars():
                svc.record_evidence(
                    db, selection, kind="activity", actor_type="agent",
                    actor_agent_id=agent.id, outcome="pass",
                )
            result = svc.compute_level_of_trust(db, anf)

        assert result.passing == 0
        assert result.meets_target is False

    def test_a_fully_measured_application_reaches_its_target(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            zero = svc.level_zero(db, onf)
            user, agent = _two_actors(db, tenant_id)
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, zero, approved_by=user.id)
            for selection in db.execute(
                select(AnfAsc).where(AnfAsc.anf_id == anf.id)
            ).scalars():
                svc.record_evidence(
                    db, selection, kind="activity", actor_type="agent",
                    actor_agent_id=agent.id, outcome="pass",
                )
                svc.record_evidence(
                    db, selection, kind="measurement", actor_type="human",
                    actor_user_id=user.id, outcome="pass",
                )
            decision = svc.release_decision(db, anf)

        assert decision["allowed"] is True
        assert decision["actual_level"] >= decision["targeted_level"]
        assert decision["blocking"] == []

    def test_a_level_that_adds_no_control_is_reported_as_a_design_defect(self, tenant_id):
        """Found by this suite: level one required nothing level zero did not, so
        passing the floor silently demonstrated level one. The arithmetic was
        right; the level design was not, and nothing surfaced it."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            issues = svc.onf_level_design_issues(db, onf)
        assert all("indistinguishable" in i for i in issues)
        # Recorded rather than asserted away: the shipped library has this
        # defect at level one and PR-APS-04 owns closing it.
        assert any("Level 1" in i for i in issues), (
            "the shipped seed has an indistinguishable level one; if that has been "
            "fixed, remove this assertion"
        )

    def test_the_computation_is_reproducible(self, tenant_id):
        """Running unattended is only defensible because the answer is arithmetic
        an auditor can recompute."""
        with session_scope(tenant_id=tenant_id) as db:
            onf = svc.current_onf(db, tenant_id)
            zero = svc.level_zero(db, onf)
            app = _application(db, tenant_id)
            anf = svc.build_anf(db, app, zero, approved_by=uuid.uuid4())
            first = svc.compute_level_of_trust(db, anf).as_dict()
            second = svc.compute_level_of_trust(db, anf).as_dict()
        assert first == second


# ==========================================================================
# AI management system
# ==========================================================================
class TestAiManagementSystem:
    def _ai_system(self, db, tenant_id) -> AiSystem:
        system = AiSystem(
            tenant_id=tenant_id,
            code=_unique("AI"),
            name="Model gateway",
            intended_use="Drafting and triage of compliance artefacts.",
            created_at=utcnow(),
        )
        db.add(system)
        db.flush()
        return system

    def test_an_impact_assessment_cannot_be_approved_without_a_human(self, tenant_id):
        """ISO/IEC 42001 A.5 assigns the judgement to the organisation. A fluent
        draft is not an organisational judgement."""
        with pytest.raises(Exception) as exc:
            with session_scope(tenant_id=tenant_id) as db:
                system = self._ai_system(db, tenant_id)
                db.add(
                    AiImpactAssessment(
                        tenant_id=tenant_id,
                        ai_system_id=system.id,
                        trigger_reason="initial",
                        lifecycle_stage="design",
                        status="approved",
                        draft_provenance="ai_generated",
                        created_at=utcnow(),
                    )
                )
                db.flush()
        assert "ck_ai_impact_human_approval" in str(exc.value)

    def test_an_agent_drafted_assessment_must_be_labelled_as_such(self, tenant_id):
        with pytest.raises(Exception) as exc:
            with session_scope(tenant_id=tenant_id) as db:
                agent = db.execute(
                    select(AgentIdentity).where(AgentIdentity.agent_key == "ai_impact")
                ).scalar_one()
                system = self._ai_system(db, tenant_id)
                db.add(
                    AiImpactAssessment(
                        tenant_id=tenant_id,
                        ai_system_id=system.id,
                        trigger_reason="initial",
                        lifecycle_stage="design",
                        status="draft",
                        drafted_by_agent_id=agent.id,
                        draft_provenance="human_attested",
                        created_at=utcnow(),
                    )
                )
                db.flush()
        assert "ck_ai_impact_agent_draft_labelled" in str(exc.value)

    def test_an_approved_assessment_with_a_named_approver_is_accepted(self, tenant_id):
        with session_scope(tenant_id=tenant_id) as db:
            user, _agent = _two_actors(db, tenant_id)
            system = self._ai_system(db, tenant_id)
            assessment = AiImpactAssessment(
                tenant_id=tenant_id,
                ai_system_id=system.id,
                trigger_reason="initial",
                lifecycle_stage="design",
                status="approved",
                draft_provenance="ai_assisted",
                approved_by=user.id,
                approved_at=utcnow(),
                societal_impacts=[{"impact": "None identified", "basis": "Internal-only tooling"}],
                created_at=utcnow(),
            )
            db.add(assessment)
            db.flush()
            assert assessment.id is not None

    def test_an_ai_system_with_no_owning_application_is_reported(self, tenant_id):
        """The junction between the two standards is where things fall through: a
        model with no application has no ANF, so nothing measuring it."""
        with session_scope(tenant_id=tenant_id) as db:
            self._ai_system(db, tenant_id)
            orphans = svc.ai_systems_without_application(db, tenant_id)
        assert orphans, "an unowned AI system should be surfaced, not tolerated"


# ==========================================================================
# Statement of Applicability
# ==========================================================================
class TestStatementOfApplicability:
    def test_an_exclusion_without_a_reason_is_refused(self, tenant_id):
        """The first thing an assessor looks for in a Statement of Applicability
        is an exclusion nobody justified."""
        with pytest.raises(Exception) as exc:
            with session_scope(tenant_id=tenant_id) as db:
                db.add(
                    SoaEntry(
                        tenant_id=tenant_id,
                        control_ref="A.5.2",
                        is_applicable=False,
                        justification="Not relevant to us",
                        created_at=utcnow(),
                    )
                )
                db.flush()
        assert "ck_soa_exclusion_reasoned" in str(exc.value)

    def test_one_table_serves_every_framework(self, tenant_id):
        """A Statement of Applicability is the same artefact whether the
        reference set is 27001 Annex A, 42001 Annex A or the ASC library."""
        with session_scope(tenant_id=tenant_id) as db:
            for ref, framework in (("A.8.1", "iso27001"), ("A.5.2", "iso42001")):
                fw = db.execute(select(Framework).where(Framework.code == framework)).scalar_one()
                db.add(
                    SoaEntry(
                        tenant_id=tenant_id,
                        framework_id=fw.id,
                        control_ref=f"{framework}:{ref}",
                        is_applicable=True,
                        inclusion_basis=["risk_treatment"],
                        justification="Selected by the AI risk treatment plan.",
                        created_at=utcnow(),
                    )
                )
            db.flush()
            count = db.execute(
                select(func.count(SoaEntry.id)).where(SoaEntry.tenant_id == tenant_id)
            ).scalar_one()
        assert count >= 2


# ==========================================================================
# The process repository and the agent estate
# ==========================================================================
class TestRepositoryIntegration:
    def test_the_new_tracks_are_registered_and_valid(self):
        from app.processes import DOMAIN_BY_CODE, PROCESS_BY_CODE, validate

        assert validate() == []
        assert "APS" in DOMAIN_BY_CODE
        for code in ("PR-APS-01", "PR-APS-09", "PR-AIG-07", "PR-AIG-12"):
            assert code in PROCESS_BY_CODE

    def test_the_agent_registry_still_grants_nobody_approval_authority(self):
        from app.agents.registry import AGENTS, validate

        assert validate() == []
        offending = [
            a.key for a in AGENTS for p in a.permissions if p.startswith("gate.")
        ]
        assert offending == []

    def test_execution_and_verification_are_separate_agent_identities(self):
        """The database separates duties by actor identity, so one agent with two
        modes would defeat the trigger entirely."""
        from app.agents.registry import AGENT_BY_KEY

        assert "appsec" in AGENT_BY_KEY and "verification" in AGENT_BY_KEY
        assert AGENT_BY_KEY["appsec"].key != AGENT_BY_KEY["verification"].key

    def test_unattended_automation_stays_inside_the_supported_band(self):
        """The rate is derived by classifying each activity, not by aiming at a
        number, and ASSIST is not counted as automation."""
        from app.processes import statistics

        rate = statistics()["unattended_rate"]
        assert 0.15 <= rate <= 0.45, f"unattended rate {rate:.1%} outside the practice band"

    def test_ai_specific_clauses_are_never_inherited_from_another_standard(self):
        """A security risk assessment does not ask whether a model treats people
        unfairly, so 6.1.2, 6.1.3 and 6.1.4 must be discharged by the AI track."""
        from app.processes import NEVER_INHERITED, PROCESS_BY_CODE, clause_coverage

        coverage = clause_coverage()["iso42001"]
        for ref in ("6.1.2", "6.1.3", "6.1.4", "8.4"):
            assert ref in NEVER_INHERITED
            owners = coverage.get(ref, [])
            assert owners, f"iso42001:{ref} is discharged by no process"
            for code in owners:
                assert PROCESS_BY_CODE[code].domain == "AIG", (
                    f"iso42001:{ref} claimed by {code}, which is not an AI governance process"
                )

    def test_the_shared_annex_sl_clauses_are_covered_once_and_reused(self):
        """Running clause 9.2 three times for three standards is the cost an
        integrated management system exists to avoid."""
        from app.processes import clause_coverage

        coverage = clause_coverage()
        for ref in ("4.1", "4.2", "9.2", "9.3", "10.2"):
            assert ref in coverage["iso27001"]
            assert ref in coverage["iso42001"], f"iso42001:{ref} inherited nothing"
        # Inheritance must not manufacture coverage the source never had.
        # ISO/IEC 27001 7.5 is discharged by no process in this build, so
        # nothing should have inherited it either.
        assert "7.5" not in coverage["iso27001"]

    def test_every_iso42001_clause_is_discharged_by_some_process(self):
        from app.processes import clause_coverage
        from app.seed.catalogue_iso42001 import ISO42001_CLAUSES

        covered = set(clause_coverage()["iso42001"])
        missing = sorted({ref for ref, _t, _s in ISO42001_CLAUSES} - covered)
        assert missing == [], f"uncovered ISO/IEC 42001 clauses: {missing}"


# ==========================================================================
# The endpoints
# ==========================================================================
class TestEndpoints:
    def test_the_onf_endpoint_reports_its_own_level_design_defects(self, client, headers):
        response = client.get("/v1/appsec/onf", headers=headers["ciso"])
        assert response.status_code == 200
        body = response.json()
        assert body["approved_ascs"] == 27
        assert len(body["trust_levels"]) == 4
        # Reported on the resource itself rather than hidden behind a report
        # somebody has to know to run.
        assert "level_design_issues" in body

    def test_the_control_library_can_be_filtered_to_human_verified_controls(
        self, client, headers
    ):
        response = client.get(
            "/v1/appsec/onf/controls?human_verified_only=true", headers=headers["ciso"]
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert items
        assert all(i["measurement_requires_human"] for i in items)

    def test_the_inventory_names_ai_systems_no_application_accounts_for(
        self, client, headers, tenant_id
    ):
        with session_scope(tenant_id=tenant_id) as db:
            db.add(
                AiSystem(
                    tenant_id=tenant_id,
                    code=_unique("AI"),
                    name="Orphan model",
                    intended_use="Unowned by any application.",
                    created_at=utcnow(),
                )
            )
        response = client.get("/v1/ai/systems", headers=headers["ciso"])
        assert response.status_code == 200
        assert response.json()["unowned"]

    def test_certification_is_reported_as_blocked_with_a_reason(self, client, headers):
        response = client.get("/v1/ai/certification-block", headers=headers["ciso"])
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is True
        assert body["reason"]

    def test_the_bootstrap_account_cannot_read_the_normative_framework(self, client):
        """The bootstrap administrator holds platform and security administration
        and no business authority at all. If it could read the ONF, the seeder
        would be handing out compliance access on first boot."""
        from app.config import get_settings

        settings = get_settings()
        token = client.post(
            "/v1/auth/login",
            json={
                "email": settings.bootstrap_admin_email,
                "password": settings.bootstrap_admin_password,
            },
        ).json()["access_token"]
        response = client.get(
            "/v1/appsec/onf", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
