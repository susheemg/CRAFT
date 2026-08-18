"""Model package. Importing this module registers every table on ``Base``."""

from app.models.base import (  # noqa: F401
    ActorType,
    AutomationLevel,
    AutonomyTier,
    Base,
    DataClass,
    GateDecision,
    GateReason,
    ImplementationStatus,
    IncidentStatus,
    Pillar,
    RiskStatus,
    RunStatus,
    Severity,
    TreatmentStrategy,
    utcnow,
)
from app.models.iam import (  # noqa: F401
    AgentIdentity,
    ApiToken,
    GateAuthority,
    Permission,
    Role,
    RoleGrant,
    RolePermission,
    SodConstraint,
    Tenant,
    UserAccount,
)
from app.models.core import (  # noqa: F401
    Activity,
    ActivityRun,
    ApprovalGate,
    EvidenceRecord,
    Run,
    Workflow,
)
from app.models.compliance import (  # noqa: F401
    ComplianceProgramme,
    ControlImplementation,
    ControlMapping,
    Framework,
    FrameworkControl,
    Gap,
    ReadinessSnapshot,
)
from app.models.domain import (  # noqa: F401
    Asset,
    Breach,
    BusinessImpactAnalysis,
    ContinuityExercise,
    ContinuityPlan,
    DsarRequest,
    Incident,
    ProcessingRecord,
    Risk,
    Supplier,
    SupplierAssessment,
)
from app.models.llm import (  # noqa: F401
    LlmConfigVersion,
    LlmModel,
    LlmPolicy,
    LlmProvider,
    LlmRoute,
    ModelInvocation,
    PromptCacheEntry,
    PromptTemplate,
)
from app.models.appsec import (  # noqa: F401
    Anf,
    AnfAsc,
    Application,
    Asc,
    AscEdge,
    AscEvidence,
    AscTrustLevel,
    AslcrmLayer,
    AslcrmStage,
    LifecycleStageMap,
    Onf,
    OnfCommitteeMember,
    OnfContext,
    SoaEntry,
    TrustLevel,
)
from app.models.aims import (  # noqa: F401
    AgentBudgetLedger,
    AgentCharter,
    AgentToolGrant,
    AiDataProvenance,
    AiImpactAssessment,
    AiIncidentLink,
    AiSystem,
    AiSystemResource,
    AiThirdParty,
)
from app.models.audit import (  # noqa: F401
    AuditChainCheck,
    AuditLog,
    ExternalConnection,
    IdempotencyKey,
    OutboxEvent,
    SyncLog,
    WebhookDelivery,
    WebhookSubscription,
)

SCHEMAS = ("iam", "ref", "core", "domain", "compliance", "config", "audit", "integ")
