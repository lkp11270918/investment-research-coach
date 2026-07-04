from __future__ import annotations

import json
import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .auth import authenticate_user, create_access_token, create_user, get_current_user, get_optional_current_user, init_auth_db, to_auth_user
from .file_parsers import FileParseError, parse_uploaded_file
from .models import AnalyzeRequest, AnalyzeResponse, AuthResponse, AuthUser, HealthResponse, LoginRequest, RegisterRequest, ResearchRunDetail, ResearchRunSummary, ReviewRequest
from .storage import get_user_run, init_research_runs_db, list_user_runs, save_user_run
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


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, current_user: AuthUser | None = Depends(get_optional_current_user)) -> AnalyzeResponse:
    state = run_analysis_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="analysis", state=state)
    return AnalyzeResponse(run_id=state.run_id, status="completed", state=state)


@app.post("/api/analyze-files", response_model=AnalyzeResponse)
async def analyze_files(
    company_profile: str = Form(...),
    options: str | None = Form(None),
    text_materials: str | None = Form(None),
    material_ids: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
    current_user: AuthUser | None = Depends(get_optional_current_user),
) -> AnalyzeResponse:
    try:
        payload = {
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

    state = run_analysis_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="analysis", state=state)
    return AnalyzeResponse(run_id=state.run_id, status="completed", state=state)


@app.post("/api/review", response_model=AnalyzeResponse)
def review(request: ReviewRequest, current_user: AuthUser | None = Depends(get_optional_current_user)) -> AnalyzeResponse:
    state = run_review_workflow(request)
    save_user_run(user_id=current_user.user_id if current_user else None, run_type="review", state=state)
    return AnalyzeResponse(run_id=state.run_id, status="completed", state=state)


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
