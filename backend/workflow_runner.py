from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextvars import copy_context
from time import perf_counter

from .agent_architecture import record_event
from .agents import run_firm_doctrine_case_retrieval
from .config import get_settings
from .evidence_graph import build_evidence_graph
from .financial_calculations import calculate_financial_metrics
from .industry_skills import (
    run_bank_analysis_skill,
    run_consumer_analysis_skill,
    run_general_business_analysis_skill,
    run_manufacturing_analysis_skill,
    run_utility_analysis_skill,
)
from .llm_agents import (
    run_business_model_moat_llm,
    run_compliance_gate_llm,
    run_evidence_extractor_llm,
    run_financial_quality_dividend_llm,
    run_management_view_comparison_llm,
    run_material_organizer_llm,
    run_research_coach_review_llm,
    run_value_trap_contradiction_llm,
)
from .llm_client import OpenAIClient, collected_usage, start_usage_tracking
from .memo_writing import run_memo_writing_skill
from .model_pipeline import execute_model_pipeline
from .models import AgentFinding, AgentOutput, AgentStatus, AnalyzeRequest, Confidence, ResearchClaim, ReviewRequest, SkillResult, WorkflowState, WorkflowStopAfter
from .research_agents import run_analyst_agent, run_judge_agent, run_planner_agent, to_skill_result
from .research_judgment import build_research_judgment
from .research_quality import assess_graph_quality, detect_financial_anomalies
from .storage import save_run
from .valuation import analyze_valuation

MAIN_KEYS=("research_planner","evidence","research_analyst","red_team_judge")


def _sync_graph(state: WorkflowState, semantic: bool = False) -> None:
    state.evidence_graph=build_evidence_graph(state,OpenAIClient() if semantic else None,include_semantic=semantic)
    state.evidence_graph_quality=assess_graph_quality(state.evidence_graph)


def _execution_metadata(skill_id: str, output: AgentOutput) -> tuple[str, str | None]:
    fallback_warning=any(
        term in warning
        for warning in output.warnings
        for term in ("回退", "未运行", "未启用", "模型不可用", "降级")
    )
    settings=get_settings()
    deterministic_skills={"doctrine_context","valuation_margin"}
    expects_model=skill_id not in deterministic_skills
    model_capable=expects_model and settings.use_llm_agents and bool(settings.openai_api_key)
    mode="degraded" if fallback_warning or (expects_model and not model_capable) else "model" if model_capable else "deterministic"
    return mode, settings.openai_model if mode=="model" else None


def _retry_model_fallback(runner, state: WorkflowState, output: AgentOutput) -> AgentOutput:
    """Retry a transient model failure once before accepting deterministic fallback."""
    if get_settings().use_llm_agents and get_settings().openai_api_key and any("调用失败" in item for item in output.warnings):
        retried=runner(state)
        if not any("调用失败" in item for item in retried.warnings):
            return retried
        output.warnings.extend(item for item in retried.warnings if item not in output.warnings)
    return output


def _financials(state: WorkflowState) -> None:
    records,derived=calculate_financial_metrics(state.evidence_items); state.financial_calculations=records
    existing={(item.metric_name,item.period) for item in state.evidence_items}; state.evidence_items.extend(item for item in derived if (item.metric_name,item.period) not in existing)
    state.financial_anomalies=detect_financial_anomalies(state.evidence_items); state.valuation_analysis=analyze_valuation(state.evidence_items,state.company_profile.industry)


def _valuation_output(state: WorkflowState) -> AgentOutput:
    value=state.valuation_analysis
    return AgentOutput(agent_name="Valuation & Margin of Safety Skill",status=AgentStatus.PASS if value.scenarios else AgentStatus.PARTIAL,summary=value.conclusion,findings=[AgentFinding(title="估值方法",detail=f"{value.method or '未确定'}：{value.method_reason or value.conclusion}",classification="reasoning",evidence_ids=value.evidence_ids,confidence=Confidence.MEDIUM)],missing_materials=value.missing_inputs,warnings=value.warnings,confidence=Confidence.MEDIUM)


def _runner(skill_id: str):
    if skill_id=="financial_quality_dividend": return run_financial_quality_dividend_llm
    if skill_id=="business_model_moat": return run_business_model_moat_llm
    if skill_id=="management_view_comparison": return run_management_view_comparison_llm
    if skill_id=="valuation_margin": return _valuation_output
    if skill_id=="bank_analysis": return run_bank_analysis_skill
    if skill_id=="manufacturing_analysis": return run_manufacturing_analysis_skill
    if skill_id=="consumer_analysis": return run_consumer_analysis_skill
    if skill_id=="utility_analysis": return run_utility_analysis_skill
    if skill_id=="general_business_analysis": return run_general_business_analysis_skill
    raise KeyError(skill_id)


def _execute_skill(state: WorkflowState, skill_id: str, max_attempts: int = 2) -> SkillResult:
    runner=_runner(skill_id); payload={"skill":skill_id,"plan":state.research_plan.model_dump(mode="json") if state.research_plan else None,"evidence":[item.evidence_id for item in state.evidence_items]}
    last_error=None
    for attempt in range(1,max_attempts+1):
        started=perf_counter(); record_event(state,f"skill:{skill_id}","running",attempt=attempt)
        try:
            output=runner(state); duration=int((perf_counter()-started)*1000)
            mode,model_name=_execution_metadata(skill_id,output)
            result=to_skill_result(skill_id,output,payload,duration,attempt,execution_mode=mode,model_name=model_name)
            record_event(state,f"skill:{skill_id}",result.status,attempt=attempt); return result
        except Exception as exc:
            last_error=exc; record_event(state,f"skill:{skill_id}","retry" if attempt<max_attempts else "failed",str(exc),attempt)
    return SkillResult(skill_id=skill_id,status="fail",failure_code=type(last_error).__name__ if last_error else "unknown",warnings=[str(last_error)],attempt=max_attempts,execution_mode="not_run")


def _publish(state: WorkflowState, main: dict[str,AgentOutput]) -> None:
    state.agent_outputs={key:main[key] for key in MAIN_KEYS if key in main}


def _save(state: WorkflowState, main: dict[str,AgentOutput]) -> WorkflowState:
    _publish(state,main); state.model_usage=collected_usage(); save_run(state,state.run_id); return state


def _stop(request: AnalyzeRequest,*steps: WorkflowStopAfter) -> bool: return request.options.stop_after in steps


def _execute_planned_skills(
    state: WorkflowState,
    required: list[str],
    request: AnalyzeRequest,
    allowed: set[str] | None = None,
) -> None:
    selected_required=[item for item in required if allowed is None or item in allowed]
    groups=state.research_plan.parallel_groups or [selected_required]
    executed={item for item in state.skill_outputs if item in required}
    for group in groups:
        selected=[]
        for skill in group:
            if skill not in selected_required or skill in executed:
                continue
            dependencies=state.research_plan.dependencies.get(skill,[])
            failed=[item for item in dependencies if item in state.skill_outputs and getattr(state.skill_outputs[item],"status",None) not in {"pass","partial"}]
            pending=[item for item in dependencies if item not in state.skill_outputs and item in selected_required]
            if failed:
                state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="dependency_failed",missing_inputs=failed,execution_mode="not_run")
                record_event(state,f"skill:{skill}","skipped",f"依赖失败：{failed}")
                executed.add(skill)
            elif not pending:
                selected.append(skill)
        if not selected:
            continue
        if request.options.enable_parallel and len(selected)>1:
            with ThreadPoolExecutor(max_workers=min(4,len(selected))) as pool:
                futures={skill:pool.submit(copy_context().run,_execute_skill,state,skill) for skill in selected}
                for skill,future in futures.items():
                    try:
                        state.skill_outputs[skill]=future.result(timeout=get_settings().llm_timeout_seconds*2+5)
                    except TimeoutError:
                        state.skill_outputs[skill]=SkillResult(skill_id=skill,status="fail",failure_code="timeout",execution_mode="not_run")
                        record_event(state,f"skill:{skill}","failed","执行超时")
        else:
            for skill in selected:
                state.skill_outputs[skill]=_execute_skill(state,skill)
        executed.update(selected)
    for skill in selected_required:
        if skill in executed:
            continue
        dependencies=state.research_plan.dependencies.get(skill,[])
        if any(item not in state.skill_outputs or getattr(state.skill_outputs[item],"status",None) not in {"pass","partial"} for item in dependencies if item in selected_required):
            state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="dependency_unavailable",missing_inputs=dependencies,execution_mode="not_run")
            record_event(state,f"skill:{skill}","skipped",f"依赖不可用：{dependencies}")
        else:
            state.skill_outputs[skill]=_execute_skill(state,skill)


def run_analysis_workflow(request: AnalyzeRequest) -> WorkflowState:
    start_usage_tracking(); state=WorkflowState(company_profile=request.company_profile,raw_materials=request.materials); main={}
    record_event(state,"planning","running")
    state.research_plan,main["research_planner"]=run_planner_agent(state,request.research_objective,request.investment_horizon,request.initial_view,request.key_question)
    doctrine=run_firm_doctrine_case_retrieval(state)
    state.skill_outputs["doctrine_context"]=to_skill_result("doctrine_context",doctrine,{"mode":state.company_profile.user_mode.value},execution_mode="deterministic")
    record_event(state,"planning","completed",main["research_planner"].summary)
    state.current_stage=WorkflowStopAfter.DOCTRINE.value
    if _stop(request,WorkflowStopAfter.DOCTRINE): return _save(state,main)

    record_event(state,"evidence","running"); organizer=_retry_model_fallback(run_material_organizer_llm,state,run_material_organizer_llm(state))
    organizer_mode,organizer_model=_execution_metadata("material_organization",organizer)
    state.skill_outputs["material_organization"]=to_skill_result("material_organization",organizer,{"materials":[m.title for m in state.raw_materials]},execution_mode=organizer_mode,model_name=organizer_model)
    state.current_stage=WorkflowStopAfter.MATERIAL_ORGANIZER.value
    _sync_graph(state)
    if _stop(request,WorkflowStopAfter.MATERIAL_ORGANIZER): return _save(state,main)
    extractor=_retry_model_fallback(run_evidence_extractor_llm,state,run_evidence_extractor_llm(state))
    evidence_mode,evidence_model=_execution_metadata("evidence_extraction",extractor)
    state.skill_outputs["evidence_extraction"]=to_skill_result("evidence_extraction",extractor,{"sources":[d.source_id for d in state.source_documents]},execution_mode=evidence_mode,model_name=evidence_model)
    state.processing_records=execute_model_pipeline(state.raw_materials,state.evidence_items); _financials(state)
    _sync_graph(state,semantic=True)
    evidence_findings=[*organizer.findings,*extractor.findings]
    main["evidence"]=AgentOutput(agent_name="Evidence Agent",status=AgentStatus.PASS if state.evidence_items else AgentStatus.FAIL,summary=f"建立 {len(state.evidence_items)} 条可追溯证据。",findings=evidence_findings,missing_materials=list(dict.fromkeys([*organizer.missing_materials,*extractor.missing_materials])),confidence=Confidence.MEDIUM if state.evidence_items else Confidence.LOW)
    record_event(state,"evidence","completed",main["evidence"].summary)
    state.current_stage=WorkflowStopAfter.EVIDENCE_EXTRACTOR.value
    if _stop(request,WorkflowStopAfter.EVIDENCE_EXTRACTOR): return _save(state,main)

    usable=sum(bool(item.source_refs) for item in state.evidence_items)
    required=[skill for skill in state.research_plan.required_skills if usable>=state.research_plan.minimum_evidence.get(skill,1)]
    skipped=[skill for skill in state.research_plan.required_skills if skill not in required]
    for skill in skipped: state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="insufficient_evidence",missing_inputs=["可追溯证据"],execution_mode="not_run")
    record_event(state,"analysis","running",f"执行 {required}；跳过 {skipped}")
    focused_stops={
        WorkflowStopAfter.FINANCIAL_QUALITY:["financial_quality_dividend"],
        WorkflowStopAfter.BUSINESS_MODEL:["financial_quality_dividend","business_model_moat"],
        WorkflowStopAfter.MANAGEMENT_VIEW:["financial_quality_dividend","business_model_moat","management_view_comparison"],
    }
    if request.options.stop_after in focused_stops:
        stages=focused_stops[request.options.stop_after]
        for skill in stages:
            _execute_planned_skills(state,required,request,{skill})
            state.current_stage=skill
            if request.options.stop_after.value==skill:
                return _save(state,main)
    else:
        _execute_planned_skills(state,required,request)
    state.research_claims,main["research_analyst"]=run_analyst_agent(state)
    _sync_graph(state)
    record_event(state,"analysis","completed",main["research_analyst"].summary)
    state.current_stage="research_analyst"
    red_output=run_value_trap_contradiction_llm(state); red_mode,red_model=_execution_metadata("value_trap_contradiction",red_output); state.skill_outputs["value_trap_contradiction"]=to_skill_result("value_trap_contradiction",red_output,{"claims":[c.claim_id for c in state.research_claims]},execution_mode=red_mode,model_name=red_model)
    state.research_claims.extend(
        ResearchClaim(
            topic=finding.title,
            statement=finding.detail,
            claim_type="risk",
            supporting_evidence_ids=finding.evidence_ids,
            confidence=finding.confidence,
            source_skill_ids=["value_trap_contradiction"],
            falsification_conditions=[f"若后续证据排除“{finding.title}”所述机制，可降低该风险权重。"],
        )
        for finding in red_output.findings
        if finding.detail
    )
    state.research_judgment=build_research_judgment(state); _sync_graph(state)
    state.current_stage=WorkflowStopAfter.VALUE_TRAP.value
    if _stop(request,WorkflowStopAfter.VALUE_TRAP): return _save(state,main)
    state.pre_memo_gate=run_compliance_gate_llm(state,"pre_memo_gate")
    unavailable=[
        skill for skill in state.research_plan.required_skills
        if skill not in state.skill_outputs or state.skill_outputs[skill].status in {"fail","skipped"}
    ]
    if unavailable:
        state.pre_memo_gate.status="fail"
        state.pre_memo_gate.evidence_issues.append(f"研究计划中的必要 Skills 未完成：{', '.join(unavailable)}")
    state.current_stage=WorkflowStopAfter.PRE_MEMO_GATE.value
    if _stop(request,WorkflowStopAfter.PRE_MEMO_GATE): return _save(state,main)
    state.judge_decisions,main["red_team_judge"]=run_judge_agent(state,state.pre_memo_gate.status)
    _sync_graph(state)
    record_event(state,"judge",main["red_team_judge"].status.value,main["red_team_judge"].summary)
    if state.pre_memo_gate.status!="pass" or not any(item.decision in {"approved","downgraded"} for item in state.judge_decisions):
        state.workflow_status="needs_evidence"
        record_event(state,"writing","running")
        state.memo=run_memo_writing_skill(state)
        _sync_graph(state)
        record_event(state,"writing","completed","生成固定 19 章待补证据草稿。")
    else:
        record_event(state,"writing","running"); state.memo=run_memo_writing_skill(state); _sync_graph(state); record_event(state,"writing","completed")
    state.current_stage=WorkflowStopAfter.MEMO.value
    if _stop(request,WorkflowStopAfter.MEMO): return _save(state,main)
    if not request.options.skip_post_gate:
        state.post_memo_gate=run_compliance_gate_llm(state,"post_memo_gate",state.memo)
        if state.post_memo_gate.status=="fail" and state.workflow_status=="completed": state.workflow_status="needs_revision"
    _sync_graph(state)
    state.current_stage=WorkflowStopAfter.POST_MEMO_GATE.value
    if _stop(request,WorkflowStopAfter.POST_MEMO_GATE): return _save(state,main)
    state.current_stage="complete"; record_event(state,"completed",state.workflow_status); return _save(state,main)


def run_review_workflow(request: ReviewRequest) -> WorkflowState:
    start_usage_tracking()
    if request.company_profile is None:
        from .models import CompanyProfile,UserMode
        profile=CompanyProfile(company_name="未指定公司",industry="未指定行业",user_mode=UserMode.TO_C)
    else: profile=request.company_profile
    state=WorkflowState(company_profile=profile,raw_materials=request.materials); plan,planner=run_planner_agent(state)
    state.research_plan=plan; doctrine=run_firm_doctrine_case_retrieval(state); organizer=_retry_model_fallback(run_material_organizer_llm,state,run_material_organizer_llm(state)); extractor=_retry_model_fallback(run_evidence_extractor_llm,state,run_evidence_extractor_llm(state))
    organizer_mode,organizer_model=_execution_metadata("material_organization",organizer)
    state.skill_outputs["doctrine_context"]=to_skill_result("doctrine_context",doctrine,{"mode":state.company_profile.user_mode.value},execution_mode="deterministic"); state.skill_outputs["material_organization"]=to_skill_result("material_organization",organizer,{},execution_mode=organizer_mode,model_name=organizer_model); evidence_mode,evidence_model=_execution_metadata("evidence_extraction",extractor); state.skill_outputs["evidence_extraction"]=to_skill_result("evidence_extraction",extractor,{},execution_mode=evidence_mode,model_name=evidence_model)
    state.processing_records=execute_model_pipeline(state.raw_materials,state.evidence_items); _financials(state)
    _sync_graph(state,semantic=True)
    review=run_research_coach_review_llm(request.memo_text,state); review_mode,review_model=_execution_metadata("research_coach_review",review); state.skill_outputs["research_coach_review"]=to_skill_result("research_coach_review",review,{"memo":request.memo_text},execution_mode=review_mode,model_name=review_model)
    main={"research_planner":planner,"evidence":AgentOutput(agent_name="Evidence Agent",status=AgentStatus.PASS if state.evidence_items else AgentStatus.PARTIAL,summary=f"建立 {len(state.evidence_items)} 条批改证据。",confidence=Confidence.MEDIUM),"research_analyst":AgentOutput(agent_name="Research Analyst Agent",status=AgentStatus.PASS,summary="已将用户 Memo 拆解为待审查研究表达。",confidence=Confidence.MEDIUM),"red_team_judge":AgentOutput(agent_name="Red Team & Judge Agent",status=review.status,summary=review.summary,findings=review.findings,missing_materials=review.missing_materials,warnings=review.warnings,confidence=review.confidence)}
    _publish(state,main); _sync_graph(state); return _save(state,main)
