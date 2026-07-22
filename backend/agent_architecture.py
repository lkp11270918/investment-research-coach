from __future__ import annotations

from .models import AgentFinding, AgentOutput, AgentStatus, Confidence, ResearchExecutionPlan, WorkflowEvent, WorkflowState

MAIN_AGENT_KEYS = ("research_planner", "evidence", "research_analyst", "red_team_judge")

SKILL_LABELS = {
    "financial_quality_dividend": "财务质量、现金流与分红",
    "business_model_moat": "商业模式与护城河",
    "management_view_comparison": "管理层、资本配置与多方观点",
    "valuation_margin": "估值与安全边际",
    "value_trap_contradiction": "价值陷阱与反证",
}


def record_event(state: WorkflowState, stage: str, status: str, detail: str = "", attempt: int = 1) -> None:
    state.workflow_events.append(WorkflowEvent(stage=stage, status=status, detail=detail, attempt=attempt))


def build_research_plan(state: WorkflowState) -> ResearchExecutionPlan:
    industry = state.company_profile.industry.lower()
    company_type = "general"
    required = ["financial_quality_dividend", "business_model_moat", "management_view_comparison", "valuation_margin"]
    skipped: list[str] = []
    questions = ["盈利是否能稳定转化为现金流？", "竞争优势和关键经营假设是什么？", "什么证据会推翻当前判断？"]
    if any(token in industry for token in ("银行", "bank")):
        company_type = "bank"
        questions = ["净息差变化由什么驱动？", "资产质量和拨备能否吸收潜在损失？", "资本充足率和分红是否可持续？"]
    elif any(token in industry for token in ("保险", "insurance")):
        company_type = "insurance"
        questions = ["新业务价值和续期质量如何？", "投资收益假设是否稳健？", "偿付能力与分红是否兼容？"]
    elif any(token in industry for token in ("消费", "食品", "零售")):
        company_type = "consumer"
        questions = ["品牌力是否能转化为定价权？", "渠道库存和终端需求是否匹配？", "增长是销量、价格还是渠道扩张驱动？"]
    elif any(token in industry for token in ("制造", "工业", "机械")):
        company_type = "manufacturing"
        questions = ["产能利用率与新增产能是否匹配需求？", "资本开支能否转化为现金回报？", "原材料和价格周期如何影响利润率？"]
    elif any(token in industry for token in ("公用事业", "电力", "水务", "燃气")):
        company_type = "utility"
        questions = ["监管与定价机制是否稳定？", "资本开支、负债与自由现金流是否匹配？", "分红是否由可持续现金流支持？"]
    if not state.raw_materials:
        required = []
        skipped = list(SKILL_LABELS)[:-1]
    return ResearchExecutionPlan(company_type=company_type, required_skills=required, skipped_skills=skipped, parallel_groups=[required[:2], required[2:]] if required else [], priority_questions=questions, missing_materials=[] if state.raw_materials else ["公司研究资料"], replan_triggers=["新增关键证据", "出现跨来源冲突", "用户修改研究目标"], rationale=f"根据{state.company_profile.industry or '未指定行业'}和当前资料覆盖生成。")


def planner_output(plan: ResearchExecutionPlan) -> AgentOutput:
    return AgentOutput(agent_name="Research Planner Agent", status=AgentStatus.PASS if plan.required_skills else AgentStatus.PARTIAL, summary=f"识别为 {plan.company_type} 研究路径，计划执行 {len(plan.required_skills)} 个分析 Skill。", findings=[AgentFinding(title="优先研究问题", detail="；".join(plan.priority_questions), classification="research_plan", confidence=Confidence.MEDIUM)], missing_materials=plan.missing_materials, confidence=Confidence.MEDIUM)


def aggregate_output(name: str, outputs: list[AgentOutput], summary: str) -> AgentOutput:
    findings = [finding for output in outputs for finding in output.findings]
    missing = list(dict.fromkeys(item for output in outputs for item in output.missing_materials))
    warnings = list(dict.fromkeys(item for output in outputs for item in output.warnings))
    status = AgentStatus.FAIL if any(output.status == AgentStatus.FAIL for output in outputs) else AgentStatus.PARTIAL if any(output.status == AgentStatus.PARTIAL for output in outputs) else AgentStatus.PASS
    return AgentOutput(agent_name=name, status=status, summary=summary, findings=findings, missing_materials=missing, confidence=Confidence.MEDIUM if findings else Confidence.LOW, warnings=warnings)
