"""Idempotent seeding of reference data and the first tenant.

Running this twice changes nothing. It creates:

  * the default tenant and a bootstrap administrator
  * the permission catalogue, the eleven default roles and their permissions
  * the segregation-of-duties constraints and the gate-authority map
  * the three compliance frameworks and their controls, plus cross-mappings
  * starter workflows for the risk, compliance and privacy journeys
  * default LLM routes and a global budget policy (no provider — the
    administrator adds that with their own credential)

Reference data is deliberately part of the code, not something a user edits,
so an environment is reproducible from migrations plus seeds alone.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.base import (
    ActorType,
    AutomationLevel,
    AutonomyTier,
    GateReason,
    utcnow,
)
from app.models.compliance import ControlMapping, Framework, FrameworkControl
from app.models.core import Activity, Workflow
from app.models.iam import (
    AgentIdentity,
    GateAuthority,
    Permission,
    Role,
    RoleGrant,
    RolePermission,
    SodConstraint,
    Tenant,
    UserAccount,
)
from app.models.llm import LlmPolicy, PromptTemplate
from app.seed.catalogue import CONTROL_MAPPINGS, CONTROLS_BY_FRAMEWORK, FRAMEWORKS
from app.seed.prompts import PROMPTS
from app.seed.workflows import WORKFLOWS
from app.security.auth import hash_password

log = logging.getLogger(__name__)
_settings = get_settings()

# --------------------------------------------------------------------------
# Permission catalogue (Admin & RBAC design, Appendix A)
# --------------------------------------------------------------------------
PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("wf.execute", "Run workflows", "Workflow", "Run and operate workflow instances."),
    ("wf.author", "Author workflows", "Workflow", "Create and edit workflow definitions."),
    ("wf.deploy.approve", "Approve deployment", "Workflow",
     "Approve deployment of a new or changed workflow."),
    ("gate.privacy.approve", "Approve privacy gates", "Gate",
     "Decide subject-request release, breach notification, lawful basis and regulator contact."),
    ("gate.access.approve", "Approve access gates", "Gate",
     "Approve access grants, recertification and leaver exceptions."),
    ("gate.change.approve", "Approve change gates", "Gate",
     "Approve change go/no-go and implementation."),
    ("gate.risk.approve", "Accept residual risk", "Gate", "Accept residual risk."),
    ("gate.supplier.approve", "Approve supplier gates", "Gate",
     "Approve supplier engagement and contract execution."),
    ("gate.resilience.approve", "Approve continuity gates", "Gate",
     "Approve BIA outputs, continuity plans and live failover."),
    ("gate.golive.approve", "Approve go-live", "Gate", "Approve security-by-design go-live."),
    ("gate.config.approve", "Approve configuration change", "Gate",
     "Second-approve a production LLM configuration change."),
    ("gate.rbac.approve", "Approve access-model change", "Gate",
     "Second-approve a high-privilege role or permission change."),
    ("risk.manage", "Manage the risk register", "Risk", "Score, treat and age risks."),
    ("compliance.manage", "Manage compliance", "Compliance",
     "Maintain control implementations, gaps and programmes."),
    ("compliance.attest", "Attest control status", "Compliance",
     "Attest that a control is implemented and operating."),
    ("audit.conduct", "Conduct audits", "Audit", "Conduct audits and control tests."),
    ("audit.validate", "Validate findings", "Audit", "Independently validate audit findings."),
    ("data.register.read", "Read registers", "Data", "Read domain register records."),
    ("data.register.write", "Write registers", "Data", "Create and edit register records."),
    ("data.pii.read", "Read personal data", "Data",
     "Access restricted personal data, scoped by lawful basis."),
    ("evidence.write", "Add evidence", "Data", "Attach evidence to controls and runs."),
    ("integration.manage", "Manage integrations", "Integration",
     "Configure outbound connections such as Brata, and run syncs."),
    ("admin.llm.manage", "Manage LLM configuration", "Admin",
     "Configure providers, models, routing and policies."),
    ("admin.llm.view", "View LLM configuration", "Admin",
     "View LLM configuration and spend without changing it."),
    ("admin.rbac.manage", "Manage access model", "Admin",
     "Manage roles, permissions and grants."),
    ("admin.guardrail.manage", "Manage guardrails", "Admin",
     "Manage guardrail and policy definitions."),
    ("admin.tenant.manage", "Manage tenant", "Admin",
     "Manage tenant settings and webhook subscriptions."),
    ("sec.identity.manage", "Manage identities", "Security",
     "Manage user and agent identities."),
    ("sec.auditlog.read", "Read the audit log", "Security",
     "Read and verify the immutable audit log."),
    ("rpt.dashboard.view", "View dashboards", "Reporting", "View dashboards and reports."),
]

# role name -> (description, is_system, agent_eligible, permission codes)
ROLES: dict[str, tuple[str, bool, bool, list[str]]] = {
    "Platform Admin": (
        "Configures the platform. Holds no business gate authority: configures, does not decide.",
        True, False,
        ["admin.llm.manage", "admin.guardrail.manage", "admin.tenant.manage",
         "integration.manage", "rpt.dashboard.view", "data.register.read"],
    ),
    "Security Admin": (
        "Manages identities, the access model and the audit log.",
        True, False,
        ["admin.rbac.manage", "sec.identity.manage", "sec.auditlog.read", "admin.llm.view",
         "gate.access.approve", "gate.rbac.approve", "gate.config.approve",
         "rpt.dashboard.view", "data.register.read"],
    ),
    "DPO": (
        "Privacy authority: approves subject-request release, breach notification, "
        "lawful basis, regulator contact and policy publication.",
        True, False,
        ["gate.privacy.approve", "gate.change.approve", "gate.supplier.approve",
         "data.pii.read", "wf.author", "wf.deploy.approve", "compliance.manage",
         "compliance.attest", "data.register.read", "data.register.write",
         "evidence.write", "rpt.dashboard.view", "sec.auditlog.read", "wf.execute"],
    ),
    "CISO": (
        "Security oversight: go-live approval, high residual risk acceptance and guardrails.",
        True, False,
        ["gate.golive.approve", "gate.risk.approve", "gate.access.approve",
         "gate.config.approve", "admin.guardrail.manage", "wf.author",
         "wf.deploy.approve", "compliance.manage", "compliance.attest", "risk.manage",
         "data.register.read", "data.pii.read", "evidence.write", "sec.auditlog.read",
         "rpt.dashboard.view", "wf.execute"],
    ),
    "Risk Officer": (
        "Second line. Owns the risk register and residual-risk acceptance.",
        False, False,
        ["risk.manage", "gate.risk.approve", "compliance.manage", "data.register.read",
         "data.register.write", "evidence.write", "rpt.dashboard.view", "wf.execute"],
    ),
    "Internal Auditor": (
        "Third line. Independent testing and validation; read-only elsewhere.",
        False, False,
        ["audit.conduct", "audit.validate", "sec.auditlog.read", "data.register.read",
         "rpt.dashboard.view", "evidence.write"],
    ),
    "Control Owner": (
        "Approves domain actions and owns register data for their area.",
        False, False,
        ["gate.access.approve", "gate.change.approve", "gate.supplier.approve",
         "gate.resilience.approve", "compliance.manage", "compliance.attest",
         "data.register.read", "data.register.write", "evidence.write", "wf.execute",
         "rpt.dashboard.view"],
    ),
    "Operator": (
        "First line. Runs workflows and maintains register data.",
        False, False,
        ["wf.execute", "data.register.read", "data.register.write", "evidence.write",
         "rpt.dashboard.view"],
    ),
    "Business Requestor": (
        "Raises requests and reads their own records.",
        False, False,
        ["wf.execute", "data.register.read"],
    ),
    "AI Agent": (
        "Service principal that executes activities and drafts assessments. "
        "Never holds gate authority: accountability stays with a person.",
        True, True,
        ["wf.execute", "wf.author", "data.register.read", "data.register.write",
         "risk.manage", "compliance.manage", "audit.conduct", "evidence.write"],
    ),
    "Read-only": (
        "Dashboards and read access only.",
        False, False,
        ["rpt.dashboard.view", "data.register.read"],
    ),
}

SOD_PAIRS: list[tuple[str, str, str]] = [
    ("Internal Auditor", "Operator",
     "Auditor independence: the third line cannot operate the controls it tests."),
    ("Internal Auditor", "Control Owner",
     "Auditor independence: the third line cannot own the controls it tests."),
    ("Platform Admin", "DPO",
     "Configuration administration is separated from privacy decision authority."),
    ("Platform Admin", "CISO",
     "Configuration administration is separated from security approval authority."),
    ("Security Admin", "Operator",
     "Whoever provisions access cannot also be an ordinary consumer of it."),
    ("Risk Officer", "Operator",
     "Whoever assesses a risk cannot also be the first line accepting it in practice."),
]

GATE_AUTHORITY: list[tuple[str, str]] = [
    ("privacy.dsar_release", "DPO"),
    ("privacy.breach_notify", "DPO"),
    ("privacy.lawful_basis", "DPO"),
    ("privacy.regulator_contact", "DPO"),
    ("privacy.dpia_decision", "DPO"),
    ("access.privileged_grant", "Security Admin"),
    ("access.recertification", "Security Admin"),
    ("access.leaver_exception", "Security Admin"),
    ("change.go_no_go", "DPO"),
    ("change.implementation", "Control Owner"),
    ("risk.residual_acceptance", "Risk Officer"),
    ("risk.residual_acceptance", "CISO"),
    ("risk.approve", "Risk Officer"),
    ("supplier.engagement", "Control Owner"),
    ("supplier.contract", "DPO"),
    ("golive.security_by_design", "CISO"),
    ("resilience.bia_signoff", "Control Owner"),
    ("resilience.plan_approval", "Control Owner"),
    ("resilience.live_failover", "CISO"),
    ("workflow.deployment", "DPO"),
    ("workflow.deployment", "CISO"),
    ("config.llm_activation", "Security Admin"),
    ("config.llm_activation", "CISO"),
    ("rbac.high_privilege", "Security Admin"),
]

DEFAULT_ROUTES: list[tuple[str, str, str]] = [
    ("default", "General reasoning where no specific route applies.", "balanced"),
    ("control_assessment", "Assess a control implementation against its requirement.", "deep"),
    ("gap_analysis", "Identify shortfalls and draft remediation.", "deep"),
    ("risk_drafting", "Draft a risk statement, threat and vulnerability.", "balanced"),
    ("evidence_summary", "Summarise an evidence artefact for a reviewer.", "cheap"),
    ("policy_drafting", "Draft or revise a policy or procedure.", "deep"),
    ("supplier_assessment", "Score a supplier questionnaire response.", "balanced"),
    ("classification", "Classify or triage a record into a category.", "cheap"),
    ("bia_drafting", "Draft business impact analysis outputs.", "balanced"),
    ("dpia_drafting", "Draft a data protection impact assessment.", "deep"),
]


def _upsert_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.execute(select(Permission)).scalars().all()}
    for code, name, category, description in PERMISSIONS:
        if code in existing:
            continue
        p = Permission(code=code, name=name, category=category, description=description)
        db.add(p)
        existing[code] = p
    db.flush()
    return existing


def _upsert_roles(db: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    roles = {r.name: r for r in db.execute(select(Role)).scalars().all()}
    for name, (description, is_system, agent_eligible, codes) in ROLES.items():
        role = roles.get(name)
        if role is None:
            role = Role(
                name=name,
                description=description,
                is_system=is_system,
                agent_eligible=agent_eligible,
                created_at=utcnow(),
            )
            db.add(role)
            db.flush()
            roles[name] = role
        held = {
            rp.permission_id
            for rp in db.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).scalars().all()
        }
        for code in codes:
            perm = permissions.get(code)
            if perm and perm.id not in held:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id, scope="all"))
    db.flush()
    return roles


def _upsert_sod(db: Session, roles: dict[str, Role]) -> None:
    for a, b, reason in SOD_PAIRS:
        ra, rb = roles.get(a), roles.get(b)
        if not ra or not rb:
            continue
        exists = db.execute(
            select(SodConstraint).where(
                SodConstraint.role_a_id == ra.id, SodConstraint.role_b_id == rb.id
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                SodConstraint(
                    role_a_id=ra.id, role_b_id=rb.id,
                    rule="mutually_exclusive", reason=reason, created_at=utcnow(),
                )
            )
    db.flush()


def _upsert_gate_authority(db: Session, roles: dict[str, Role]) -> None:
    for gate_type, role_name in GATE_AUTHORITY:
        role = roles.get(role_name)
        if not role:
            continue
        exists = db.execute(
            select(GateAuthority).where(
                GateAuthority.gate_type == gate_type, GateAuthority.role_id == role.id
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(GateAuthority(gate_type=gate_type, role_id=role.id))
    db.flush()


def _upsert_frameworks(db: Session) -> dict[str, Framework]:
    frameworks: dict[str, Framework] = {
        f.code: f for f in db.execute(select(Framework)).scalars().all()
    }
    for spec in FRAMEWORKS:
        fw = frameworks.get(spec["code"])
        if fw is None:
            fw = Framework(**spec)
            db.add(fw)
            db.flush()
            frameworks[spec["code"]] = fw
        existing_refs = {
            c.ref_code
            for c in db.execute(
                select(FrameworkControl).where(FrameworkControl.framework_id == fw.id)
            ).scalars().all()
        }
        for control in CONTROLS_BY_FRAMEWORK[spec["code"]]():
            if control["ref_code"] in existing_refs:
                continue
            db.add(FrameworkControl(framework_id=fw.id, **control))
    db.flush()
    return frameworks


def _upsert_mappings(db: Session, frameworks: dict[str, Framework]) -> None:
    def control_id(fw_code: str, ref: str) -> uuid.UUID | None:
        fw = frameworks.get(fw_code)
        if not fw:
            return None
        return db.execute(
            select(FrameworkControl.id).where(
                FrameworkControl.framework_id == fw.id, FrameworkControl.ref_code == ref
            )
        ).scalar_one_or_none()

    for src_fw, src_ref, tgt_fw, tgt_ref in CONTROL_MAPPINGS:
        sid, tid = control_id(src_fw, src_ref), control_id(tgt_fw, tgt_ref)
        if not sid or not tid:
            continue
        exists = db.execute(
            select(ControlMapping).where(
                ControlMapping.source_control_id == sid,
                ControlMapping.target_control_id == tid,
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                ControlMapping(
                    source_control_id=sid, target_control_id=tid,
                    relationship_type="equivalent",
                )
            )
    db.flush()


def _upsert_workflows(db: Session, tenant: Tenant, roles: dict[str, Role]) -> None:
    for spec in WORKFLOWS:
        exists = db.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant.id, Workflow.wf_code == spec["wf_code"]
            )
        ).scalar_one_or_none()
        if exists:
            continue
        owner = roles.get(spec.get("owner_role", "Control Owner"))
        wf = Workflow(
            tenant_id=tenant.id,
            wf_code=spec["wf_code"],
            name=spec["name"],
            family=spec["family"],
            pillars=spec["pillars"],
            autonomy_tier=AutonomyTier(spec.get("tier", "L3")),
            owner_role_id=owner.id if owner else None,
            version=1,
            status="active",
            definition={"activities": spec["activities"]},
            created_at=utcnow(),
        )
        db.add(wf)
        db.flush()
        for i, act in enumerate(spec["activities"], start=1):
            accountable = roles.get(act.get("accountable_role", "Control Owner"))
            db.add(
                Activity(
                    workflow_id=wf.id,
                    seq=i,
                    act_code=act["code"],
                    what=act["what"],
                    who_responsible={"actor": act.get("responsible", "agent")},
                    who_accountable_role_id=accountable.id if accountable else None,
                    when_trigger=act.get("trigger", "sequence"),
                    input_refs={"inputs": act.get("inputs", [])},
                    output_refs={"outputs": act.get("outputs", [])},
                    ai_role=act.get("ai_role"),
                    task_class=act.get("task_class"),
                    automation=AutomationLevel(act.get("automation", "auto")),
                    control_ref=act.get("control"),
                    is_gate=act.get("automation") == "gate",
                    gate_type=act.get("gate_type"),
                    gate_reason=GateReason(act["gate_reason"])
                    if act.get("gate_reason")
                    else None,
                )
            )
    db.flush()


def _upsert_prompts(db: Session, tenant: Tenant) -> None:
    for spec in PROMPTS:
        exists = db.execute(
            select(PromptTemplate).where(
                PromptTemplate.tenant_id == tenant.id,
                PromptTemplate.name == spec["name"],
                PromptTemplate.version == 1,
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            PromptTemplate(
                tenant_id=tenant.id,
                name=spec["name"],
                version=1,
                task_class=spec["task_class"],
                cache_prefix=spec.get("cache_prefix"),
                template=spec["template"],
                output_schema=spec.get("output_schema"),
                is_active=True,
                created_at=utcnow(),
            )
        )
    db.flush()


def _upsert_policy(db: Session, tenant: Tenant) -> None:
    exists = db.execute(
        select(LlmPolicy).where(
            LlmPolicy.tenant_id == tenant.id,
            LlmPolicy.scope == "global",
            LlmPolicy.scope_ref.is_(None),
        )
    ).scalar_one_or_none()
    if exists:
        return
    db.add(
        LlmPolicy(
            tenant_id=tenant.id,
            scope="global",
            scope_ref=None,
            rate_rpm=120,
            token_budget_daily=2_000_000,
            cost_cap_monthly=500.00,
            alert_threshold=0.8,
            kill_switch=False,
            created_at=utcnow(),
        )
    )
    db.flush()


def run(db: Session) -> dict:
    """Seed everything. Returns a summary, including the bootstrap password if
    one was generated — it is shown once and never stored in clear."""
    tenant = db.execute(
        select(Tenant).where(Tenant.name == _settings.default_tenant_name)
    ).scalar_one_or_none()
    created_tenant = tenant is None
    if tenant is None:
        tenant = Tenant(
            name=_settings.default_tenant_name,
            region=_settings.default_tenant_region,
            status="active",
            created_at=utcnow(),
        )
        db.add(tenant)
        db.flush()

    permissions = _upsert_permissions(db)
    roles = _upsert_roles(db, permissions)
    _upsert_sod(db, roles)
    _upsert_gate_authority(db, roles)
    # The catalogue lives in ``ref``, which the serving credential may only
    # read. Seed it on the owning credential, then re-read it here so the rest
    # of the seeder works with rows visible to the session it is running in.
    from app.db import owner_session_scope

    with owner_session_scope() as owner:
        owned = _upsert_frameworks(owner)
        _upsert_mappings(owner, owned)
        # The application security life cycle reference model is reference data
        # too, so it rides the same credential.
        from app.seed.onf_loader import load_reference

        reference_summary = load_reference(owner)
    frameworks = {f.code: f for f in db.execute(select(Framework)).scalars().all()}
    # The process repository supersedes the starter workflows: 36 processes
    # across ten domains, loaded from app.processes, which is the specification
    # the engine executes rather than a document describing it.
    from app.seed.repository import load as load_repository

    repository_summary = load_repository(db, tenant)
    _upsert_prompts(db, tenant)
    _upsert_policy(db, tenant)

    # The Organization Normative Framework and its ASC library. Loaded after the
    # frameworks so an ASC can cite a control reference that exists.
    from app.seed.onf_loader import load_onf

    onf_summary = load_onf(db, tenant)

    # Bootstrap administrator ------------------------------------------------
    generated_password: str | None = None
    admin = db.execute(
        select(UserAccount).where(
            UserAccount.tenant_id == tenant.id,
            UserAccount.email == _settings.bootstrap_admin_email,
        )
    ).scalar_one_or_none()
    if admin is None:
        password = _settings.bootstrap_admin_password or secrets.token_urlsafe(18)
        generated_password = None if _settings.bootstrap_admin_password else password
        admin = UserAccount(
            tenant_id=tenant.id,
            email=_settings.bootstrap_admin_email,
            display_name="Bootstrap Administrator",
            status="active",
            password_hash=hash_password(password),
            created_at=utcnow(),
        )
        db.add(admin)
        db.flush()
        # The bootstrap account gets platform and security administration only.
        # It deliberately holds no business gate authority.
        for role_name in ("Platform Admin", "Security Admin"):
            role = roles[role_name]
            db.add(
                RoleGrant(
                    tenant_id=tenant.id,
                    principal_id=admin.id,
                    principal_type=ActorType.HUMAN,
                    role_id=role.id,
                    scope="all",
                    granted_by=admin.id,
                    granted_at=utcnow(),
                    justification="Bootstrap administrator created by the seeder.",
                )
            )

    # Agent principals come from the registry, each with its own scoped role.
    # A single broad agent role would give the privacy agent the reach of the
    # audit agent, which defeats the point of scoping them at all.

    return {
        **repository_summary,
        **reference_summary,
        **onf_summary,
        "tenant_id": str(tenant.id),
        "tenant_created": created_tenant,
        "permissions": len(permissions),
        "roles": len(roles),
        "frameworks": len(frameworks),
        "controls": db.execute(select(FrameworkControl)).scalars().all().__len__(),
        "admin_email": admin.email,
        "generated_password": generated_password,
    }
