"""The server-rendered console.

Every page answers one question and puts the answer at the top. The rule
throughout: the figure a person came for is the first thing they see, and the
supporting detail sits beneath it.

Pages read the same services as the API, so the console cannot show a number
the API would contradict.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from app.api.deps import DbSession, get_principal
from app.config import get_settings
from app.db import identity_lookup, set_session_context
from app.models.base import ActorType, GateDecision, utcnow
from app.models.compliance import (
    ComplianceProgramme,
    ControlImplementation,
    Framework,
    FrameworkControl,
    Gap,
)
from app.models.core import ApprovalGate, Run, Workflow
from app.models.domain import ContinuityPlan, DsarRequest, Incident, Risk
from app.models.iam import UserAccount
from app.models.llm import LlmModel, LlmProvider, LlmRoute
from app.security.auth import create_access_token, verify_password
from app.security.rbac import resolve_access
from app.services import audit as audit_service
from app.services import compliance as compliance_svc
from app.services import risk as risk_svc
from app.services.llm import cache as prompt_cache
from app.services.llm import gateway

settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(include_in_schema=False)


def _page(request: Request, template: str, principal, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "principal": principal,
            "can": lambda p: "*" in principal.permissions or p in principal.permissions,
            "version": settings.version,
            **context,
        },
    )


def ui_principal(request: Request, db: DbSession):
    """Send a browser to the sign-in page rather than returning a bare 401."""
    try:
        return get_principal(
            request, db, credentials=None, session_token=request.cookies.get("craft_session")
        )
    except HTTPException as exc:
        raise HTTPException(
            status_code=307, detail="sign-in required", headers={"Location": "/login"}
        ) from exc


UiPrincipal = Depends(ui_principal)


# ==========================================================================
# Sign in
# ==========================================================================
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error, "version": settings.version},
    )


@router.post("/login")
def login_submit(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    password: str = Form(...),
):
    with identity_lookup(db):
        user = db.execute(
            select(UserAccount).where(UserAccount.email == email.lower().strip())
        ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash) or user.status != "active":
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "That email address and password did not match.",
                "version": settings.version,
            },
            status_code=401,
        )
    set_session_context(db, user.tenant_id, f"human:{user.email}")
    access = resolve_access(db, user.id, user.tenant_id)
    token = create_access_token(
        user.id, user.tenant_id, ActorType.HUMAN, user.email, sorted(access.permissions)
    )
    user.last_login_at = utcnow()
    audit_service.record(
        db,
        tenant_id=user.tenant_id,
        action="auth.login",
        actor_type=ActorType.HUMAN,
        actor_ref=f"human:{user.email}",
        actor_id=user.id,
        entity="user_account",
        entity_id=user.id,
        detail={"channel": "console"},
    )
    db.commit()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "craft_session",
        token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("craft_session", path="/")
    return response


# ==========================================================================
# Dashboard
# ==========================================================================
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession, principal=UiPrincipal) -> HTMLResponse:
    tenant_id = principal.tenant_id
    risk = risk_svc.register_summary(db, tenant_id)
    programmes = compliance_svc.cross_framework_coverage(db, tenant_id)

    pending_gates = db.execute(
        select(ApprovalGate)
        .where(
            ApprovalGate.tenant_id == tenant_id,
            ApprovalGate.decision == GateDecision.PENDING,
        )
        .order_by(ApprovalGate.due_at.nulls_last())
        .limit(6)
    ).scalars().all()
    open_gaps = db.execute(
        select(Gap.severity, func.count(Gap.id))
        .where(Gap.tenant_id == tenant_id, Gap.status == "open")
        .group_by(Gap.severity)
    ).all()
    now = utcnow()
    overdue_gaps = db.execute(
        select(func.count(Gap.id)).where(
            Gap.tenant_id == tenant_id, Gap.status == "open", Gap.due_at < now
        )
    ).scalar_one()
    dsar_open = db.execute(
        select(func.count(DsarRequest.id)).where(
            DsarRequest.tenant_id == tenant_id, DsarRequest.status != "released"
        )
    ).scalar_one()
    open_incidents = db.execute(
        select(func.count(Incident.id)).where(
            Incident.tenant_id == tenant_id, Incident.status != "closed"
        )
    ).scalar_one()
    head_seq, head_hash = audit_service.head(db, tenant_id)

    return _page(
        request,
        "dashboard.html",
        principal,
        headline=_headline(risk, programmes, pending_gates, overdue_gaps),
        risk=risk,
        heatmap=risk_svc.heatmap(db, tenant_id),
        top_risks=risk_svc.top_risks(db, tenant_id, limit=5),
        programmes=programmes,
        pending_gates=pending_gates,
        gaps_by_severity={s.value: c for s, c in open_gaps},
        overdue_gaps=overdue_gaps,
        dsar_open=dsar_open,
        open_incidents=open_incidents,
        audit_head=(head_seq, (head_hash or "")[:16]),
        spend=gateway.spend_summary(db, tenant_id, days=30),
        cache=prompt_cache.statistics(db, tenant_id, days=30),
        now=now,
    )


def _headline(risk: dict, programmes: list, gates, overdue_gaps: int) -> dict:
    """Lead with whatever most needs a decision today, not with a generic total."""
    pending = len(gates)
    if overdue_gaps:
        plural = "s" if overdue_gaps != 1 else ""
        return {
            "tone": "urgent",
            "text": f"{overdue_gaps} remediation gap{plural} past the agreed due date",
            "detail": "Overdue remediation is among the first things an auditor samples.",
            "link": "/compliance",
        }
    if pending:
        plural = "s" if pending != 1 else ""
        return {
            "tone": "action",
            "text": f"{pending} decision{plural} waiting for approval",
            "detail": "Work stops at these gates until an authorised person decides.",
            "link": "/approvals",
        }
    above = risk.get("above_appetite", 0)
    if above:
        plural = "s" if above != 1 else ""
        return {
            "tone": "action",
            "text": f"{above} risk{plural} above appetite without a recorded acceptance",
            "detail": "Each needs either treatment or a named acceptance.",
            "link": "/risks",
        }
    if programmes:
        lowest = min(programmes, key=lambda p: p.get("readiness_pct", 0))
        return {
            "tone": "steady",
            "text": f"{lowest['name']} readiness is {lowest['readiness_pct']:.0f}%",
            "detail": "No overdue gaps and no decisions waiting.",
            "link": "/compliance",
        }
    return {
        "tone": "steady",
        "text": "No compliance programme has been started",
        "detail": "Start one to begin tracking readiness against a framework.",
        "link": "/compliance",
    }


# ==========================================================================
# Compliance
# ==========================================================================
@router.get("/compliance", response_class=HTMLResponse)
def compliance_page(request: Request, db: DbSession, principal=UiPrincipal) -> HTMLResponse:
    frameworks = db.execute(select(Framework).order_by(Framework.sort_order)).scalars().all()
    started = {
        p.framework_id: p
        for p in db.execute(
            select(ComplianceProgramme).where(
                ComplianceProgramme.tenant_id == principal.tenant_id
            )
        ).scalars().all()
    }
    rows = []
    for fw in frameworks:
        total = db.execute(
            select(func.count(FrameworkControl.id)).where(
                FrameworkControl.framework_id == fw.id
            )
        ).scalar_one()
        programme = started.get(fw.id)
        readiness = (
            compliance_svc.compute_readiness(db, principal.tenant_id, fw.code)
            if programme
            else None
        )
        rows.append(
            {
                "framework": fw,
                "control_count": total,
                "programme": programme,
                "readiness": readiness,
            }
        )
    return _page(
        request,
        "compliance.html",
        principal,
        rows=rows,
        phases=compliance_svc.JOURNEY_PHASES,
    )


@router.get("/compliance/{code}", response_class=HTMLResponse)
def framework_detail(
    code: str,
    request: Request,
    db: DbSession,
    principal=UiPrincipal,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    section: Optional[str] = None,
) -> HTMLResponse:
    fw = db.execute(select(Framework).where(Framework.code == code)).scalar_one_or_none()
    if fw is None:
        raise HTTPException(status_code=404, detail="Unknown framework")
    try:
        readiness = compliance_svc.compute_readiness(db, principal.tenant_id, code)
    except compliance_svc.ComplianceError:
        return _page(request, "framework_not_started.html", principal, framework=fw)

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
    if status_filter:
        from app.models.base import ImplementationStatus

        stmt = stmt.where(ControlImplementation.status == ImplementationStatus(status_filter))
    if section:
        stmt = stmt.where(FrameworkControl.section == section)
    controls = db.execute(stmt.order_by(FrameworkControl.sort_order)).all()

    sections = db.execute(
        select(FrameworkControl.section, func.count(FrameworkControl.id))
        .where(FrameworkControl.framework_id == fw.id)
        .group_by(FrameworkControl.section)
        .order_by(FrameworkControl.section)
    ).all()
    gap_counts = dict(
        db.execute(
            select(Gap.control_implementation_id, func.count(Gap.id))
            .where(Gap.tenant_id == principal.tenant_id, Gap.status == "open")
            .group_by(Gap.control_implementation_id)
        ).all()
    )
    return _page(
        request,
        "framework.html",
        principal,
        framework=fw,
        readiness=readiness,
        controls=controls,
        sections=sections,
        gap_counts=gap_counts,
        active_status=status_filter,
        active_section=section,
    )


# ==========================================================================
# Risk
# ==========================================================================
@router.get("/risks", response_class=HTMLResponse)
def risks_page(
    request: Request,
    db: DbSession,
    principal=UiPrincipal,
    band: Optional[str] = None,
) -> HTMLResponse:
    stmt = select(Risk).where(
        Risk.tenant_id == principal.tenant_id, Risk.is_deleted.is_(False)
    )
    if band:
        from app.models.base import Severity

        stmt = stmt.where(Risk.severity_band == Severity(band))
    rows = db.execute(
        stmt.order_by(func.coalesce(Risk.residual_score, Risk.inherent_score).desc()).limit(200)
    ).scalars().all()
    return _page(
        request,
        "risks.html",
        principal,
        risks=rows,
        summary=risk_svc.register_summary(db, principal.tenant_id),
        heatmap=risk_svc.heatmap(db, principal.tenant_id),
        active_band=band,
        acceptance_threshold=risk_svc.ACCEPTANCE_GATE_FROM.value,
        now=utcnow(),
    )


# ==========================================================================
# Approvals
# ==========================================================================
@router.get("/approvals", response_class=HTMLResponse)
def approvals_page(request: Request, db: DbSession, principal=UiPrincipal) -> HTMLResponse:
    from app.security.rbac import gate_permission_for

    access = resolve_access(db, principal.id, principal.tenant_id)
    gates = db.execute(
        select(ApprovalGate)
        .where(
            ApprovalGate.tenant_id == principal.tenant_id,
            ApprovalGate.decision == GateDecision.PENDING,
        )
        .order_by(ApprovalGate.due_at.nulls_last(), ApprovalGate.raised_at)
    ).scalars().all()
    decided = db.execute(
        select(ApprovalGate)
        .where(
            ApprovalGate.tenant_id == principal.tenant_id,
            ApprovalGate.decision != GateDecision.PENDING,
        )
        .order_by(ApprovalGate.decided_at.desc())
        .limit(20)
    ).scalars().all()

    def authority(gate: ApprovalGate) -> tuple[bool, str]:
        if not principal.is_human:
            return False, "Approval authority rests with a person."
        perm = gate_permission_for(gate.gate_type)
        if perm not in principal.permissions and "*" not in principal.permissions:
            return False, f"Requires the {perm} permission."
        if gate.requested_by == principal.id:
            return False, "You raised this request, so you cannot decide it."
        if gate.approver_role_id and gate.approver_role_id not in access.role_ids:
            return False, "Reserved for a role you do not hold."
        return True, ""

    return _page(
        request,
        "approvals.html",
        principal,
        gates=[(g, *authority(g)) for g in gates],
        decided=decided,
        now=utcnow(),
    )


# ==========================================================================
# Operations
# ==========================================================================
@router.get("/operations", response_class=HTMLResponse)
def operations_page(request: Request, db: DbSession, principal=UiPrincipal) -> HTMLResponse:
    tenant_id = principal.tenant_id
    runs = db.execute(
        select(Run, Workflow)
        .join(Workflow, Workflow.id == Run.workflow_id)
        .where(Run.tenant_id == tenant_id)
        .order_by(Run.started_at.desc())
        .limit(25)
    ).all()
    incidents = db.execute(
        select(Incident)
        .where(Incident.tenant_id == tenant_id, Incident.is_deleted.is_(False))
        .order_by(Incident.created_at.desc())
        .limit(20)
    ).scalars().all()
    dsars = db.execute(
        select(DsarRequest)
        .where(DsarRequest.tenant_id == tenant_id, DsarRequest.is_deleted.is_(False))
        .order_by(DsarRequest.sla_due_at.nulls_last())
        .limit(20)
    ).scalars().all()
    plans = db.execute(
        select(ContinuityPlan)
        .where(ContinuityPlan.tenant_id == tenant_id, ContinuityPlan.is_deleted.is_(False))
        .order_by(ContinuityPlan.name)
    ).scalars().all()
    workflows = db.execute(
        select(Workflow).where(Workflow.tenant_id == tenant_id).order_by(Workflow.wf_code)
    ).scalars().all()
    return _page(
        request,
        "operations.html",
        principal,
        runs=runs,
        incidents=incidents,
        dsars=dsars,
        plans=plans,
        workflows=workflows,
        now=utcnow(),
    )


# ==========================================================================
# Admin — AI providers
# ==========================================================================
@router.get("/admin/ai", response_class=HTMLResponse)
def admin_ai(request: Request, db: DbSession, principal=UiPrincipal) -> HTMLResponse:
    if "admin.llm.view" not in principal.permissions and "*" not in principal.permissions:
        raise HTTPException(status_code=403, detail="Not authorised")
    tenant_id = principal.tenant_id
    providers = db.execute(
        select(LlmProvider).where(LlmProvider.tenant_id == tenant_id).order_by(LlmProvider.name)
    ).scalars().all()
    models = db.execute(
        select(LlmModel, LlmProvider)
        .join(LlmProvider, LlmProvider.id == LlmModel.provider_id)
        .where(LlmModel.tenant_id == tenant_id)
    ).all()
    routes = db.execute(
        select(LlmRoute).where(LlmRoute.tenant_id == tenant_id).order_by(LlmRoute.task_class)
    ).scalars().all()
    return _page(
        request,
        "admin_ai.html",
        principal,
        providers=providers,
        models=models,
        routes=routes,
        model_names={m.id: m.model_key for m, _ in models},
        policy=gateway.check_policy(db, tenant_id),
        spend=gateway.spend_summary(db, tenant_id, days=30),
        cache=prompt_cache.statistics(db, tenant_id, days=30),
    )


# ==========================================================================
# Audit
# ==========================================================================
@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    db: DbSession,
    principal=UiPrincipal,
    action: Optional[str] = None,
    cursor: Optional[int] = None,
) -> HTMLResponse:
    if "sec.auditlog.read" not in principal.permissions and "*" not in principal.permissions:
        raise HTTPException(status_code=403, detail="Not authorised")
    from app.models.audit import AuditLog

    stmt = select(AuditLog).where(AuditLog.tenant_id == principal.tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    if cursor:
        stmt = stmt.where(AuditLog.seq < cursor)
    entries = db.execute(stmt.order_by(AuditLog.seq.desc()).limit(60)).scalars().all()
    actions = db.execute(
        select(AuditLog.action, func.count(AuditLog.seq))
        .where(AuditLog.tenant_id == principal.tenant_id)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.seq).desc())
        .limit(20)
    ).all()
    return _page(
        request,
        "audit.html",
        principal,
        entries=entries,
        report=audit_service.verify_chain(db, principal.tenant_id),
        actions=actions,
        active_action=action,
        next_cursor=entries[-1].seq if len(entries) == 60 else None,
    )
