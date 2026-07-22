from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
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


class ModelLayer(str, Enum):
    RULES = "rules"
    LIGHTWEIGHT_CLASSIFIER = "lightweight_classifier"
    SPECIALIZED_MODEL = "specialized_model"
    LARGE_MODEL = "large_model"
    EVIDENCE_GATE = "evidence_gate"


class ModelExecutionRecord(BaseModel):
    layer: ModelLayer
    component: str
    purpose: str
    deterministic: bool = False
    input_count: int = 0
    output_count: int = 0
    status: str = "completed"
    provider: str | None = None
    model_name: str | None = None
    latency_ms: int | None = None
    fallback_reason: str | None = None


class ModelUsageRecord(BaseModel):
    model_name: str
    endpoint: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0


class FinancialCalculationRecord(BaseModel):
    calculation_id: str = Field(default_factory=lambda: f"CALC-{uuid4().hex[:10]}")
    metric_name: str
    period: str | None = None
    value: float | None = None
    unit: str | None = None
    formula: str
    input_evidence_ids: list[str] = Field(default_factory=list)
    status: str = "completed"
    error: str | None = None

class FinancialAnomaly(BaseModel):
    anomaly_id: str = Field(default_factory=lambda: f"ANOM-{uuid4().hex[:10]}")
    anomaly_type: str
    severity: str
    period: str | None = None
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    verification_question: str

class ValuationScenarioResult(BaseModel):
    name: str
    method: str = ""
    assumptions: dict[str, float] = Field(default_factory=dict)
    enterprise_value: float | None = None
    equity_value: float | None = None
    estimated_value_per_share: float | None = None
    margin_of_safety_percent: float | None = None
    meets_required_margin: bool | None = None

class ValuationSensitivityPoint(BaseModel):
    growth_rate: float
    discount_rate: float
    value_per_share: float | None = None

class ValuationAssumptions(BaseModel):
    project_id: str | None = None
    method: Literal["auto", "fcff", "fcfe", "ddm", "relative"] = "auto"
    cash_flow_type: Literal["auto", "fcff", "fcfe"] = "auto"
    forecast_years: int = Field(default=5, ge=3, le=10)
    bear_growth: float = -0.05
    base_growth: float = 0.03
    bull_growth: float = 0.08
    wacc: float = Field(default=0.10, gt=0, lt=0.5)
    cost_of_equity: float = Field(default=0.11, gt=0, lt=0.5)
    terminal_growth: float = Field(default=0.02, ge=-0.1, lt=0.2)
    margin_of_safety_required: float = Field(default=0.25, ge=0, lt=1)
    confirmed: bool = False
    confirmation_note: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ValuationAnalysis(BaseModel):
    status: str = "insufficient_data"
    method: str | None = None
    method_reason: str | None = None
    assumptions_confirmed: bool = False
    formal_conclusion_allowed: bool = False
    market_price: float | None = None
    required_margin_percent: float = 25.0
    multiples: dict[str, float] = Field(default_factory=dict)
    historical_ranges: dict[str, dict[str, float]] = Field(default_factory=dict)
    peer_ranges: dict[str, dict[str, float]] = Field(default_factory=dict)
    equity_bridge: dict[str, float] = Field(default_factory=dict)
    reverse_assumptions: list[str] = Field(default_factory=list)
    scenarios: list[ValuationScenarioResult] = Field(default_factory=list)
    sensitivity: list[ValuationSensitivityPoint] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    conclusion: str = "资料不足，不能形成安全边际判断"

class EvidenceGraphQuality(BaseModel):
    score: float = 0
    traceability_rate: float = 0
    verified_rate: float = 0
    relation_coverage: float = 0
    unresolved_conflicts: int = 0
    issues: list[str] = Field(default_factory=list)


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
    QUESTIONED_BY = "questioned_by"


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
    relation_source: str = "deterministic"
    model_name: str | None = None
    reviewed_by_user: bool = False
    user_review_note: str | None = None


class EvidenceGraph(BaseModel):
    version: int = 1
    parent_version: int | None = None
    nodes: list[EvidenceGraphNode] = Field(default_factory=list)
    edges: list[EvidenceGraphEdge] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    change_summary: str | None = None
    removed_node_ids: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceNodeReview(BaseModel):
    verification_status: VerificationStatus
    note: str | None = None


class EvidenceEdgeReview(BaseModel):
    relation: EvidenceRelation
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
    rationale: str | None = None
    required_evidence_types: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    generated_from: str = "framework"
    change_reason: str | None = None


class ResearchMap(BaseModel):
    project_id: str
    industry: str
    version: int = 1
    questions: list[ResearchQuestion] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    core_variables: list[str] = Field(default_factory=list)
    material_requests: list[str] = Field(default_factory=list)
    planner_model: str = "deterministic_framework"
    context_fingerprint: str | None = None
    change_summary: str | None = None
    completion_rate: float = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchExecutionPlan(BaseModel):
    company_type: str = "general"
    required_skills: list[str] = Field(default_factory=list)
    skipped_skills: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    priority_questions: list[str] = Field(default_factory=list)
    missing_materials: list[str] = Field(default_factory=list)
    replan_triggers: list[str] = Field(default_factory=list)
    rationale: str = ""


class WorkflowEvent(BaseModel):
    stage: str
    status: str
    detail: str = ""
    attempt: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThesisVariable(BaseModel):
    name: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class ThesisScenario(BaseModel):
    name: str
    assumptions: list[str] = Field(default_factory=list)
    outcome: str
    trigger_conditions: list[str] = Field(default_factory=list)


class ThesisDraft(BaseModel):
    core_view: str
    core_variables: list[ThesisVariable] = Field(default_factory=list, max_length=3)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    counter_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    scenarios: list[ThesisScenario] = Field(default_factory=list)
    user_internal_label: str | None = None


class ThesisAssessment(BaseModel):
    status: AgentStatus
    issues: list[str] = Field(default_factory=list)
    evidence_coverage: float = 0
    sell_side_repetition_risk: bool = False
    confidence: Confidence = Confidence.LOW
    ai_suggestions: list[str] = Field(default_factory=list)
    relevant_support_ids: list[str] = Field(default_factory=list)
    relevant_counter_ids: list[str] = Field(default_factory=list)


class ThesisVersion(BaseModel):
    thesis_id: str = Field(default_factory=lambda: f"THESIS-{uuid4().hex[:10]}")
    project_id: str
    version: int
    draft: ThesisDraft
    assessment: ThesisAssessment
    evidence_graph_version: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DefenseRole(str, Enum):
    PORTFOLIO_MANAGER = "portfolio_manager"
    INVESTMENT_DIRECTOR = "investment_director"
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
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class DefenseSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"DEF-{uuid4().hex[:10]}")
    project_id: str
    thesis_id: str
    status: str = "active"
    turns: list[DefenseTurn] = Field(default_factory=list)
    overall_score: float | None = None
    improvement_tasks: list[str] = Field(default_factory=list)
    question_model: str = "deterministic"
    targeted_gaps: list[str] = Field(default_factory=list)
    question_bank: list[DefenseTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"TASK-{uuid4().hex[:10]}")
    project_id: str
    title: str
    detail: str
    source_type: str
    source_id: str
    priority: int = 1
    status: str = "open"
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completion_evidence_ids: list[str] = Field(default_factory=list)
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchTaskUpdate(BaseModel):
    status: str
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchBehaviorEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVENT-{uuid4().hex[:12]}")
    user_id: str
    project_id: str | None = None
    action: str
    dimension: str
    outcome: str
    score: float | None = None
    object_type: str | None = None
    object_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DefenseAnswerRequest(BaseModel):
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class CapabilityDimension(BaseModel):
    dimension: str
    score: float | None = None
    evidence: list[str] = Field(default_factory=list)
    repeated_errors: list[str] = Field(default_factory=list)
    sample_count: int = 0
    confidence: Confidence = Confidence.LOW
    trend: str = "insufficient_data"
    change: float | None = None


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
    review_status: str = "pending"
    review_note: str | None = None
    cross_check_status: str = "not_applicable"
    cross_check_matches: list[str] = Field(default_factory=list)


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
    publisher: str | None = None
    published_at: datetime | None = None
    modality: MaterialModality = MaterialModality.TEXT
    blocks: list[ContentBlock] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    classification_model: str | None = None
    classification_confidence: float | None = None


class UrlIngestRequest(BaseModel):
    url: str
    source_type: SourceType = SourceType.NEWS_SUMMARY


class MaterialBlockReview(BaseModel):
    confirmed: bool
    note: str | None = None


class SourceDocument(BaseModel):
    source_id: str = Field(default_factory=lambda: f"SRC-{uuid4().hex[:8]}")
    title: str
    source_type: SourceType
    file_name: str | None = None
    url: str | None = None
    provided_by_user: bool = True
    usage_rights_confirmed: bool | None = None
    period_covered: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
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
    sheet: str | None = None
    row_id: str | None = None
    cell_range: str | None = None
    url: str | None = None
    block_id: str | None = None
    region: dict[str, float] | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    extraction_method: str | None = None
    requires_confirmation: bool = False


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
    classification_model: str | None = None
    classification_confidence: float | None = None
    semantic_neighbor_ids: list[str] = Field(default_factory=list)


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


class ViewComparisonPoint(BaseModel):
    point_type: str
    topic: str
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    assumption_difference: str | None = None
    buyer_verification_question: str | None = None


class RedTeamChallenge(BaseModel):
    challenge_id: str = Field(default_factory=lambda: f"RTC-{uuid4().hex[:10]}")
    title: str
    mechanism: str
    severity: str = "medium"
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    falsification_test: str
    status: str = "open"


class ResearchJudgment(BaseModel):
    view_points: list[ViewComparisonPoint] = Field(default_factory=list)
    red_team_challenges: list[RedTeamChallenge] = Field(default_factory=list)
    sell_side_source_count: int = 0
    independent_fact_count: int = 0
    unresolved_critical_count: int = 0


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


class MemoSuggestion(BaseModel):
    suggestion_id: str = Field(default_factory=lambda: f"SUG-{uuid4().hex[:10]}")
    section_id: str
    proposed_body: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "pending"


class MemoVersionCreate(BaseModel):
    sections: list[MemoSection]
    change_summary: str | None = None
    request_formal: bool = False


class MemoVersion(BaseModel):
    memo_version_id: str = Field(default_factory=lambda: f"MEMOV-{uuid4().hex[:10]}")
    project_id: str
    version: int
    sections: list[MemoSection]
    source_run_id: str | None = None
    created_by: str = "user"
    change_summary: str | None = None
    gate_status: str = "draft"
    gate_issues: list[str] = Field(default_factory=list)
    suggestions: list[MemoSuggestion] = Field(default_factory=list)
    evidence_graph_version: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoSuggestionDecision(BaseModel):
    status: str


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
    skill_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    research_plan: ResearchExecutionPlan | None = None
    workflow_events: list[WorkflowEvent] = Field(default_factory=list)
    processing_records: list[ModelExecutionRecord] = Field(default_factory=list)
    model_usage: list[ModelUsageRecord] = Field(default_factory=list)
    financial_calculations: list[FinancialCalculationRecord] = Field(default_factory=list)
    financial_anomalies: list[FinancialAnomaly] = Field(default_factory=list)
    valuation_analysis: ValuationAnalysis = Field(default_factory=ValuationAnalysis)
    evidence_graph_quality: EvidenceGraphQuality = Field(default_factory=EvidenceGraphQuality)
    research_judgment: ResearchJudgment = Field(default_factory=ResearchJudgment)
    pre_memo_gate: ComplianceGateOutput | None = None
    post_memo_gate: ComplianceGateOutput | None = None
    memo: ResearchMemo | None = None
    workflow_status: str = "completed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def evidence_by_category(self, *categories: EvidenceCategory) -> list[EvidenceItem]:
        allowed = set(categories)
        return [item for item in self.evidence_items if item.category in allowed]

    def output_for(self, key: str) -> AgentOutput | None:
        """Read new Skill output first and transparently support historical runs."""
        return self.skill_outputs.get(key) or self.agent_outputs.get(key)


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


class ProjectMaterial(BaseModel):
    material_id: str = Field(default_factory=lambda: f"MAT-{uuid4().hex[:10]}")
    project_id: str
    run_id: str
    version: int = 1
    title: str
    source_type: SourceType
    modality: MaterialModality
    file_name: str | None = None
    url: str | None = None
    period_covered: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    content_hash: str
    content: str
    blocks: list[ContentBlock] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchProjectDetail(BaseModel):
    project: ResearchProjectSummary
    timeline: list[ResearchRunSummary] = Field(default_factory=list)
    materials: list[ProjectMaterial] = Field(default_factory=list)


class ResearchRunDetail(BaseModel):
    summary: ResearchRunSummary
    state: WorkflowState


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "value-investing-research-coach"
    version: str = "0.1.0"


JsonDict = dict[str, Any]
