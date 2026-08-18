"""Generate the SOP manual from the process repository.

The manual is rendered, not written. A hand-written procedure manual and the
system that executes the procedure drift apart within a quarter, and the manual
is the one that gets believed in an audit. Generating it means the documented
procedure and the executed procedure are the same object viewed two ways.

Run:  python -m docs.generate_sop > docs/SOP_Manual.md
"""

from __future__ import annotations

import sys
from datetime import date

from app.agents.registry import AGENT_BY_KEY
from app.processes import (
    DOMAINS,
    PROCESS_BY_CODE,
    PROCESSES,
    Automation,
    clause_coverage,
    statistics,
)

FRAMEWORK_NAMES = {
    "iso27001": "ISO/IEC 27001:2022",
    "iso22301": "ISO 22301:2019",
    "uk_gdpr": "UK GDPR",
}

AUTOMATION_LABEL = {
    Automation.MANUAL: "Performed by a person",
    Automation.ASSIST: "AI-drafted, person owns the output",
    Automation.AUTO_NOTIFY: "Performed by the platform, owner notified",
    Automation.AUTO: "Performed by the platform",
    Automation.GATE: "**Human decision required**",
}

GATE_REASON_LABEL = {
    "irreversible": "the action cannot be undone",
    "statutory": "a legal duty attaches to the decision",
    "high_risk": "the exposure or value is material",
    "low_confidence": "the model's confidence was below the threshold",
}


def _out(line: str = "") -> None:
    print(line)


def header() -> None:
    stats = statistics()
    _out("# Standard Operating Procedure Manual")
    _out()
    _out("**CRAFT — Governance, Risk and Compliance**")
    _out()
    _out(f"Generated {date.today().isoformat()} from the process repository "
         f"(`app/processes`). Version 1.0.")
    _out()
    _out("---")
    _out()
    _out("## How to read this manual")
    _out()
    _out(
        "This manual is generated from the same definitions the platform "
        "executes. There is no separate written procedure that could disagree "
        "with it: if a step appears here, the engine runs it, and if the engine "
        "runs a step, it appears here. Regenerating the manual after a change "
        "to the repository is how the document stays true."
    )
    _out()
    _out(
        "Each process states its purpose, its owner, what triggers it, and the "
        "clauses it discharges. Each activity states the five-part contract — "
        "what is done, who does it, who is accountable, what goes in, what "
        "comes out — plus whether the platform performs it, whether AI drafts "
        "it, and whether it stops for a human decision."
    )
    _out()
    _out("### The rule that governs every process")
    _out()
    _out(
        "**Accountability never rests with an agent.** An AI agent may gather, "
        "draft, score and propose. It may not approve. Every decision point in "
        "this manual resolves to a named human role, and the platform enforces "
        "that structurally rather than by convention: an agent principal cannot "
        "hold approval authority, and the gate check refuses a non-human "
        "principal independently of what permissions it was granted."
    )
    _out()
    _out("### Where work stops for a person")
    _out()
    _out("A process stops at a gate when any of four tests is met:")
    _out()
    _out("| Test | Meaning |")
    _out("|---|---|")
    for reason, meaning in GATE_REASON_LABEL.items():
        _out(f"| `{reason}` | The step is stopped because {meaning}. |")
    _out()
    _out("### The shape of the repository")
    _out()
    _out("| Measure | Value |")
    _out("|---|---|")
    _out(f"| Domains | {stats['domains']} |")
    _out(f"| Processes | {stats['processes']} |")
    _out(f"| Activities | {stats['activities']} |")
    _out(f"| Human decision gates | {stats['gates']} |")
    _out(f"| Activities with AI participation | {stats['agent_assisted_activities']} |")
    _out(f"| Activities performed unattended | {stats['unattended_activities']} "
         f"({stats['unattended_rate']:.1%}) |")
    _out()
    _out(
        "The unattended figure counts only steps the platform completes without "
        "a person acting. AI-drafted steps are counted as human work, because a "
        "draft still has to be read. Counting drafting as automation is how "
        "implausible automation claims are arrived at, and the figure above sits "
        "deliberately inside the 20–40% band that current practice supports for "
        "repetitive compliance work."
    )
    _out()


def coverage_section() -> None:
    _out("---")
    _out()
    _out("## Clause coverage")
    _out()
    _out(
        "Which process discharges which requirement. A clause with no process "
        "against it is a hole in the management system, and this table is how "
        "it is found rather than discovered during a certification audit."
    )
    _out()
    coverage = clause_coverage()
    for framework in sorted(coverage):
        _out(f"### {FRAMEWORK_NAMES.get(framework, framework)}")
        _out()
        _out("| Clause | Discharged by |")
        _out("|---|---|")
        for clause, processes in sorted(coverage[framework].items()):
            names = ", ".join(f"`{p}`" for p in processes)
            _out(f"| {clause} | {names} |")
        _out()


def domain_index() -> None:
    _out("---")
    _out()
    _out("## Process index")
    _out()
    for domain in DOMAINS:
        _out(f"### {domain.code} — {domain.name}")
        _out()
        _out(f"*{domain.purpose}*")
        _out()
        _out(f"**Domain owner:** {domain.owner_role}")
        _out()
        _out("| Process | Name | Owner | Cadence | Gates |")
        _out("|---|---|---|---|---|")
        for code in domain.processes:
            p = PROCESS_BY_CODE[code]
            _out(
                f"| `{p.code}` | {p.name} | {p.owner_role} | "
                f"{p.cadence.value.replace('_', ' ')} | {len(p.gates)} |"
            )
        _out()


def process_detail(code: str) -> None:
    p = PROCESS_BY_CODE[code]
    _out("---")
    _out()
    _out(f"## {p.code} — {p.name}")
    _out()
    _out(p.purpose)
    _out()
    _out("| | |")
    _out("|---|---|")
    _out(f"| **Domain** | {p.domain} |")
    _out(f"| **Process owner** | {p.owner_role} |")
    _out(f"| **Trigger** | {p.trigger} |")
    _out(f"| **Cadence** | {p.cadence.value.replace('_', ' ')} |")
    _out(f"| **Autonomy tier** | {p.autonomy_tier} |")
    _out(f"| **Human decision gates** | {len(p.gates)} |")
    _out(f"| **Unattended steps** | {p.automation_rate:.0%} |")
    _out()

    _out("**Clauses discharged**")
    _out()
    for framework, refs in sorted(p.clauses.items()):
        _out(f"- {FRAMEWORK_NAMES.get(framework, framework)}: {', '.join(refs)}")
    _out()

    if p.kpis:
        _out("**How this process is measured**")
        _out()
        for kpi in p.kpis:
            _out(f"- {kpi}")
        _out()

    if p.notes:
        _out(f"> {p.notes}")
        _out()

    _out("### Procedure")
    _out()
    for activity in p.activities:
        gate_marker = " 🛑" if activity.automation is Automation.GATE else ""
        _out(f"#### {activity.code}. {activity.what}{gate_marker}")
        _out()
        _out("| | |")
        _out("|---|---|")
        _out(f"| **Who performs it** | {_performer(activity)} |")
        _out(f"| **Who is accountable** | {activity.accountable} |")
        _out(f"| **When** | {activity.trigger} |")
        if activity.inputs:
            _out(f"| **Input** | {', '.join(activity.inputs)} |")
        if activity.outputs:
            _out(f"| **Output** | {', '.join(activity.outputs)} |")
        _out(f"| **Mode** | {AUTOMATION_LABEL[activity.automation]} |")
        if activity.sla_hours:
            _out(f"| **Target** | Within {activity.sla_hours} hours |")
        if activity.control_refs:
            _out(f"| **Evidences** | {', '.join(activity.control_refs)} |")
        if activity.evidence:
            _out(f"| **Records produced** | {', '.join(activity.evidence)} |")
        _out()

        if activity.automation is Automation.GATE:
            reason = GATE_REASON_LABEL.get(activity.gate_reason or "", activity.gate_reason)
            _out(
                f"> **This step stops for a human decision** (`{activity.gate_type}`) "
                f"because {reason}. It cannot be performed by an agent, and it "
                f"cannot be decided by whoever raised it."
            )
            _out()

        if activity.agent:
            agent = AGENT_BY_KEY[activity.agent]
            _out(f"**AI participation — {agent.name}**")
            _out()
            if activity.ai_role:
                _out(f"- *Asked to:* {activity.ai_role}")
            floor = activity.min_confidence or agent.escalates_below_confidence
            _out(f"- *Escalates to a person below confidence:* {floor}")
            _out(f"- *Accountable for this agent:* {agent.accountable_role}")
            _out()


def agent_section() -> None:
    from app.agents.registry import AGENTS, UNIVERSAL_REFUSALS

    _out("---")
    _out()
    _out("## Appendix A — AI agents")
    _out()
    _out(
        "Each agent is scoped to work it can do reliably, has a named person "
        "accountable for it, and declares what it refuses. None can approve "
        "anything."
    )
    _out()
    _out("### What every agent refuses, without exception")
    _out()
    for refusal in UNIVERSAL_REFUSALS:
        _out(f"- {refusal}")
    _out()
    _out("### Autonomy tiers")
    _out()
    _out("| Tier | Meaning |")
    _out("|---|---|")
    _out("| L1 | Observes and reports. Takes no action. |")
    _out("| L2 | Drafts for a named person, who owns the output. |")
    _out("| L3 | Acts on reversible things; anything irreversible raises a gate. |")
    _out("| L4 | Acts unattended within a bounded, deterministic scope. |")
    _out()
    _out(
        "An agent is tiered to the least deterministic thing it does. An L4 "
        "agent calls no model at all — acting without review on model output is "
        "precisely what the tiers exist to prevent."
    )
    _out()
    for agent in AGENTS:
        _out(f"### {agent.name} (`{agent.key}`)")
        _out()
        _out(agent.purpose)
        _out()
        _out("| | |")
        _out("|---|---|")
        _out(f"| **Accountable role** | {agent.accountable_role} |")
        _out(f"| **Autonomy tier** | {agent.autonomy.value} |")
        _out(f"| **Escalates below confidence** | {agent.escalates_below_confidence} |")
        _out(f"| **Permissions** | {', '.join(f'`{p}`' for p in agent.permissions) or 'none'} |")
        _out(f"| **Holds approval authority** | No — structurally prevented |")
        if agent.processes:
            _out(f"| **Participates in** | {', '.join(f'`{c}`' for c in agent.processes)} |")
        _out()
        specific = [r for r in agent.refuses if r not in UNIVERSAL_REFUSALS]
        if specific:
            _out("**Additionally refuses**")
            _out()
            for refusal in specific:
                _out(f"- {refusal}")
            _out()
        if agent.notes:
            _out(f"> {agent.notes}")
            _out()


def _performer(activity) -> str:
    if activity.agent:
        agent = AGENT_BY_KEY[activity.agent]
        return f"{agent.name} (AI agent), supervised by {activity.accountable}"
    return activity.responsible


def main() -> None:
    header()
    domain_index()
    for domain in DOMAINS:
        for code in domain.processes:
            process_detail(code)
    coverage_section()
    agent_section()
    _out("---")
    _out()
    _out(
        "*End of manual. Regenerate with `python -m docs.generate_sop` after any "
        "change to `app/processes` or `app/agents`, and the document will match "
        "what the platform executes.*"
    )


if __name__ == "__main__":
    main()
