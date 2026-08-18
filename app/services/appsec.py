"""Application security service — ISO/IEC 27034.

Three things happen here that the rest of the platform depends on.

**Building an Application Normative Framework.** Given an application and an
approved targeted level of trust, select from the ONF exactly the Application
Security Controls that level requires — every level-zero control included and
flagged as unwaivable — and place each at the project's own delivery stage.

**Computing the actual level of trust.** This is arithmetic over measurement
records, not a judgement, which is why it runs unattended and why any auditor
can reproduce it. An application reaches level *n* when every mandatory control
required at every level up to and including *n* has a passing measurement. A
single failed or missing mandatory measurement holds it at the level below.

**Blocking the release.** The gate is computed, not asserted: promotion is
refused while the actual level sits below the target, and the refusal names the
controls responsible rather than returning a bare denial.

One rule runs through all of it. Recording evidence goes through
``record_evidence`` so the separation-of-duties failure from the database
surfaces as a domain error rather than an opaque driver exception — but the
check itself lives in the trigger, not here. A service-level guard would be one
refactor away from gone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models.aims import AiSystem
from app.models.appsec import (
    Anf,
    AnfAsc,
    Application,
    Asc,
    AscEvidence,
    AscTrustLevel,
    LifecycleStageMap,
    Onf,
    TrustLevel,
)
from app.models.base import utcnow


class AppSecError(Exception):
    """A refusal the caller can act on, rather than a driver traceback."""


# --------------------------------------------------------------------------
# ONF lookups
# --------------------------------------------------------------------------
def current_onf(db: Session, tenant_id: uuid.UUID) -> Onf:
    """The latest ONF iteration for the tenant."""
    onf = db.execute(
        select(Onf)
        .where(Onf.tenant_id == tenant_id)
        .order_by(Onf.iteration_no.desc())
        .limit(1)
    ).scalar_one_or_none()
    if onf is None:
        raise AppSecError(
            "No Organization Normative Framework exists for this tenant. "
            "Run PR-APS-01 before assessing an application."
        )
    return onf


def trust_levels(db: Session, onf: Onf) -> list[TrustLevel]:
    return list(
        db.execute(
            select(TrustLevel).where(TrustLevel.onf_id == onf.id).order_by(TrustLevel.level_no)
        ).scalars()
    )


def level_zero(db: Session, onf: Onf) -> TrustLevel:
    level = db.execute(
        select(TrustLevel).where(TrustLevel.onf_id == onf.id, TrustLevel.is_level_zero.is_(True))
    ).scalar_one_or_none()
    if level is None:
        raise AppSecError(
            "This ONF iteration defines no level zero. Without a floor there is "
            "nothing a project team cannot remove."
        )
    return level


def _ascs_for_level(db: Session, onf: Onf, level_no: int) -> list[tuple[Asc, bool]]:
    """Every ASC required at or below ``level_no``, with its level-zero flag.

    Cumulative on purpose: a level-two application inherits everything level zero
    and level one require. Selecting only the controls attached to the target
    level would produce an ANF that omits the floor.
    """
    rows = db.execute(
        select(Asc, TrustLevel.is_level_zero, AscTrustLevel.is_mandatory)
        .join(AscTrustLevel, AscTrustLevel.asc_id == Asc.id)
        .join(TrustLevel, TrustLevel.id == AscTrustLevel.trust_level_id)
        .where(
            Asc.onf_id == onf.id,
            Asc.status == "approved",
            TrustLevel.level_no <= level_no,
        )
    ).all()

    selected: dict[uuid.UUID, tuple[Asc, bool]] = {}
    for asc, is_zero, _mandatory in rows:
        existing = selected.get(asc.id)
        # If a control appears at several levels, the level-zero flag wins:
        # once a control is part of the floor it stays part of it.
        selected[asc.id] = (asc, bool(is_zero) or (existing[1] if existing else False))
    return sorted(selected.values(), key=lambda pair: pair[0].asc_uid)


# --------------------------------------------------------------------------
# Building the ANF
# --------------------------------------------------------------------------
def build_anf(
    db: Session,
    application: Application,
    targeted_level: TrustLevel,
    *,
    approved_by: uuid.UUID | None = None,
    lifecycle_model: str | None = None,
) -> Anf:
    """Create the next ANF version for an application.

    ``approved_by`` is the application owner's approval of the target. It is
    accepted here rather than defaulted, because a target nobody approved is a
    default, and 27034-1 8.2.4 makes owner approval the point of the exercise.
    """
    onf = current_onf(db, application.tenant_id)
    if targeted_level.onf_id != onf.id:
        raise AppSecError("The targeted level of trust belongs to a different ONF iteration.")

    previous = db.execute(
        select(Anf)
        .where(Anf.application_id == application.id)
        .order_by(Anf.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous is not None:
        previous.status = "superseded"

    anf = Anf(
        tenant_id=application.tenant_id,
        application_id=application.id,
        onf_id=onf.id,
        version=(previous.version + 1) if previous else 1,
        targeted_trust_level_id=targeted_level.id,
        status="targeted" if approved_by else "draft",
        target_approved_by=approved_by,
        target_approved_at=utcnow() if approved_by else None,
        created_at=utcnow(),
    )
    db.add(anf)
    db.flush()

    stage_map = {
        m.aslcrm_stage_code: m.local_stage_code
        for m in db.execute(
            select(LifecycleStageMap).where(
                LifecycleStageMap.onf_id == onf.id,
                LifecycleStageMap.model_name
                == (lifecycle_model or application.lifecycle_model_name or "CRAFT delivery model"),
            )
        ).scalars()
    }

    for asc, is_zero in _ascs_for_level(db, onf, targeted_level.level_no):
        db.add(
            AnfAsc(
                tenant_id=application.tenant_id,
                anf_id=anf.id,
                asc_id=asc.id,
                # Where the delivery model has no local stage for a reference
                # stage, the control is still selected but carries no local
                # placement — PR-APS-01/A5 reports that gap rather than hiding it.
                local_stage_code=stage_map.get(asc.aslcrm_stage_code or ""),
                is_mandatory=True,
                is_level_zero=is_zero,
                created_at=utcnow(),
            )
        )
    db.flush()
    return anf


# --------------------------------------------------------------------------
# Recording evidence
# --------------------------------------------------------------------------
def record_evidence(
    db: Session,
    selection: AnfAsc,
    *,
    kind: str,
    actor_type: str,
    actor_user_id: uuid.UUID | None = None,
    actor_agent_id: uuid.UUID | None = None,
    outcome: str = "pass",
    provenance: str | None = None,
    result_detail: dict | None = None,
    run_id: uuid.UUID | None = None,
    evidence_record_id: uuid.UUID | None = None,
) -> AscEvidence:
    """Record one half of one control, translating a refusal into a domain error.

    The separation-of-duties and human-verifier rules are enforced by the
    ``asc_evidence_sod`` trigger. This function does not re-implement them; it
    catches the refusal so the caller gets a sentence rather than a stack trace.
    Duplicating the rule here would create a second place for it to be wrong.
    """
    if provenance is None:
        provenance = "tool_output" if actor_type == "agent" else "human_attested"

    row = AscEvidence(
        tenant_id=selection.tenant_id,
        anf_asc_id=selection.id,
        kind=kind,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        actor_agent_id=actor_agent_id,
        outcome=outcome,
        provenance=provenance,
        result_detail=result_detail or {},
        run_id=run_id,
        evidence_record_id=evidence_record_id,
        performed_at=utcnow(),
        created_at=utcnow(),
    )
    db.add(row)
    try:
        db.flush()
    except (DBAPIError, IntegrityError) as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc))
        if "Separation of duties" in message:
            raise AppSecError(
                "This actor performed the security activity for the control and "
                "cannot record its verification measurement."
            ) from exc
        if "requires a human verifier" in message:
            raise AppSecError(
                "This control requires a human verifier; an agent-recorded "
                "measurement is refused."
            ) from exc
        raise
    return row


# --------------------------------------------------------------------------
# Level of trust
# --------------------------------------------------------------------------
@dataclass
class LevelOfTrustResult:
    """Everything a release gate needs, and everything an auditor would ask."""

    targeted_level_no: int | None
    actual_level_no: int | None
    actual_level_id: uuid.UUID | None
    meets_target: bool
    total_controls: int
    passing: int
    failing: list[str] = field(default_factory=list)
    unmeasured: list[str] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "targeted_level": self.targeted_level_no,
            "actual_level": self.actual_level_no,
            "meets_target": self.meets_target,
            "controls": self.total_controls,
            "passing": self.passing,
            "failing": self.failing,
            "unmeasured": self.unmeasured,
            "blocking": self.blocking,
        }


def compute_level_of_trust(db: Session, anf: Anf) -> LevelOfTrustResult:
    """Determine the actual level of trust from measurement records alone.

    A control counts as satisfied when it has at least one measurement with a
    passing outcome. An activity record is not enough: the whole point of the
    two-part control is that someone independent confirmed the activity worked.
    """
    onf = db.get(Onf, anf.onf_id)
    levels = trust_levels(db, onf) if onf else []
    target = db.get(TrustLevel, anf.targeted_trust_level_id) if anf.targeted_trust_level_id else None

    rows = db.execute(
        select(AnfAsc, Asc)
        .join(Asc, Asc.id == AnfAsc.asc_id)
        .where(AnfAsc.anf_id == anf.id)
    ).all()

    # Which levels require which control, so a shortfall can be attributed to a
    # level rather than only to the application as a whole.
    required_at: dict[uuid.UUID, set[int]] = {}
    for asc_id, level_no in db.execute(
        select(AscTrustLevel.asc_id, TrustLevel.level_no)
        .join(TrustLevel, TrustLevel.id == AscTrustLevel.trust_level_id)
        .where(AscTrustLevel.is_mandatory.is_(True))
    ).all():
        required_at.setdefault(asc_id, set()).add(level_no)

    measurements = db.execute(
        select(AscEvidence.anf_asc_id, AscEvidence.outcome).where(
            AscEvidence.kind == "measurement",
            AscEvidence.anf_asc_id.in_([sel.id for sel, _ in rows]) if rows else False,
        )
    ).all()
    outcomes: dict[uuid.UUID, set[str]] = {}
    for anf_asc_id, outcome in measurements:
        outcomes.setdefault(anf_asc_id, set()).add(outcome)

    failing: list[str] = []
    unmeasured: list[str] = []
    passing = 0
    satisfied_levels: dict[int, bool] = {lvl.level_no: True for lvl in levels}

    for selection, asc in rows:
        seen = outcomes.get(selection.id, set())
        waived = selection.waived_at is not None
        if waived and not selection.is_level_zero:
            # A waiver with an approver is a governed decision, so it does not
            # hold the level down. A level-zero waiver cannot exist: the check
            # constraint refuses it.
            continue
        if "pass" in seen or "not_applicable" in seen:
            passing += 1
            continue
        if not selection.is_mandatory:
            continue
        if seen:
            failing.append(asc.asc_uid)
        else:
            unmeasured.append(asc.asc_uid)
        for level_no in required_at.get(asc.id, set()):
            satisfied_levels[level_no] = False

    # A level can only be *assessed* if the ANF actually contains every mandatory
    # control that level requires. Without this cap an ANF built at level zero
    # would report level three, because there would be no level-three controls
    # present to fail it — an absence of evidence read as evidence of assurance.
    selected_asc_ids = {asc.id for _sel, asc in rows}
    assessable = -1
    for level in levels:
        required_here = {
            asc_id for asc_id, level_nos in required_at.items() if level.level_no in level_nos
        }
        if required_here - selected_asc_ids:
            break
        assessable = level.level_no

    # The actual level is the highest assessable level for which every level up
    # to and including it is fully satisfied. Walking upward and stopping at the
    # first failure is what stops a high-level pass masking a level-zero hole.
    actual: TrustLevel | None = None
    for level in levels:
        if level.level_no > assessable:
            break
        if satisfied_levels.get(level.level_no, True):
            actual = level
        else:
            break

    blocking = sorted(set(failing) | set(unmeasured))
    meets = bool(
        target is not None and actual is not None and actual.level_no >= target.level_no
    )

    anf.actual_trust_level_id = actual.id if actual else None
    anf.actual_level_computed_at = utcnow()

    return LevelOfTrustResult(
        targeted_level_no=target.level_no if target else None,
        actual_level_no=actual.level_no if actual else None,
        actual_level_id=actual.id if actual else None,
        meets_target=meets,
        total_controls=len(rows),
        passing=passing,
        failing=sorted(failing),
        unmeasured=sorted(unmeasured),
        blocking=blocking,
    )


def release_decision(db: Session, anf: Anf) -> dict:
    """The computed release gate. Blocks with reasons, never with a bare refusal."""
    result = compute_level_of_trust(db, anf)
    if result.meets_target:
        return {"allowed": True, **result.as_dict()}
    if result.targeted_level_no is None:
        reason = "No targeted level of trust has been approved for this application."
    elif result.blocking:
        reason = (
            f"{len(result.blocking)} mandatory control(s) lack a passing verification "
            f"measurement: {', '.join(result.blocking[:6])}"
            + ("…" if len(result.blocking) > 6 else "")
        )
    else:
        reason = (
            f"Actual level of trust {result.actual_level_no} is below the approved "
            f"target {result.targeted_level_no}."
        )
    return {"allowed": False, "reason": reason, **result.as_dict()}


# --------------------------------------------------------------------------
# Certification block
# --------------------------------------------------------------------------
def certification_block(framework_code: str) -> str | None:
    """Why certification submission is blocked for a framework, or ``None``.

    ISO/IEC 42001's catalogue in this build is a paraphrase written by CRAFT.
    Certifying against a paraphrase is not certification, so the block is a
    property of the catalogue rather than a policy someone has to remember.
    """
    if framework_code != "iso42001":
        return None
    from app.seed.catalogue_iso42001 import RECONCILED

    if RECONCILED:
        return None
    return (
        "The ISO/IEC 42001 catalogue in this build is a CRAFT paraphrase and has "
        "not been reconciled against a licensed copy of the standard. Complete "
        "the reconciliation and record the attestation before submitting for "
        "certification."
    )


def onf_level_design_issues(db: Session, onf: Onf) -> list[str]:
    """Levels of trust that are not actually distinguishable from each other.

    If level *n* requires no control that level *n-1* does not, then an
    application meeting the lower level automatically meets the higher one, and
    the higher level tells an owner nothing. That is a design defect in the ONF
    and it is invisible until someone computes an actual level of trust and gets
    a surprising answer.
    """
    issues: list[str] = []
    previous: set[uuid.UUID] = set()
    previous_label: str | None = None
    for level in trust_levels(db, onf):
        current = {
            asc_id
            for (asc_id,) in db.execute(
                select(AscTrustLevel.asc_id)
                .join(TrustLevel, TrustLevel.id == AscTrustLevel.trust_level_id)
                .where(TrustLevel.onf_id == onf.id, TrustLevel.level_no <= level.level_no)
            ).all()
        }
        if previous_label is not None and not (current - previous):
            issues.append(
                f"Level {level.level_no} ({level.label}) requires no control that "
                f"{previous_label} does not; the two levels are indistinguishable."
            )
        previous, previous_label = current, f"level {level.level_no}"
    return issues


def ai_systems_without_application(db: Session, tenant_id: uuid.UUID) -> Sequence[AiSystem]:
    """AI systems that no application in the register accounts for.

    The junction between the two standards is where things fall through: a model
    wired into the gateway with no owning application has no ANF, so no control
    set, so nothing measuring it.
    """
    return list(
        db.execute(
            select(AiSystem).where(
                AiSystem.tenant_id == tenant_id,
                AiSystem.application_id.is_(None),
                AiSystem.status == "active",
            )
        ).scalars()
    )
