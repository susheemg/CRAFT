"""Request and response contracts.

Every field is typed and constrained here rather than validated ad hoc in the
handlers, so the OpenAPI document is the contract of record and unknown fields
are rejected at the edge.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_email(value: str) -> str:
    """Deliberately permissive.

    Strict RFC validators reject reserved top-level domains such as .local and
    .internal, which is exactly what an on-premise GRC deployment uses for its
    internal accounts. Refusing to let an organisation sign in with its own
    internal address would be a validator enforcing a rule nobody asked for.
    """
    value = value.strip().lower()
    if not _EMAIL.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address")
    return value


# --------------------------------------------------------------------------
# Errors and envelopes
# --------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page(BaseModel):
    data: list[Any]
    next_cursor: Optional[str] = None
    total: Optional[int] = None


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
class LoginRequest(Strict):
    email: str
    password: str = Field(min_length=1, max_length=256)

    _check_email = field_validator("email")(classmethod(lambda cls, v: _valid_email(v)))


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    principal: dict


class RefreshRequest(Strict):
    refresh_token: str


class ApiTokenRequest(Strict):
    name: str = Field(min_length=3, max_length=120)
    principal_id: Optional[uuid.UUID] = None
    principal_type: Literal["human", "agent"] = "agent"
    scopes: list[str] = Field(default_factory=list)
    expires_days: int = Field(default=90, ge=1, le=730)


class ApiTokenResponse(BaseModel):
    id: uuid.UUID
    name: str
    token: str = Field(description="Shown once. Store it now; it cannot be retrieved again.")
    hint: str
    expires_at: Optional[datetime]


# --------------------------------------------------------------------------
# Risk
# --------------------------------------------------------------------------
class RiskCreate(Strict):
    title: str = Field(min_length=5, max_length=300)
    description: str = ""
    category: Literal[
        "information_security", "privacy", "continuity", "third_party",
        "operational", "regulatory",
    ] = "information_security"
    threat: str = ""
    vulnerability: str = ""
    inherent_likelihood: int = Field(default=3, ge=1, le=5)
    inherent_impact: int = Field(default=3, ge=1, le=5)
    residual_likelihood: Optional[int] = Field(default=None, ge=1, le=5)
    residual_impact: Optional[int] = Field(default=None, ge=1, le=5)
    treatment: Literal["mitigate", "transfer", "avoid", "accept"] = "mitigate"
    treatment_plan: str = ""
    owner_user_id: Optional[uuid.UUID] = None
    linked_controls: list[str] = Field(default_factory=list)
    review_days: int = Field(default=90, ge=1, le=1095)


class RiskRescore(Strict):
    residual_likelihood: int = Field(ge=1, le=5)
    residual_impact: int = Field(ge=1, le=5)
    note: str = ""


class RiskAccept(Strict):
    rationale: str = Field(min_length=20, max_length=4000)
    review_days: int = Field(default=180, ge=1, le=1095)


class RiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    risk_ref: str
    title: str
    description: Optional[str] = None
    category: str
    inherent_likelihood: int
    inherent_impact: int
    inherent_score: int
    residual_likelihood: Optional[int] = None
    residual_impact: Optional[int] = None
    residual_score: Optional[int] = None
    severity_band: str
    treatment: str
    treatment_plan: Optional[str] = None
    status: str
    owner_user_id: Optional[uuid.UUID] = None
    accepted_at: Optional[datetime] = None
    review_at: Optional[datetime] = None
    linked_controls: Optional[list] = None
    created_at: datetime

    @field_validator("severity_band", "treatment", "status", mode="before")
    @classmethod
    def _enum_value(cls, v):
        return getattr(v, "value", v)


# --------------------------------------------------------------------------
# Compliance
# --------------------------------------------------------------------------
class ProgrammeStart(Strict):
    framework: str = Field(min_length=2, max_length=40)
    scope_statement: str = ""
    target_date: Optional[date] = None
    owner_user_id: Optional[uuid.UUID] = None


class ProgrammePhase(Strict):
    phase: str


class ControlUpdate(Strict):
    is_applicable: Optional[bool] = None
    applicability_justification: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[
        Literal[
            "not_started", "planned", "in_progress", "implemented", "operating",
            "not_applicable",
        ]
    ] = None
    maturity: Optional[int] = Field(default=None, ge=0, le=5)
    how_implemented: Optional[str] = Field(default=None, max_length=8000)
    implementation_note: Optional[str] = Field(default=None, max_length=8000)
    owner_user_id: Optional[uuid.UUID] = None
    linked_policy_uri: Optional[str] = None
    review_in_days: Optional[int] = Field(default=None, ge=1, le=1095)


class ControlOut(BaseModel):
    id: uuid.UUID
    ref_code: str
    title: str
    section: str
    theme: Optional[str] = None
    control_type: str
    is_applicable: bool
    applicability_justification: Optional[str] = None
    status: str
    maturity: int
    how_implemented: Optional[str] = None
    evidence_count: int = 0
    open_gaps: int = 0
    next_review_at: Optional[datetime] = None


class GapCreate(Strict):
    control_implementation_id: uuid.UUID
    title: str = Field(min_length=5, max_length=300)
    description: str = ""
    severity: Literal["very_low", "low", "medium", "high", "very_high"] = "medium"
    source: Literal[
        "assessment", "internal_audit", "external_audit", "incident", "ai_review"
    ] = "assessment"
    remediation_plan: str = ""
    owner_user_id: Optional[uuid.UUID] = None
    due_days: int = Field(default=60, ge=1, le=730)


class GapClose(Strict):
    note: str = Field(min_length=10, max_length=4000)


class EvidenceCreate(Strict):
    kind: Literal[
        "document", "screenshot", "log", "attestation", "report", "export",
        "decision", "activity_output",
    ] = "document"
    title: str = Field(min_length=3, max_length=200)
    payload: Optional[dict] = None
    artifact_uri: Optional[str] = None
    subject_type: Optional[
        Literal["control_implementation", "risk", "supplier", "incident", "continuity_plan"]
    ] = None
    subject_id: Optional[uuid.UUID] = None
    valid_days: Optional[int] = Field(default=365, ge=1, le=3650)

    @field_validator("artifact_uri")
    @classmethod
    def _one_of(cls, v, info):
        if bool(v) == bool(info.data.get("payload")):
            raise ValueError("Provide exactly one of payload or artifact_uri")
        return v


# --------------------------------------------------------------------------
# Continuity (ISO 22301)
# --------------------------------------------------------------------------
class BiaCreate(Strict):
    activity_name: str = Field(min_length=3, max_length=200)
    business_function: str = ""
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    mtpd_hours: Optional[int] = Field(default=None, ge=1, le=8760)
    rto_hours: Optional[int] = Field(default=None, ge=0, le=8760)
    rpo_minutes: Optional[int] = Field(default=None, ge=0, le=525_600)
    mbco: str = ""
    impact_over_time: dict = Field(default_factory=dict)
    dependencies: dict = Field(default_factory=dict)

    @field_validator("rto_hours")
    @classmethod
    def _rto_within_mtpd(cls, v, info):
        mtpd = info.data.get("mtpd_hours")
        if v is not None and mtpd is not None and v > mtpd:
            raise ValueError(
                "The recovery time objective cannot exceed the maximum tolerable "
                "period of disruption — recovery must complete before the impact "
                "becomes intolerable."
            )
        return v


class ContinuityPlanCreate(Strict):
    name: str = Field(min_length=3, max_length=200)
    plan_type: Literal[
        "business_continuity", "disaster_recovery", "incident_response",
        "crisis_communication",
    ] = "business_continuity"
    scope: str = ""
    bia_id: Optional[uuid.UUID] = None
    rto_hours: Optional[int] = Field(default=None, ge=0, le=8760)
    rpo_minutes: Optional[int] = Field(default=None, ge=0, le=525_600)
    strategy: str = ""
    invocation_criteria: str = ""
    response_team: dict = Field(default_factory=dict)
    document_uri: Optional[str] = None


class ExerciseCreate(Strict):
    plan_id: uuid.UUID
    exercise_type: Literal[
        "tabletop", "walkthrough", "simulation", "technical_failover", "live"
    ] = "tabletop"
    scenario: str = ""
    performed_at: Optional[datetime] = None
    participants: dict = Field(default_factory=dict)
    rto_achieved_hours: Optional[float] = Field(default=None, ge=0)
    rpo_achieved_minutes: Optional[float] = Field(default=None, ge=0)
    objectives_met: Optional[bool] = None
    findings: dict = Field(default_factory=dict)
    report_uri: Optional[str] = None


# --------------------------------------------------------------------------
# Privacy
# --------------------------------------------------------------------------
class ProcessingRecordCreate(Strict):
    name: str = Field(min_length=3, max_length=200)
    business_function: str = ""
    purpose: str = Field(min_length=5, max_length=4000)
    lawful_basis: Literal[
        "consent", "contract", "legal_obligation", "vital_interests",
        "public_task", "legitimate_interests",
    ]
    special_category_basis: Optional[str] = None
    data_subjects: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    international_transfers: dict = Field(default_factory=dict)
    retention_rule: str = ""
    security_measures: str = ""
    dpia_required: bool = False


class DsarCreate(Strict):
    subject_ref: str = Field(min_length=1, max_length=120)
    request_type: Literal[
        "access", "rectification", "erasure", "restriction", "portability", "objection"
    ] = "access"
    received_at: Optional[datetime] = None
    notes: str = ""


class IncidentCreate(Strict):
    title: str = Field(min_length=5, max_length=300)
    description: str = ""
    incident_type: Literal[
        "security", "privacy", "availability", "third_party", "physical"
    ] = "security"
    severity: Literal["very_low", "low", "medium", "high", "very_high"] = "medium"
    involves_personal_data: bool = False
    detected_at: Optional[datetime] = None


# --------------------------------------------------------------------------
# Gates and runs
# --------------------------------------------------------------------------
class GateDecideRequest(Strict):
    decision: Literal["approved", "rejected"]
    rationale: str = Field(default="", max_length=4000)


class RunStartRequest(Strict):
    workflow_code: str = Field(min_length=2, max_length=10)
    context: dict = Field(default_factory=dict)
    subject_ref: Optional[str] = None
    sla_days: Optional[int] = Field(default=None, ge=1, le=365)


class RunAdvanceRequest(Strict):
    output: dict = Field(default_factory=dict)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


# --------------------------------------------------------------------------
# Admin: LLM configuration
# --------------------------------------------------------------------------
class ProviderCreate(Strict):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal[
        "anthropic", "openai", "azure_openai", "openai_compatible", "ollama",
        "google", "bedrock",
    ]
    base_url: Optional[str] = None
    region: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = Field(
        default=None,
        description="Sealed on receipt and never returned. Omit if using vault_ref.",
    )
    vault_ref: Optional[str] = Field(
        default=None, description="External secret reference, e.g. env:OPENAI_API_KEY"
    )
    extra_headers: dict = Field(default_factory=dict)
    is_default: bool = False


class ProviderUpdate(Strict):
    base_url: Optional[str] = None
    region: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    vault_ref: Optional[str] = None
    status: Optional[Literal["active", "disabled"]] = None
    is_default: Optional[bool] = None


class ProviderOut(BaseModel):
    """Note the absence of any credential field. Keys never leave the server."""

    id: uuid.UUID
    name: str
    kind: str
    base_url: Optional[str] = None
    region: Optional[str] = None
    status: str
    is_default: bool
    credential_hint: Optional[str] = None
    credential_source: str
    supports_prompt_cache: bool
    model_count: int = 0
    last_health_ok: Optional[bool] = None
    last_health_at: Optional[datetime] = None
    last_health_detail: Optional[str] = None


class ModelCreate(Strict):
    provider_id: uuid.UUID
    model_key: str = Field(min_length=1, max_length=120)
    display_name: Optional[str] = None
    capability: Literal["chat", "embedding", "classify", "vision"] = "chat"
    context_window: Optional[int] = Field(default=None, ge=1)
    max_output: Optional[int] = Field(default=None, ge=1)
    in_cost_per_1k: float = Field(default=0, ge=0)
    out_cost_per_1k: float = Field(default=0, ge=0)
    cache_write_cost_per_1k: float = Field(default=0, ge=0)
    cache_read_cost_per_1k: float = Field(default=0, ge=0)
    supports_native_cache: bool = False


class RouteUpsert(Strict):
    model_id: uuid.UUID
    fallback_model_ids: list[uuid.UUID] = Field(default_factory=list)
    description: str = ""
    environment: Literal["development", "test", "staging", "production"] = "production"
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=200_000)
    cache_enabled: bool = True
    cache_ttl_seconds: int = Field(default=86400, ge=60, le=2_592_000)
    system_prompt: Optional[str] = None
    is_active: bool = True


class PolicyUpsert(Strict):
    scope: Literal["global", "provider", "route"] = "global"
    scope_ref: Optional[uuid.UUID] = None
    rate_rpm: Optional[int] = Field(default=None, ge=1)
    token_budget_daily: Optional[int] = Field(default=None, ge=0)
    cost_cap_monthly: Optional[float] = Field(default=None, ge=0)
    alert_threshold: float = Field(default=0.8, ge=0, le=1)
    kill_switch: bool = False
    kill_switch_reason: Optional[str] = None


class CompletionRequest(Strict):
    """Ad-hoc governed completion, for testing a route from the console."""

    task_class: str = Field(default="default", max_length=60)
    prompt: str = Field(min_length=1, max_length=100_000)
    system: str = ""
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32_000)
    json_mode: bool = False


# --------------------------------------------------------------------------
# Admin: RBAC
# --------------------------------------------------------------------------
class RoleCreate(Strict):
    name: str = Field(min_length=2, max_length=80)
    description: str = ""
    parent_role_id: Optional[uuid.UUID] = None
    agent_eligible: bool = False
    permissions: list[str] = Field(default_factory=list)


class RoleGrantCreate(Strict):
    principal_id: uuid.UUID
    principal_type: Literal["human", "agent"]
    role_id: uuid.UUID
    scope: str = "all"
    expires_days: Optional[int] = Field(default=None, ge=1, le=730)
    is_break_glass: bool = False
    justification: str = Field(default="", max_length=2000)


class SodConstraintCreate(Strict):
    role_a_id: uuid.UUID
    role_b_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=1000)


class UserCreate(Strict):
    email: str
    display_name: str = Field(min_length=2, max_length=120)
    password: Optional[str] = Field(default=None, min_length=12, max_length=256)
    idp_subject: Optional[str] = None

    _check_email = field_validator("email")(classmethod(lambda cls, v: _valid_email(v)))


# --------------------------------------------------------------------------
# Integrations
# --------------------------------------------------------------------------
class ConnectionCreate(Strict):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["brata", "rest_generic", "mcp_generic"] = "brata"
    transport: Literal["rest", "mcp"] = "rest"
    base_url: str = Field(min_length=8, max_length=2000)
    auth_scheme: Literal[
        "bearer", "api_key_header", "oauth2_client_credentials", "none"
    ] = "bearer"
    auth_header_name: Optional[str] = None
    credential: Optional[str] = None
    vault_ref: Optional[str] = None
    oauth_token_url: Optional[str] = None
    oauth_scope: Optional[str] = None
    verify_tls: bool = True
    timeout_seconds: float = Field(default=30.0, ge=1, le=300)
    sync_config: dict = Field(default_factory=dict)


class ConnectionOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    transport: str
    base_url: str
    auth_scheme: str
    is_active: bool
    verify_tls: bool
    last_sync_at: Optional[datetime] = None
    last_health_ok: Optional[bool] = None
    last_health_detail: Optional[str] = None


class SyncRequest(Strict):
    operation: Literal["push_risks", "pull_risks"] = "pull_risks"
    limit: int = Field(default=100, ge=1, le=1000)


class McpToolCall(Strict):
    tool: str = Field(min_length=1, max_length=120)
    arguments: dict = Field(default_factory=dict)


class WebhookCreate(Strict):
    name: str = Field(min_length=2, max_length=120)
    url: str = Field(min_length=8, max_length=2000)
    topics: list[str] = Field(min_length=1)
    secret: Optional[str] = Field(default=None, min_length=16, max_length=256)
