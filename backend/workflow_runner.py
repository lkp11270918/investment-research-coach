from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from .agent_architecture import aggregate_output, build_research_plan, planner_output, record_event
from .agents import run_gate_blocked_memo, run_material_organizer
from .evidence_graph import build_evidence_graph
from .financial_calculations import calculate_financial_metrics
from .llm_agents import run_business_model_moat_llm, run_compliance_gate_llm, run_evidence_extractor_llm, run_financial_quality_dividend_llm, run_management_view_comparison_llm, run_research_coach_review_llm, run_value_trap_contradiction_llm
from .llm_client import OpenAIClient, collected_usage, start_usage_tracking
from .model_pipeline import execute_model_pipeline
from .memo_writing import run_memo_writing_skill
from .models import AgentFinding, AgentOutput, AgentStatus, AnalyzeRequest, Confidence, ReviewRequest, WorkflowState, WorkflowStopAfter
from .research_judgment import build_research_judgment
from .research_quality import assess_graph_quality, detect_financial_anomalies
from .storage import save_run
from .valuation import analyze_valuation


def _apply_financial_calculations(state: WorkflowState) -> None:
    records, derived = calculate_financial_metrics(state.evidence_items)
    state.financial_calculations = records
    existing = {(item.metric_name, item.period) for item in state.evidence_items}
    state.evidence_items.extend(item for item in derived if (item.metric_name, item.period) not in existing)
    state.financial_anomalies = detect_financial_anomalies(state.evidence_items)
    state.valuation_analysis = analyze_valuation(state.evidence_items, state.company_profile.industry)


def _valuation_skill_output(state: WorkflowState) -> AgentOutput:
    valuation = state.valuation_analysis
    findings = [AgentFinding(title="估值方法", detail=f"{valuation.method or '未确定'}：{valuation.method_reason or valuation.conclusion}", classification="ai_reasoning", evidence_ids=valuation.evidence_ids, confidence=Confidence.MEDIUM)]
    return AgentOutput(agent_name="Valuation & Margin of Safety Skill", status=AgentStatus.PASS if valuation.scenarios else AgentStatus.PARTIAL, summary=valuation.conclusion, findings=findings, missing_materials=valuation.missing_inputs, warnings=valuation.warnings, confidence=Confidence.MEDIUM if valuation.scenarios else Confidence.LOW)


def _legacy_context(state: WorkflowState) -> None:
    """Let retained Skill implementations read their historical keys during migration."""
    state.agent_outputs.update(state.skill_outputs)


def _publish_main_agents(state: WorkflowState, main: dict[str, AgentOutput]) -> None:
    state.agent_outputs = {key: main[key] for key in ("research_planner", "evidence", "research_analyst", "red_team_judge") if key in main}


def _save_and_return(state: WorkflowState, main: dict[str, AgentOutput]) -> WorkflowState:
    _publish_main_agents(state, main)
    state.model_usage = collected_usage()
    save_run(state, state.run_id)
    return state


def _should_stop(request: AnalyzeRequest, *steps: WorkflowStopAfter) -> bool:
    return request.options.stop_after in steps


def run_analysis_workflow(request: AnalyzeRequest) -> WorkflowState:
    start_usage_tracking()
    state = WorkflowState(company_profile=request.company_profile, raw_materials=request.materials)
    main: dict[str, AgentOutput] = {}

    record_event(state, "planning", "running")
    state.research_plan = build_research_plan(state)
    main["research_planner"] = planner_output(state.research_plan)
    record_event(state, "planning", "completed", main["research_planner"].summary)
    if _should_stop(request, WorkflowStopAfter.DOCTRINE): return _save_and_return(state, main)

    record_event(state, "extracting_evidence", "running")
    organizer = run_material_organizer(state)
    extractor = run_evidence_extractor_llm(state)
    state.skill_outputs["material_organizer"] = organizer
    state.skill_outputs["evidence_extractor"] = extractor
    state.processing_records = execute_model_pipeline(state.raw_materials, state.evidence_items)
    _apply_financial_calculations(state)
    state.evidence_graph = build_evidence_graph(state, OpenAIClient())
    state.evidence_graph_quality = assess_graph_quality(state.evidence_graph)
    main["evidence"] = aggregate_output("Evidence Agent", [organizer, extractor], f"已整理 {len(state.source_documents)} 份资料并建立 {len(state.evidence_items)} 条证据。")
    record_event(state, "extracting_evidence", "completed", main["evidence"].summary)
    if _should_stop(request, WorkflowStopAfter.MATERIAL_ORGANIZER, WorkflowStopAfter.EVIDENCE_EXTRACTOR): return _save_and_return(state, main)

    record_event(state, "analyzing", "running")
    required = set(state.research_plan.required_skills)
    analysis_outputs: list[AgentOutput] = []
    if request.options.enable_parallel:
        jobs = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            if "financial_quality_dividend" in required: jobs.append(("financial_quality_dividend", executor.submit(copy_context().run, run_financial_quality_dividend_llm, state)))
            if "business_model_moat" in required: jobs.append(("business_model_moat", executor.submit(copy_context().run, run_business_model_moat_llm, state)))
            for key, future in jobs:
                output = future.result(); state.skill_outputs[key] = output; analysis_outputs.append(output)
    else:
        for key, runner in (("financial_quality_dividend", run_financial_quality_dividend_llm), ("business_model_moat", run_business_model_moat_llm)):
            if key in required:
                output = runner(state); state.skill_outputs[key] = output; analysis_outputs.append(output)
    _legacy_context(state)
    if "management_view_comparison" in required:
        output = run_management_view_comparison_llm(state); state.skill_outputs["management_view_comparison"] = output; analysis_outputs.append(output)
    if "valuation_margin" in required:
        output = _valuation_skill_output(state); state.skill_outputs["valuation_margin"] = output; analysis_outputs.append(output)
    main["research_analyst"] = aggregate_output("Research Analyst Agent", analysis_outputs, f"按研究计划完成 {len(analysis_outputs)} 个专项分析。")
    record_event(state, "analyzing", "completed", main["research_analyst"].summary)
    if _should_stop(request, WorkflowStopAfter.FINANCIAL_QUALITY, WorkflowStopAfter.BUSINESS_MODEL, WorkflowStopAfter.MANAGEMENT_VIEW): return _save_and_return(state, main)

    record_event(state, "judging", "running")
    _legacy_context(state)
    traps = run_value_trap_contradiction_llm(state)
    state.skill_outputs["value_trap_contradiction"] = traps
    _legacy_context(state)
    state.research_judgment = build_research_judgment(state)
    state.evidence_graph = build_evidence_graph(state, OpenAIClient())
    state.evidence_graph_quality = assess_graph_quality(state.evidence_graph)
    state.pre_memo_gate = run_compliance_gate_llm(state, "pre_memo_gate")
    gate_finding = AgentFinding(title="Pre-Memo Gate", detail="；".join([*state.pre_memo_gate.evidence_issues, *state.pre_memo_gate.compliance_warnings]) or "证据与合规门禁通过。", classification="quality_gate", confidence=Confidence.HIGH)
    gate_output = AgentOutput(agent_name="Evidence Gate Skill", status=AgentStatus.PASS if state.pre_memo_gate.status == "pass" else AgentStatus.FAIL, summary=f"Pre-Memo Gate: {state.pre_memo_gate.status}", findings=[gate_finding], confidence=Confidence.HIGH)
    state.skill_outputs["pre_memo_gate"] = gate_output
    main["red_team_judge"] = aggregate_output("Red Team & Judge Agent", [traps, gate_output], "已完成反证、价值陷阱、证据充分性和合规审查。")
    record_event(state, "judging", "completed" if state.pre_memo_gate.status == "pass" else "needs_evidence", main["red_team_judge"].summary)
    if _should_stop(request, WorkflowStopAfter.VALUE_TRAP, WorkflowStopAfter.PRE_MEMO_GATE): return _save_and_return(state, main)

    _legacy_context(state)
    if state.pre_memo_gate.status == "fail":
        state.workflow_status = "needs_evidence"; state.memo = run_gate_blocked_memo(state)
    else:
        record_event(state, "writing", "running"); state.memo = run_memo_writing_skill(state); record_event(state, "writing", "completed")
    if _should_stop(request, WorkflowStopAfter.MEMO): return _save_and_return(state, main)

    if not request.options.skip_post_gate:
        state.post_memo_gate = run_compliance_gate_llm(state, "post_memo_gate", state.memo)
        if state.post_memo_gate.status == "fail" and state.workflow_status == "completed": state.workflow_status = "needs_revision"
    state.evidence_graph = build_evidence_graph(state, OpenAIClient())
    state.evidence_graph_quality = assess_graph_quality(state.evidence_graph)
    record_event(state, "completed", state.workflow_status)
    return _save_and_return(state, main)


def run_review_workflow(request: ReviewRequest) -> WorkflowState:
    start_usage_tracking()
    if request.company_profile is None:
        from .models import CompanyProfile, UserMode
        company_profile = CompanyProfile(company_name="未指定公司", industry="未指定行业", user_mode=UserMode.TO_C)
    else: company_profile = request.company_profile
    state = WorkflowState(company_profile=company_profile, raw_materials=request.materials)
    state.research_plan = build_research_plan(state)
    organizer = run_material_organizer(state); extractor = run_evidence_extractor_llm(state)
    state.skill_outputs.update(material_organizer=organizer, evidence_extractor=extractor)
    state.processing_records = execute_model_pipeline(state.raw_materials, state.evidence_items); _apply_financial_calculations(state)
    review = run_research_coach_review_llm(request.memo_text, state); state.skill_outputs["research_coach_review"] = review
    state.evidence_graph = build_evidence_graph(state, OpenAIClient())
    main = {
        "research_planner": planner_output(state.research_plan),
        "evidence": aggregate_output("Evidence Agent", [organizer, extractor], f"已建立 {len(state.evidence_items)} 条批改证据。"),
        "research_analyst": AgentOutput(agent_name="Research Analyst Agent", status=AgentStatus.PASS, summary="已读取用户 Memo 作为待审核研究对象。", confidence=Confidence.MEDIUM),
        "red_team_judge": aggregate_output("Red Team & Judge Agent", [review], "已完成卖方复读、证据缺口、价值陷阱和理念符合度批改。"),
    }
    _publish_main_agents(state, main); state.model_usage = collected_usage(); save_run(state, state.run_id)
    return state
