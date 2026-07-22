from __future__ import annotations

import json
import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .production import ProductionGuardMiddleware, production_configuration_report

from .auth import authenticate_user, create_access_token, create_user, delete_user_account, get_current_user, get_optional_current_user, init_auth_db, to_auth_user
from .file_parsers import FileParseError, cross_check_multimodal_materials, parse_uploaded_file
from .models import AnalyzeRequest, AnalyzeResponse, AuthResponse, AuthUser, CapabilityProfile, DefenseAnswerRequest, DefenseSession, EvidenceEdgeReview, EvidenceGraph, EvidenceNodeReview, HealthResponse, LoginRequest, MaterialBlockReview, MemoSuggestionDecision, MemoVersion, MemoVersionCreate, ProjectMaterial, RawMaterial, RegisterRequest, ResearchBehaviorEvent, ResearchJudgment, ResearchMap, ResearchProjectCreate, ResearchProjectDetail, ResearchProjectSummary, ResearchProjectUpdate, ResearchRunDetail, ResearchRunSummary, ResearchTask, ResearchTaskUpdate, ReviewRequest, ThesisDraft, ThesisVersion, UrlIngestRequest, ValuationAssumptions, ValuationAnalysis
from .research_map import generate_research_map
from .storage import create_research_project, decide_memo_suggestion, get_defense_session, get_project_evidence_graph, get_research_project, get_user_run, init_research_runs_db, list_behavior_events, list_capability_profiles, list_defense_sessions, list_evidence_graph_versions, list_memo_versions, list_project_materials, list_research_map_versions, list_research_projects, list_research_tasks, list_thesis_versions, list_user_runs, project_belongs_to_user, record_behavior_event, review_evidence_for_material_block, review_project_evidence_edge, review_project_evidence_node, review_project_material_block, save_capability_profile, save_defense_session, save_memo_version, save_research_map_version, save_thesis_version, save_user_run, sync_defense_tasks, update_memo_suggestions, update_research_project, update_research_task, upsert_research_tasks, get_valuation_assumptions, save_valuation_assumptions
from .capability_profile import build_capability_profile
from .defense import answer_defense, start_defense
from .thesis_builder import assess_thesis
from .workflow_runner import run_analysis_workflow, run_review_workflow
from .web_ingestion import WebIngestionError, ingest_web_url
from .memo_coauthor import generate_memo_suggestions
from .llm_client import OpenAIClient
from .task_feedback import tasks_from_memo, tasks_from_research_state, tasks_from_thesis
from .research_quality import assess_graph_quality
from .valuation import analyze_valuation


app = FastAPI(
    title="Value Investing Research Coach",
    version="0.1.0",
    description="Material-package-driven buy-side value investing research training agent.",
)

default_cors_origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:3001",
    "http://localhost:3001",
]
configured_cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_cors_origins + configured_cors_origins,
    allow_origin_regex=os.environ.get("CORS_ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ProductionGuardMiddleware)


@app.on_event("startup")
def startup() -> None:
    report = production_configuration_report(get_settings())
    if get_settings().app_env == "production" and not report["passed"]:
        raise RuntimeError("unsafe production configuration: " + "; ".join(report["errors"]))
    init_auth_db()
    init_research_runs_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/ready")
def ready() -> dict:
    return production_configuration_report(get_settings())


@app.post("/api/materials/ingest-url", response_model=RawMaterial)
def ingest_url(request: UrlIngestRequest) -> RawMaterial:
    try:
        return ingest_web_url(request.url, request.source_type)
    except WebIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest) -> AuthResponse:
    user = create_user(email=request.email, password=request.password, name=request.name)
    auth_user = to_auth_user(user)
    return AuthResponse(access_token=create_access_token(user.user_id), user=auth_user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user = authenticate_user(email=request.email, password=request.password)
    auth_user = to_auth_user(user)
    return AuthResponse(access_token=create_access_token(user.user_id), user=auth_user)


@app.get("/api/me", response_model=AuthUser)
def me(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return current_user


@app.delete("/api/me", status_code=204)
def delete_me(current_user: AuthUser = Depends(get_current_user)) -> None:
    delete_user_account(current_user.user_id)


def _validate_project_access(current_user: AuthUser | None, project_id: str | None) -> None:
    if not project_id:
        return
    if not current_user:
        raise HTTPException(status_code=401, detail="研究项目功能需要登录")
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, current_user: AuthUser | None = Depends(get_optional_current_user)) -> AnalyzeResponse:
    _validate_project_access(current_user, request.project_id)
    state = run_analysis_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="analysis", state=state, project_id=request.project_id)
    return AnalyzeResponse(run_id=state.run_id, status=state.workflow_status, state=state)


@app.post("/api/analyze-files", response_model=AnalyzeResponse)
async def analyze_files(
    company_profile: str = Form(...),
    project_id: str | None = Form(None),
    options: str | None = Form(None),
    text_materials: str | None = Form(None),
    research_context: str | None = Form(None),
    material_ids: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
    current_user: AuthUser | None = Depends(get_optional_current_user),
) -> AnalyzeResponse:
    try:
        context_payload = json.loads(research_context) if research_context else {}
        payload = {
            "project_id": project_id,
            "company_profile": json.loads(company_profile),
            "materials": json.loads(text_materials) if text_materials else [],
            "options": json.loads(options) if options else {},
            **context_payload,
        }
        request = AnalyzeRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"请求参数解析失败：{exc}") from exc

    if material_ids and len(material_ids) != len(files):
        raise HTTPException(status_code=400, detail="material_ids 数量必须与 files 数量一致")
    settings = get_settings()
    if len(files) > settings.max_files_per_request:
        raise HTTPException(status_code=413, detail=f"单次最多上传 {settings.max_files_per_request} 个文件")

    for index, upload in enumerate(files):
        data = await upload.read()
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail=f"文件 {upload.filename or index} 超过大小限制")
        material_id = material_ids[index] if index < len(material_ids) else None
        try:
            material = parse_uploaded_file(
                filename=upload.filename or f"uploaded-{index}",
                data=data,
                material_id=material_id,
                title=upload.filename,
            )
        except FileParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        request.materials.append(material)

    if not request.materials:
        raise HTTPException(status_code=400, detail="请至少提供一份文本资料或上传文件")

    cross_check_multimodal_materials(request.materials)

    _validate_project_access(current_user, request.project_id)
    state = run_analysis_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="analysis", state=state, project_id=request.project_id)
    return AnalyzeResponse(run_id=state.run_id, status=state.workflow_status, state=state)


@app.post("/api/review", response_model=AnalyzeResponse)
def review(request: ReviewRequest, current_user: AuthUser | None = Depends(get_optional_current_user)) -> AnalyzeResponse:
    _validate_project_access(current_user, request.project_id)
    state = run_review_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="review", state=state, project_id=request.project_id)
    return AnalyzeResponse(run_id=state.run_id, status=state.workflow_status, state=state)


@app.get("/api/runs", response_model=list[ResearchRunSummary])
def runs(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
) -> list[ResearchRunSummary]:
    return list_user_runs(current_user.user_id, limit=limit)


@app.get("/api/runs/{run_id}", response_model=ResearchRunDetail)
def run_detail(run_id: str, current_user: AuthUser = Depends(get_current_user)) -> ResearchRunDetail:
    detail = get_user_run(current_user.user_id, run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究记录")
    return detail


@app.post("/api/projects", response_model=ResearchProjectSummary)
def create_project(
    request: ResearchProjectCreate,
    current_user: AuthUser = Depends(get_current_user),
) -> ResearchProjectSummary:
    return create_research_project(current_user.user_id, request)


@app.get("/api/projects", response_model=list[ResearchProjectSummary])
def projects(
    include_archived: bool = Query(default=False),
    current_user: AuthUser = Depends(get_current_user),
) -> list[ResearchProjectSummary]:
    return list_research_projects(current_user.user_id, include_archived=include_archived)


@app.get("/api/projects/{project_id}", response_model=ResearchProjectDetail)
def project_detail(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> ResearchProjectDetail:
    detail = get_research_project(current_user.user_id, project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return detail


@app.get("/api/projects/{project_id}/materials", response_model=list[ProjectMaterial])
def project_materials(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ProjectMaterial]:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_project_materials(current_user.user_id, project_id)


@app.patch("/api/projects/{project_id}/materials/{material_id}/blocks/{block_id}", response_model=ProjectMaterial)
def review_material_block(project_id: str, material_id: str, block_id: str, request: MaterialBlockReview, current_user: AuthUser = Depends(get_current_user)) -> ProjectMaterial:
    material = review_project_material_block(current_user.user_id, project_id, material_id, block_id, request)
    if material is None:
        raise HTTPException(status_code=404, detail="未找到该材料或内容块")
    review_evidence_for_material_block(current_user.user_id, project_id, block_id, request.confirmed, request.note)
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="review_multimodal_inference", dimension="evidence_awareness", outcome="confirmed" if request.confirmed else "rejected", score=85, object_type="content_block", object_id=block_id))
    return material


@app.patch("/api/projects/{project_id}", response_model=ResearchProjectDetail)
def update_project(
    project_id: str,
    request: ResearchProjectUpdate,
    current_user: AuthUser = Depends(get_current_user),
) -> ResearchProjectDetail:
    detail = update_research_project(current_user.user_id, project_id, request)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return detail


@app.post("/api/projects/{project_id}/archive", response_model=ResearchProjectDetail)
def archive_project(
    project_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> ResearchProjectDetail:
    detail = update_research_project(
        current_user.user_id,
        project_id,
        ResearchProjectUpdate(status="archived"),
    )
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return detail


@app.get("/api/projects/{project_id}/evidence-graph", response_model=EvidenceGraph)
def project_evidence_graph(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> EvidenceGraph:
    graph = get_project_evidence_graph(current_user.user_id, project_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="该项目尚未生成证据图谱")
    return graph


@app.get("/api/projects/{project_id}/evidence-graph/history", response_model=list[EvidenceGraph])
def project_evidence_graph_history(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[EvidenceGraph]:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_evidence_graph_versions(current_user.user_id, project_id)


@app.patch("/api/projects/{project_id}/evidence-graph/nodes/{node_id}", response_model=EvidenceGraph)
def review_evidence_node(project_id: str, node_id: str, request: EvidenceNodeReview, current_user: AuthUser = Depends(get_current_user)) -> EvidenceGraph:
    graph = review_project_evidence_node(current_user.user_id, project_id, node_id, request)
    if graph is None:
        raise HTTPException(status_code=404, detail="未找到该项目或证据节点")
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="review_evidence", dimension="evidence_awareness", outcome=request.verification_status.value, score=90 if request.verification_status.value in {"verified", "unsupported"} else 70, object_type="evidence_node", object_id=node_id))
    return graph


@app.patch("/api/projects/{project_id}/evidence-graph/edges/{edge_id}", response_model=EvidenceGraph)
def review_evidence_edge(project_id: str, edge_id: str, request: EvidenceEdgeReview, current_user: AuthUser = Depends(get_current_user)) -> EvidenceGraph:
    graph = review_project_evidence_edge(current_user.user_id, project_id, edge_id, request)
    if graph is None:
        raise HTTPException(status_code=404, detail="未找到该项目或证据关系")
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="correct_evidence_relation", dimension="evidence_awareness", outcome=request.relation.value, score=90, object_type="evidence_edge", object_id=edge_id))
    return graph


@app.get("/api/projects/{project_id}/research-map", response_model=ResearchMap)
def project_research_map(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> ResearchMap:
    detail = get_research_project(current_user.user_id, project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    project = detail.project
    history = list_research_map_versions(current_user.user_id, project_id)
    generated = generate_research_map(project_id, project.company_profile.industry, graph, company_name=project.company_profile.company_name, research_objective=project.research_objective, investment_horizon=project.investment_horizon, initial_view=project.initial_view, key_question=project.key_question, previous=history[-1] if history else None)
    return save_research_map_version(current_user.user_id, generated)


@app.get("/api/projects/{project_id}/research-map/history", response_model=list[ResearchMap])
def project_research_map_history(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ResearchMap]:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_research_map_versions(current_user.user_id, project_id)


@app.get("/api/projects/{project_id}/research-judgment", response_model=ResearchJudgment)
def project_research_judgment(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> ResearchJudgment:
    detail = get_research_project(current_user.user_id, project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    if not detail.timeline:
        return ResearchJudgment()
    latest = get_user_run(current_user.user_id, detail.timeline[-1].run_id)
    return latest.state.research_judgment if latest else ResearchJudgment()

@app.get("/api/projects/{project_id}/research-quality")
def project_research_quality(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> dict:
    detail = get_research_project(current_user.user_id, project_id)
    if not detail: raise HTTPException(status_code=404, detail="未找到该研究项目")
    latest = get_user_run(current_user.user_id, detail.timeline[-1].run_id) if detail.timeline else None
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    live_quality = assess_graph_quality(graph)
    if not latest: return {"valuation_analysis": {}, "financial_anomalies": [], "evidence_graph_quality": live_quality.model_dump(mode="json")}
    assumptions=get_valuation_assumptions(current_user.user_id,project_id)
    valuation=analyze_valuation(latest.state.evidence_items,detail.project.company_profile.industry,assumptions)
    return {"valuation_analysis": valuation.model_dump(mode="json"), "valuation_assumptions": assumptions.model_dump(mode="json"), "financial_anomalies": [item.model_dump(mode="json") for item in latest.state.financial_anomalies], "evidence_graph_quality": live_quality.model_dump(mode="json")}

@app.put("/api/projects/{project_id}/valuation-assumptions", response_model=ValuationAnalysis)
def update_valuation_assumptions(project_id: str, request: ValuationAssumptions, current_user: AuthUser = Depends(get_current_user)) -> ValuationAnalysis:
    detail=get_research_project(current_user.user_id,project_id)
    if not detail or not detail.timeline: raise HTTPException(status_code=404,detail="未找到可估值的研究项目")
    if request.terminal_growth >= min(request.wacc,request.cost_of_equity): raise HTTPException(status_code=400,detail="永续增长率必须低于WACC和股权成本")
    if not request.bear_growth <= request.base_growth <= request.bull_growth: raise HTTPException(status_code=400,detail="增长率必须满足悲观情景 ≤ 基准情景 ≤ 乐观情景")
    saved=save_valuation_assumptions(current_user.user_id,project_id,request)
    latest=get_user_run(current_user.user_id,detail.timeline[-1].run_id)
    if not latest: raise HTTPException(status_code=404,detail="未找到研究记录")
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id,project_id=project_id,action="confirm_valuation_assumptions",dimension="valuation",outcome="confirmed" if saved.confirmed else "draft",score=90 if saved.confirmed else 70,object_type="valuation_assumptions",object_id=project_id))
    return analyze_valuation(latest.state.evidence_items,detail.project.company_profile.industry,saved)

@app.get("/api/capability-profile/current", response_model=CapabilityProfile)
def current_capability_profile(current_user: AuthUser = Depends(get_current_user)) -> CapabilityProfile:
    run_details = [detail for summary in list_user_runs(current_user.user_id, limit=100) if (detail := get_user_run(current_user.user_id, summary.run_id))]
    projects = list_research_projects(current_user.user_id, include_archived=True)
    theses = [thesis for project in projects for thesis in list_thesis_versions(current_user.user_id, project.project_id)]
    defenses = list_defense_sessions(current_user.user_id)
    return build_capability_profile(current_user.user_id, run_details, theses, defenses, list_behavior_events(current_user.user_id))


@app.post("/api/projects/{project_id}/thesis", response_model=ThesisVersion)
def create_thesis_version(project_id: str, request: ThesisDraft, current_user: AuthUser = Depends(get_current_user)) -> ThesisVersion:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    history = list_thesis_versions(current_user.user_id, project_id)
    thesis = ThesisVersion(project_id=project_id, version=len(history) + 1, draft=request, assessment=assess_thesis(request, graph), evidence_graph_version=graph.version)
    saved = save_thesis_version(current_user.user_id, thesis)
    upsert_research_tasks(current_user.user_id, tasks_from_thesis(saved), project_id)
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="save_thesis", dimension="counter_evidence", outcome=saved.assessment.status.value, score=saved.assessment.evidence_coverage, object_type="thesis", object_id=saved.thesis_id, metadata={"error_code": saved.assessment.issues[0] if saved.assessment.issues else ""}))
    return saved


@app.get("/api/projects/{project_id}/thesis", response_model=list[ThesisVersion])
def thesis_history(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ThesisVersion]:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_thesis_versions(current_user.user_id, project_id)


@app.get("/api/projects/{project_id}/memo-versions", response_model=list[MemoVersion])
def memo_versions(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[MemoVersion]:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_memo_versions(current_user.user_id, project_id)


@app.post("/api/projects/{project_id}/memo-versions", response_model=MemoVersion)
def create_memo_version(project_id: str, request: MemoVersionCreate, current_user: AuthUser = Depends(get_current_user)) -> MemoVersion:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    version = save_memo_version(current_user.user_id, project_id, request)
    upsert_research_tasks(current_user.user_id, tasks_from_memo(version), project_id)
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="save_memo_version", dimension="memo_writing", outcome=version.gate_status, score=100 if version.gate_status == "formal" else 45 if version.gate_issues else 75, object_type="memo_version", object_id=version.memo_version_id, metadata={"error_code": version.gate_issues[0] if version.gate_issues else ""}))
    return version


@app.post("/api/projects/{project_id}/memo-versions/{memo_version_id}/suggestions", response_model=MemoVersion)
def create_memo_suggestions(project_id: str, memo_version_id: str, current_user: AuthUser = Depends(get_current_user)) -> MemoVersion:
    version = next((item for item in list_memo_versions(current_user.user_id, project_id) if item.memo_version_id == memo_version_id), None)
    if not version: raise HTTPException(status_code=404, detail="未找到该 Memo 版本")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    return update_memo_suggestions(current_user.user_id, version, generate_memo_suggestions(version.sections, graph, OpenAIClient()))


@app.patch("/api/projects/{project_id}/memo-versions/{memo_version_id}/suggestions/{suggestion_id}", response_model=MemoVersion)
def update_memo_suggestion(project_id: str, memo_version_id: str, suggestion_id: str, request: MemoSuggestionDecision, current_user: AuthUser = Depends(get_current_user)) -> MemoVersion:
    version = decide_memo_suggestion(current_user.user_id, project_id, memo_version_id, suggestion_id, request.status)
    if not version: raise HTTPException(status_code=400, detail="未找到建议或状态无效")
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="decide_memo_suggestion", dimension="memo_writing", outcome=request.status, score=80, object_type="memo_suggestion", object_id=suggestion_id))
    return version


@app.post("/api/projects/{project_id}/defense", response_model=DefenseSession)
def create_defense(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> DefenseSession:
    theses = list_thesis_versions(current_user.user_id, project_id)
    if not theses:
        raise HTTPException(status_code=400, detail="请先完成 Thesis Builder")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    prior_errors = [str(event.metadata.get("error_code")) for event in list_behavior_events(current_user.user_id) if event.project_id != project_id and event.metadata.get("error_code")]
    return save_defense_session(current_user.user_id, start_defense(project_id, theses[-1], graph, prior_errors=prior_errors[-10:]))


@app.post("/api/defense/{session_id}/answer", response_model=DefenseSession)
def submit_defense_answer(session_id: str, request: DefenseAnswerRequest, current_user: AuthUser = Depends(get_current_user)) -> DefenseSession:
    session = get_defense_session(current_user.user_id, session_id)
    if not session: raise HTTPException(status_code=404, detail="未找到答辩会话")
    theses = list_thesis_versions(current_user.user_id, session.project_id)
    thesis = next((item for item in theses if item.thesis_id == session.thesis_id), None)
    if not thesis: raise HTTPException(status_code=404, detail="答辩对应的 Thesis 已不存在")
    graph = get_project_evidence_graph(current_user.user_id, session.project_id) or EvidenceGraph()
    try: session = answer_defense(session, thesis, graph, request.answer, request.evidence_ids)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    saved = save_defense_session(current_user.user_id, session)
    sync_defense_tasks(current_user.user_id, saved)
    latest = saved.turns[-2] if saved.turns and saved.turns[-1].answer is None and len(saved.turns) > 1 else saved.turns[-1]
    if latest.score is not None:
        dimension = {"risk_manager":"counter_evidence","financial_researcher":"financial_analysis","industry_researcher":"industry_understanding","portfolio_manager":"thesis_reasoning","investment_director":"valuation"}.get(latest.role.value, "defense")
        record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=saved.project_id, action="answer_defense", dimension=dimension, outcome="passed" if latest.passed else "needs_improvement", score=latest.score, object_type="defense_turn", object_id=latest.turn_id, metadata={"error_code": latest.feedback or ""}))
    return saved


@app.get("/api/projects/{project_id}/defense", response_model=list[DefenseSession])
def project_defenses(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[DefenseSession]:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_defense_sessions(current_user.user_id, project_id)


@app.get("/api/projects/{project_id}/tasks", response_model=list[ResearchTask])
def project_tasks(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ResearchTask]:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    detail = get_research_project(current_user.user_id, project_id)
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    project = detail.project
    history = list_research_map_versions(current_user.user_id, project_id)
    research_map = generate_research_map(project_id, project.company_profile.industry, graph, company_name=project.company_profile.company_name, research_objective=project.research_objective, investment_horizon=project.investment_horizon, initial_view=project.initial_view, key_question=project.key_question, previous=history[-1] if history else None)
    save_research_map_version(current_user.user_id, research_map)
    return upsert_research_tasks(current_user.user_id, tasks_from_research_state(project_id, research_map, graph), project_id)


@app.patch("/api/projects/{project_id}/tasks/{task_id}", response_model=ResearchTask)
def update_project_task(project_id: str, task_id: str, request: ResearchTaskUpdate, current_user: AuthUser = Depends(get_current_user)) -> ResearchTask:
    try:
        task = update_research_task(current_user.user_id, project_id, task_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if task is None: raise HTTPException(status_code=404, detail="未找到研究任务")
    record_behavior_event(ResearchBehaviorEvent(user_id=current_user.user_id, project_id=project_id, action="complete_research_task" if task.status == "completed" else "reopen_research_task", dimension="evidence_awareness", outcome=task.status, score=95 if task.status == "completed" else 60, object_type="research_task", object_id=task.task_id))
    return task


@app.post("/api/capability-profile", response_model=CapabilityProfile)
def refresh_capability_profile(current_user: AuthUser = Depends(get_current_user)) -> CapabilityProfile:
    run_details = [detail for summary in list_user_runs(current_user.user_id, limit=100) if (detail := get_user_run(current_user.user_id, summary.run_id))]
    projects = list_research_projects(current_user.user_id, include_archived=True)
    theses = [thesis for project in projects for thesis in list_thesis_versions(current_user.user_id, project.project_id)]
    defenses = list_defense_sessions(current_user.user_id)
    return save_capability_profile(build_capability_profile(current_user.user_id, run_details, theses, defenses, list_behavior_events(current_user.user_id)))


@app.get("/api/behavior-events", response_model=list[ResearchBehaviorEvent])
def behavior_events(limit: int = Query(default=200, ge=1, le=1000), current_user: AuthUser = Depends(get_current_user)) -> list[ResearchBehaviorEvent]:
    return list_behavior_events(current_user.user_id, limit)


@app.get("/api/capability-profile/history", response_model=list[CapabilityProfile])
def capability_profile_history(limit: int = Query(default=30, ge=1, le=100), current_user: AuthUser = Depends(get_current_user)) -> list[CapabilityProfile]:
    return list_capability_profiles(current_user.user_id, limit)
