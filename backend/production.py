from __future__ import annotations

from collections import defaultdict, deque
from time import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import Settings, get_settings


class ProductionGuardMiddleware(BaseHTTPMiddleware):
    buckets: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get("x-request-id") or f"REQ-{uuid4().hex[:12]}"
        length = int(request.headers.get("content-length", "0") or 0)
        if length > settings.max_upload_bytes:
            return JSONResponse({"detail": "请求文件超过允许大小", "request_id": request_id}, status_code=413)
        key = request.client.host if request.client else "unknown"
        now = time()
        bucket = self.buckets[key]
        while bucket and bucket[0] < now - 60: bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "请求过于频繁，请稍后再试", "request_id": request_id}, status_code=429)
        bucket.append(now)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def production_configuration_report(settings: Settings) -> dict:
    errors = []
    if settings.app_env == "production":
        if settings.auth_secret_key == "dev-only-change-this-secret" or len(settings.auth_secret_key) < 32: errors.append("production AUTH_SECRET_KEY must be at least 32 characters")
        if not settings.openai_api_key: errors.append("production OPENAI_API_KEY is missing")
        if settings.database_url.startswith("sqlite:///"): errors.append("production database must be persistent and shared")
    if settings.max_upload_bytes <= 0 or settings.max_upload_bytes > 100 * 1024 * 1024: errors.append("MAX_UPLOAD_BYTES must be between 1 and 100MB")
    if settings.max_files_per_request < 1 or settings.max_files_per_request > 50: errors.append("MAX_FILES_PER_REQUEST must be between 1 and 50")
    if settings.rate_limit_per_minute < 1: errors.append("RATE_LIMIT_PER_MINUTE must be positive")
    if settings.max_llm_calls_per_workflow < 1: errors.append("MAX_LLM_CALLS_PER_WORKFLOW must be positive")
    return {"suite":"production_configuration", "passed":not errors, "environment":settings.app_env, "errors":errors}
