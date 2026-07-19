from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .agents import (
    run_firm_doctrine_case_retrieval,
    run_gate_blocked_memo,
)
from .llm_agents import (
    run_business_model_moat_llm,
    run_compliance_gate_llm,
    run_evidence_extractor_llm,
    run_financial_quality_dividend_llm,
    run_management_view_comparison_llm,
    run_material_organizer_llm,
    run_research_coach_review_llm,
    run_research_memo_generator_llm,
    run_value_trap_contradiction_llm,
)
from .models import AnalyzeRequest, ReviewRequest, WorkflowState, WorkflowStopAfter
from .evidence_graph import build_evidence_graph
from .storage import save_run
from .llm_client import OpenAIClient
from .model_pipeline import pipeline_records


def _should_stop(request: AnalyzeRequest, step: WorkflowStopAfter) -> bool:
    return request.options.stop_after == step


def _save_and_return(state: WorkflowState) -> WorkflowState:
    save_run(state, state.run_id)
    return state


def run_analysis_workflow(request: AnalyzeRequest) -> WorkflowState:
    state = WorkflowState(
        company_profile=request.company_profile,
        raw_materials=request.materials,
    )

    doctrine = run_firm_doctrine_case_retrieval(state)
    state.agent_outputs["firm_doctrine_case_retrieval"] = doctrine
    if _should_stop(request, WorkflowStopAfter.DOCTRINE):
        return _save_and_return(state)

    organizer = run_material_organizer_llm(state)
    state.agent_outputs["material_organizer"] = organizer
    if _should_stop(request, WorkflowStopAfter.MATERIAL_ORGANIZER):
        return _save_and_return(state)

    extractor = run_evidence_extractor_llm(state)
    state.agent_outputs["evidence_extractor"] = extractor
    if _should_stop(request, WorkflowStopAfter.EVIDENCE_EXTRACTOR):
        return _save_and_return(state)

    if request.options.enable_parallel:
        with ThreadPoolExecutor(max_workers=2) as executor:
            financial_future = executor.submit(run_financial_quality_dividend_llm, state)
            business_future = executor.submit(run_business_model_moat_llm, state)
            financial = financial_future.result()
            business = business_future.result()
    else:
        financial = run_financial_quality_dividend_llm(state)
        business = run_business_model_moat_llm(state)

    state.agent_outputs["financial_quality_dividend"] = financial
    state.agent_outputs["business_model_moat"] = business
    if _should_stop(request, WorkflowStopAfter.FINANCIAL_QUALITY) or _should_stop(request, WorkflowStopAfter.BUSINESS_MODEL):
        return _save_and_return(state)

    views = run_management_view_comparison_llm(state)
    state.agent_outputs["management_view_comparison"] = views
    if _should_stop(request, WorkflowStopAfter.MANAGEMENT_VIEW):
        return _save_and_return(state)

    traps = run_value_trap_contradiction_llm(state)
    state.agent_outputs["value_trap_contradiction"] = traps
    if _should_stop(request, WorkflowStopAfter.VALUE_TRAP):
        return _save_and_return(state)

    state.evidence_graph = build_evidence_graph(state)
    state.pre_memo_gate = run_compliance_gate_llm(state, "pre_memo_gate")
    if _should_stop(request, WorkflowStopAfter.PRE_MEMO_GATE):
        return _save_and_return(state)

    if state.pre_memo_gate.status == "fail":
        state.workflow_status = "needs_evidence"
        state.memo = run_gate_blocked_memo(state)
    else:
        state.memo = run_research_memo_generator_llm(state)
    if _should_stop(request, WorkflowStopAfter.MEMO):
        return _save_and_return(state)

    if not request.options.skip_post_gate:
        state.post_memo_gate = run_compliance_gate_llm(state, "post_memo_gate", state.memo)
        if state.post_memo_gate.status == "fail" and state.workflow_status == "completed":
            state.workflow_status = "needs_revision"
    state.evidence_graph = build_evidence_graph(state)
    state.processing_records = pipeline_records(state.raw_materials, state.evidence_items, OpenAIClient().available)

    return _save_and_return(state)


def run_review_workflow(request: ReviewRequest) -> WorkflowState:
    company_profile = request.company_profile
    if company_profile is None:
        from .models import CompanyProfile, UserMode

        company_profile = CompanyProfile(
            company_name="未指定公司",
            industry="未指定行业",
            user_mode=UserMode.TO_C,
        )

    state = WorkflowState(
        company_profile=company_profile,
        raw_materials=request.materials,
    )

    doctrine = run_firm_doctrine_case_retrieval(state)
    state.agent_outputs["firm_doctrine_case_retrieval"] = doctrine

    organizer = run_material_organizer_llm(state)
    state.agent_outputs["material_organizer"] = organizer

    extractor = run_evidence_extractor_llm(state)
    state.agent_outputs["evidence_extractor"] = extractor

    review = run_research_coach_review_llm(request.memo_text, state)
    state.agent_outputs["research_coach_review"] = review
    state.evidence_graph = build_evidence_graph(state)
    state.processing_records = pipeline_records(state.raw_materials, state.evidence_items, OpenAIClient().available)

    save_run(state, state.run_id)
    return state
