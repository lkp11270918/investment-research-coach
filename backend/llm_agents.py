from __future__ import annotations

from typing import Any

from .agents import run_evidence_extractor as run_stub_evidence_extractor
from .agents import run_financial_quality_dividend as run_stub_financial_quality_dividend
from .agents import run_business_model_moat as run_stub_business_model_moat
from .agents import run_compliance_gate as run_stub_compliance_gate
from .agents import run_management_view_comparison as run_stub_management_view_comparison
from .agents import run_material_organizer as run_stub_material_organizer
from .agents import run_research_memo_generator as run_stub_research_memo_generator
from .agents import run_value_trap_contradiction as run_stub_value_trap_contradiction
from .llm_client import LLMError, OpenAIClient
from .models import (
    AgentFinding,
    AgentOutput,
    AgentStatus,
    ComplianceGateOutput,
    Confidence,
    DowngradedClaim,
    EvidenceCategory,
    EvidenceItem,
    SourceDocument,
    SourceRef,
    SourceType,
    VerificationStatus,
    WorkflowState,
    ResearchMemo,
    MemoSection,
    UserMode,
)


GLOBAL_AGENT_RULES = """
你是 Value Investing Research Coach 的一个子 Agent。
产品定位：面向初级研究员的买方价值投资研究训练 Agent，不是荐股、交易建议或短期价格预测工具。

硬性规则：
- 必须区分事实、观点、假设和 AI 推理。
- 关键事实必须绑定来源；没有来源不得写成事实。
- 不得把“用户整理资料”表述为“权威来源确认”；除非 source 明确来自年报、公告、交易所文件或公司正式披露。
- 缺失数据输出 null、not provided 或待验证，不得补造。
- 卖方观点只是输入材料，不是买方结论。
- 不得把高股息直接等同于安全。
- 不得把低估值直接等同于安全边际。
- 不得输出收益承诺或确定性买卖建议。
- 只返回 JSON，不要 markdown。
""".strip()


MATERIAL_ORGANIZER_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Material Organizer Agent。请根据用户提供资料，判断资料类型、覆盖范围、缺失资料和可靠性提示。

返回 JSON 格式：
{
  "summary": "string",
  "documents": [
    {
      "input_index": 0,
      "source_type": "financial_table | annual_report_summary | announcement_excerpt | management_note | sell_side_summary | news_summary | industry_material | user_note | institution_doctrine | historical_memo | failed_case | memo_template | other",
      "reliability_note": "string",
      "period_covered": "string or null"
    }
  ],
  "findings": [
    {"title": "string", "detail": "string", "classification": "fact_based | missing_data | ai_reasoning", "confidence": "high | medium | low"}
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low"
}
"""
)


EVIDENCE_EXTRACTOR_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Evidence Extractor Agent。请从用户材料中抽取价值投资研究所需的关键证据。

只抽取材料中明确出现的信息，不得根据常识补充。
每条 evidence 必须引用一个已有 source_id，并尽量保留原文 excerpt。

category 只能使用：
fact, financial_fact, management_opinion, sell_side_opinion, news_or_market_opinion, user_opinion, assumption, ai_reasoning, risk, verification_question

verification_status 只能使用：
verified, partially_supported, unsupported, to_be_verified

返回 JSON 格式：
{
  "summary": "string",
  "evidence": [
    {
      "category": "financial_fact",
      "statement": "string",
      "source_id": "SRC-...",
      "excerpt": "string",
      "period": "string or null",
      "metric_name": "string or null",
      "metric_value": "number/string/null",
      "unit": "string or null",
      "confidence": "high | medium | low",
      "verification_status": "verified | partially_supported | unsupported | to_be_verified",
      "notes": "string or null"
    }
  ],
  "findings": [
    {"title": "string", "detail": "string", "classification": "fact_based | opinion_based | assumption_based | ai_reasoning | risk | missing_data", "confidence": "high | medium | low"}
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low"
}
"""
)


FINANCIAL_QUALITY_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Financial Quality & Dividend Agent。请只基于已抽取 evidence 分析财务质量、现金流质量、分红可持续性和资产负债表安全。

特别要求：
- 不得补造缺失财务数据。
- 如果没有自由现金流、资本开支、分红金额、分红率、资产负债率、有息负债、短债压力、ROE 拆解等数据，必须写入 missing_materials。
- 不得把“现金流稳定”直接推导为“分红安全”。
- 不得把“高股息/高分红”直接推导为“安全资产”。
- 每条 finding 尽量引用 evidence_ids；不要引用不存在的 evidence_id。
- 如果证据不足，confidence 必须是 low。

返回 JSON 格式：
{
  "summary": "string",
  "findings": [
    {
      "title": "string",
      "detail": "string",
      "classification": "fact_based | opinion_based | assumption_based | ai_reasoning | risk | missing_data",
      "evidence_ids": ["EV-..."],
      "confidence": "high | medium | low"
    }
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low",
  "status": "pass | partial | fail"
}
"""
)


BUSINESS_MODEL_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Business Model & Moat Agent。请只基于已抽取 evidence 分析公司靠什么赚钱、商业模式稳定性、竞争优势、周期性、资本开支需求和能力圈匹配度。

特别要求：
- 不得把管理层愿景、卖方乐观观点或行业标签直接当作护城河。
- 不得凭常识补充公司业务细节；材料没给就写缺失。
- 如果缺少收入结构、利润来源、成本结构、行业竞争格局、资本开支需求、需求稳定性等资料，必须写入 missing_materials。
- 需要指出核心经营变量，例如销量、价格、成本、利用率、来水、电价、客流、开店、产能、资本开支等；但只能使用 evidence 中出现或由 evidence 明确支持的变量。
- 每条 finding 尽量引用 evidence_ids；不要引用不存在的 evidence_id。

返回 JSON 格式：
{
  "summary": "string",
  "findings": [
    {
      "title": "string",
      "detail": "string",
      "classification": "fact_based | opinion_based | assumption_based | ai_reasoning | risk | missing_data",
      "evidence_ids": ["EV-..."],
      "confidence": "high | medium | low"
    }
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low",
  "status": "pass | partial | fail"
}
"""
)


MANAGEMENT_VIEW_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Management & View Comparison Agent。请比较管理层叙事、卖方观点、新闻/市场观点、用户观点和财务事实之间的一致性、分歧和待追问问题。

特别要求：
- 管理层观点、卖方观点、新闻观点都只能作为观点输入，不得直接写成事实或买方结论。
- 必须区分共识、分歧、少数派观点、核心假设差异和管理层可信度观察。
- 如果缺少管理层观点、卖方观点或财务事实，必须写入 missing_materials 并降低 confidence。
- 不得根据模型常识补充材料未提供的卖方观点或管理层说法。
- 每条 finding 尽量引用 evidence_ids；不要引用不存在的 evidence_id。
- 输出应服务于买方研究训练，重点提示后续追问和需要验证的问题。

返回 JSON 格式：
{
  "summary": "string",
  "findings": [
    {
      "title": "string",
      "detail": "string",
      "classification": "fact_based | opinion_based | assumption_based | ai_reasoning | risk | missing_data",
      "evidence_ids": ["EV-..."],
      "confidence": "high | medium | low"
    }
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low",
  "status": "pass | partial | fail"
}
"""
)


VALUE_TRAP_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Value Trap & Contradiction Agent。你的职责是主动寻找可能推翻当前价值投资判断的反证、价值陷阱信号和一票否决变量。

你不是补充乐观结论的 Agent。你必须从怀疑视角检查：
- 高股息是否不可持续。
- 低估值是否来自主业衰退，而不是真正低估。
- 经营现金流是否与利润匹配。
- 自由现金流是否足以覆盖分红。
- 分红是否依赖一次性收益或历史现金。
- ROE 是否依赖高杠杆。
- 利润是否依赖非经常性损益。
- 行业需求是否长期下行。
- 应收账款和存货是否恶化。
- 管理层叙事是否与财务现实冲突。
- 当前判断是否过度依赖乐观假设。

特别要求：
- 资料缺失本身就是风险，必须写入 missing_materials 或 findings。
- 不得因为缺少数据而跳过价值陷阱检查。
- 不得给买入/卖出建议。
- 每条 finding 尽量引用 evidence_ids；不要引用不存在的 evidence_id。
- 输出必须包含至少一个“待验证问题”或“结论降级原因”。

返回 JSON 格式：
{
  "summary": "string",
  "findings": [
    {
      "title": "string",
      "detail": "string",
      "classification": "risk | missing_data | fact_based | opinion_based | assumption_based | ai_reasoning",
      "evidence_ids": ["EV-..."],
      "confidence": "high | medium | low"
    }
  ],
  "missing_materials": ["string"],
  "warnings": ["string"],
  "confidence": "high | medium | low",
  "status": "pass | partial | fail"
}
"""
)


COMPLIANCE_GATE_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Evidence & Compliance Gate Agent。请检查当前工作流状态或最终 Memo 是否存在证据和合规风险。

你必须检查：
- 财务数字是否有来源。
- 核心结论是否有证据支持。
- 是否把观点写成事实。
- 是否把假设写成结论。
- 是否出现收益承诺或交易指令。
- To C 模式是否输出买入/卖出/增持/减持等评级。
- To B 模式内部评级是否有内部研究标签和免责声明。
- 是否把高股息直接等同于安全。
- 是否把低估值直接等同于安全边际。
- 是否复述或重构未授权付费研报。
- 资料不足时是否强行高置信判断。

返回 JSON 格式：
{
  "status": "pass | fail",
  "unsupported_claims": ["string"],
  "evidence_issues": ["string"],
  "downgraded_claims": [
    {"original_claim": "string", "downgraded_expression": "string", "reason": "string or null"}
  ],
  "compliance_warnings": ["string"],
  "rewrite_suggestions": ["string"]
}
"""
)


MEMO_GENERATOR_PROMPT = (
    GLOBAL_AGENT_RULES
    + """

任务：你是 Research Memo Generator Agent。请基于当前工作流状态生成结构化买方研究训练 Memo。

你必须遵守：
- 只能基于用户资料、evidence 和前序 Agent 输出写作。
- 不得新增未提供的财务数字或事实。
- 事实、观点、假设和 AI 推理要在表达上区分清楚。
- 资料不足处必须降级表达。
- To C 模式不得输出买入、卖出、增持、减持等评级；只能使用“积极关注/中性观察/谨慎观察/资料不足暂不评级”等研究训练标签。
- 不得给交易指令或收益承诺。
- 不得把高股息直接等同安全。
- 不得把低估值直接等同安全边际。
- 必须包含不构成投资建议声明。
- 每个章节尽量引用 evidence_ids；不要引用不存在的 evidence_id。

章节必须按以下 section_id 输出：
material_scope_confidence, company_info, doctrine, circle_of_competence, business_model,
cash_flow_quality, dividend_quality, balance_sheet, moat, management_capital_allocation,
narrative_vs_financials, sell_side_views, valuation_margin, value_trap, verification_questions,
research_view, uncertainty, sources, disclaimer

返回 JSON 格式：
{
  "confidence": "high | medium | low",
  "sections": [
    {
      "section_id": "material_scope_confidence",
      "title": "资料范围与结论置信度",
      "body": "string",
      "evidence_ids": ["EV-..."],
      "confidence": "high | medium | low"
    }
  ],
  "disclaimer": "string",
  "warnings": ["string"]
}
"""
)


def _confidence(value: Any, default: Confidence = Confidence.LOW) -> Confidence:
    try:
        return Confidence(str(value))
    except ValueError:
        return default


def _source_type(value: Any, default: SourceType = SourceType.OTHER) -> SourceType:
    try:
        return SourceType(str(value))
    except ValueError:
        return default


def _category(value: Any) -> EvidenceCategory:
    try:
        return EvidenceCategory(str(value))
    except ValueError:
        return EvidenceCategory.AI_REASONING


def _verification_status(value: Any) -> VerificationStatus:
    try:
        return VerificationStatus(str(value))
    except ValueError:
        return VerificationStatus.TO_BE_VERIFIED


def _finding(raw: dict[str, Any]) -> AgentFinding:
    return AgentFinding(
        title=str(raw.get("title") or "未命名发现"),
        detail=str(raw.get("detail") or ""),
        classification=str(raw.get("classification") or "ai_reasoning"),
        evidence_ids=[str(item) for item in raw.get("evidence_ids", [])],
        confidence=_confidence(raw.get("confidence")),
    )


def _agent_status(value: Any, default: AgentStatus = AgentStatus.PARTIAL) -> AgentStatus:
    try:
        return AgentStatus(str(value))
    except ValueError:
        return default


def _gate_status(value: Any, fallback_status: str) -> str:
    raw = str(value or fallback_status).lower()
    return "pass" if raw == "pass" else "fail"


def _is_blocking_warning(text: str) -> bool:
    safe_phrases = [
        "未输出",
        "符合合规",
        "符合",
        "不构成投资建议",
        "不构成",
        "无交易指令",
        "未发现",
    ]
    if any(phrase in text for phrase in safe_phrases):
        return False
    blocking_terms = [
        "买入",
        "卖出",
        "增持",
        "减持",
        "交易指令",
        "收益承诺",
        "保证收益",
        "必涨",
        "稳赚",
        "无来源事实",
        "unsupported",
        "未授权付费研报",
        "版权",
        "To C 模式",
        "公众用户",
    ]
    return any(term in text for term in blocking_terms)


def run_material_organizer_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_material_organizer(state)

    try:
        result = client.generate_json(
            system_prompt=MATERIAL_ORGANIZER_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "materials": [
                    {
                        "input_index": index,
                        "title": material.title,
                        "declared_source_type": material.source_type.value,
                        "file_name": material.file_name,
                        "url": material.url,
                        "period_covered": material.period_covered,
                        "content_excerpt": material.content[:4000],
                    }
                    for index, material in enumerate(state.raw_materials)
                ],
            },
        )
    except LLMError as exc:
        output = run_stub_material_organizer(state)
        output.warnings.append(f"LLM Material Organizer 调用失败，已回退规则骨架：{exc}")
        return output

    documents: list[SourceDocument] = []
    raw_docs = result.get("documents", [])
    by_index = {int(doc.get("input_index", -1)): doc for doc in raw_docs if isinstance(doc, dict)}
    for index, raw in enumerate(state.raw_materials):
        llm_doc = by_index.get(index, {})
        documents.append(
            SourceDocument(
                title=raw.title,
                source_type=_source_type(llm_doc.get("source_type"), raw.source_type),
                file_name=raw.file_name,
                url=raw.url,
                usage_rights_confirmed=raw.usage_rights_confirmed,
                period_covered=llm_doc.get("period_covered") or raw.period_covered,
                reliability_note=llm_doc.get("reliability_note") or "用户提供资料，需以后续证据抽取和交叉验证为准。",
                content=raw.content,
            )
        )
    state.source_documents = documents

    findings = [_finding(item) for item in result.get("findings", []) if isinstance(item, dict)]
    return AgentOutput(
        agent_name="Material Organizer Agent",
        status=AgentStatus.PASS if documents else AgentStatus.FAIL,
        summary=str(result.get("summary") or f"已整理 {len(documents)} 份用户资料。"),
        findings=findings,
        missing_materials=[str(item) for item in result.get("missing_materials", [])],
        confidence=_confidence(result.get("confidence")),
        warnings=[str(item) for item in result.get("warnings", [])],
    )


def run_evidence_extractor_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_evidence_extractor(state)

    try:
        result = client.generate_json(
            system_prompt=EVIDENCE_EXTRACTOR_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "source_documents": [
                    {
                        "source_id": doc.source_id,
                        "title": doc.title,
                        "source_type": doc.source_type.value,
                        "period_covered": doc.period_covered,
                        "url": doc.url,
                        "content": doc.content[:6000],
                    }
                    for doc in state.source_documents
                ],
            },
        )
    except LLMError as exc:
        output = run_stub_evidence_extractor(state)
        output.warnings.append(f"LLM Evidence Extractor 调用失败，已回退规则骨架：{exc}")
        return output

    source_by_id = {doc.source_id: doc for doc in state.source_documents}
    evidence: list[EvidenceItem] = []
    for raw in result.get("evidence", []):
        if not isinstance(raw, dict):
            continue
        source_id = str(raw.get("source_id") or "")
        if source_id not in source_by_id:
            continue
        source = source_by_id[source_id]
        category = _category(raw.get("category"))
        refs = [
            SourceRef(
                source_id=source_id,
                excerpt=raw.get("excerpt"),
                url=source.url,
            )
        ]
        status = _verification_status(raw.get("verification_status"))
        if category in {EvidenceCategory.FACT, EvidenceCategory.FINANCIAL_FACT} and not raw.get("excerpt"):
            status = VerificationStatus.TO_BE_VERIFIED
        evidence.append(
            EvidenceItem(
                category=category,
                statement=str(raw.get("statement") or ""),
                source_refs=refs,
                period=raw.get("period"),
                metric_name=raw.get("metric_name"),
                metric_value=raw.get("metric_value"),
                unit=raw.get("unit"),
                confidence=_confidence(raw.get("confidence")),
                verification_status=status,
                notes=raw.get("notes"),
            )
        )

    state.evidence_items = evidence
    findings = [_finding(item) for item in result.get("findings", []) if isinstance(item, dict)]
    return AgentOutput(
        agent_name="Evidence Extractor Agent",
        status=AgentStatus.PASS if evidence else AgentStatus.FAIL,
        summary=str(result.get("summary") or f"抽取 {len(evidence)} 条证据项。"),
        findings=findings,
        evidence_ids=[item.evidence_id for item in evidence],
        missing_materials=[str(item) for item in result.get("missing_materials", [])],
        confidence=_confidence(result.get("confidence")),
        warnings=[str(item) for item in result.get("warnings", [])],
    )


def run_financial_quality_dividend_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_financial_quality_dividend(state)

    financial_evidence = [
        item
        for item in state.evidence_items
        if item.category
        in {
            EvidenceCategory.FINANCIAL_FACT,
            EvidenceCategory.FACT,
            EvidenceCategory.MANAGEMENT_OPINION,
            EvidenceCategory.SELL_SIDE_OPINION,
            EvidenceCategory.RISK,
        }
    ]
    if not financial_evidence:
        return run_stub_financial_quality_dividend(state)

    try:
        result = client.generate_json(
            system_prompt=FINANCIAL_QUALITY_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in financial_evidence
                ],
            },
        )
    except LLMError as exc:
        output = run_stub_financial_quality_dividend(state)
        output.warnings.append(f"LLM Financial Quality 调用失败，已回退规则骨架：{exc}")
        return output

    valid_evidence_ids = {item.evidence_id for item in state.evidence_items}
    findings: list[AgentFinding] = []
    for raw in result.get("findings", []):
        if not isinstance(raw, dict):
            continue
        finding = _finding(raw)
        finding.evidence_ids = [item for item in finding.evidence_ids if item in valid_evidence_ids]
        findings.append(finding)

    evidence_ids = sorted({evidence_id for finding in findings for evidence_id in finding.evidence_ids})
    missing_materials = [str(item) for item in result.get("missing_materials", [])]
    confidence = _confidence(result.get("confidence"))
    status = _agent_status(result.get("status"))
    if missing_materials and status == AgentStatus.PASS:
        status = AgentStatus.PARTIAL
    if missing_materials and confidence == Confidence.HIGH:
        confidence = Confidence.MEDIUM

    return AgentOutput(
        agent_name="Financial Quality & Dividend Agent",
        status=status,
        summary=str(result.get("summary") or "已完成财务质量与分红可持续性分析。"),
        findings=findings,
        evidence_ids=evidence_ids,
        missing_materials=missing_materials,
        confidence=confidence,
        warnings=[str(item) for item in result.get("warnings", [])],
    )


def run_business_model_moat_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_business_model_moat(state)

    business_evidence = [
        item
        for item in state.evidence_items
        if item.category
        in {
            EvidenceCategory.FACT,
            EvidenceCategory.FINANCIAL_FACT,
            EvidenceCategory.MANAGEMENT_OPINION,
            EvidenceCategory.SELL_SIDE_OPINION,
            EvidenceCategory.NEWS_OR_MARKET_OPINION,
            EvidenceCategory.USER_OPINION,
            EvidenceCategory.RISK,
        }
    ]
    if not business_evidence:
        return run_stub_business_model_moat(state)

    try:
        result = client.generate_json(
            system_prompt=BUSINESS_MODEL_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in business_evidence
                ],
            },
        )
    except LLMError as exc:
        output = run_stub_business_model_moat(state)
        output.warnings.append(f"LLM Business Model 调用失败，已回退规则骨架：{exc}")
        return output

    valid_evidence_ids = {item.evidence_id for item in state.evidence_items}
    findings: list[AgentFinding] = []
    for raw in result.get("findings", []):
        if not isinstance(raw, dict):
            continue
        finding = _finding(raw)
        finding.evidence_ids = [item for item in finding.evidence_ids if item in valid_evidence_ids]
        findings.append(finding)

    evidence_ids = sorted({evidence_id for finding in findings for evidence_id in finding.evidence_ids})
    missing_materials = [str(item) for item in result.get("missing_materials", [])]
    confidence = _confidence(result.get("confidence"))
    status = _agent_status(result.get("status"))
    if missing_materials and status == AgentStatus.PASS:
        status = AgentStatus.PARTIAL
    if missing_materials and confidence == Confidence.HIGH:
        confidence = Confidence.MEDIUM

    return AgentOutput(
        agent_name="Business Model & Moat Agent",
        status=status,
        summary=str(result.get("summary") or "已完成商业模式与竞争优势分析。"),
        findings=findings,
        evidence_ids=evidence_ids,
        missing_materials=missing_materials,
        confidence=confidence,
        warnings=[str(item) for item in result.get("warnings", [])],
    )


def run_management_view_comparison_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_management_view_comparison(state)

    view_evidence = [
        item
        for item in state.evidence_items
        if item.category
        in {
            EvidenceCategory.FINANCIAL_FACT,
            EvidenceCategory.FACT,
            EvidenceCategory.MANAGEMENT_OPINION,
            EvidenceCategory.SELL_SIDE_OPINION,
            EvidenceCategory.NEWS_OR_MARKET_OPINION,
            EvidenceCategory.USER_OPINION,
            EvidenceCategory.RISK,
        }
    ]
    if not view_evidence:
        return run_stub_management_view_comparison(state)

    prior_outputs = {
        key: value.model_dump(mode="json")
        for key, value in state.agent_outputs.items()
        if key in {"financial_quality_dividend", "business_model_moat"}
    }

    try:
        result = client.generate_json(
            system_prompt=MANAGEMENT_VIEW_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in view_evidence
                ],
                "prior_analysis_outputs": prior_outputs,
            },
        )
    except LLMError as exc:
        output = run_stub_management_view_comparison(state)
        output.warnings.append(f"LLM Management View 调用失败，已回退规则骨架：{exc}")
        return output

    valid_evidence_ids = {item.evidence_id for item in state.evidence_items}
    findings: list[AgentFinding] = []
    for raw in result.get("findings", []):
        if not isinstance(raw, dict):
            continue
        finding = _finding(raw)
        finding.evidence_ids = [item for item in finding.evidence_ids if item in valid_evidence_ids]
        findings.append(finding)

    evidence_ids = sorted({evidence_id for finding in findings for evidence_id in finding.evidence_ids})
    missing_materials = [str(item) for item in result.get("missing_materials", [])]
    confidence = _confidence(result.get("confidence"))
    status = _agent_status(result.get("status"))
    if missing_materials and status == AgentStatus.PASS:
        status = AgentStatus.PARTIAL
    if missing_materials and confidence == Confidence.HIGH:
        confidence = Confidence.MEDIUM

    return AgentOutput(
        agent_name="Management & View Comparison Agent",
        status=status,
        summary=str(result.get("summary") or "已完成管理层与多方观点比较。"),
        findings=findings,
        evidence_ids=evidence_ids,
        missing_materials=missing_materials,
        confidence=confidence,
        warnings=[str(item) for item in result.get("warnings", [])],
    )


def run_value_trap_contradiction_llm(state: WorkflowState, client: OpenAIClient | None = None) -> AgentOutput:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_value_trap_contradiction(state)

    if not state.evidence_items:
        return run_stub_value_trap_contradiction(state)

    prior_outputs = {
        key: value.model_dump(mode="json")
        for key, value in state.agent_outputs.items()
        if key
        in {
            "financial_quality_dividend",
            "business_model_moat",
            "management_view_comparison",
        }
    }

    try:
        result = client.generate_json(
            system_prompt=VALUE_TRAP_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in state.evidence_items
                ],
                "prior_analysis_outputs": prior_outputs,
                "mandatory_checks": [
                    "高股息是否不可持续",
                    "低估值是否来自主业衰退",
                    "经营现金流是否与利润匹配",
                    "自由现金流是否覆盖分红",
                    "分红是否依赖一次性收益或历史现金",
                    "ROE 是否依赖高杠杆",
                    "利润是否依赖非经常性损益",
                    "行业需求是否长期下行",
                    "应收账款和存货是否恶化",
                    "管理层叙事是否与财务现实冲突",
                    "当前判断是否过度依赖乐观假设",
                ],
            },
        )
    except LLMError as exc:
        output = run_stub_value_trap_contradiction(state)
        output.warnings.append(f"LLM Value Trap 调用失败，已回退规则骨架：{exc}")
        return output

    valid_evidence_ids = {item.evidence_id for item in state.evidence_items}
    findings: list[AgentFinding] = []
    for raw in result.get("findings", []):
        if not isinstance(raw, dict):
            continue
        finding = _finding(raw)
        finding.evidence_ids = [item for item in finding.evidence_ids if item in valid_evidence_ids]
        findings.append(finding)

    evidence_ids = sorted({evidence_id for finding in findings for evidence_id in finding.evidence_ids})
    missing_materials = [str(item) for item in result.get("missing_materials", [])]
    confidence = _confidence(result.get("confidence"))
    status = _agent_status(result.get("status"))
    if missing_materials and status == AgentStatus.PASS:
        status = AgentStatus.PARTIAL
    if findings and status == AgentStatus.FAIL:
        status = AgentStatus.PARTIAL
    if confidence == Confidence.HIGH:
        confidence = Confidence.MEDIUM

    warnings = [str(item) for item in result.get("warnings", [])]
    if not any("高股息" in item or "低估值" in item or "价值陷阱" in item for item in warnings):
        warnings.append("价值陷阱检查不能被前序乐观结论覆盖。")

    return AgentOutput(
        agent_name="Value Trap & Contradiction Agent",
        status=status,
        summary=str(result.get("summary") or "已完成价值陷阱与反证风险检查。"),
        findings=findings,
        evidence_ids=evidence_ids,
        missing_materials=missing_materials,
        confidence=confidence,
        warnings=warnings,
    )


def run_compliance_gate_llm(
    state: WorkflowState,
    gate_name: str,
    draft_memo: ResearchMemo | None = None,
    client: OpenAIClient | None = None,
) -> ComplianceGateOutput:
    client = client or OpenAIClient()
    rule_gate = run_stub_compliance_gate(state, gate_name, draft_memo)
    if not client.available:
        return rule_gate

    try:
        result = client.generate_json(
            system_prompt=COMPLIANCE_GATE_PROMPT,
            user_payload={
                "gate_name": gate_name,
                "company_profile": state.company_profile.model_dump(mode="json"),
                "user_mode": state.company_profile.user_mode.value,
                "rule_gate_result": rule_gate.model_dump(mode="json"),
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in state.evidence_items
                ],
                "agent_outputs": {
                    key: value.model_dump(mode="json")
                    for key, value in state.agent_outputs.items()
                },
                "draft_memo": draft_memo.model_dump(mode="json") if draft_memo else None,
            },
        )
    except LLMError as exc:
        rule_gate.compliance_warnings.append(f"LLM Compliance Gate 调用失败，已使用规则门禁：{exc}")
        return rule_gate

    unsupported_claims = [
        *rule_gate.unsupported_claims,
        *[str(item) for item in result.get("unsupported_claims", [])],
    ]
    evidence_issues = [
        *rule_gate.evidence_issues,
        *[str(item) for item in result.get("evidence_issues", [])],
    ]
    downgraded_claims = [*rule_gate.downgraded_claims]
    for raw in result.get("downgraded_claims", []):
        if not isinstance(raw, dict):
            continue
        downgraded_claims.append(
            DowngradedClaim(
                original_claim=str(raw.get("original_claim") or ""),
                downgraded_expression=str(raw.get("downgraded_expression") or ""),
                reason=raw.get("reason"),
            )
        )
    compliance_warnings = [
        *rule_gate.compliance_warnings,
        *[str(item) for item in result.get("compliance_warnings", [])],
    ]
    rewrite_suggestions = [
        *rule_gate.rewrite_suggestions,
        *[str(item) for item in result.get("rewrite_suggestions", [])],
    ]

    seen: set[str] = set()

    def dedupe(items: list[str]) -> list[str]:
        output: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                output.append(item)
        return output

    blocking_warnings = [item for item in compliance_warnings if _is_blocking_warning(item)]
    status = _gate_status(result.get("status"), rule_gate.status)
    if rule_gate.status == "fail":
        status = "fail"
    if unsupported_claims or evidence_issues or blocking_warnings:
        status = "fail"
    elif status == "fail":
        status = "pass"

    return ComplianceGateOutput(
        gate_name=gate_name,
        status=status,
        unsupported_claims=dedupe(unsupported_claims),
        evidence_issues=dedupe(evidence_issues),
        downgraded_claims=downgraded_claims,
        compliance_warnings=dedupe(compliance_warnings),
        rewrite_suggestions=dedupe(rewrite_suggestions),
    )


def run_research_memo_generator_llm(state: WorkflowState, client: OpenAIClient | None = None) -> ResearchMemo:
    client = client or OpenAIClient()
    if not client.available:
        return run_stub_research_memo_generator(state)

    try:
        result = client.generate_json(
            system_prompt=MEMO_GENERATOR_PROMPT,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "user_mode": state.company_profile.user_mode.value,
                "source_documents": [
                    {
                        "source_id": doc.source_id,
                        "title": doc.title,
                        "source_type": doc.source_type.value,
                        "period_covered": doc.period_covered,
                        "reliability_note": doc.reliability_note,
                    }
                    for doc in state.source_documents
                ],
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "confidence": item.confidence.value,
                        "verification_status": item.verification_status.value,
                        "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
                    }
                    for item in state.evidence_items
                ],
                "agent_outputs": {
                    key: value.model_dump(mode="json")
                    for key, value in state.agent_outputs.items()
                },
                "pre_memo_gate": state.pre_memo_gate.model_dump(mode="json") if state.pre_memo_gate else None,
            },
        )
    except LLMError:
        return run_stub_research_memo_generator(state)

    valid_evidence_ids = {item.evidence_id for item in state.evidence_items}
    allowed_sections = [
        "material_scope_confidence",
        "company_info",
        "doctrine",
        "circle_of_competence",
        "business_model",
        "cash_flow_quality",
        "dividend_quality",
        "balance_sheet",
        "moat",
        "management_capital_allocation",
        "narrative_vs_financials",
        "sell_side_views",
        "valuation_margin",
        "value_trap",
        "verification_questions",
        "research_view",
        "uncertainty",
        "sources",
        "disclaimer",
    ]
    default_titles = {
        "material_scope_confidence": "资料范围与结论置信度",
        "company_info": "公司基本信息",
        "doctrine": "研究准则适用说明",
        "circle_of_competence": "能力圈判断",
        "business_model": "公司靠什么赚钱",
        "cash_flow_quality": "现金流质量",
        "dividend_quality": "分红质量与可持续性",
        "balance_sheet": "资产负债表安全性",
        "moat": "商业模式稳定性与竞争优势",
        "management_capital_allocation": "管理层资本配置",
        "narrative_vs_financials": "管理层叙事 vs 财务现实",
        "sell_side_views": "卖方共识与核心分歧",
        "valuation_margin": "估值与安全边际",
        "value_trap": "价值陷阱与反证风险",
        "verification_questions": "待验证问题",
        "research_view": "研究观点或内部研究标签",
        "uncertainty": "不确定性与资料缺口",
        "sources": "来源列表",
        "disclaimer": "不构成投资建议声明",
    }

    raw_sections = {
        str(item.get("section_id")): item
        for item in result.get("sections", [])
        if isinstance(item, dict) and str(item.get("section_id")) in allowed_sections
    }
    fallback_memo = run_stub_research_memo_generator(state)
    fallback_by_id = {section.section_id: section for section in fallback_memo.sections}

    sections: list[MemoSection] = []
    for section_id in allowed_sections:
        raw = raw_sections.get(section_id)
        fallback = fallback_by_id.get(section_id)
        if raw:
            evidence_ids = [
                str(item)
                for item in raw.get("evidence_ids", [])
                if str(item) in valid_evidence_ids
            ]
            sections.append(
                MemoSection(
                    section_id=section_id,
                    title=str(raw.get("title") or default_titles[section_id]),
                    body=str(raw.get("body") or ""),
                    evidence_ids=evidence_ids,
                    confidence=_confidence(raw.get("confidence")),
                )
            )
        elif fallback:
            sections.append(fallback)
        else:
            sections.append(
                MemoSection(
                    section_id=section_id,
                    title=default_titles[section_id],
                    body="当前资料不足以生成该章节，需要补充材料后再判断。",
                    confidence=Confidence.LOW,
                )
            )

    disclaimer = str(result.get("disclaimer") or fallback_memo.disclaimer)
    if "不构成" not in disclaimer:
        disclaimer = fallback_memo.disclaimer
    memo = ResearchMemo(
        company_profile=state.company_profile,
        user_mode=state.company_profile.user_mode,
        confidence=_confidence(result.get("confidence")),
        sections=sections,
        source_ids=[doc.source_id for doc in state.source_documents],
        disclaimer=disclaimer,
    )

    if state.company_profile.user_mode == UserMode.TO_C:
        forbidden = ["买入", "卖出", "增持", "减持", "强烈推荐", "立即买", "立即卖"]
        for section in memo.sections:
            if any(word in section.body for word in forbidden):
                section.body = "资料不足暂不评级。该标签仅用于研究训练，不构成投资建议。"
                section.confidence = Confidence.LOW

    memo.markdown = "\n\n".join(f"## {section.title}\n\n{section.body}" for section in memo.sections)
    return memo
