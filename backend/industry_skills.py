from __future__ import annotations

from dataclasses import dataclass

from .llm_client import LLMError, OpenAIClient
from .models import (
    AgentFinding,
    AgentOutput,
    AgentStatus,
    Confidence,
    WorkflowState,
)
from .value_investing_doctrine import doctrine_text


@dataclass(frozen=True)
class IndustrySkillSpec:
    label: str
    drivers: tuple[str, ...]
    risks: tuple[str, ...]
    required_inputs: tuple[str, ...]


INDUSTRY_SPECS = {
    "bank_analysis": IndustrySkillSpec(
        label="银行",
        drivers=("净息差", "生息资产", "存款成本", "不良率", "拨备覆盖率", "资本充足率"),
        risks=("资产质量恶化", "拨备不足", "净息差收窄", "资本消耗", "房地产与地方债暴露"),
        required_inputs=("净息差及其驱动", "不良贷款率", "关注类贷款", "拨备覆盖率", "核心一级资本充足率"),
    ),
    "manufacturing_analysis": IndustrySkillSpec(
        label="制造业",
        drivers=("销量", "价格", "产能", "产能利用率", "原材料", "资本开支", "存货"),
        risks=("产能过剩", "价格竞争", "原材料上涨", "存货积压", "资本开支回报不足"),
        required_inputs=("产能与利用率", "销量和价格", "原材料成本", "资本开支", "存货与订单"),
    ),
    "consumer_analysis": IndustrySkillSpec(
        label="消费品",
        drivers=("品牌", "提价", "销量", "渠道", "终端动销", "库存", "同店"),
        risks=("渠道压货", "品牌弱化", "提价损害销量", "库存积压", "获客成本上升"),
        required_inputs=("销量与价格拆分", "渠道库存", "终端动销", "品牌和市占率", "同店或单店数据"),
    ),
    "utility_analysis": IndustrySkillSpec(
        label="公用事业",
        drivers=("监管", "电价", "水价", "气价", "利用小时", "资本开支", "负债", "分红"),
        risks=("监管定价下调", "燃料成本无法传导", "资本开支过重", "高杠杆", "分红依赖举债"),
        required_inputs=("监管与定价机制", "成本传导机制", "利用率", "资本开支计划", "债务期限与分红覆盖"),
    ),
    "general_business_analysis": IndustrySkillSpec(
        label="通用行业",
        drivers=("收入来源", "利润来源", "销量", "价格", "成本", "竞争格局", "资本回报"),
        risks=("需求下降", "竞争加剧", "成本失控", "资本回报下降", "客户集中"),
        required_inputs=("收入结构", "利润结构", "成本结构", "竞争格局", "资本投入与回报"),
    ),
}


def _matching_evidence(state: WorkflowState, terms: tuple[str, ...]):
    return [
        item
        for item in state.evidence_items
        if any(term.lower() in item.statement.lower() for term in terms)
    ]


def _fallback_output(state: WorkflowState, skill_id: str) -> AgentOutput:
    spec = INDUSTRY_SPECS[skill_id]
    driver_evidence = _matching_evidence(state, spec.drivers)
    risk_evidence = _matching_evidence(state, spec.risks)
    covered = {
        term
        for term in spec.drivers
        if any(term.lower() in item.statement.lower() for item in driver_evidence)
    }
    missing = [
        item
        for item in spec.required_inputs
        if not any(term.lower() in " ".join(covered).lower() for term in item.split("与"))
    ]
    findings = []
    if driver_evidence:
        findings.append(
            AgentFinding(
                title=f"{spec.label}核心经营驱动",
                detail="；".join(item.statement for item in driver_evidence[:5]),
                classification="fact_based",
                evidence_ids=[item.evidence_id for item in driver_evidence[:5]],
                confidence=Confidence.MEDIUM,
            )
        )
    if risk_evidence:
        findings.append(
            AgentFinding(
                title=f"{spec.label}行业风险信号",
                detail="；".join(item.statement for item in risk_evidence[:5]),
                classification="risk",
                evidence_ids=[item.evidence_id for item in risk_evidence[:5]],
                confidence=Confidence.MEDIUM,
            )
        )
    if not findings:
        findings.append(
            AgentFinding(
                title=f"{spec.label}分析资料不足",
                detail=f"当前证据未覆盖{spec.label}核心变量，不能形成行业经营判断。",
                classification="missing_data",
                confidence=Confidence.LOW,
            )
        )
    return AgentOutput(
        agent_name=f"{spec.label} Analysis Skill",
        status=AgentStatus.PARTIAL if findings else AgentStatus.FAIL,
        summary=f"已按{spec.label}专属指标检查当前证据；模型不可用，结果为规则降级分析。",
        findings=findings,
        missing_materials=missing,
        warnings=["行业深度模型未运行，当前结果已明确降级。"],
        confidence=Confidence.LOW,
    )


def run_industry_analysis_skill(
    state: WorkflowState,
    skill_id: str,
    client: OpenAIClient | None = None,
) -> AgentOutput:
    spec = INDUSTRY_SPECS[skill_id]
    client = client or OpenAIClient()
    if not client.available:
        return _fallback_output(state, skill_id)
    prompt = f"""
你是 Research Analyst Agent 调用的{spec.label}专属研究 Skill。
只根据输入证据完成公司研究，不得依赖常识补造事实。

必须分析：
- 核心经营驱动：{", ".join(spec.drivers)}
- 主要风险机制：{", ".join(spec.risks)}
- 资料要求：{", ".join(spec.required_inputs)}
- 经营变量如何传导至利润、现金流和资本回报
- 哪些证据会推翻当前判断

每条结论必须引用有效 evidence_ids。证据不足时必须列入
missing_materials，不得输出空泛的行业模板。

返回 JSON：summary, findings, missing_materials, warnings, confidence, status。
findings 每项包含 title, detail, classification, evidence_ids, confidence。

{doctrine_text()}
""".strip()
    try:
        result = client.generate_json(
            system_prompt=prompt,
            user_payload={
                "company_profile": state.company_profile.model_dump(mode="json"),
                "industry_skill": skill_id,
                "evidence_items": [
                    {
                        "evidence_id": item.evidence_id,
                        "category": item.category.value,
                        "statement": item.statement,
                        "period": item.period,
                        "metric_name": item.metric_name,
                        "metric_value": item.metric_value,
                        "unit": item.unit,
                        "verification_status": item.verification_status.value,
                    }
                    for item in state.evidence_items
                ],
                "financial_anomalies": [
                    item.model_dump(mode="json") for item in state.financial_anomalies
                ],
            },
            temperature=0,
        )
    except (LLMError, TimeoutError, OSError, TypeError, ValueError) as exc:
        output = _fallback_output(state, skill_id)
        output.warnings.append(f"行业深度模型调用失败：{exc}")
        return output
    if not isinstance(result, dict):
        return _fallback_output(state, skill_id)
    valid_ids = {item.evidence_id for item in state.evidence_items}
    findings = []
    for raw in result.get("findings", []):
        if not isinstance(raw, dict) or not str(raw.get("detail") or "").strip():
            continue
        ids = [str(item) for item in raw.get("evidence_ids", []) if str(item) in valid_ids]
        classification = str(raw.get("classification") or "ai_reasoning")
        confidence = (
            Confidence(str(raw.get("confidence")))
            if str(raw.get("confidence")) in {"high", "medium", "low"}
            else Confidence.LOW
        )
        if classification != "missing_data" and not ids:
            classification = "missing_data"
            confidence = Confidence.LOW
        findings.append(
            AgentFinding(
                title=str(raw.get("title") or f"{spec.label}研究发现"),
                detail=str(raw["detail"]),
                classification=classification,
                evidence_ids=ids,
                confidence=confidence,
            )
        )
    if not findings:
        return _fallback_output(state, skill_id)
    status_value = str(result.get("status") or "partial")
    status = AgentStatus(status_value if status_value in {"pass", "partial", "fail"} else "partial")
    return AgentOutput(
        agent_name=f"{spec.label} Analysis Skill",
        status=status,
        summary=str(result.get("summary") or f"已完成{spec.label}专属分析。"),
        findings=findings,
        missing_materials=[str(item) for item in result.get("missing_materials", [])],
        warnings=[str(item) for item in result.get("warnings", [])],
        confidence=Confidence(str(result.get("confidence"))) if str(result.get("confidence")) in {"high", "medium", "low"} else Confidence.LOW,
    )


def run_bank_analysis_skill(state: WorkflowState) -> AgentOutput:
    return run_industry_analysis_skill(state, "bank_analysis")


def run_manufacturing_analysis_skill(state: WorkflowState) -> AgentOutput:
    return run_industry_analysis_skill(state, "manufacturing_analysis")


def run_consumer_analysis_skill(state: WorkflowState) -> AgentOutput:
    return run_industry_analysis_skill(state, "consumer_analysis")


def run_utility_analysis_skill(state: WorkflowState) -> AgentOutput:
    return run_industry_analysis_skill(state, "utility_analysis")


def run_general_business_analysis_skill(state: WorkflowState) -> AgentOutput:
    return run_industry_analysis_skill(state, "general_business_analysis")
