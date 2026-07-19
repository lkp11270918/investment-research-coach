from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class UserMode(str, Enum):
    TO_C = "to_c"
    TO_B = "to_b"


class Language(str, Enum):
    ZH = "zh"
    EN = "en"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentStatus(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


class EvidenceCategory(str, Enum):
    FACT = "fact"
    FINANCIAL_FACT = "financial_fact"
    MANAGEMENT_OPINION = "management_opinion"
    SELL_SIDE_OPINION = "sell_side_opinion"
    NEWS_OR_MARKET_OPINION = "news_or_market_opinion"
    USER_OPINION = "user_opinion"
    ASSUMPTION = "assumption"
    AI_REASONING = "ai_reasoning"
    RISK = "risk"
    VERIFICATION_QUESTION = "verification_question"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    TO_BE_VERIFIED = "to_be_verified"


class EvidenceRelation(str, Enum):
    FROM_SOURCE = "from_source"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    DUPLICATES = "duplicates"
    MENTIONS = "mentions"


class EvidenceGraphNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    evidence_id: str | None = None
    source_id: str | None = None
    confidence: Confidence = Confidence.LOW
    verification_status: VerificationStatus = VerificationStatus.TO_BE_VERIFIED
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: f"EDGE-{uuid4().hex[:10]}")
    from_node_id: str
    to_node_id: str
    relation: EvidenceRelation
    rationale: str | None = None
    confidence: Confidence = Confidence.LOW


class EvidenceGraph(BaseModel):
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceNodeReview(BaseModel):
    verification_status: VerificationStatus
    note: str | None = None


class ResearchQuestionStatus(str, Enum):
    UNANSWERED = "unanswered"
    PARTIAL = "partial"
    ANSWERED = "answered"
    CONFLICTED = "conflicted"


class ResearchQuestion(BaseModel):
    question_id: str
    category: str
    question: str
    priority: int = 2
    status: ResearchQuestionStatus = ResearchQuestionStatus.UNANSWERED
    evidence_ids: list[str] = Field(default_factory=list)
    missing_materials: list[str] = Field(default_factory=list)


class ResearchMap(BaseModel):
    project_id: str
    industry: str
    questions: list[ResearchQuestion] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    completion_rate: float = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThesisVariable(BaseModel):
    name: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class ThesisDraft(BaseModel):
    core_view: str
    core_variables: list[ThesisVariable] = Field(default_factory=list, max_length=3)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    user_internal_label: str | None = None


class ThesisAssessment(BaseModel):
    status: AgentStatus
    issues: list[str] = Field(default_factory=list)
    evidence_coverage: float = 0
    sell_side_repetition_risk: bool = False
    confidence: Confidence = Confidence.LOW


class ThesisVersion(BaseModel):
    thesis_id: str = Field(default_factory=lambda: f"THESIS-{uuid4().hex[:10]}")
    project_id: str
    version: int
    draft: ThesisDraft
    assessment: ThesisAssessment
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DefenseRole(str, Enum):
    PORTFOLIO_MANAGER = "portfolio_manager"
    INDUSTRY_RESEARCHER = "industry_researcher"
    FINANCIAL_RESEARCHER = "financial_researcher"
    RISK_MANAGER = "risk_manager"


class DefenseTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: f"TURN-{uuid4().hex[:10]}")
    role: DefenseRole
    question: str
    thesis_reference: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    answer_evidence_ids: list[str] = Field(default_factory=list)
    score: float | None = None
    feedback: str | None = None
    passed: bool | None = None


class DefenseSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"DEF-{uuid4().hex[:10]}")
    project_id: str
    thesis_id: str
    status: str = "active"
    turns: list[DefenseTurn] = Field(default_factory=list)
    overall_score: float | None = None
    improvement_tasks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DefenseAnswerRequest(BaseModel):
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class CapabilityDimension(BaseModel):
    dimension: str
    score: float
    evidence: list[str] = Field(default_factory=list)
    repeated_errors: list[str] = Field(default_factory=list)


class CapabilityProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: f"PROFILE-{uuid4().hex[:10]}")
    user_id: str
    dimensions: list[CapabilityDimension]
    strengths: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    recommended_tasks: list[str] = Field(default_factory=list)
    sample_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceType(str, Enum):
    FINANCIAL_TABLE = "financial_table"
    ANNUAL_REPORT_SUMMARY = "annual_report_summary"
    ANNOUNCEMENT_EXCERPT = "announcement_excerpt"
    MANAGEMENT_NOTE = "management_note"
    SELL_SIDE_SUMMARY = "sell_side_summary"
    NEWS_SUMMARY = "news_summary"
    INDUSTRY_MATERIAL = "industry_material"
    USER_NOTE = "user_note"
    INSTITUTION_DOCTRINE = "institution_doctrine"
    HISTORICAL_MEMO = "historical_memo"
    FAILED_CASE = "failed_case"
    MEMO_TEMPLATE = "memo_template"
    OTHER = "other"


class MaterialModality(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    AUDIO = "audio"


class ContentBlock(BaseModel):
    block_id: str = Field(default_factory=lambda: f"BLK-{uuid4().hex[:10]}")
    modality: MaterialModality
    content: str
    page: int | None = None
    paragraph: int | None = None
    sheet: str | None = None
    row: int | None = None
    region: dict[str, float] | None = None
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    extraction_method: str = "deterministic"
    requires_confirmation: bool = False


class WorkflowStopAfter(str, Enum):
    DOCTRINE = "firm_doctrine_case_retrieval"
    MATERIAL_ORGANIZER = "material_organizer"
    EVIDENCE_EXTRACTOR = "evidence_extractor"
    FINANCIAL_QUALITY = "financial_quality_dividend"
    BUSINESS_MODEL = "business_model_moat"
    MANAGEMENT_VIEW = "management_view_comparison"
    VALUE_TRAP = "value_trap_contradiction"
    PRE_MEMO_GATE = "pre_memo_gate"
    MEMO = "research_memo_generator"
    POST_MEMO_GATE = "post_memo_gate"


class WorkflowOptions(BaseModel):
    stop_after: WorkflowStopAfter | None = None
    skip_post_gate: bool = False
    enable_parallel: bool = True


class AuthUser(BaseModel):
    user_id: str
    email: str
    name: str | None = None
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class CompanyProfile(BaseModel):
    ticker: str | None = None
    company_name: str
    industry: str
    market: str | None = None
    research_language: Language = Language.ZH
    user_mode: UserMode = UserMode.TO_C
    institution_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawMaterial(BaseModel):
    title: str
    content: str
    source_type: SourceType = SourceType.OTHER
    file_name: str | None = None
    url: str | None = None
    usage_rights_confirmed: bool | None = None
    period_covered: str | None = None
    modality: MaterialModality = MaterialModality.TEXT
    blocks: list[ContentBlock] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class SourceDocument(BaseModel):
    source_id: str = Field(default_factory=lambda: f"SRC-{uuid4().hex[:8]}")
    title: str
    source_type: SourceType
    file_name: str | None = None
    url: str | None = None
    provided_by_user: bool = True
    usage_rights_confirmed: bool | None = None
    period_covered: str | None = None
    reliability_note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: str = ""
    modality: MaterialModality = MaterialModality.TEXT
    blocks: list[ContentBlock] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class SourceRef(BaseModel):
    source_id: str
    excerpt: str | None = None
    page: str | None = None
    paragraph_id: str | None = None
    row_id: str | None = None
    url: str | None = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"EV-{uuid4().hex[:8]}")
    category: EvidenceCategory
    statement: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    period: str | None = None
    metric_name: str | None = None
    metric_value: float | str | None = None
    unit: str | None = None
    confidence: Confidence = Confidence.LOW
    verification_status: VerificationStatus = VerificationStatus.TO_BE_VERIFIED
    notes: str | None = None


class AgentFinding(BaseModel):
    title: str
    detail: str
    classification: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.LOW


class AgentOutput(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.PARTIAL
    summary: str
    findings: list[AgentFinding] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_materials: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.LOW
    warnings: list[str] = Field(default_factory=list)


class DowngradedClaim(BaseModel):
    original_claim: str
    downgraded_expression: str
    reason: str | None = None


class ComplianceGateOutput(BaseModel):
    gate_name: str
    status: str
    unsupported_claims: list[str] = Field(default_factory=list)
    evidence_issues: list[str] = Field(default_factory=list)
    downgraded_claims: list[DowngradedClaim] = Field(default_factory=list)
    compliance_warnings: list[str] = Field(default_factory=list)
    rewrite_suggestions: list[str] = Field(default_factory=list)


class MemoSection(BaseModel):
    section_id: str
    title: str
    body: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.LOW


class ResearchMemo(BaseModel):
    memo_id: str = Field(default_factory=lambda: f"MEMO-{uuid4().hex[:8]}")
    company_profile: CompanyProfile
    user_mode: UserMode
    confidence: Confidence = Confidence.LOW
    sections: list[MemoSection]
    source_ids: list[str] = Field(default_factory=list)
    disclaimer: str
    markdown: str | None = None


class AnalyzeRequest(BaseModel):
    project_id: str | None = None
    company_profile: CompanyProfile
    materials: list[RawMaterial] = Field(default_factory=list)
    options: WorkflowOptions = Field(default_factory=WorkflowOptions)


class ReviewRequest(BaseModel):
    project_id: str | None = None
    company_profile: CompanyProfile | None = None
    memo_text: str
    materials: list[RawMaterial] = Field(default_factory=list)


class WorkflowState(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid4().hex[:10]}")
    company_profile: CompanyProfile
    raw_materials: list[RawMaterial] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    pre_memo_gate: ComplianceGateOutput | None = None
    post_memo_gate: ComplianceGateOutput | None = None
    memo: ResearchMemo | None = None
    workflow_status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def evidence_by_category(self, *categories: EvidenceCategory) -> list[EvidenceItem]:
        allowed = set(categories)
        return [item for item in self.evidence_items if item.category in allowed]


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str
    state: WorkflowState


class ResearchRunSummary(BaseModel):
    run_id: str
    run_type: str
    company_name: str
    ticker: str | None = None
    industry: str | None = None
    memo_confidence: Confidence | None = None
    material_count: int = 0
    evidence_count: int = 0
    created_at: datetime


class ResearchProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ResearchProjectCreate(BaseModel):
    company_profile: CompanyProfile
    research_objective: str | None = None
    investment_horizon: str | None = None
    initial_view: str | None = None
    key_question: str | None = None


class ResearchProjectUpdate(BaseModel):
    company_profile: CompanyProfile | None = None
    research_objective: str | None = None
    investment_horizon: str | None = None
    initial_view: str | None = None
    key_question: str | None = None
    status: ResearchProjectStatus | None = None


class ResearchProjectSummary(BaseModel):
    project_id: str
    company_profile: CompanyProfile
    research_objective: str | None = None
    investment_horizon: str | None = None
    initial_view: str | None = None
    key_question: str | None = None
    status: ResearchProjectStatus = ResearchProjectStatus.ACTIVE
    run_count: int = 0
    created_at: datetime
    updated_at: datetime


class ResearchProjectDetail(BaseModel):
    project: ResearchProjectSummary
    timeline: list[ResearchRunSummary] = Field(default_factory=list)


class ResearchRunDetail(BaseModel):
    summary: ResearchRunSummary
    state: WorkflowState


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "value-investing-research-coach"
    version: str = "0.1.0"


JsonDict = dict[str, Any]
