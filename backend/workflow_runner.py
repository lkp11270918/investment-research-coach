from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from contextvars import copy_context
from time import perf_counter

from .agent_architecture import record_event
from .agents import run_business_model_moat, run_compliance_gate, run_financial_quality_dividend, run_gate_blocked_memo, run_management_view_comparison, run_material_organizer, run_value_trap_contradiction
from .config import get_settings
from .evidence_graph import build_evidence_graph
from .financial_calculations import calculate_financial_metrics
from .llm_agents import run_evidence_extractor_llm, run_research_coach_review_llm
from .llm_client import OpenAIClient, collected_usage, start_usage_tracking
from .memo_writing import run_memo_writing_skill
from .model_pipeline import execute_model_pipeline
from .models import AgentFinding, AgentOutput, AgentStatus, AnalyzeRequest, Confidence, ReviewRequest, SkillResult, WorkflowState, WorkflowStopAfter
from .research_agents import run_analyst_agent, run_judge_agent, run_planner_agent, to_skill_result
from .research_judgment import build_research_judgment
from .research_quality import assess_graph_quality, detect_financial_anomalies
from .storage import save_run
from .valuation import analyze_valuation

MAIN_KEYS=("research_planner","evidence","research_analyst","red_team_judge")


def _financials(state: WorkflowState) -> None:
    records,derived=calculate_financial_metrics(state.evidence_items); state.financial_calculations=records
    existing={(item.metric_name,item.period) for item in state.evidence_items}; state.evidence_items.extend(item for item in derived if (item.metric_name,item.period) not in existing)
    state.financial_anomalies=detect_financial_anomalies(state.evidence_items); state.valuation_analysis=analyze_valuation(state.evidence_items,state.company_profile.industry)


def _valuation_output(state: WorkflowState) -> AgentOutput:
    value=state.valuation_analysis
    return AgentOutput(agent_name="Valuation & Margin of Safety Skill",status=AgentStatus.PASS if value.scenarios else AgentStatus.PARTIAL,summary=value.conclusion,findings=[AgentFinding(title="估值方法",detail=f"{value.method or '未确定'}：{value.method_reason or value.conclusion}",classification="reasoning",evidence_ids=value.evidence_ids,confidence=Confidence.MEDIUM)],missing_materials=value.missing_inputs,warnings=value.warnings,confidence=Confidence.MEDIUM)


def _runner(skill_id: str):
    if skill_id=="financial_quality_dividend": return run_financial_quality_dividend
    if skill_id=="management_view_comparison": return run_management_view_comparison
    if skill_id=="valuation_margin": return _valuation_output
    if skill_id in {"bank_analysis","manufacturing_analysis","consumer_analysis","utility_analysis","general_business_analysis"}: return run_business_model_moat
    raise KeyError(skill_id)


def _execute_skill(state: WorkflowState, skill_id: str, max_attempts: int = 2) -> SkillResult:
    runner=_runner(skill_id); payload={"skill":skill_id,"plan":state.research_plan.model_dump(mode="json") if state.research_plan else None,"evidence":[item.evidence_id for item in state.evidence_items]}
    last_error=None
    for attempt in range(1,max_attempts+1):
        started=perf_counter(); record_event(state,f"skill:{skill_id}","running",attempt=attempt)
        try:
            output=runner(state); duration=int((perf_counter()-started)*1000)
            result=to_skill_result(skill_id,output,payload,duration,attempt)
            record_event(state,f"skill:{skill_id}",result.status,attempt=attempt); return result
        except Exception as exc:
            last_error=exc; record_event(state,f"skill:{skill_id}","retry" if attempt<max_attempts else "failed",str(exc),attempt)
    return SkillResult(skill_id=skill_id,status="fail",failure_code=type(last_error).__name__ if last_error else "unknown",warnings=[str(last_error)],attempt=max_attempts)


def _publish(state: WorkflowState, main: dict[str,AgentOutput]) -> None:
    state.agent_outputs={key:main[key] for key in MAIN_KEYS if key in main}


def _save(state: WorkflowState, main: dict[str,AgentOutput]) -> WorkflowState:
    _publish(state,main); state.model_usage=collected_usage(); save_run(state,state.run_id); return state


def _stop(request: AnalyzeRequest,*steps: WorkflowStopAfter) -> bool: return request.options.stop_after in steps


def run_analysis_workflow(request: AnalyzeRequest) -> WorkflowState:
    start_usage_tracking(); state=WorkflowState(company_profile=request.company_profile,raw_materials=request.materials); main={}
    record_event(state,"planning","running")
    state.research_plan,main["research_planner"]=run_planner_agent(state,request.research_objective,request.investment_horizon,request.initial_view,request.key_question)
    record_event(state,"planning","completed",main["research_planner"].summary)
    if _stop(request,WorkflowStopAfter.DOCTRINE): return _save(state,main)

    record_event(state,"evidence","running"); organizer=run_material_organizer(state); extractor=run_evidence_extractor_llm(state)
    state.skill_outputs["material_organization"]=to_skill_result("material_organization",organizer,{"materials":[m.title for m in state.raw_materials]})
    state.skill_outputs["evidence_extraction"]=to_skill_result("evidence_extraction",extractor,{"sources":[d.source_id for d in state.source_documents]})
    state.processing_records=execute_model_pipeline(state.raw_materials,state.evidence_items); _financials(state)
    state.evidence_graph=build_evidence_graph(state,OpenAIClient()); state.evidence_graph_quality=assess_graph_quality(state.evidence_graph)
    evidence_findings=[*organizer.findings,*extractor.findings]
    main["evidence"]=AgentOutput(agent_name="Evidence Agent",status=AgentStatus.PASS if state.evidence_items else AgentStatus.FAIL,summary=f"建立 {len(state.evidence_items)} 条可追溯证据。",findings=evidence_findings,missing_materials=list(dict.fromkeys([*organizer.missing_materials,*extractor.missing_materials])),confidence=Confidence.MEDIUM if state.evidence_items else Confidence.LOW)
    record_event(state,"evidence","completed",main["evidence"].summary)
    if _stop(request,WorkflowStopAfter.MATERIAL_ORGANIZER,WorkflowStopAfter.EVIDENCE_EXTRACTOR): return _save(state,main)

    usable=sum(bool(item.source_refs) for item in state.evidence_items)
    required=[skill for skill in state.research_plan.required_skills if usable>=state.research_plan.minimum_evidence.get(skill,1)]
    skipped=[skill for skill in state.research_plan.required_skills if skill not in required]
    for skill in skipped: state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="insufficient_evidence",missing_inputs=["可追溯证据"])
    record_event(state,"analysis","running",f"执行 {required}；跳过 {skipped}")
    groups=state.research_plan.parallel_groups or [required]
    executed=set()
    for group in groups:
        selected=[]
        for skill in group:
            if skill not in required or skill in executed: continue
            dependencies=state.research_plan.dependencies.get(skill,[])
            failed_dependencies=[item for item in dependencies if item in state.skill_outputs and getattr(state.skill_outputs[item],"status",None) not in {"pass","partial"}]
            pending_dependencies=[item for item in dependencies if item not in state.skill_outputs]
            if failed_dependencies:
                state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="dependency_failed",missing_inputs=failed_dependencies); executed.add(skill)
            elif not pending_dependencies: selected.append(skill)
        if not selected: continue
        if request.options.enable_parallel and len(selected)>1:
            with ThreadPoolExecutor(max_workers=min(4,len(selected))) as pool:
                futures={skill:pool.submit(copy_context().run,_execute_skill,state,skill) for skill in selected}
                for skill,future in futures.items():
                    try: state.skill_outputs[skill]=future.result(timeout=get_settings().llm_timeout_seconds*2+5)
                    except TimeoutError: state.skill_outputs[skill]=SkillResult(skill_id=skill,status="fail",failure_code="timeout")
        else:
            for skill in selected: state.skill_outputs[skill]=_execute_skill(state,skill)
        executed.update(selected)
    for skill in required:
        if skill not in executed:
            dependencies=state.research_plan.dependencies.get(skill,[])
            if any(item not in state.skill_outputs or getattr(state.skill_outputs[item],"status",None) not in {"pass","partial"} for item in dependencies):
                state.skill_outputs[skill]=SkillResult(skill_id=skill,status="skipped",failure_code="dependency_unavailable",missing_inputs=dependencies)
            else: state.skill_outputs[skill]=_execute_skill(state,skill)
    state.research_claims,main["research_analyst"]=run_analyst_agent(state)
    record_event(state,"analysis","completed",main["research_analyst"].summary)
    if _stop(request,WorkflowStopAfter.FINANCIAL_QUALITY,WorkflowStopAfter.BUSINESS_MODEL,WorkflowStopAfter.MANAGEMENT_VIEW): return _save(state,main)

    red_output=run_value_trap_contradiction(state); state.skill_outputs["value_trap_contradiction"]=to_skill_result("red_team_checks",red_output,{"claims":[c.claim_id for c in state.research_claims]})
    state.research_judgment=build_research_judgment(state); state.pre_memo_gate=run_compliance_gate(state,"pre_memo_gate")
    state.judge_decisions,main["red_team_judge"]=run_judge_agent(state,state.pre_memo_gate.status)
    record_event(state,"judge",main["red_team_judge"].status.value,main["red_team_judge"].summary)
    if _stop(request,WorkflowStopAfter.VALUE_TRAP,WorkflowStopAfter.PRE_MEMO_GATE): return _save(state,main)

    if state.pre_memo_gate.status!="pass" or not any(item.decision in {"approved","downgraded"} for item in state.judge_decisions):
        state.workflow_status="needs_evidence"; state.memo=run_gate_blocked_memo(state)
    else:
        record_event(state,"writing","running"); state.memo=run_memo_writing_skill(state); record_event(state,"writing","completed")
    if not request.options.skip_post_gate:
        state.post_memo_gate=run_compliance_gate(state,"post_memo_gate",state.memo)
        if state.post_memo_gate.status=="fail" and state.workflow_status=="completed": state.workflow_status="needs_revision"
    record_event(state,"completed",state.workflow_status); return _save(state,main)


def run_review_workflow(request: ReviewRequest) -> WorkflowState:
    start_usage_tracking()
    if request.company_profile is None:
        from .models import CompanyProfile,UserMode
        profile=CompanyProfile(company_name="未指定公司",industry="未指定行业",user_mode=UserMode.TO_C)
    else: profile=request.company_profile
    state=WorkflowState(company_profile=profile,raw_materials=request.materials); plan,planner=run_planner_agent(state)
    state.research_plan=plan; organizer=run_material_organizer(state); extractor=run_evidence_extractor_llm(state); review=run_research_coach_review_llm(request.memo_text,state)
    state.skill_outputs["material_organization"]=to_skill_result("material_organization",organizer,{}); state.skill_outputs["evidence_extraction"]=to_skill_result("evidence_extraction",extractor,{}); state.skill_outputs["research_coach_review"]=to_skill_result("research_coach_review",review,{"memo":request.memo_text})
    state.evidence_graph=build_evidence_graph(state,OpenAIClient())
    main={"research_planner":planner,"evidence":AgentOutput(agent_name="Evidence Agent",status=AgentStatus.PASS if state.evidence_items else AgentStatus.PARTIAL,summary=f"建立 {len(state.evidence_items)} 条批改证据。",confidence=Confidence.MEDIUM),"research_analyst":AgentOutput(agent_name="Research Analyst Agent",status=AgentStatus.PASS,summary="已将用户 Memo 拆解为待审查研究表达。",confidence=Confidence.MEDIUM),"red_team_judge":AgentOutput(agent_name="Red Team & Judge Agent",status=review.status,summary=review.summary,findings=review.findings,missing_materials=review.missing_materials,warnings=review.warnings,confidence=review.confidence)}
    return _save(state,main)
