from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import Settings, get_settings


class LLMError(RuntimeError):
    pass


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
    ) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")

        body = {
            "model": self.settings.openai_model,
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
        return _extract_json(text)
