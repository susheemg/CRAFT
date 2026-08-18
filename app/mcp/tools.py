"""The tools CRAFT exposes over MCP.

Every tool declares the permission it needs, and that permission is checked
against the calling principal exactly as it would be on the REST API — an MCP
client is not a privileged back door. Three properties are deliberate:

  * **Read tools are broad, write tools are narrow.** An external agent can
    read the register and readiness position freely, but the only writes it can
    make are ones a person would have had to justify anyway.
  * **No tool can decide a gate.** ``assert_human`` refuses, and agent
    principals cannot hold gate permissions in the first place. A tool that
    would need approval returns the gate id and stops.
  * **Every call is logged** to the same hash-chained audit log as everything
    else, with the tool name and arguments recorded.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import GateReason, Severity, TreatmentStrategy, utcnow
from app.models.compliance import ControlImplementation, Framework, FrameworkControl, Gap
from app.models.core import ApprovalGate, Run, Workflow
from app.models.domain import Incident, Risk
from app.security.auth import Principal
from app.services import audit, compliance as compliance_svc, engine, risk as risk_svc
from app.services.outbox import publish


class ToolError(RuntimeError):
    """A tool could not complete. The message is returned to the caller."""


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    permission: str
    input_schema: dict
    handler: Callable[[Session, Principal, dict], dict]
    mutating: bool = False

    def manifest(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "readOnlyHint": not self.mutating,
                "destructiveHint": False,
                "idempotentHint": not self.mutating,
                "requiredScope": self.permission,
            },
        }


def _obj(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


# ==========================================================================
# Read tools
# ==========================================================================
def _list_risks(db: Session, principal: Principal, args: dict) -> dict:
    stmt = select(Risk).where(
        Risk.tenant_id == principal.tenant_id, Risk.is_deleted.is_(False)
    )
    if args.get("band"):
        stmt = stmt.where(Risk.severity_band == Severity(args["band"]))
    if args.get("status"):
        from app.models.base import RiskStatus

        stmt = stmt.where(Risk.status == RiskStatus(args["status"]))
    rows = db.execute(
        stmt.order_by(
            func.coalesce(Risk.residual_score, Risk.inherent_score).desc()
        ).limit(min(int(args.get("limit", 25)), 100))
    ).scalars().all()
    return {
        "risks": [
            {
                "ref": r.risk_ref,
                "title": r.title,
                "category": r.category,
                "inherent_score": r.inherent_score,
                "residual_score": r.residual_score,
                "band": r.severity_band.value,
                "treatment": r.treatment.value,
                "status": r.status.value,
                "review_at": r.review_at.isoformat() if r.review_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


def _risk_summary(db: Session, principal: Principal, args: dict) -> dict:
    return {
        "summary": risk_svc.register_summary(db, principal.tenant_id),
        "heatmap": risk_svc.heatmap(db, principal.tenant_id),
    }


def _compliance_readiness(db: Session, principal: Principal, args: dict) -> dict:
    framework = args.get("framework")
    if framework:
        try:
            return compliance_svc.compute_readiness(
                db, principal.tenant_id, framework
            ).as_dict()
        except compliance_svc.ComplianceError as exc:
            raise ToolError(str(exc)) from exc
    return {"programmes": compliance_svc.cross_framework_coverage(db, principal.tenant_id)}


def _list_controls(db: Session, principal: Principal, args: dict) -> dict:
    framework = args["framework"]
    fw = db.execute(select(Framework).where(Framework.code == framework)).scalar_one_or_none()
    if fw is None:
        raise ToolError(f"'{framework}' is not in the framework catalogue.")
    stmt = (
        select(ControlImplementation, FrameworkControl)
        .join(
            FrameworkControl,
            FrameworkControl.id == ControlImplementation.framework_control_id,
        )
        .where(
            ControlImplementation.tenant_id == principal.tenant_id,
            FrameworkControl.framework_id == fw.id,
        )
    )
    if args.get("status"):
        from app.models.base import ImplementationStatus

        stmt = stmt.where(ControlImplementation.status == ImplementationStatus(args["status"]))
    rows = db.execute(
        stmt.order_by(FrameworkControl.sort_order).limit(min(int(args.get("limit", 50)), 200))
    ).all()
    return {
        "framework": fw.code,
        "controls": [
            {
                "ref": ctl.ref_code,
                "title": ctl.title,
                "section": ctl.section,
                "theme": ctl.theme,
                "applicable": impl.is_applicable,
                "status": impl.status.value,
                "maturity": impl.maturity,
                "how_implemented": impl.how_implemented,
            }
            for impl, ctl in rows
        ],
    }


def _list_gaps(db: Session, principal: Principal, args: dict) -> dict:
    stmt = (
        select(Gap, FrameworkControl)
        .join(
            ControlImplementation,
            ControlImplementation.id == Gap.control_implementation_id,
        )
        .join(
            FrameworkControl,
            FrameworkControl.id == ControlImplementation.framework_control_id,
        )
        .where(Gap.tenant_id == principal.tenant_id)
    )
    if args.get("status", "open") != "all":
        stmt = stmt.where(Gap.status == args.get("status", "open"))
    if args.get("severity"):
        stmt = stmt.where(Gap.severity == Severity(args["severity"]))
    rows = db.execute(stmt.order_by(Gap.due_at.nulls_last()).limit(100)).all()
    now = utcnow()
    return {
        "gaps": [
            {
                "id": str(g.id),
                "title": g.title,
                "severity": g.severity.value,
                "status": g.status,
                "control": ctl.ref_code,
                "remediation_plan": g.remediation_plan,
                "due_at": g.due_at.isoformat() if g.due_at else None,
                "overdue": bool(g.due_at and g.due_at < now and g.status == "open"),
            }
            for g, ctl in rows
        ]
    }


def _pending_gates(db: Session, principal: Principal, args: dict) -> dict:
    from app.models.base import GateDecision

    rows = db.execute(
        select(ApprovalGate)
        .where(
            ApprovalGate.tenant_id == principal.tenant_id,
            ApprovalGate.decision == GateDecision.PENDING,
        )
        .order_by(ApprovalGate.due_at.nulls_last())
        .limit(100)
    ).scalars().all()
    now = utcnow()
    return {
        "gates": [
            {
                "id": str(g.id),
                "gate_type": g.gate_type,
                "reason": g.reason.value,
                "summary": g.summary,
                "raised_at": g.raised_at.isoformat(),
                "due_at": g.due_at.isoformat() if g.due_at else None,
                "overdue": bool(g.due_at and g.due_at < now),
            }
            for g in rows
        ],
        "note": (
            "Gates are decided by an authorised person through the approver "
            "inbox. No MCP tool can decide one."
        ),
    }


def _soa(db: Session, principal: Principal, args: dict) -> dict:
    try:
        return compliance_svc.statement_of_applicability(
            db, principal.tenant_id, args["framework"]
        )
    except compliance_svc.ComplianceError as exc:
        raise ToolError(str(exc)) from exc


def _audit_verify(db: Session, principal: Principal, args: dict) -> dict:
    report = audit.verify_chain(db, principal.tenant_id)
    return {
        "intact": report.is_intact,
        "rows_checked": report.rows_checked,
        "head_seq": report.to_seq,
        "head_hash": report.head_hash,
        "first_broken_seq": report.first_broken_seq,
        "reason": report.reason,
    }


# ==========================================================================
# Write tools
# ==========================================================================
def _create_risk(db: Session, principal: Principal, args: dict) -> dict:
    try:
        risk = risk_svc.create_risk(
            db,
            tenant_id=principal.tenant_id,
            title=args["title"],
            description=args.get("description", ""),
            category=args.get("category", "information_security"),
            threat=args.get("threat", ""),
            vulnerability=args.get("vulnerability", ""),
            inherent_likelihood=int(args.get("inherent_likelihood", 3)),
            inherent_impact=int(args.get("inherent_impact", 3)),
            residual_likelihood=args.get("residual_likelihood"),
            residual_impact=args.get("residual_impact"),
            treatment=TreatmentStrategy(args.get("treatment", "mitigate")),
            treatment_plan=args.get("treatment_plan", ""),
            source=args.get("source", "mcp"),
            created_by=principal.id,
        )
    except risk_svc.RiskError as exc:
        raise ToolError(str(exc)) from exc
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="risk.raised",
        payload={"ref": risk.risk_ref, "band": risk.severity_band.value, "via": "mcp"},
    )
    return {
        "ref": risk.risk_ref,
        "id": str(risk.id),
        "inherent_score": risk.inherent_score,
        "residual_score": risk.residual_score,
        "band": risk.severity_band.value,
        "note": (
            "Recorded. Acceptance above appetite still requires an authorised "
            "person to decide it."
        ),
    }


def _raise_gap(db: Session, principal: Principal, args: dict) -> dict:
    fw = db.execute(
        select(Framework).where(Framework.code == args["framework"])
    ).scalar_one_or_none()
    if fw is None:
        raise ToolError(f"'{args['framework']}' is not in the framework catalogue.")
    row = db.execute(
        select(ControlImplementation)
        .join(
            FrameworkControl,
            FrameworkControl.id == ControlImplementation.framework_control_id,
        )
        .where(
            ControlImplementation.tenant_id == principal.tenant_id,
            FrameworkControl.framework_id == fw.id,
            FrameworkControl.ref_code == args["control_ref"],
        )
    ).scalar_one_or_none()
    if row is None:
        raise ToolError(
            f"No implementation record for {args['control_ref']}. "
            f"Has the {fw.code} programme been started?"
        )
    gap = compliance_svc.raise_gap(
        db,
        tenant_id=principal.tenant_id,
        control_implementation_id=row.id,
        title=args["title"],
        description=args.get("description", ""),
        severity=Severity(args.get("severity", "medium")),
        source="ai_review",
        remediation_plan=args.get("remediation_plan", ""),
        due_days=int(args.get("due_days", 60)),
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="gap.raised",
        payload={
            "control": args["control_ref"],
            "severity": gap.severity.value,
            "via": "mcp",
        },
    )
    return {"id": str(gap.id), "control": args["control_ref"], "severity": gap.severity.value}


def _record_evidence(db: Session, principal: Principal, args: dict) -> dict:
    record = engine.record_evidence(
        db,
        tenant_id=principal.tenant_id,
        kind=args.get("kind", "document"),
        title=args["title"],
        payload=args.get("payload"),
        artifact_uri=args.get("artifact_uri"),
        subject_type=args.get("subject_type"),
        subject_id=uuid.UUID(args["subject_id"]) if args.get("subject_id") else None,
        created_by=principal.id,
    )
    return {
        "id": str(record.id),
        "content_hash": record.content_hash.hex(),
        "note": "The content hash fixes this evidence; later edits would be detectable.",
    }


def _start_run(db: Session, principal: Principal, args: dict) -> dict:
    try:
        run = engine.start_run(
            db,
            tenant_id=principal.tenant_id,
            workflow_code=args["workflow_code"],
            principal=principal,
            context=args.get("context", {}),
            subject_ref=args.get("subject_ref"),
        )
    except engine.EngineError as exc:
        raise ToolError(str(exc)) from exc
    return {"run_id": str(run.id), "workflow": args["workflow_code"], "status": run.status.value}


def _create_incident(db: Session, principal: Principal, args: dict) -> dict:
    from datetime import timedelta

    from app.models.base import IncidentStatus
    from app.models.domain import Breach

    count = db.execute(
        select(func.count(Incident.id)).where(Incident.tenant_id == principal.tenant_id)
    ).scalar_one()
    detected = utcnow()
    incident = Incident(
        tenant_id=principal.tenant_id,
        incident_no=f"INC-{count + 1:04d}",
        title=args["title"],
        description=args.get("description"),
        incident_type=args.get("incident_type", "security"),
        severity=Severity(args.get("severity", "medium")),
        status=IncidentStatus.RECORDED,
        detected_at=detected,
        involves_personal_data=bool(args.get("involves_personal_data")),
        created_at=utcnow(),
        created_by=principal.id,
    )
    db.add(incident)
    db.flush()
    result = {"incident_no": incident.incident_no, "id": str(incident.id)}
    if incident.involves_personal_data:
        breach = Breach(
            tenant_id=principal.tenant_id,
            incident_id=incident.id,
            summary=incident.title,
            risk_to_individuals="unknown",
            clock_started_at=detected,
            notify_due_at=detected + timedelta(hours=72),
            created_at=utcnow(),
            created_by=principal.id,
        )
        db.add(breach)
        db.flush()
        result["breach_id"] = str(breach.id)
        result["notify_due_at"] = breach.notify_due_at.isoformat()
        result["note"] = (
            "Personal data is involved, so the 72-hour notification clock has "
            "started from the moment of recording. The notification decision "
            "belongs to the DPO."
        )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="incident.created",
        payload={"incident_no": incident.incident_no, "via": "mcp"},
    )
    return result


# ==========================================================================
# Registry
# ==========================================================================
TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool(
            name="craft_list_risks",
            title="List risks",
            description=(
                "Read the risk register. Filter by severity band or status. Returns "
                "inherent and residual scores on the organisation's 5x5 matrix."
            ),
            permission="data.register.read",
            input_schema=_obj(
                {
                    "band": {
                        "type": "string",
                        "enum": ["very_low", "low", "medium", "high", "very_high"],
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "accepted", "closed"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                }
            ),
            handler=_list_risks,
        ),
        Tool(
            name="craft_risk_summary",
            title="Risk register summary",
            description=(
                "Counts by band and status, plus the 5x5 heatmap. Use this before "
                "listing individual risks to understand the shape of the register."
            ),
            permission="data.register.read",
            input_schema=_obj({}),
            handler=_risk_summary,
        ),
        Tool(
            name="craft_compliance_readiness",
            title="Compliance readiness",
            description=(
                "Readiness against a framework, or across all active programmes if "
                "no framework is given. Readiness is discounted where an "
                "implementation claim has no current evidence, and certification "
                "readiness is reported separately and more strictly."
            ),
            permission="rpt.dashboard.view",
            input_schema=_obj(
                {"framework": {"type": "string", "description": "e.g. iso27001, iso22301, ukgdpr"}}
            ),
            handler=_compliance_readiness,
        ),
        Tool(
            name="craft_list_controls",
            title="List controls",
            description=(
                "Controls for a framework with their implementation status and "
                "maturity. Filter by status to find what is outstanding."
            ),
            permission="data.register.read",
            input_schema=_obj(
                {
                    "framework": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "not_started", "planned", "in_progress", "implemented",
                            "operating", "not_applicable",
                        ],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                },
                required=["framework"],
            ),
            handler=_list_controls,
        ),
        Tool(
            name="craft_list_gaps",
            title="List compliance gaps",
            description="Open gaps with severity, remediation plan and due date.",
            permission="data.register.read",
            input_schema=_obj(
                {
                    "status": {"type": "string", "enum": ["open", "closed", "all"]},
                    "severity": {
                        "type": "string",
                        "enum": ["very_low", "low", "medium", "high", "very_high"],
                    },
                }
            ),
            handler=_list_gaps,
        ),
        Tool(
            name="craft_pending_gates",
            title="List pending approvals",
            description=(
                "Approval gates awaiting a human decision, with what is being "
                "decided and by when. Read-only: no tool can decide a gate."
            ),
            permission="data.register.read",
            input_schema=_obj({}),
            handler=_pending_gates,
        ),
        Tool(
            name="craft_statement_of_applicability",
            title="Statement of Applicability",
            description=(
                "The full SoA for a framework: every control, whether it applies, "
                "the justification for any exclusion, and its status. This is the "
                "document an ISO 27001 certification auditor asks for first."
            ),
            permission="rpt.dashboard.view",
            input_schema=_obj({"framework": {"type": "string"}}, required=["framework"]),
            handler=_soa,
        ),
        Tool(
            name="craft_verify_audit_chain",
            title="Verify the audit log",
            description=(
                "Recompute the hash chain over the audit log and report whether it "
                "is intact. A break names the exact sequence number."
            ),
            permission="sec.auditlog.read",
            input_schema=_obj({}),
            handler=_audit_verify,
        ),
        Tool(
            name="craft_create_risk",
            title="Record a risk",
            description=(
                "Add a risk to the register with inherent and optional residual "
                "scores on the 1-5 likelihood and impact scales. Recording is not "
                "acceptance: a risk above appetite still needs an authorised "
                "person to accept it."
            ),
            permission="risk.manage",
            input_schema=_obj(
                {
                    "title": {"type": "string", "minLength": 5},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "information_security", "privacy", "continuity",
                            "third_party", "operational", "regulatory",
                        ],
                    },
                    "threat": {"type": "string"},
                    "vulnerability": {"type": "string"},
                    "inherent_likelihood": {"type": "integer", "minimum": 1, "maximum": 5},
                    "inherent_impact": {"type": "integer", "minimum": 1, "maximum": 5},
                    "residual_likelihood": {"type": "integer", "minimum": 1, "maximum": 5},
                    "residual_impact": {"type": "integer", "minimum": 1, "maximum": 5},
                    "treatment": {
                        "type": "string",
                        "enum": ["mitigate", "transfer", "avoid", "accept"],
                    },
                    "treatment_plan": {"type": "string"},
                    "source": {"type": "string"},
                },
                required=["title", "inherent_likelihood", "inherent_impact"],
            ),
            handler=_create_risk,
            mutating=True,
        ),
        Tool(
            name="craft_raise_gap",
            title="Raise a compliance gap",
            description=(
                "Record a shortfall against a named control, with severity and a "
                "remediation plan. Rate severity on consequence if unaddressed, "
                "not on how hard it is to fix."
            ),
            permission="compliance.manage",
            input_schema=_obj(
                {
                    "framework": {"type": "string"},
                    "control_ref": {"type": "string", "description": "e.g. A.5.19"},
                    "title": {"type": "string", "minLength": 5},
                    "description": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["very_low", "low", "medium", "high", "very_high"],
                    },
                    "remediation_plan": {"type": "string"},
                    "due_days": {"type": "integer", "minimum": 1, "maximum": 730},
                },
                required=["framework", "control_ref", "title"],
            ),
            handler=_raise_gap,
            mutating=True,
        ),
        Tool(
            name="craft_record_evidence",
            title="Attach evidence",
            description=(
                "Attach an evidence record to a control, risk or plan. The content "
                "is hashed on receipt, so any later alteration is detectable."
            ),
            permission="evidence.write",
            input_schema=_obj(
                {
                    "title": {"type": "string", "minLength": 3},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "document", "screenshot", "log", "attestation", "report",
                            "export", "decision", "activity_output",
                        ],
                    },
                    "payload": {"type": "object"},
                    "artifact_uri": {"type": "string"},
                    "subject_type": {
                        "type": "string",
                        "enum": [
                            "control_implementation", "risk", "supplier", "incident",
                            "continuity_plan",
                        ],
                    },
                    "subject_id": {"type": "string"},
                },
                required=["title"],
            ),
            handler=_record_evidence,
            mutating=True,
        ),
        Tool(
            name="craft_start_workflow",
            title="Start a workflow run",
            description=(
                "Start a governed workflow run. The run advances through its "
                "activities and stops at any approval gate it reaches."
            ),
            permission="wf.execute",
            input_schema=_obj(
                {
                    "workflow_code": {"type": "string", "description": "e.g. WF-22"},
                    "context": {"type": "object"},
                    "subject_ref": {"type": "string"},
                },
                required=["workflow_code"],
            ),
            handler=_start_run,
            mutating=True,
        ),
        Tool(
            name="craft_create_incident",
            title="Raise an incident",
            description=(
                "Record an incident. If personal data is involved, the 72-hour "
                "regulator notification clock starts from the moment of recording, "
                "because that is when the organisation became aware."
            ),
            permission="data.register.write",
            input_schema=_obj(
                {
                    "title": {"type": "string", "minLength": 5},
                    "description": {"type": "string"},
                    "incident_type": {
                        "type": "string",
                        "enum": ["security", "privacy", "availability", "third_party", "physical"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["very_low", "low", "medium", "high", "very_high"],
                    },
                    "involves_personal_data": {"type": "boolean"},
                },
                required=["title"],
            ),
            handler=_create_incident,
            mutating=True,
        ),
    ]
}


def manifests(principal: Principal) -> list[dict]:
    """Only advertise tools the caller could actually use.

    Listing a tool the principal cannot call wastes a round trip and invites
    the client to plan work it will not be allowed to do.
    """
    return [
        tool.manifest()
        for tool in TOOLS.values()
        if "*" in principal.permissions or tool.permission in principal.permissions
    ]


def invoke(db: Session, principal: Principal, name: str, arguments: dict) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolError(f"Unknown tool '{name}'. Call tools/list for what is available.")
    if "*" not in principal.permissions and tool.permission not in principal.permissions:
        raise ToolError(
            f"'{name}' requires the {tool.permission} permission, which this "
            "principal does not hold."
        )
    result = tool.handler(db, principal, arguments or {})
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action=f"mcp.{name}",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="mcp_tool",
        detail={"arguments": _safe_args(arguments or {}), "mutating": tool.mutating},
    )
    return result


def _safe_args(arguments: dict) -> dict:
    """Log the shape of the call, not the substance of large payloads."""
    out: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str) and len(value) > 300:
            out[key] = value[:300] + f"… ({len(value)} chars)"
        elif isinstance(value, (dict, list)):
            out[key] = f"<{type(value).__name__} of {len(value)}>"
        else:
            out[key] = value
    return out
