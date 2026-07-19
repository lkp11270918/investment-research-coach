from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.request
from uuid import uuid4

from .config import get_settings
from .models import ContentBlock, MaterialModality


class MultimodalParseError(ValueError):
    pass


def parse_image(filename: str, data: bytes) -> tuple[str, list[ContentBlock], list[str]]:
    settings = get_settings()
    if not settings.openai_api_key or not settings.use_llm_agents:
        raise MultimodalParseError("图片解析需要配置可用的多模态模型")
    media_type = mimetypes.guess_type(filename)[0] or "image/png"
    body = {
        "model": settings.openai_model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": (
                    "识别这张投研图片中的标题、图表含义、坐标轴、年份、指标、可见数值和注释。"
                    "严格区分图中可见内容与推断。返回JSON："
                    '{"visible_text":"...","chart_summary":"...","visible_data":["..."],"inferences":["..."]}'
                )},
                {"type": "input_image", "image_url": f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"},
            ],
        }],
        "temperature": 0,
    }
    payload = _request_json(f"{settings.openai_base_url.rstrip('/')}/responses", body, settings.openai_api_key, settings.llm_timeout_seconds)
    text = _response_text(payload)
    parsed = _extract_json(text)
    visible = "\n".join(filter(None, [parsed.get("visible_text"), parsed.get("chart_summary"), *parsed.get("visible_data", [])]))
    inferences = parsed.get("inferences", [])
    blocks = [ContentBlock(modality=MaterialModality.IMAGE, content=visible, extraction_method="vision_model")]
    if inferences:
        blocks.append(ContentBlock(modality=MaterialModality.IMAGE, content="；".join(inferences), extraction_method="vision_inference", requires_confirmation=True))
    warnings = ["图片中的模型推断已单独标记，使用前需要用户确认。"] if inferences else []
    return visible, blocks, warnings


def parse_audio(filename: str, data: bytes) -> tuple[str, list[ContentBlock], list[str]]:
    settings = get_settings()
    if not settings.openai_api_key or not settings.use_llm_agents:
        raise MultimodalParseError("音频解析需要配置语音识别模型")
    boundary = f"----research-{uuid4().hex}"
    fields = [("model", "gpt-4o-mini-transcribe"), ("response_format", "json")]
    parts: list[bytes] = []
    for name, value in fields:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {media_type}\r\n\r\n".encode()
        + data + f"\r\n--{boundary}--\r\n".encode()
    )
    request = urllib.request.Request(
        f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions",
        data=b"".join(parts),
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(settings.llm_timeout_seconds, 120)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise MultimodalParseError(f"音频转写失败：{exc}") from exc
    text = str(payload.get("text", "")).strip()
    if not text:
        raise MultimodalParseError("音频未转写出有效文本")
    return text, [ContentBlock(modality=MaterialModality.AUDIO, content=text, speaker="unknown", extraction_method="speech_to_text", requires_confirmation=True)], ["当前转写未确认说话人，管理层归因必须由用户确认。"]


def _request_json(url: str, body: dict, api_key: str, timeout: int) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise MultimodalParseError(f"图片识别失败：{exc}") from exc


def _response_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    return "\n".join(str(part.get("text", "")) for item in payload.get("output", []) for part in item.get("content", []))


def _extract_json(text: str) -> dict:
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise MultimodalParseError("视觉模型未返回结构化结果") from exc
