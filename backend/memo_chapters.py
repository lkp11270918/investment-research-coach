from __future__ import annotations

from enum import Enum


class MemoChapter(str, Enum):
    COMPANY_INFO = "company_info"
    SCOPE_DOCTRINE_CONFIDENCE = "scope_doctrine_confidence"
    CIRCLE_OF_COMPETENCE = "circle_of_competence"
    BUSINESS_MODEL = "business_model"
    KEY_VARIABLES = "key_variables"
    FINANCIAL_EARNINGS_QUALITY = "financial_earnings_quality"
    CASH_FLOW = "cash_flow"
    DIVIDEND = "dividend"
    BALANCE_SHEET = "balance_sheet"
    BUSINESS_STABILITY_MOAT = "business_stability_moat"
    INDUSTRY_COMPETITION = "industry_competition"
    MANAGEMENT_CAPITAL_ALLOCATION = "management_capital_allocation"
    NARRATIVE_VS_FINANCIALS = "narrative_vs_financials"
    SELL_SIDE_CONSENSUS_DIVERGENCE = "sell_side_consensus_divergence"
    VALUATION_MARGIN = "valuation_margin"
    VALUE_TRAP = "value_trap"
    VERIFICATION_QUESTIONS = "verification_questions"
    RESEARCH_VIEW_UNCERTAINTY = "research_view_uncertainty"
    SOURCES_DISCLAIMER = "sources_disclaimer"


MEMO_CHAPTERS: tuple[tuple[str, str], ...] = (
    (MemoChapter.COMPANY_INFO.value, "公司基本信息"),
    (MemoChapter.SCOPE_DOCTRINE_CONFIDENCE.value, "资料范围、研究准则适用性与结论置信度"),
    (MemoChapter.CIRCLE_OF_COMPETENCE.value, "能力圈判断"),
    (MemoChapter.BUSINESS_MODEL.value, "商业模式：公司靠什么赚钱"),
    (MemoChapter.KEY_VARIABLES.value, "核心经营变量"),
    (MemoChapter.FINANCIAL_EARNINGS_QUALITY.value, "财务质量与盈利质量"),
    (MemoChapter.CASH_FLOW.value, "现金流质量"),
    (MemoChapter.DIVIDEND.value, "分红质量与可持续性"),
    (MemoChapter.BALANCE_SHEET.value, "资产负债表安全性"),
    (MemoChapter.BUSINESS_STABILITY_MOAT.value, "商业模式稳定性、护城河与竞争优势"),
    (MemoChapter.INDUSTRY_COMPETITION.value, "行业与竞争格局"),
    (MemoChapter.MANAGEMENT_CAPITAL_ALLOCATION.value, "管理层资本配置"),
    (MemoChapter.NARRATIVE_VS_FINANCIALS.value, "管理层叙事与财务现实"),
    (MemoChapter.SELL_SIDE_CONSENSUS_DIVERGENCE.value, "卖方共识、核心分歧与分歧来源"),
    (MemoChapter.VALUATION_MARGIN.value, "估值与安全边际"),
    (MemoChapter.VALUE_TRAP.value, "价值陷阱与反证风险"),
    (MemoChapter.VERIFICATION_QUESTIONS.value, "待验证问题"),
    (MemoChapter.RESEARCH_VIEW_UNCERTAINTY.value, "研究观点、内部研究标签、不确定性与资料缺口"),
    (MemoChapter.SOURCES_DISCLAIMER.value, "来源列表与不构成投资建议声明"),
)

MEMO_CHAPTER_TITLES = dict(MEMO_CHAPTERS)
MEMO_CHAPTER_IDS = tuple(chapter_id for chapter_id, _ in MEMO_CHAPTERS)

MEMO_CHAPTERS_EN: tuple[tuple[str, str], ...] = (
    (MemoChapter.COMPANY_INFO.value, "Company Information"),
    (MemoChapter.SCOPE_DOCTRINE_CONFIDENCE.value, "Material Scope, Doctrine Applicability, and Conclusion Confidence"),
    (MemoChapter.CIRCLE_OF_COMPETENCE.value, "Circle of Competence"),
    (MemoChapter.BUSINESS_MODEL.value, "Business Model: How the Company Makes Money"),
    (MemoChapter.KEY_VARIABLES.value, "Key Operating Variables"),
    (MemoChapter.FINANCIAL_EARNINGS_QUALITY.value, "Financial and Earnings Quality"),
    (MemoChapter.CASH_FLOW.value, "Cash Flow Quality"),
    (MemoChapter.DIVIDEND.value, "Dividend Quality and Sustainability"),
    (MemoChapter.BALANCE_SHEET.value, "Balance Sheet Safety"),
    (MemoChapter.BUSINESS_STABILITY_MOAT.value, "Business Stability, Moat, and Competitive Advantages"),
    (MemoChapter.INDUSTRY_COMPETITION.value, "Industry and Competition"),
    (MemoChapter.MANAGEMENT_CAPITAL_ALLOCATION.value, "Management Capital Allocation"),
    (MemoChapter.NARRATIVE_VS_FINANCIALS.value, "Management Narrative vs. Financial Reality"),
    (MemoChapter.SELL_SIDE_CONSENSUS_DIVERGENCE.value, "Sell-side Consensus, Core Disagreements, and Their Sources"),
    (MemoChapter.VALUATION_MARGIN.value, "Valuation and Margin of Safety"),
    (MemoChapter.VALUE_TRAP.value, "Value Traps and Counter-Evidence Risks"),
    (MemoChapter.VERIFICATION_QUESTIONS.value, "Questions to Verify"),
    (MemoChapter.RESEARCH_VIEW_UNCERTAINTY.value, "Research View, Internal Label, Uncertainty, and Information Gaps"),
    (MemoChapter.SOURCES_DISCLAIMER.value, "Sources and Investment-advice Disclaimer"),
)

MEMO_CHAPTER_TITLES_EN = dict(MEMO_CHAPTERS_EN)

# Used only for migration of persisted claims and historical LLM responses.
LEGACY_CHAPTER_ALIASES = {
    "material_scope_confidence": MemoChapter.SCOPE_DOCTRINE_CONFIDENCE.value,
    "doctrine": MemoChapter.SCOPE_DOCTRINE_CONFIDENCE.value,
    "financial_quality": MemoChapter.FINANCIAL_EARNINGS_QUALITY.value,
    "earnings_quality": MemoChapter.FINANCIAL_EARNINGS_QUALITY.value,
    "moat": MemoChapter.BUSINESS_STABILITY_MOAT.value,
    "view_comparison": MemoChapter.SELL_SIDE_CONSENSUS_DIVERGENCE.value,
    "sell_side_views": MemoChapter.SELL_SIDE_CONSENSUS_DIVERGENCE.value,
    "verification_gaps": MemoChapter.VERIFICATION_QUESTIONS.value,
    "research_view": MemoChapter.RESEARCH_VIEW_UNCERTAINTY.value,
    "uncertainty": MemoChapter.RESEARCH_VIEW_UNCERTAINTY.value,
    "sources": MemoChapter.SOURCES_DISCLAIMER.value,
    "disclaimer": MemoChapter.SOURCES_DISCLAIMER.value,
    "cash_flow_quality": MemoChapter.CASH_FLOW.value,
    "dividend_quality": MemoChapter.DIVIDEND.value,
}


def canonical_chapter_id(section_id: str | None) -> str | None:
    if not section_id:
        return None
    return LEGACY_CHAPTER_ALIASES.get(section_id, section_id if section_id in MEMO_CHAPTER_IDS else None)


MEMO_CHAPTER_REVIEW_CUES: dict[str, tuple[str, ...]] = {
    MemoChapter.COMPANY_INFO.value: ("公司基本信息", "公司概述", "公司简介"),
    MemoChapter.SCOPE_DOCTRINE_CONFIDENCE.value: ("资料范围", "研究准则", "结论置信度"),
    MemoChapter.CIRCLE_OF_COMPETENCE.value: ("能力圈",),
    MemoChapter.BUSINESS_MODEL.value: ("商业模式", "靠什么赚钱", "收入来源"),
    MemoChapter.KEY_VARIABLES.value: ("核心经营变量", "关键变量", "核心变量"),
    MemoChapter.FINANCIAL_EARNINGS_QUALITY.value: ("财务质量", "盈利质量", "利润质量"),
    MemoChapter.CASH_FLOW.value: ("现金流质量", "经营现金流", "自由现金流"),
    MemoChapter.DIVIDEND.value: ("分红", "股息", "派息"),
    MemoChapter.BALANCE_SHEET.value: ("资产负债表", "有息负债", "偿债"),
    MemoChapter.BUSINESS_STABILITY_MOAT.value: ("商业模式稳定性", "护城河", "竞争优势"),
    MemoChapter.INDUSTRY_COMPETITION.value: ("行业与竞争", "竞争格局", "行业格局"),
    MemoChapter.MANAGEMENT_CAPITAL_ALLOCATION.value: ("管理层资本配置", "资本配置"),
    MemoChapter.NARRATIVE_VS_FINANCIALS.value: ("管理层叙事", "财务现实"),
    MemoChapter.SELL_SIDE_CONSENSUS_DIVERGENCE.value: ("卖方共识", "核心分歧", "分歧来源"),
    MemoChapter.VALUATION_MARGIN.value: ("估值", "安全边际"),
    MemoChapter.VALUE_TRAP.value: ("价值陷阱", "反证风险", "反证"),
    MemoChapter.VERIFICATION_QUESTIONS.value: ("待验证问题", "待验证"),
    MemoChapter.RESEARCH_VIEW_UNCERTAINTY.value: ("研究观点", "研究标签", "不确定性", "资料缺口"),
    MemoChapter.SOURCES_DISCLAIMER.value: ("来源列表", "不构成投资建议", "出处"),
}


def score_memo_chapter_coverage(memo_text: str) -> list[dict[str, object]]:
    normalized = memo_text.lower()
    return [
        {
            "section_id": section_id,
            "title": title,
            "score": 100 if any(cue.lower() in normalized for cue in MEMO_CHAPTER_REVIEW_CUES[section_id]) else 0,
            "covered": any(cue.lower() in normalized for cue in MEMO_CHAPTER_REVIEW_CUES[section_id]),
        }
        for section_id, title in MEMO_CHAPTERS
    ]
