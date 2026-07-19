from __future__ import annotations

import json
import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .auth import authenticate_user, create_access_token, create_user, get_current_user, get_optional_current_user, init_auth_db, to_auth_user
from .file_parsers import FileParseError, cross_check_multimodal_materials, parse_uploaded_file
from .models import AnalyzeRequest, AnalyzeResponse, AuthResponse, AuthUser, CapabilityProfile, DefenseAnswerRequest, DefenseSession, EvidenceGraph, EvidenceNodeReview, HealthResponse, LoginRequest, ProjectMaterial, RegisterRequest, ResearchMap, ResearchProjectCreate, ResearchProjectDetail, ResearchProjectSummary, ResearchProjectUpdate, ResearchRunDetail, ResearchRunSummary, ResearchTask, ReviewRequest, ThesisDraft, ThesisVersion
from .research_map import generate_research_map
from .storage import create_research_project, get_defense_session, get_project_evidence_graph, get_research_project, get_user_run, init_research_runs_db, list_capability_profiles, list_defense_sessions, list_project_materials, list_research_projects, list_research_tasks, list_thesis_versions, list_user_runs, project_belongs_to_user, review_project_evidence_node, save_capability_profile, save_defense_session, save_thesis_version, save_user_run, sync_defense_tasks, update_research_project
from .capability_profile import build_capability_profile
from .defense import answer_defense, start_defense
from .thesis_builder import assess_thesis
from .workflow_runner import run_analysis_workflow, run_review_workflow


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


@app.on_event("startup")
def startup() -> None:
    init_auth_db()
    init_research_runs_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


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
    material_ids: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
    current_user: AuthUser | None = Depends(get_optional_current_user),
) -> AnalyzeResponse:
    try:
        payload = {
            "project_id": project_id,
            "company_profile": json.loads(company_profile),
            "materials": json.loads(text_materials) if text_materials else [],
            "options": json.loads(options) if options else {},
        }
        request = AnalyzeRequest.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"请求参数解析失败：{exc}") from exc

    if material_ids and len(material_ids) != len(files):
        raise HTTPException(status_code=400, detail="material_ids 数量必须与 files 数量一致")

    for index, upload in enumerate(files):
        data = await upload.read()
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


@app.patch("/api/projects/{project_id}/evidence-graph/nodes/{node_id}", response_model=EvidenceGraph)
def review_evidence_node(project_id: str, node_id: str, request: EvidenceNodeReview, current_user: AuthUser = Depends(get_current_user)) -> EvidenceGraph:
    graph = review_project_evidence_node(current_user.user_id, project_id, node_id, request)
    if graph is None:
        raise HTTPException(status_code=404, detail="未找到该项目或证据节点")
    return graph


@app.get("/api/projects/{project_id}/research-map", response_model=ResearchMap)
def project_research_map(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> ResearchMap:
    detail = get_research_project(current_user.user_id, project_id)
    if not detail:
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    project = detail.project
    return generate_research_map(project_id, project.company_profile.industry, graph, company_name=project.company_profile.company_name, research_objective=project.research_objective, initial_view=project.initial_view, key_question=project.key_question)


@app.post("/api/projects/{project_id}/thesis", response_model=ThesisVersion)
def create_thesis_version(project_id: str, request: ThesisDraft, current_user: AuthUser = Depends(get_current_user)) -> ThesisVersion:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    history = list_thesis_versions(current_user.user_id, project_id)
    thesis = ThesisVersion(project_id=project_id, version=len(history) + 1, draft=request, assessment=assess_thesis(request, graph))
    return save_thesis_version(current_user.user_id, thesis)


@app.get("/api/projects/{project_id}/thesis", response_model=list[ThesisVersion])
def thesis_history(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ThesisVersion]:
    if not project_belongs_to_user(current_user.user_id, project_id):
        raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_thesis_versions(current_user.user_id, project_id)


@app.post("/api/projects/{project_id}/defense", response_model=DefenseSession)
def create_defense(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> DefenseSession:
    theses = list_thesis_versions(current_user.user_id, project_id)
    if not theses:
        raise HTTPException(status_code=400, detail="请先完成 Thesis Builder")
    graph = get_project_evidence_graph(current_user.user_id, project_id) or EvidenceGraph()
    return save_defense_session(current_user.user_id, start_defense(project_id, theses[-1], graph))


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
    return saved


@app.get("/api/projects/{project_id}/defense", response_model=list[DefenseSession])
def project_defenses(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[DefenseSession]:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_defense_sessions(current_user.user_id, project_id)


@app.get("/api/projects/{project_id}/tasks", response_model=list[ResearchTask])
def project_tasks(project_id: str, current_user: AuthUser = Depends(get_current_user)) -> list[ResearchTask]:
    if not project_belongs_to_user(current_user.user_id, project_id): raise HTTPException(status_code=404, detail="未找到该研究项目")
    return list_research_tasks(current_user.user_id, project_id)


@app.post("/api/capability-profile", response_model=CapabilityProfile)
def refresh_capability_profile(current_user: AuthUser = Depends(get_current_user)) -> CapabilityProfile:
    run_details = [detail for summary in list_user_runs(current_user.user_id, limit=100) if (detail := get_user_run(current_user.user_id, summary.run_id))]
    projects = list_research_projects(current_user.user_id, include_archived=True)
    theses = [thesis for project in projects for thesis in list_thesis_versions(current_user.user_id, project.project_id)]
    defenses = list_defense_sessions(current_user.user_id)
    return save_capability_profile(build_capability_profile(current_user.user_id, run_details, theses, defenses))


@app.get("/api/capability-profile/history", response_model=list[CapabilityProfile])
def capability_profile_history(limit: int = Query(default=30, ge=1, le=100), current_user: AuthUser = Depends(get_current_user)) -> list[CapabilityProfile]:
    return list_capability_profiles(current_user.user_id, limit)
