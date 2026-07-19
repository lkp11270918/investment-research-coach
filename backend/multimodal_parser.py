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
                    '{"visible_text":"...","chart_summary":"...","visible_data":[{"text":"...","region":{"x":0.0,"y":0.0,"width":0.0,"height":0.0}}],"inferences":[{"text":"...","region":{"x":0.0,"y":0.0,"width":0.0,"height":0.0}}]}'
                )},
                {"type": "input_image", "image_url": f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"},
            ],
        }],
        "temperature": 0,
    }
    payload = _request_json(f"{settings.openai_base_url.rstrip('/')}/responses", body, settings.openai_api_key, settings.llm_timeout_seconds)
    text = _response_text(payload)
    parsed = _extract_json(text)
    visible_items = [_visual_item(item) for item in parsed.get("visible_data", [])]
    visible = "\n".join(filter(None, [parsed.get("visible_text"), parsed.get("chart_summary"), *(item[0] for item in visible_items)]))
    inferences = parsed.get("inferences", [])
    blocks = [ContentBlock(modality=MaterialModality.IMAGE, content=text, region=region, extraction_method="vision_visible_data", requires_confirmation=True) for text, region in visible_items if text]
    if not blocks and visible:
        blocks = [ContentBlock(modality=MaterialModality.IMAGE, content=visible, extraction_method="vision_visible_data", requires_confirmation=True)]
    for item in inferences:
        text, region = _visual_item(item)
        if text:
            blocks.append(ContentBlock(modality=MaterialModality.IMAGE, content=text, region=region, extraction_method="vision_inference", requires_confirmation=True))
    warnings = ["图片可见数据和模型推断已分区，正式使用前需要用户确认。"]
    return visible, blocks, warnings


def parse_audio(filename: str, data: bytes) -> tuple[str, list[ContentBlock], list[str]]:
    settings = get_settings()
    if not settings.openai_api_key or not settings.use_llm_agents:
        raise MultimodalParseError("音频解析需要配置语音识别模型")
    boundary = f"----research-{uuid4().hex}"
    fields = [("model", "gpt-4o-transcribe-diarize"), ("response_format", "diarized_json"), ("chunking_strategy", "auto")]
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
    blocks: list[ContentBlock] = []
    for segment in payload.get("segments", []):
        if not isinstance(segment, dict) or not str(segment.get("text", "")).strip():
            continue
        blocks.append(ContentBlock(modality=MaterialModality.AUDIO, content=str(segment["text"]).strip(), speaker=str(segment.get("speaker") or "unknown"), start_seconds=_float_or_none(segment.get("start")), end_seconds=_float_or_none(segment.get("end")), extraction_method="speech_to_text_diarized", requires_confirmation=not bool(segment.get("speaker"))))
    if not blocks:
        blocks = [ContentBlock(modality=MaterialModality.AUDIO, content=text, speaker="unknown", extraction_method="speech_to_text", requires_confirmation=True)]
    analysis = _analyze_management_transcript(text, settings)
    for signal_type, items in analysis.items() if analysis else []:
        for item in items if isinstance(items, list) else []:
            signal_text = str(item.get("excerpt") or item.get("text") or item) if isinstance(item, dict) else str(item)
            blocks.append(ContentBlock(modality=MaterialModality.AUDIO, content=signal_text, speaker=str(item.get("speaker") or "unknown") if isinstance(item, dict) else "unknown", start_seconds=_float_or_none(item.get("start")) if isinstance(item, dict) else None, end_seconds=_float_or_none(item.get("end")) if isinstance(item, dict) else None, extraction_method=f"management_signal:{signal_type}", requires_confirmation=True))
    warnings = [] if all(block.speaker != "unknown" for block in blocks if block.extraction_method.startswith("speech_to_text")) else ["部分说话人尚未确认，管理层归因需要用户复核。"]
    if analysis:
        warnings.append("管理层语气、回避和承诺属于模型判断，已标记为待确认。")
    return text, blocks, warnings


def parse_scanned_pdf(filename: str, data: bytes) -> tuple[str, list[ContentBlock], list[str]]:
    settings = get_settings()
    if not settings.openai_api_key or not settings.use_llm_agents:
        raise MultimodalParseError("扫描PDF需要配置可用的文档视觉模型")
    body = {"model": settings.openai_model, "input": [{"role": "user", "content": [{"type": "input_text", "text": "逐页识别这份扫描投研PDF。返回JSON：{\"pages\":[{\"page\":1,\"text\":\"...\",\"tables\":[\"...\"]}]}。保留数字、单位、年份和表格行，不得补写不可见内容。"}, {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{base64.b64encode(data).decode('ascii')}"}]}], "temperature": 0}
    payload = _request_json(f"{settings.openai_base_url.rstrip('/')}/responses", body, settings.openai_api_key, max(settings.llm_timeout_seconds, 120))
    parsed = _extract_json(_response_text(payload))
    blocks: list[ContentBlock] = []
    rendered: list[str] = []
    for item in parsed.get("pages", []):
        if not isinstance(item, dict): continue
        page = int(item.get("page") or len(rendered) + 1)
        page_text = str(item.get("text") or "").strip()
        tables = [str(value) for value in item.get("tables", [])]
        content = "\n".join([page_text, *tables]).strip()
        if content:
            rendered.append(f"## Page {page}\n{content}")
            blocks.append(ContentBlock(modality=MaterialModality.TEXT, content=content, page=page, extraction_method="document_vision_ocr", requires_confirmation=True))
    text = "\n\n".join(rendered)
    if not text: raise MultimodalParseError("扫描PDF未识别出有效内容")
    return text, blocks, ["扫描PDF由视觉模型识别，关键数字使用前需要与原页复核。"]


def _analyze_management_transcript(text: str, settings) -> dict:
    body = {"model": settings.openai_model, "input": [{"role": "user", "content": [{"type": "input_text", "text": "分析以下电话会转写，仅返回JSON：{\"management_views\":[],\"commitments\":[],\"evasive_answers\":[],\"tone_changes\":[]}。每项保留原话片段并区分事实与推断。\n" + text[:24000]}]}], "temperature": 0}
    try:
        payload = _request_json(f"{settings.openai_base_url.rstrip('/')}/responses", body, settings.openai_api_key, settings.llm_timeout_seconds)
        return _extract_json(_response_text(payload))
    except MultimodalParseError:
        return {}


def _float_or_none(value) -> float | None:
    try: return float(value)
    except (TypeError, ValueError): return None


def _visual_item(item) -> tuple[str, dict[str, float] | None]:
    if isinstance(item, dict):
        text = str(item.get("text") or item.get("value") or "").strip()
        raw_region = item.get("region")
        if isinstance(raw_region, dict):
            try: region = {key: float(raw_region[key]) for key in ("x", "y", "width", "height") if key in raw_region}
            except (TypeError, ValueError): region = None
        else: region = None
        return text, region
    return str(item).strip(), None


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
