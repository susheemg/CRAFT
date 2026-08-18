"""Loads the Organization Normative Framework into the database.

Split from ``app.seed.appsec`` for the same reason the process repository is
split from its loader: the data is the specification and should be readable
without knowing anything about SQLAlchemy.

Two loaders, deliberately separate:

``load_reference`` writes ``ref.aslcrm_stage`` and ``ref.aslcrm_layer``. It runs
on the *owning* credential because ``ref`` is read-only to the application.

``load_onf`` writes the tenant's ONF iteration, contexts, trust levels, life
cycle mapping and ASC library. It runs on the application credential inside the
seeder's bypass window, like every other tenant-scoped seed.

Both are idempotent: re-running updates in place rather than duplicating, so a
redeploy does not accumulate ONF iterations.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appsec import (
    Asc,
    AscTrustLevel,
    AslcrmLayer,
    AslcrmStage,
    LifecycleStageMap,
    Onf,
    OnfContext,
    TrustLevel,
)
from app.models.base import utcnow
from app.models.iam import Tenant
from app.seed.appsec import (
    ASC_LIBRARY,
    ASLCRM_LAYERS,
    ASLCRM_STAGES,
    LIFECYCLE_MAP,
    LIFECYCLE_MODEL_NAME,
    ONF_CONTEXTS,
    ONF_SPEC,
    SOURCE_NOTE,
    TRUST_LEVELS,
)

log = logging.getLogger(__name__)


def load_reference(db: Session) -> dict:
    """Seed the Application Security Life Cycle Reference Model.

    Must run on the schema-owning credential: ``ref`` is reference data shipped
    with the code and the serving role holds SELECT on it only.
    """
    layers = {row.code: row for row in db.execute(select(AslcrmLayer)).scalars()}
    for code, label, ordinal, description in ASLCRM_LAYERS:
        row = layers.get(code)
        if row is None:
            db.add(
                AslcrmLayer(
                    code=code, label=label, ordinal=ordinal,
                    description=description, source_note=SOURCE_NOTE,
                )
            )
        else:
            row.label, row.ordinal, row.description = label, ordinal, description

    stages = {row.code: row for row in db.execute(select(AslcrmStage)).scalars()}
    for code, label, phase, ordinal, description in ASLCRM_STAGES:
        row = stages.get(code)
        if row is None:
            db.add(
                AslcrmStage(
                    code=code, label=label, phase=phase, ordinal=ordinal,
                    description=description, source_note=SOURCE_NOTE,
                )
            )
        else:
            row.label, row.phase, row.ordinal, row.description = label, phase, ordinal, description

    db.flush()
    return {"aslcrm_layers": len(ASLCRM_LAYERS), "aslcrm_stages": len(ASLCRM_STAGES)}


def load_onf(db: Session, tenant: Tenant) -> dict:
    """Seed the tenant's ONF iteration and its ASC library."""
    onf = db.execute(
        select(Onf).where(
            Onf.tenant_id == tenant.id, Onf.iteration_no == ONF_SPEC["iteration_no"]
        )
    ).scalar_one_or_none()
    created_onf = onf is None
    if onf is None:
        onf = Onf(tenant_id=tenant.id, created_at=utcnow(), **ONF_SPEC)
        db.add(onf)
        db.flush()
    else:
        onf.name = ONF_SPEC["name"]
        onf.scope_statement = ONF_SPEC["scope_statement"]

    # Contexts ------------------------------------------------------------
    existing_contexts = {
        (c.context_type, c.code): c
        for c in db.execute(select(OnfContext).where(OnfContext.onf_id == onf.id)).scalars()
    }
    for context_type, code, label in ONF_CONTEXTS:
        row = existing_contexts.get((context_type, code))
        if row is None:
            db.add(
                OnfContext(
                    tenant_id=tenant.id, onf_id=onf.id, context_type=context_type,
                    code=code, label=label, created_at=utcnow(),
                )
            )
        else:
            row.label = label

    # Levels of trust -----------------------------------------------------
    levels: dict[int, TrustLevel] = {
        t.level_no: t
        for t in db.execute(select(TrustLevel).where(TrustLevel.onf_id == onf.id)).scalars()
    }
    for level_no, label, is_zero, description in TRUST_LEVELS:
        row = levels.get(level_no)
        if row is None:
            row = TrustLevel(
                tenant_id=tenant.id, onf_id=onf.id, level_no=level_no, label=label,
                is_level_zero=is_zero, description=description, created_at=utcnow(),
            )
            db.add(row)
            db.flush()
            levels[level_no] = row
        else:
            row.label, row.description, row.is_level_zero = label, description, is_zero

    # Life cycle mapping --------------------------------------------------
    mapped = {
        m.local_stage_code: m
        for m in db.execute(
            select(LifecycleStageMap).where(LifecycleStageMap.onf_id == onf.id)
        ).scalars()
    }
    for local_code, local_label, stage, layer in LIFECYCLE_MAP:
        row = mapped.get(local_code)
        if row is None:
            db.add(
                LifecycleStageMap(
                    tenant_id=tenant.id, onf_id=onf.id, model_name=LIFECYCLE_MODEL_NAME,
                    local_stage_code=local_code, local_stage_label=local_label,
                    aslcrm_stage_code=stage, aslcrm_layer_code=layer, created_at=utcnow(),
                )
            )
        else:
            row.local_stage_label = local_label
            row.aslcrm_stage_code = stage
            row.aslcrm_layer_code = layer

    # The ASC library -----------------------------------------------------
    existing_ascs = {
        a.asc_uid: a
        for a in db.execute(select(Asc).where(Asc.onf_id == onf.id)).scalars()
    }
    created_ascs = 0
    for spec in ASC_LIBRARY:
        row = existing_ascs.get(spec["asc_uid"])
        if row is None:
            row = Asc(
                tenant_id=tenant.id,
                onf_id=onf.id,
                asc_uid=spec["asc_uid"],
                label=spec["label"],
                aslcrm_stage_code=spec["stage"],
                aslcrm_layer_code=spec["layer"],
                activity_spec=spec["activity"],
                measurement_spec=spec["measurement"],
                automation_capability=spec["automation"],
                measurement_requires_human=spec["human_measurement"],
                control_refs=spec["control_refs"],
                status="approved",
                source_note=SOURCE_NOTE,
                created_at=utcnow(),
            )
            db.add(row)
            db.flush()
            created_ascs += 1
        else:
            # Keep the library in step with the shipped definition, but never
            # widen what an agent may attest to on its own: that field only
            # tightens here, and loosening it is a governed change.
            row.label = spec["label"]
            row.activity_spec = spec["activity"]
            row.measurement_spec = spec["measurement"]
            row.automation_capability = spec["automation"]
            row.control_refs = spec["control_refs"]
            if spec["human_measurement"]:
                row.measurement_requires_human = True

        for level_no in spec["levels"]:
            level = levels.get(level_no)
            if level is None:
                continue
            link = db.execute(
                select(AscTrustLevel).where(
                    AscTrustLevel.asc_id == row.id,
                    AscTrustLevel.trust_level_id == level.id,
                )
            ).scalar_one_or_none()
            if link is None:
                db.add(
                    AscTrustLevel(
                        tenant_id=tenant.id, asc_id=row.id, trust_level_id=level.id,
                        is_mandatory=True,
                    )
                )

    db.flush()
    log.info(
        "ONF loaded: iteration %s %s, %s ASCs (%s new)",
        onf.iteration_no,
        "created" if created_onf else "updated",
        len(ASC_LIBRARY),
        created_ascs,
    )
    return {
        "onf_iteration": onf.iteration_no,
        "onf_created": created_onf,
        "trust_levels": len(TRUST_LEVELS),
        "onf_contexts": len(ONF_CONTEXTS),
        "ascs": len(ASC_LIBRARY),
        "ascs_created": created_ascs,
    }
