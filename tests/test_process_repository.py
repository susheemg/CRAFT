"""The process repository and agent registry must hold together.

These are structural tests over design data rather than behaviour tests over
code, and they matter for the same reason a schema constraint matters: a
process that references an agent that cannot perform it is not a documentation
error, it is a run that will fail at the moment someone depends on it.
"""

from __future__ import annotations

import pytest

from app.agents import registry
from app.agents.registry import AGENTS, AutonomyTier
from app.processes import (
    Automation,
    DOMAINS,
    PROCESSES,
    clause_coverage,
    statistics,
    validate,
)


class TestRepositoryIntegrity:
    def test_the_repository_validates(self):
        assert validate() == []

    def test_the_agent_registry_validates_against_the_processes(self):
        assert registry.validate() == []

    def test_every_domain_has_processes_and_an_owner(self):
        for domain in DOMAINS:
            assert domain.processes, f"{domain.code} owns no process"
            assert domain.owner_role

    def test_every_process_discharges_at_least_one_clause(self):
        for process in PROCESSES:
            assert process.clauses, f"{process.code} claims no clause"

    def test_the_three_target_frameworks_are_covered(self):
        coverage = clause_coverage()
        assert {"iso27001", "iso22301", "uk_gdpr"} <= set(coverage)
        for framework in ("iso27001", "iso22301", "uk_gdpr"):
            assert len(coverage[framework]) >= 20, (
                f"{framework} has only {len(coverage[framework])} clauses claimed"
            )


class TestAccountabilityIsNeverDelegated:
    def test_no_activity_makes_an_agent_accountable(self):
        for process in PROCESSES:
            for activity in process.activities:
                assert activity.accountable.lower() not in {"agent", "ai", "system"}, (
                    f"{process.code}/{activity.code} makes an agent accountable"
                )

    def test_no_gate_is_performed_by_an_agent(self):
        for process in PROCESSES:
            for gate in process.gates:
                assert gate.agent is None, (
                    f"{process.code}/{gate.code} assigns a gate to an agent"
                )

    def test_no_agent_holds_approval_authority(self):
        for agent in AGENTS:
            offending = [p for p in agent.permissions if p.startswith("gate.")]
            assert not offending, f"{agent.key} holds {offending}"

    def test_the_registry_refuses_to_construct_an_approving_agent(self):
        """The guarantee is structural, not a convention someone must remember."""
        from app.agents.registry import Agent

        with pytest.raises(ValueError, match="Accountability"):
            Agent(
                key="rogue", name="Rogue", purpose="x", accountable_role="CISO",
                autonomy=AutonomyTier.L2, permissions=("gate.risk.approve",),
                task_classes=(), tools=(), refuses=(),
            )

    def test_every_agent_has_a_named_accountable_role(self):
        for agent in AGENTS:
            assert agent.accountable_role
            assert agent.accountable_role.lower() not in {"team", "agent", "system"}


class TestAutonomyIsJustified:
    def test_unattended_agents_call_no_model(self):
        """L4 means acting without review. Acting without review on the output
        of a model is exactly what the autonomy tiers exist to prevent."""
        for agent in AGENTS:
            if agent.autonomy is AutonomyTier.L4:
                assert not agent.task_classes, (
                    f"{agent.key} is unattended but routes to a model"
                )

    def test_every_agent_declines_the_five_things_that_must_not_be_automated(self):
        required = ("approv", "interpret", "risk", "regulator", "evidence")
        for agent in AGENTS:
            joined = " ".join(agent.refuses).lower()
            for token in required:
                assert token in joined, f"{agent.key} does not decline anything about '{token}'"

    def test_statutory_processes_escalate_at_a_higher_threshold(self):
        """Privacy work carries statutory deadlines and irreversible disclosure,
        so it must be more willing to escalate than ordinary compliance work."""
        privacy = registry.AGENT_BY_KEY["privacy"]
        assessor = registry.AGENT_BY_KEY["control_assessor"]
        assert privacy.escalates_below_confidence > assessor.escalates_below_confidence


class TestAutomationClaimsAreHonest:
    def test_unattended_automation_sits_in_the_evidenced_band(self):
        """Reported practice puts reliable agentic automation of repetitive
        compliance work at roughly 20-40%. A repository claiming far more is
        either counting drafting as automation or is not being honest."""
        rate = statistics()["unattended_rate"]
        assert 0.15 <= rate <= 0.45, (
            f"Unattended automation is {rate:.0%}, outside the band the evidence "
            "supports. Check whether ASSIST steps are being counted as automated."
        )

    def test_drafting_is_not_counted_as_automation(self):
        for process in PROCESSES:
            assisted = [a for a in process.activities if a.automation is Automation.ASSIST]
            unattended = [
                a for a in process.activities
                if a.automation in {Automation.AUTO, Automation.AUTO_NOTIFY}
            ]
            if assisted:
                assert process.automation_rate == round(
                    len(unattended) / len(process.activities), 3
                )

    def test_every_process_with_an_irreversible_step_has_a_gate(self):
        for process in PROCESSES:
            irreversible = [
                a for a in process.activities
                if a.gate_reason in {"irreversible", "statutory"}
            ]
            if irreversible:
                assert process.gates, f"{process.code} has irreversible steps but no gate"

    def test_ai_assisted_steps_declare_a_confidence_floor_or_are_deterministic(self):
        """A model-backed judgement with no escalation threshold cannot escalate,
        which means low confidence would pass silently."""
        for process in PROCESSES:
            for activity in process.activities:
                if activity.ai_role and activity.automation is Automation.ASSIST:
                    agent = registry.AGENT_BY_KEY[activity.agent]
                    assert (
                        activity.min_confidence is not None
                        or agent.escalates_below_confidence > 0
                    ), f"{process.code}/{activity.code} can never escalate"


class TestPrivacyClocks:
    def test_the_breach_process_carries_the_statutory_deadline(self):
        from app.processes import PROCESS_BY_CODE

        breach = PROCESS_BY_CODE["PR-PRV-03"]
        notify = next(a for a in breach.gates if a.gate_type == "privacy.breach_notify")
        assert notify.sla_hours == 72
        assert notify.gate_reason == "statutory"

    def test_subject_request_release_is_gated_as_irreversible(self):
        from app.processes import PROCESS_BY_CODE

        dsar = PROCESS_BY_CODE["PR-PRV-02"]
        release = next(a for a in dsar.gates if a.gate_type == "privacy.dsar_release")
        assert release.gate_reason == "irreversible"


class TestGeneratedDocumentation:
    """The SOP manual is generated, so it cannot drift from what executes.

    These tests are what makes that claim true rather than aspirational: if the
    generator ever silently skips a process or an activity, the document would
    quietly describe less than the platform does, which is the exact failure
    generating it was meant to prevent.
    """

    @pytest.fixture(scope="class")
    def manual(self) -> str:
        import io
        import contextlib

        from docs import generate_sop

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            generate_sop.main()
        return buffer.getvalue()

    def test_every_process_appears(self, manual):
        for process in PROCESSES:
            assert f"## {process.code} — {process.name}" in manual, (
                f"{process.code} is executed but undocumented"
            )

    def test_every_activity_appears(self, manual):
        rendered = manual.count("\n#### ")
        expected = sum(len(p.activities) for p in PROCESSES)
        assert rendered == expected, (
            f"The manual documents {rendered} activities but the platform "
            f"executes {expected}"
        )

    def test_every_gate_is_marked_as_a_human_decision(self, manual):
        for process in PROCESSES:
            for gate in process.gates:
                assert f"`{gate.gate_type}`" in manual, (
                    f"{process.code}/{gate.code} is a gate but the manual does "
                    "not identify it as one"
                )

    def test_the_stated_automation_figure_matches_the_repository(self, manual):
        rate = statistics()["unattended_rate"]
        assert f"{rate:.1%}" in manual, (
            "The manual quotes an automation figure that is not the one the "
            "repository computes"
        )

    def test_the_accountability_rule_is_stated_prominently(self, manual):
        assert "Accountability never rests with an agent" in manual
        assert manual.index("Accountability never rests with an agent") < 3000, (
            "The rule that governs every process should be near the front"
        )
