"""Risk scoring and treatment.

The scoring model is a 5×5 likelihood × impact matrix, scored twice: inherent
(before controls) and residual (after them). Both are kept, because ISO 27001
clause 6.1.2 expects the assessment to be repeatable and the treatment to be
traceable — showing only the residual number hides whether a control did
anything.

The band thresholds below are the platform default. They are deliberately in
one place so a risk manager can change the organisation's appetite without
touching any other code.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import RiskStatus, Severity, TreatmentStrategy, utcnow
from app.models.domain import Risk

# score → band. Upper bound inclusive.
BANDS: tuple[tuple[int, Severity], ...] = (
    (3, Severity.VERY_LOW),
    (6, Severity.LOW),
    (11, Severity.MEDIUM),
    (16, Severity.HIGH),
    (25, Severity.VERY_HIGH),
)

# Residual risk at or above this band needs a named acceptor, not a note.
ACCEPTANCE_GATE_FROM = Severity.HIGH

SEVERITY_RANK = {
    Severity.VERY_LOW: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.VERY_HIGH: 4,
}


class RiskError(Exception):
    code = "risk_error"


def validate_scale(value: int, name: str) -> int:
    if not isinstance(value, int) or not 1 <= value <= 5:
        raise RiskError(f"{name} must be a whole number from 1 to 5, got {value!r}")
    return value


def band_for(score: int) -> Severity:
    for upper, severity in BANDS:
        if score <= upper:
            return severity
    return Severity.VERY_HIGH


def requires_acceptance_gate(band: Severity) -> bool:
    return SEVERITY_RANK[band] >= SEVERITY_RANK[ACCEPTANCE_GATE_FROM]


@dataclass
class Scored:
    likelihood: int
    impact: int
    score: int
    band: Severity


def score(likelihood: int, impact: int) -> Scored:
    l = validate_scale(likelihood, "Likelihood")
    i = validate_scale(impact, "Impact")
    s = l * i
    return Scored(likelihood=l, impact=i, score=s, band=band_for(s))


def next_reference(db: Session, tenant_id: uuid.UUID) -> str:
    count = db.execute(
        select(func.count(Risk.id)).where(Risk.tenant_id == tenant_id)
    ).scalar_one()
    return f"R-{count + 1:04d}"


def create_risk(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    title: str,
    description: str = "",
    category: str = "information_security",
    inherent_likelihood: int = 3,
    inherent_impact: int = 3,
    residual_likelihood: int | None = None,
    residual_impact: int | None = None,
    treatment: TreatmentStrategy = TreatmentStrategy.MITIGATE,
    treatment_plan: str = "",
    owner_user_id: uuid.UUID | None = None,
    linked_controls: list[str] | None = None,
    threat: str = "",
    vulnerability: str = "",
    review_days: int = 90,
    run_id: uuid.UUID | None = None,
    lineage: dict | None = None,
    created_by: uuid.UUID | None = None,
) -> Risk:
    inherent = score(inherent_likelihood, inherent_impact)
    residual = (
        score(residual_likelihood, residual_impact)
        if residual_likelihood is not None and residual_impact is not None
        else None
    )
    risk = Risk(
        tenant_id=tenant_id,
        risk_ref=next_reference(db, tenant_id),
        title=title[:300],
        description=description,
        category=category,
        threat=threat or None,
        vulnerability=vulnerability or None,
        inherent_likelihood=inherent.likelihood,
        inherent_impact=inherent.impact,
        inherent_score=inherent.score,
        residual_likelihood=residual.likelihood if residual else None,
        residual_impact=residual.impact if residual else None,
        residual_score=residual.score if residual else None,
        severity_band=(residual or inherent).band,
        treatment=treatment,
        treatment_plan=treatment_plan or None,
        owner_user_id=owner_user_id,
        status=RiskStatus.OPEN,
        review_at=utcnow() + timedelta(days=review_days),
        linked_controls=linked_controls or [],
        run_id=run_id,
        lineage=lineage,
        created_at=utcnow(),
        created_by=created_by,
    )
    db.add(risk)
    db.flush()
    return risk


def rescore(
    db: Session,
    risk: Risk,
    *,
    residual_likelihood: int,
    residual_impact: int,
    note: str = "",
    updated_by: uuid.UUID | None = None,
) -> Risk:
    residual = score(residual_likelihood, residual_impact)
    if residual.score > risk.inherent_score:
        raise RiskError(
            f"Residual score ({residual.score}) cannot exceed the inherent score "
            f"({risk.inherent_score}). Controls reduce risk; if the exposure has grown, "
            "raise the inherent score first."
        )
    risk.residual_likelihood = residual.likelihood
    risk.residual_impact = residual.impact
    risk.residual_score = residual.score
    risk.severity_band = residual.band
    if note:
        risk.treatment_plan = f"{risk.treatment_plan or ''}\n\n{note}".strip()
    risk.row_version += 1
    risk.updated_at = utcnow()
    risk.updated_by = updated_by
    db.flush()
    return risk


def accept(
    db: Session,
    risk: Risk,
    *,
    accepted_by: uuid.UUID,
    rationale: str,
    review_days: int = 180,
) -> Risk:
    """Accept residual risk. High and above must go through an approval gate,
    which the API layer raises before calling this."""
    if not rationale or len(rationale.strip()) < 20:
        raise RiskError(
            "Acceptance requires a rationale of at least 20 characters. An auditor "
            "will ask why this exposure was accepted; record the answer now."
        )
    risk.status = RiskStatus.ACCEPTED
    risk.treatment = TreatmentStrategy.ACCEPT
    risk.accepted_by = accepted_by
    risk.accepted_at = utcnow()
    risk.acceptance_rationale = rationale.strip()
    risk.review_at = utcnow() + timedelta(days=review_days)
    risk.row_version += 1
    risk.updated_at = utcnow()
    db.flush()
    return risk


def heatmap(db: Session, tenant_id: uuid.UUID, use_residual: bool = True) -> dict:
    """5×5 counts for the register view. Cell (likelihood, impact) → count."""
    rows = db.execute(
        select(Risk).where(
            Risk.tenant_id == tenant_id,
            Risk.is_deleted.is_(False),
            Risk.status.in_([RiskStatus.OPEN, RiskStatus.IN_PROGRESS]),
        )
    ).scalars().all()
    # Cells carry their own band so a view never has to restate the thresholds.
    grid = {
        likelihood: {
            impact: {"count": 0, "score": likelihood * impact,
                     "band": band_for(likelihood * impact).value}
            for impact in range(1, 6)
        }
        for likelihood in range(1, 6)
    }
    for r in rows:
        likelihood = (r.residual_likelihood if use_residual else None) or r.inherent_likelihood
        impact = (r.residual_impact if use_residual else None) or r.inherent_impact
        grid[likelihood][impact]["count"] += 1
    return {
        "basis": "residual" if use_residual else "inherent",
        "total": len(rows),
        "cells": grid,
    }


def register_summary(db: Session, tenant_id: uuid.UUID) -> dict:
    rows = db.execute(
        select(Risk).where(Risk.tenant_id == tenant_id, Risk.is_deleted.is_(False))
    ).scalars().all()
    now = utcnow()
    by_band: dict[str, int] = {s.value: 0 for s in Severity}
    by_status: dict[str, int] = {s.value: 0 for s in RiskStatus}
    overdue_treatment = 0
    overdue_review = 0
    for r in rows:
        by_band[r.severity_band.value] += 1
        by_status[r.status.value] += 1
        if (
            r.treatment_due_at
            and r.treatment_due_at < now
            and r.status in (RiskStatus.OPEN, RiskStatus.IN_PROGRESS)
        ):
            overdue_treatment += 1
        if r.review_at and r.review_at < now and r.status != RiskStatus.CLOSED:
            overdue_review += 1
    open_rows = [r for r in rows if r.status in (RiskStatus.OPEN, RiskStatus.IN_PROGRESS)]
    scores = [r.residual_score or r.inherent_score for r in open_rows]
    return {
        "total": len(rows),
        "open": len(open_rows),
        "by_band": by_band,
        "by_status": by_status,
        "above_appetite": sum(
            1
            for r in open_rows
            if requires_acceptance_gate(band_for(r.residual_score or r.inherent_score))
        ),
        "overdue_treatment": overdue_treatment,
        "overdue_review": overdue_review,
        "average_residual": round(sum(scores) / len(scores), 2) if scores else 0.0,
    }


def top_risks(db: Session, tenant_id: uuid.UUID, limit: int = 10) -> list[Risk]:
    return list(
        db.execute(
            select(Risk)
            .where(
                Risk.tenant_id == tenant_id,
                Risk.is_deleted.is_(False),
                Risk.status.in_([RiskStatus.OPEN, RiskStatus.IN_PROGRESS]),
            )
            .order_by(
                func.coalesce(Risk.residual_score, Risk.inherent_score).desc(),
                Risk.created_at.desc(),
            )
            .limit(limit)
        ).scalars().all()
    )
