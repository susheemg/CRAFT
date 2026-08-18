"""Compliance journey endpoints — ISO 27001, ISO 22301 and privacy."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession, RequestId, requires
from app.api.schemas import (
    ControlOut,
    ControlUpdate,
    EvidenceCreate,
    GapClose,
    GapCreate,
    ProgrammePhase,
    ProgrammeStart,
)
from app.models.base import ImplementationStatus, Severity, utcnow
from app.models.compliance import (
    ComplianceProgramme,
    ControlImplementation,
    ControlMapping,
    Framework,
    FrameworkControl,
    Gap,
)
from app.models.core import EvidenceRecord
from app.services import audit, compliance as svc, engine
from app.services.compliance import ComplianceError
from app.services.llm import gateway
from app.services.outbox import publish

router = APIRouter(prefix="/compliance", tags=["Compliance"])


def _compliance_error(exc: ComplianceError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"error": {"code": "compliance_error", "message": str(exc)}},
    )


@router.get("/frameworks", summary="List the shipped framework catalogue")
def list_frameworks(db: DbSession, principal=Depends(requires("data.register.read"))) -> dict:
    rows = db.execute(select(Framework).order_by(Framework.sort_order)).scalars().all()
    started = {
        p.framework_id
        for p in db.execute(
            select(ComplianceProgramme).where(
                ComplianceProgramme.tenant_id == principal.tenant_id
            )
        ).scalars().all()
    }
    out = []
    for f in rows:
        count = db.execute(
            select(func.count(FrameworkControl.id)).where(
                FrameworkControl.framework_id == f.id
            )
        ).scalar_one()
        out.append(
            {
                "code": f.code,
                "name": f.name,
                "issuer": f.issuer,
                "edition": f.edition,
                "certifiable": f.certifiable,
                "description": f.description,
                "control_count": count,
                "programme_started": f.id in started,
            }
        )
    return {"data": out}


@router.get("/overview", summary="Portfolio view across every active programme")
def overview(db: DbSession, principal=Depends(requires("rpt.dashboard.view"))) -> dict:
    return {"programmes": svc.cross_framework_coverage(db, principal.tenant_id)}


@router.post("/programmes", status_code=201, summary="Start a compliance journey")
def start_programme(
    payload: ProgrammeStart,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    try:
        programme = svc.start_programme(
            db,
            tenant_id=principal.tenant_id,
            framework_code=payload.framework,
            scope_statement=payload.scope_statement,
            owner_user_id=payload.owner_user_id or principal.id,
            target_date=payload.target_date,
        )
    except ComplianceError as exc:
        raise _compliance_error(exc) from exc

    framework = db.get(Framework, programme.framework_id)
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.programme_started",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="programme",
        entity_id=programme.id,
        after_state={"framework": framework.code, "scope": payload.scope_statement[:400]},
        request_id=request_id,
    )
    db.commit()
    readiness = svc.compute_readiness(db, principal.tenant_id, framework.code)
    return {
        "id": str(programme.id),
        "framework": framework.code,
        "phase": programme.phase,
        "controls_created": readiness.total_controls,
        "readiness": readiness.as_dict(),
    }


@router.post("/programmes/{framework}:advance", summary="Move the journey to a new phase")
def advance(
    framework: str,
    payload: ProgrammePhase,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    programme = _programme(db, principal.tenant_id, framework)
    before = programme.phase
    try:
        svc.advance_phase(db, programme, payload.phase)
    except ComplianceError as exc:
        raise _compliance_error(exc) from exc
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.phase_changed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="programme",
        entity_id=programme.id,
        before_state={"phase": before},
        after_state={"phase": payload.phase},
        request_id=request_id,
    )
    db.commit()
    return {"framework": framework, "phase": programme.phase, "previous_phase": before}


@router.get("/{framework}/readiness", summary="Readiness against a framework")
def readiness(
    framework: str,
    db: DbSession,
    principal=Depends(requires("rpt.dashboard.view")),
) -> dict:
    try:
        return svc.compute_readiness(db, principal.tenant_id, framework).as_dict()
    except ComplianceError as exc:
        raise _compliance_error(exc) from exc


@router.post("/{framework}/readiness:snapshot", summary="Capture readiness for the trend")
def snapshot(
    framework: str,
    db: DbSession,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    try:
        snap = svc.snapshot_readiness(db, principal.tenant_id, framework)
    except ComplianceError as exc:
        raise _compliance_error(exc) from exc
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="readiness.changed",
        payload={"framework": framework, "readiness_pct": float(snap.readiness_pct)},
    )
    db.commit()
    return {
        "captured_at": snap.captured_at.isoformat(),
        "readiness_pct": float(snap.readiness_pct),
        "evidenced_pct": float(snap.evidenced_pct),
        "open_gaps": snap.open_gap_count,
    }


@router.get("/{framework}/soa", summary="Statement of Applicability")
def soa(
    framework: str,
    db: DbSession,
    principal=Depends(requires("rpt.dashboard.view")),
) -> dict:
    try:
        return svc.statement_of_applicability(db, principal.tenant_id, framework)
    except ComplianceError as exc:
        raise _compliance_error(exc) from exc


@router.get("/{framework}/controls", summary="List controls and their position")
def list_controls(
    framework: str,
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    control_status: Optional[str] = Query(default=None, alias="status"),
    section: Optional[str] = None,
    search: Optional[str] = None,
    applicable_only: bool = False,
    limit: int = Query(default=200, ge=1, le=500),
) -> dict:
    fw = _framework(db, framework)
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
    if control_status:
        stmt = stmt.where(ControlImplementation.status == ImplementationStatus(control_status))
    if section:
        stmt = stmt.where(FrameworkControl.section == section)
    if applicable_only:
        stmt = stmt.where(ControlImplementation.is_applicable.is_(True))
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(FrameworkControl.title).like(pattern)
            | func.lower(FrameworkControl.ref_code).like(pattern)
        )
    rows = db.execute(
        stmt.order_by(FrameworkControl.sort_order).limit(limit)
    ).all()

    impl_ids = [i.id for i, _ in rows]
    ev_counts = dict(
        db.execute(
            select(EvidenceRecord.subject_id, func.count(EvidenceRecord.id))
            .where(
                EvidenceRecord.subject_type == "control_implementation",
                EvidenceRecord.subject_id.in_(impl_ids or [uuid.uuid4()]),
            )
            .group_by(EvidenceRecord.subject_id)
        ).all()
    )
    gap_counts = dict(
        db.execute(
            select(Gap.control_implementation_id, func.count(Gap.id))
            .where(
                Gap.control_implementation_id.in_(impl_ids or [uuid.uuid4()]),
                Gap.status == "open",
            )
            .group_by(Gap.control_implementation_id)
        ).all()
    )
    return {
        "framework": fw.code,
        "data": [
            ControlOut(
                id=impl.id,
                ref_code=ctl.ref_code,
                title=ctl.title,
                section=ctl.section,
                theme=ctl.theme,
                control_type=ctl.control_type,
                is_applicable=impl.is_applicable,
                applicability_justification=impl.applicability_justification,
                status=impl.status.value,
                maturity=impl.maturity,
                how_implemented=impl.how_implemented,
                evidence_count=ev_counts.get(impl.id, 0),
                open_gaps=gap_counts.get(impl.id, 0),
                next_review_at=impl.next_review_at,
            ).model_dump(mode="json")
            for impl, ctl in rows
        ],
    }


@router.patch("/controls/{implementation_id}", summary="Update a control's position")
def update_control(
    implementation_id: uuid.UUID,
    payload: ControlUpdate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    impl = _implementation(db, principal.tenant_id, implementation_id)
    control = db.get(FrameworkControl, impl.framework_control_id)

    # A mandatory clause cannot be excluded, whatever the request says.
    if (
        payload.is_applicable is False or payload.status == "not_applicable"
    ) and control.is_mandatory and control.control_type == "requirement":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "mandatory_clause",
                    "message": (
                        f"{control.ref_code} is a mandatory management-system clause. "
                        "It can be scoped, but it cannot be excluded."
                    ),
                }
            },
        )
    if payload.is_applicable is False and not (
        payload.applicability_justification or impl.applicability_justification
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "justification_required",
                    "message": (
                        "Excluding a control requires a written justification. The "
                        "Statement of Applicability must justify exclusions as well "
                        "as inclusions."
                    ),
                }
            },
        )

    before = {
        "status": impl.status.value,
        "maturity": impl.maturity,
        "is_applicable": impl.is_applicable,
    }
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"]:
        impl.status = ImplementationStatus(data["status"])
        impl.last_assessed_at = utcnow()
    for field in (
        "is_applicable", "applicability_justification", "maturity", "how_implemented",
        "implementation_note", "owner_user_id", "linked_policy_uri",
    ):
        if field in data and data[field] is not None:
            setattr(impl, field, data[field])
    if data.get("review_in_days"):
        from datetime import timedelta

        impl.next_review_at = utcnow() + timedelta(days=data["review_in_days"])
    impl.updated_at = utcnow()
    impl.updated_by = principal.id
    db.flush()

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.control_updated",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="control_implementation",
        entity_id=impl.id,
        before_state=before,
        after_state={
            "status": impl.status.value,
            "maturity": impl.maturity,
            "is_applicable": impl.is_applicable,
        },
        detail={"control": control.ref_code},
        request_id=request_id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="control.updated",
        payload={
            "control": control.ref_code,
            "status": impl.status.value,
            "maturity": impl.maturity,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(impl.id),
        "ref_code": control.ref_code,
        "status": impl.status.value,
        "maturity": impl.maturity,
        "is_applicable": impl.is_applicable,
    }


@router.get("/controls/{implementation_id}", summary="Retrieve one control in detail")
def get_control(
    implementation_id: uuid.UUID,
    db: DbSession,
    principal=Depends(requires("data.register.read")),
) -> dict:
    impl = _implementation(db, principal.tenant_id, implementation_id)
    control = db.get(FrameworkControl, impl.framework_control_id)
    framework = db.get(Framework, control.framework_id)
    evidence = db.execute(
        select(EvidenceRecord)
        .where(
            EvidenceRecord.subject_type == "control_implementation",
            EvidenceRecord.subject_id == impl.id,
        )
        .order_by(EvidenceRecord.collected_at.desc())
        .limit(50)
    ).scalars().all()
    gaps = db.execute(
        select(Gap).where(Gap.control_implementation_id == impl.id).order_by(Gap.created_at.desc())
    ).scalars().all()
    mapped = db.execute(
        select(FrameworkControl, Framework)
        .join(ControlMapping, ControlMapping.target_control_id == FrameworkControl.id)
        .join(Framework, Framework.id == FrameworkControl.framework_id)
        .where(ControlMapping.source_control_id == control.id)
    ).all()
    reverse = db.execute(
        select(FrameworkControl, Framework)
        .join(ControlMapping, ControlMapping.source_control_id == FrameworkControl.id)
        .join(Framework, Framework.id == FrameworkControl.framework_id)
        .where(ControlMapping.target_control_id == control.id)
    ).all()

    return {
        "id": str(impl.id),
        "framework": framework.code,
        "framework_name": framework.name,
        "ref_code": control.ref_code,
        "title": control.title,
        "section": control.section,
        "theme": control.theme,
        "control_type": control.control_type,
        "is_mandatory": control.is_mandatory,
        "evidence_hint": control.evidence_hint,
        "is_applicable": impl.is_applicable,
        "applicability_justification": impl.applicability_justification,
        "status": impl.status.value,
        "maturity": impl.maturity,
        "how_implemented": impl.how_implemented,
        "implementation_note": impl.implementation_note,
        "ai_assessment": impl.ai_assessment,
        "last_assessed_at": impl.last_assessed_at.isoformat() if impl.last_assessed_at else None,
        "next_review_at": impl.next_review_at.isoformat() if impl.next_review_at else None,
        "evidence": [
            {
                "id": str(e.id),
                "kind": e.kind,
                "title": e.title,
                "collected_at": e.collected_at.isoformat(),
                "valid_until": e.valid_until.isoformat() if e.valid_until else None,
                "content_hash": e.content_hash.hex(),
            }
            for e in evidence
        ],
        "gaps": [
            {
                "id": str(g.id),
                "title": g.title,
                "severity": g.severity.value,
                "status": g.status,
                "due_at": g.due_at.isoformat() if g.due_at else None,
            }
            for g in gaps
        ],
        "also_satisfies": [
            {"framework": f.code, "ref": c.ref_code, "title": c.title}
            for c, f in list(mapped) + list(reverse)
        ],
    }


@router.post(
    "/controls/{implementation_id}:assess",
    summary="Ask the model to assess a control against its evidence",
)
async def assess_control(
    implementation_id: uuid.UUID,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    """Runs the governed model call and records the draft assessment.

    The result is a recommendation, never a status change: the model's output
    lands in ``ai_assessment`` and a person attests the status. Low confidence
    is reported rather than smoothed over.
    """
    impl = _implementation(db, principal.tenant_id, implementation_id)
    control = db.get(FrameworkControl, impl.framework_control_id)
    framework = db.get(Framework, control.framework_id)
    evidence = db.execute(
        select(EvidenceRecord)
        .where(
            EvidenceRecord.subject_type == "control_implementation",
            EvidenceRecord.subject_id == impl.id,
        )
        .order_by(EvidenceRecord.collected_at.desc())
        .limit(20)
    ).scalars().all()

    template = gateway.active_prompt(db, principal.tenant_id, "control_assessment")
    if template is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "prompt_missing",
                    "message": "The control-assessment prompt is not seeded.",
                }
            },
        )
    evidence_text = (
        "\n".join(
            f"- [{e.kind}] {e.title} (collected {e.collected_at.date()}): "
            f"{json.dumps(e.payload)[:600] if e.payload else e.artifact_uri}"
            for e in evidence
        )
        or "No evidence has been attached to this control."
    )
    prompt = template.template.format(
        framework_name=framework.name,
        framework_edition=framework.edition,
        control_ref=control.ref_code,
        control_title=control.title,
        control_section=control.section,
        evidence_hint=control.evidence_hint or "Not specified.",
        current_status=impl.status.value,
        current_maturity=impl.maturity,
        how_implemented=impl.how_implemented or "Not recorded.",
        evidence=evidence_text,
    )

    try:
        result = await gateway.complete(
            db,
            tenant_id=principal.tenant_id,
            task_class="control_assessment",
            prompt=prompt,
            cache_prefix=template.cache_prefix or "",
            prompt_name=template.name,
            prompt_version=template.version,
            actor_ref=principal.actor_ref,
            json_mode=True,
        )
    except gateway.GatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"code": exc.code, "message": str(exc)}},
        ) from exc

    try:
        parsed = json.loads(result.text.strip().removeprefix("```json").removesuffix("```").strip())
    except json.JSONDecodeError:
        parsed = {"raw": result.text[:4000], "parse_error": True, "confidence": 0.0}

    # The gateway wrote the invocation before this handler could parse the
    # model's stated confidence out of the response, so it is attached here.
    # PR-AIG-02 and PR-AIG-03 both read it as a first-class measurement.
    _attach_confidence(db, result, parsed.get("confidence"))

    impl.ai_assessment = {
        **parsed,
        "model": result.model_key,
        "provider": result.provider_kind,
        "prompt_version": template.version,
        "cache_status": result.cache_status,
        "assessed_at": utcnow().isoformat(),
    }
    impl.updated_at = utcnow()
    db.flush()

    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.control_assessed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="control_implementation",
        entity_id=impl.id,
        model=result.model_key,
        prompt_version=f"{template.name}@{template.version}",
        sources={"evidence_ids": [str(e.id) for e in evidence]},
        detail={
            "control": control.ref_code,
            "confidence": parsed.get("confidence"),
            "cache_status": result.cache_status,
            "cost": result.cost,
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "control": control.ref_code,
        "assessment": parsed,
        "meta": {
            "model": result.model_key,
            "provider": result.provider_kind,
            "cache_status": result.cache_status,
            "cost": result.cost,
            "cost_saved": result.cost_saved,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "notes": result.notes,
        },
        "note": (
            "This is a recommendation. A control owner must attest the status "
            "before it counts towards readiness."
        ),
    }


# --------------------------------------------------------------------------
# Gaps and evidence
# --------------------------------------------------------------------------
@router.get("/gaps", summary="List gaps")
def list_gaps(
    db: DbSession,
    principal=Depends(requires("data.register.read")),
    gap_status: str = Query(default="open", alias="status"),
    severity: Optional[str] = None,
) -> dict:
    stmt = select(Gap, ControlImplementation, FrameworkControl).join(
        ControlImplementation, ControlImplementation.id == Gap.control_implementation_id
    ).join(
        FrameworkControl, FrameworkControl.id == ControlImplementation.framework_control_id
    ).where(Gap.tenant_id == principal.tenant_id)
    if gap_status != "all":
        stmt = stmt.where(Gap.status == gap_status)
    if severity:
        stmt = stmt.where(Gap.severity == Severity(severity))
    rows = db.execute(stmt.order_by(Gap.due_at.nulls_last(), Gap.created_at.desc())).all()
    return {
        "data": [
            {
                "id": str(g.id),
                "title": g.title,
                "description": g.description,
                "severity": g.severity.value,
                "status": g.status,
                "source": g.source,
                "control": ctl.ref_code,
                "control_title": ctl.title,
                "remediation_plan": g.remediation_plan,
                "due_at": g.due_at.isoformat() if g.due_at else None,
                "overdue": bool(g.due_at and g.due_at < utcnow() and g.status == "open"),
            }
            for g, _impl, ctl in rows
        ]
    }


@router.post("/gaps", status_code=201, summary="Raise a gap")
def create_gap(
    payload: GapCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    impl = _implementation(db, principal.tenant_id, payload.control_implementation_id)
    gap = svc.raise_gap(
        db,
        tenant_id=principal.tenant_id,
        control_implementation_id=impl.id,
        title=payload.title,
        description=payload.description,
        severity=Severity(payload.severity),
        source=payload.source,
        remediation_plan=payload.remediation_plan,
        owner_user_id=payload.owner_user_id,
        due_days=payload.due_days,
    )
    control = db.get(FrameworkControl, impl.framework_control_id)
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.gap_raised",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="gap",
        entity_id=gap.id,
        after_state={"title": gap.title, "severity": gap.severity.value},
        detail={"control": control.ref_code},
        request_id=request_id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="gap.raised",
        payload={
            "gap_id": str(gap.id),
            "control": control.ref_code,
            "severity": gap.severity.value,
        },
        request_id=request_id,
    )
    db.commit()
    return {"id": str(gap.id), "title": gap.title, "severity": gap.severity.value}


@router.post("/gaps/{gap_id}:close", summary="Close a gap")
def close_gap(
    gap_id: uuid.UUID,
    payload: GapClose,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("compliance.manage")),
) -> dict:
    gap = db.get(Gap, gap_id)
    if gap is None or gap.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "No such gap."}}
        )
    if gap.status == "closed":
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "already_closed", "message": "This gap is already closed."}},
        )
    svc.close_gap(db, gap, payload.note)
    engine.record_evidence(
        db,
        tenant_id=principal.tenant_id,
        kind="attestation",
        title=f"Gap closure — {gap.title[:120]}",
        payload={"gap_id": str(gap.id), "note": payload.note, "closed_by": str(principal.id)},
        subject_type="control_implementation",
        subject_id=gap.control_implementation_id,
        created_by=principal.id,
    )
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="compliance.gap_closed",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="gap",
        entity_id=gap.id,
        after_state={"status": "closed", "note": payload.note[:400]},
        request_id=request_id,
    )
    publish(
        db,
        tenant_id=principal.tenant_id,
        topic="gap.closed",
        payload={"gap_id": str(gap.id)},
        request_id=request_id,
    )
    db.commit()
    return {"id": str(gap.id), "status": "closed"}


@router.post("/evidence", status_code=201, summary="Attach evidence")
def add_evidence(
    payload: EvidenceCreate,
    db: DbSession,
    request_id: RequestId,
    principal=Depends(requires("evidence.write")),
) -> dict:
    record = engine.record_evidence(
        db,
        tenant_id=principal.tenant_id,
        kind=payload.kind,
        title=payload.title,
        payload=payload.payload,
        artifact_uri=payload.artifact_uri,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        valid_days=payload.valid_days,
        created_by=principal.id,
    )
    audit.record(
        db,
        tenant_id=principal.tenant_id,
        action="evidence.recorded",
        actor_type=principal.actor_type,
        actor_ref=principal.actor_ref,
        actor_id=principal.id,
        entity="evidence_record",
        entity_id=record.id,
        detail={
            "kind": payload.kind,
            "subject_type": payload.subject_type,
            "content_hash": record.content_hash.hex(),
        },
        request_id=request_id,
    )
    db.commit()
    return {
        "id": str(record.id),
        "content_hash": record.content_hash.hex(),
        "collected_at": record.collected_at.isoformat(),
        "valid_until": record.valid_until.isoformat() if record.valid_until else None,
    }


@router.get("/reviews/due", summary="Controls falling due for review")
def reviews_due(
    db: DbSession,
    within_days: int = Query(default=30, ge=1, le=365),
    principal=Depends(requires("data.register.read")),
) -> dict:
    rows = svc.controls_due_for_review(db, principal.tenant_id, within_days)
    return {
        "data": [
            {
                "implementation_id": str(impl.id),
                "ref_code": ctl.ref_code,
                "title": ctl.title,
                "status": impl.status.value,
                "next_review_at": impl.next_review_at.isoformat(),
                "overdue": impl.next_review_at < utcnow(),
            }
            for impl, ctl in rows
        ]
    }


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _attach_confidence(db, result, confidence) -> None:
    from app.models.llm import ModelInvocation

    if confidence is None or result.invocation_id is None:
        return
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return
    invocation = db.get(ModelInvocation, result.invocation_id)
    if invocation is not None:
        invocation.confidence = max(0.0, min(1.0, value))


def _framework(db, code: str) -> Framework:
    fw = db.execute(select(Framework).where(Framework.code == code)).scalar_one_or_none()
    if fw is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"'{code}' is not in the framework catalogue.",
                }
            },
        )
    return fw


def _programme(db, tenant_id: uuid.UUID, code: str) -> ComplianceProgramme:
    fw = _framework(db, code)
    programme = db.execute(
        select(ComplianceProgramme).where(
            ComplianceProgramme.tenant_id == tenant_id,
            ComplianceProgramme.framework_id == fw.id,
        )
    ).scalar_one_or_none()
    if programme is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": f"No programme has been started for {code}.",
                }
            },
        )
    return programme


def _implementation(db, tenant_id: uuid.UUID, impl_id: uuid.UUID) -> ControlImplementation:
    impl = db.get(ControlImplementation, impl_id)
    if impl is None or impl.tenant_id != tenant_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "No such control implementation."}},
        )
    return impl
