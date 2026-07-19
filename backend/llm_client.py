from __future__ import annotations

import json
import urllib.error
import urllib.request
from contextvars import ContextVar
from time import perf_counter
from typing import Any

from .config import Settings, get_settings
from .models import ModelUsageRecord


class LLMError(RuntimeError):
    pass


_usage: ContextVar[list[ModelUsageRecord] | None] = ContextVar("model_usage", default=None)


def start_usage_tracking() -> None:
    _usage.set([])


def collected_usage() -> list[ModelUsageRecord]:
    return list(_usage.get() or [])


def _check_budget(settings: Settings) -> None:
    records = _usage.get()
    if records is not None and len(records) >= settings.max_llm_calls_per_workflow:
        raise LLMError("workflow model-call budget exceeded")


def _record_usage(payload: dict[str, Any], model: str, endpoint: str, latency_ms: int) -> None:
    records = _usage.get()
    if records is None:
        return
    usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    records.append(ModelUsageRecord(model_name=model, endpoint=endpoint, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=int(usage.get("total_tokens", input_tokens + output_tokens) or input_tokens + output_tokens), latency_ms=latency_ms))


def _extract_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return response_payload["output_text"]

    parts: list[str] = []
    for item in response_payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise LLMError(f"LLM did not return valid JSON: {exc}") from exc


class OpenAIClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def available(self) -> bool:
        return bool(self.settings.openai_api_key) and self.settings.use_llm_agents

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        temperature: float = 0.1,
        model: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")

        selected_model = model or self.settings.openai_model
        _check_budget(self.settings)
        body = {
            "model": selected_model,
            "input": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Return only valid JSON. Do not include markdown fences.\n\n"
                        + json.dumps(user_payload, ensure_ascii=False)
                    ),
                },
            ],
            "temperature": temperature,
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.openai_base_url.rstrip('/')}/responses",
            data=data,
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"OpenAI API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMError(f"OpenAI API request failed: {exc}") from exc

        text = _extract_text(payload)
        if not text:
            raise LLMError("OpenAI API returned no output text.")
        _record_usage(payload, selected_model, "responses", round((perf_counter() - started) * 1000))
        return _extract_json(text)

    def embed(self, texts: list[str], *, model: str | None = None) -> tuple[list[list[float]], int]:
        if not self.settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")
        selected_model = model or self.settings.openai_embedding_model
        _check_budget(self.settings)
        body = {"model": selected_model, "input": texts}
        request = urllib.request.Request(
            f"{self.settings.openai_base_url.rstrip('/')}/embeddings",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        started = perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMError(f"Embedding API HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMError(f"Embedding API request failed: {exc}") from exc
        rows = sorted(payload.get("data", []), key=lambda item: int(item.get("index", 0)))
        vectors = [item.get("embedding", []) for item in rows]
        if len(vectors) != len(texts) or any(not vector for vector in vectors):
            raise LLMError("Embedding API returned incomplete vectors.")
        latency = round((perf_counter() - started) * 1000)
        _record_usage(payload, selected_model, "embeddings", latency)
        return vectors, latency
