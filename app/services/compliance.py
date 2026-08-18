"""The compliance journey.

A certification journey is not a checklist; it is a defensible position against
each requirement, backed by evidence, reviewed on a cycle. This module computes
that position rather than asserting it.

**Readiness** is weighted by how far each applicable control has actually got,
and discounted where the claim has no evidence behind it:

    status weight    not_started 0.00 · planned 0.15 · in_progress 0.45
                     implemented 0.80 · operating 1.00
    evidence factor  a control claimed implemented or better with no current
                     evidence record scores at 70% of its weight — an auditor
                     will not accept an unevidenced claim, so neither does this

Excluded controls do not count against readiness, but an exclusion without a
written justification is itself reported as a gap, because ISO/IEC 27001
clause 6.1.3 d) requires the Statement of Applicability to justify both
inclusions and exclusions.

**Certification readiness** is deliberately stricter than percentage complete:
a programme is not ready while any mandatory clause is unimplemented or any
high-severity gap is open, whatever the headline number says.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import ImplementationStatus, Severity, utcnow
from app.models.compliance import (
    ComplianceProgramme,
    ControlImplementation,
    Framework,
    FrameworkControl,
    Gap,
    ReadinessSnapshot,
)
from app.models.core import EvidenceRecord

STATUS_WEIGHT: dict[ImplementationStatus, float] = {
    ImplementationStatus.NOT_STARTED: 0.0,
    ImplementationStatus.PLANNED: 0.15,
    ImplementationStatus.IN_PROGRESS: 0.45,
    ImplementationStatus.IMPLEMENTED: 0.80,
    ImplementationStatus.OPERATING: 1.0,
    ImplementationStatus.NOT_APPLICABLE: 0.0,
}

EVIDENCE_DISCOUNT = 0.70  # applied to an unevidenced implementation claim
EVIDENCED_STATUSES = {ImplementationStatus.IMPLEMENTED, ImplementationStatus.OPERATING}

SEVERITY_ORDER = {
    Severity.VERY_LOW: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.VERY_HIGH: 4,
}

JOURNEY_PHASES: tuple[str, ...] = (
    "initiation",
    "gap_analysis",
    "implementation",
    "internal_audit",
    "management_review",
    "certification_stage_1",
    "certification_stage_2",
    "certified",
    "surveillance",
)


class ComplianceError(Exception):
    code = "compliance_error"


# --------------------------------------------------------------------------
# Programme setup
# --------------------------------------------------------------------------
def start_programme(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    framework_code: str,
    scope_statement: str = "",
    owner_user_id: uuid.UUID | None = None,
    target_date=None,
) -> ComplianceProgramme:
    """Open a journey and materialise one implementation row per control.

    Every catalogue control gets a row immediately, defaulting to applicable
    and not started. That means the Statement of Applicability is complete from
    day one and the gap analysis is a matter of changing rows, not creating
    them — which is also why readiness starts honestly at zero.
    """
    framework = db.execute(
        select(Framework).where(Framework.code == framework_code)
    ).scalar_one_or_none()
    if framework is None:
        raise ComplianceError(f"Framework '{framework_code}' is not in the catalogue")

    existing = db.execute(
        select(ComplianceProgramme).where(
            ComplianceProgramme.tenant_id == tenant_id,
            ComplianceProgramme.framework_id == framework.id,
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    programme = ComplianceProgramme(
        tenant_id=tenant_id,
        framework_id=framework.id,
        scope_statement=scope_statement,
        owner_user_id=owner_user_id,
        target_date=target_date,
        phase="initiation",
        created_at=utcnow(),
    )
    db.add(programme)
    db.flush()

    controls = db.execute(
        select(FrameworkControl).where(FrameworkControl.framework_id == framework.id)
    ).scalars().all()
    for control in controls:
        db.add(
            ControlImplementation(
                tenant_id=tenant_id,
                framework_control_id=control.id,
                programme_id=programme.id,
                is_applicable=True,
                status=ImplementationStatus.NOT_STARTED,
                maturity=0,
                created_at=utcnow(),
            )
        )
    db.flush()
    return programme


def advance_phase(db: Session, programme: ComplianceProgramme, phase: str) -> ComplianceProgramme:
    if phase not in JOURNEY_PHASES:
        raise ComplianceError(
            f"Unknown phase '{phase}'. Valid phases: {', '.join(JOURNEY_PHASES)}"
        )
    programme.phase = phase
    programme.updated_at = utcnow()
    db.flush()
    return programme


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------
@dataclass
class SectionReadiness:
    section: str
    applicable: int
    operating: int
    implemented: int
    in_progress: int
    not_started: int
    excluded: int
    readiness_pct: float


@dataclass
class ReadinessResult:
    framework_code: str
    framework_name: str
    phase: str
    total_controls: int
    applicable: int
    excluded: int
    readiness_pct: float
    evidenced_pct: float
    average_maturity: float
    status_counts: dict[str, int]
    sections: list[SectionReadiness] = field(default_factory=list)
    open_gaps: int = 0
    high_gaps: int = 0
    overdue_reviews: int = 0
    unjustified_exclusions: int = 0
    blockers: list[str] = field(default_factory=list)

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def as_dict(self) -> dict:
        return {
            "framework": self.framework_code,
            "framework_name": self.framework_name,
            "phase": self.phase,
            "total_controls": self.total_controls,
            "applicable": self.applicable,
            "excluded": self.excluded,
            "readiness_pct": self.readiness_pct,
            "evidenced_pct": self.evidenced_pct,
            "average_maturity": self.average_maturity,
            "status_counts": self.status_counts,
            "open_gaps": self.open_gaps,
            "high_gaps": self.high_gaps,
            "overdue_reviews": self.overdue_reviews,
            "unjustified_exclusions": self.unjustified_exclusions,
            "certification_ready": self.certification_ready,
            "blockers": self.blockers,
            "sections": [
                {
                    "section": s.section,
                    "applicable": s.applicable,
                    "operating": s.operating,
                    "implemented": s.implemented,
                    "in_progress": s.in_progress,
                    "not_started": s.not_started,
                    "excluded": s.excluded,
                    "readiness_pct": s.readiness_pct,
                }
                for s in self.sections
            ],
        }


def _evidenced_control_ids(
    db: Session, tenant_id: uuid.UUID, impl_ids: Sequence[uuid.UUID]
) -> set[uuid.UUID]:
    """Implementations with at least one evidence record that has not expired."""
    if not impl_ids:
        return set()
    now = utcnow()
    rows = db.execute(
        select(EvidenceRecord.subject_id).where(
            EvidenceRecord.tenant_id == tenant_id,
            EvidenceRecord.subject_type == "control_implementation",
            EvidenceRecord.subject_id.in_(impl_ids),
            (EvidenceRecord.valid_until.is_(None)) | (EvidenceRecord.valid_until > now),
        )
    ).scalars().all()
    return set(rows)


def compute_readiness(
    db: Session, tenant_id: uuid.UUID, framework_code: str
) -> ReadinessResult:
    programme = db.execute(
        select(ComplianceProgramme)
        .join(Framework, Framework.id == ComplianceProgramme.framework_id)
        .where(
            ComplianceProgramme.tenant_id == tenant_id, Framework.code == framework_code
        )
    ).scalar_one_or_none()
    if programme is None:
        raise ComplianceError(
            f"No programme has been started for '{framework_code}'. "
            "Start one from the Compliance page."
        )
    framework = db.get(Framework, programme.framework_id)

    rows = db.execute(
        select(ControlImplementation, FrameworkControl)
        .join(FrameworkControl, FrameworkControl.id == ControlImplementation.framework_control_id)
        .where(
            ControlImplementation.tenant_id == tenant_id,
            FrameworkControl.framework_id == framework.id,
        )
    ).all()
    if not rows:
        raise ComplianceError("The programme has no control rows; re-run the seeder.")

    impl_ids = [impl.id for impl, _ in rows]
    evidenced = _evidenced_control_ids(db, tenant_id, impl_ids)

    status_counts: dict[str, int] = {s.value: 0 for s in ImplementationStatus}
    section_buckets: dict[str, dict] = {}
    weighted_total = 0.0
    applicable = 0
    excluded = 0
    unjustified_exclusions = 0
    maturity_sum = 0
    evidenced_applicable = 0
    now = utcnow()
    overdue = 0
    blockers: list[str] = []

    for impl, control in rows:
        status_counts[impl.status.value] += 1
        bucket = section_buckets.setdefault(
            control.section or "General",
            {"applicable": 0, "operating": 0, "implemented": 0, "in_progress": 0,
             "not_started": 0, "excluded": 0, "weighted": 0.0},
        )

        if not impl.is_applicable or impl.status == ImplementationStatus.NOT_APPLICABLE:
            excluded += 1
            bucket["excluded"] += 1
            if not (impl.applicability_justification or "").strip():
                unjustified_exclusions += 1
            if control.is_mandatory and control.control_type == "requirement":
                blockers.append(
                    f"{control.ref_code} is a mandatory clause and cannot be excluded."
                )
            continue

        applicable += 1
        bucket["applicable"] += 1
        maturity_sum += impl.maturity or 0

        weight = STATUS_WEIGHT[impl.status]
        has_evidence = impl.id in evidenced
        if impl.status in EVIDENCED_STATUSES:
            if has_evidence:
                evidenced_applicable += 1
            else:
                weight *= EVIDENCE_DISCOUNT
        weighted_total += weight
        bucket["weighted"] += weight

        if impl.status == ImplementationStatus.OPERATING:
            bucket["operating"] += 1
        elif impl.status == ImplementationStatus.IMPLEMENTED:
            bucket["implemented"] += 1
        elif impl.status in (ImplementationStatus.IN_PROGRESS, ImplementationStatus.PLANNED):
            bucket["in_progress"] += 1
        else:
            bucket["not_started"] += 1

        if impl.next_review_at and impl.next_review_at < now:
            overdue += 1

        if (
            control.is_mandatory
            and control.control_type == "requirement"
            and impl.status
            in (ImplementationStatus.NOT_STARTED, ImplementationStatus.PLANNED)
        ):
            blockers.append(
                f"Mandatory clause {control.ref_code} ({control.title[:60]}) is not implemented."
            )

    gap_rows = db.execute(
        select(Gap.severity, func.count(Gap.id))
        .join(
            ControlImplementation,
            ControlImplementation.id == Gap.control_implementation_id,
        )
        .join(
            FrameworkControl,
            FrameworkControl.id == ControlImplementation.framework_control_id,
        )
        .where(
            Gap.tenant_id == tenant_id,
            Gap.status == "open",
            FrameworkControl.framework_id == framework.id,
        )
        .group_by(Gap.severity)
    ).all()
    open_gaps = sum(r[1] for r in gap_rows)
    high_gaps = sum(
        r[1] for r in gap_rows if SEVERITY_ORDER.get(r[0], 0) >= SEVERITY_ORDER[Severity.HIGH]
    )
    if high_gaps:
        blockers.append(
            f"{high_gaps} high or very high severity gap(s) remain open."
        )
    if unjustified_exclusions:
        blockers.append(
            f"{unjustified_exclusions} control(s) are excluded without a written "
            "justification, which the Statement of Applicability requires."
        )

    sections = [
        SectionReadiness(
            section=name,
            applicable=b["applicable"],
            operating=b["operating"],
            implemented=b["implemented"],
            in_progress=b["in_progress"],
            not_started=b["not_started"],
            excluded=b["excluded"],
            readiness_pct=round(b["weighted"] / b["applicable"] * 100, 1)
            if b["applicable"]
            else 0.0,
        )
        for name, b in sorted(section_buckets.items())
    ]

    # Deduplicate blockers while preserving order, and keep the list readable.
    seen: set[str] = set()
    ordered_blockers = [b for b in blockers if not (b in seen or seen.add(b))]

    return ReadinessResult(
        framework_code=framework.code,
        framework_name=framework.name,
        phase=programme.phase,
        total_controls=len(rows),
        applicable=applicable,
        excluded=excluded,
        readiness_pct=round(weighted_total / applicable * 100, 1) if applicable else 0.0,
        evidenced_pct=round(evidenced_applicable / applicable * 100, 1) if applicable else 0.0,
        average_maturity=round(maturity_sum / applicable, 2) if applicable else 0.0,
        status_counts=status_counts,
        sections=sections,
        open_gaps=open_gaps,
        high_gaps=high_gaps,
        overdue_reviews=overdue,
        unjustified_exclusions=unjustified_exclusions,
        blockers=ordered_blockers[:12],
    )


def snapshot_readiness(
    db: Session, tenant_id: uuid.UUID, framework_code: str
) -> ReadinessSnapshot:
    """Persist today's position so the trend line is history, not a recompute."""
    result = compute_readiness(db, tenant_id, framework_code)
    programme = db.execute(
        select(ComplianceProgramme)
        .join(Framework, Framework.id == ComplianceProgramme.framework_id)
        .where(ComplianceProgramme.tenant_id == tenant_id, Framework.code == framework_code)
    ).scalar_one()
    snap = ReadinessSnapshot(
        tenant_id=tenant_id,
        programme_id=programme.id,
        captured_at=utcnow(),
        readiness_pct=result.readiness_pct,
        evidenced_pct=result.evidenced_pct,
        average_maturity=result.average_maturity,
        applicable_count=result.applicable,
        open_gap_count=result.open_gaps,
        detail=result.as_dict(),
    )
    db.add(snap)
    db.flush()
    return snap


# --------------------------------------------------------------------------
# Statement of Applicability
# --------------------------------------------------------------------------
def statement_of_applicability(
    db: Session, tenant_id: uuid.UUID, framework_code: str
) -> dict:
    """The SoA an ISO 27001 auditor asks for on day one of Stage 1.

    Rows carry the control reference, the inclusion or exclusion decision with
    its justification, how the control is implemented, its current status, and
    the evidence count behind the claim.
    """
    programme = db.execute(
        select(ComplianceProgramme)
        .join(Framework, Framework.id == ComplianceProgramme.framework_id)
        .where(ComplianceProgramme.tenant_id == tenant_id, Framework.code == framework_code)
    ).scalar_one_or_none()
    if programme is None:
        raise ComplianceError(f"No programme for '{framework_code}'")
    framework = db.get(Framework, programme.framework_id)

    rows = db.execute(
        select(ControlImplementation, FrameworkControl)
        .join(FrameworkControl, FrameworkControl.id == ControlImplementation.framework_control_id)
        .where(
            ControlImplementation.tenant_id == tenant_id,
            FrameworkControl.framework_id == framework.id,
        )
        .order_by(FrameworkControl.sort_order, FrameworkControl.ref_code)
    ).all()

    counts = dict(
        db.execute(
            select(EvidenceRecord.subject_id, func.count(EvidenceRecord.id))
            .where(
                EvidenceRecord.tenant_id == tenant_id,
                EvidenceRecord.subject_type == "control_implementation",
            )
            .group_by(EvidenceRecord.subject_id)
        ).all()
    )

    entries = []
    for impl, control in rows:
        entries.append(
            {
                "ref": control.ref_code,
                "title": control.title,
                "section": control.section,
                "theme": control.theme,
                "type": control.control_type,
                "applicable": impl.is_applicable
                and impl.status != ImplementationStatus.NOT_APPLICABLE,
                "justification": impl.applicability_justification or "",
                "status": impl.status.value,
                "maturity": impl.maturity,
                "how_implemented": impl.how_implemented or "",
                "evidence_count": counts.get(impl.id, 0),
                "last_assessed_at": impl.last_assessed_at.isoformat()
                if impl.last_assessed_at
                else None,
                "next_review_at": impl.next_review_at.isoformat()
                if impl.next_review_at
                else None,
            }
        )

    included = [e for e in entries if e["applicable"]]
    return {
        "framework": framework.code,
        "framework_name": framework.name,
        "edition": framework.edition,
        "scope_statement": programme.scope_statement,
        "generated_at": utcnow().isoformat(),
        "phase": programme.phase,
        "total": len(entries),
        "included": len(included),
        "excluded": len(entries) - len(included),
        "missing_justification": sum(
            1 for e in entries if not e["applicable"] and not e["justification"].strip()
        ),
        "entries": entries,
    }


# --------------------------------------------------------------------------
# Gaps
# --------------------------------------------------------------------------
def raise_gap(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    control_implementation_id: uuid.UUID,
    title: str,
    description: str = "",
    severity: Severity = Severity.MEDIUM,
    source: str = "assessment",
    remediation_plan: str = "",
    owner_user_id: uuid.UUID | None = None,
    due_days: int = 60,
    run_id: uuid.UUID | None = None,
) -> Gap:
    gap = Gap(
        tenant_id=tenant_id,
        control_implementation_id=control_implementation_id,
        title=title[:300],
        description=description,
        severity=severity,
        source=source,
        remediation_plan=remediation_plan,
        owner_user_id=owner_user_id,
        due_at=utcnow() + timedelta(days=due_days),
        status="open",
        run_id=run_id,
        created_at=utcnow(),
    )
    db.add(gap)
    db.flush()
    return gap


def close_gap(db: Session, gap: Gap, note: str = "") -> Gap:
    gap.status = "closed"
    gap.closed_at = utcnow()
    if note:
        gap.remediation_plan = f"{gap.remediation_plan or ''}\n\nClosure note: {note}".strip()
    gap.updated_at = utcnow()
    db.flush()
    return gap


def controls_due_for_review(
    db: Session, tenant_id: uuid.UUID, within_days: int = 30
) -> list[tuple[ControlImplementation, FrameworkControl]]:
    horizon = utcnow() + timedelta(days=within_days)
    return list(
        db.execute(
            select(ControlImplementation, FrameworkControl)
            .join(
                FrameworkControl,
                FrameworkControl.id == ControlImplementation.framework_control_id,
            )
            .where(
                ControlImplementation.tenant_id == tenant_id,
                ControlImplementation.is_applicable.is_(True),
                ControlImplementation.next_review_at.isnot(None),
                ControlImplementation.next_review_at <= horizon,
            )
            .order_by(ControlImplementation.next_review_at)
        ).all()
    )


def cross_framework_coverage(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    """One line per active programme — the portfolio view for a steering group."""
    programmes = db.execute(
        select(ComplianceProgramme, Framework)
        .join(Framework, Framework.id == ComplianceProgramme.framework_id)
        .where(
            ComplianceProgramme.tenant_id == tenant_id,
            ComplianceProgramme.is_active.is_(True),
        )
        .order_by(Framework.sort_order)
    ).all()
    out = []
    for programme, framework in programmes:
        try:
            r = compute_readiness(db, tenant_id, framework.code)
        except ComplianceError:
            continue
        out.append(
            {
                "code": framework.code,
                "name": framework.name,
                "certifiable": framework.certifiable,
                "phase": programme.phase,
                "target_date": programme.target_date.isoformat()
                if programme.target_date
                else None,
                "readiness_pct": r.readiness_pct,
                "evidenced_pct": r.evidenced_pct,
                "applicable": r.applicable,
                "open_gaps": r.open_gaps,
                "high_gaps": r.high_gaps,
                "certification_ready": r.certification_ready,
                "blockers": r.blockers[:3],
            }
        )
    return out
