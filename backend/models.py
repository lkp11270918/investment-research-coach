from __future__ import annotations

from datetime import datetime
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
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RawMaterial(BaseModel):
    title: str
    content: str
    source_type: SourceType = SourceType.OTHER
    file_name: str | None = None
    url: str | None = None
    usage_rights_confirmed: bool | None = None
    period_covered: str | None = None


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    content: str = ""


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
    company_profile: CompanyProfile
    materials: list[RawMaterial] = Field(default_factory=list)
    options: WorkflowOptions = Field(default_factory=WorkflowOptions)


class ReviewRequest(BaseModel):
    company_profile: CompanyProfile | None = None
    memo_text: str
    materials: list[RawMaterial] = Field(default_factory=list)


class WorkflowState(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid4().hex[:10]}")
    company_profile: CompanyProfile
    raw_materials: list[RawMaterial] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    pre_memo_gate: ComplianceGateOutput | None = None
    post_memo_gate: ComplianceGateOutput | None = None
    memo: ResearchMemo | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def evidence_by_category(self, *categories: EvidenceCategory) -> list[EvidenceItem]:
        allowed = set(categories)
        return [item for item in self.evidence_items if item.category in allowed]


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str
    state: WorkflowState


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "value-investing-research-coach"
    version: str = "0.1.0"


JsonDict = dict[str, Any]
