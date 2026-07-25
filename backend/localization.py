from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Language


def detect_language(parts: Iterable[str | None], default: Language = Language.ZH) -> Language:
    text = "\n".join(str(part) for part in parts if part and str(part).strip())
    if not text:
        return default
    chinese = len(re.findall(r"[\u3400-\u9fff]", text))
    english = len(re.findall(r"[A-Za-z]", text))
    if chinese == english == 0:
        return default
    return Language.ZH if chinese * 2 >= english else Language.EN


def resolve_language(
    requested: Language,
    *,
    key_question: str | None = None,
    research_objective: str | None = None,
    initial_view: str | None = None,
    materials: Iterable[str | None] = (),
    default: Language = Language.ZH,
) -> tuple[Language, str]:
    if requested in {Language.ZH, Language.EN}:
        return requested, "user_selected"
    for value, source in (
        (key_question, "key_question"),
        (research_objective, "research_objective"),
        (initial_view, "initial_view"),
    ):
        if value and value.strip():
            return detect_language([value], default), source
    material_parts = list(materials)
    return detect_language(material_parts, default), "materials" if any(material_parts) else "default"


def language_instruction(language: Language) -> str:
    if language == Language.EN:
        return (
            "Output language: English. Write every generated summary, finding, warning, question, "
            "decision and memo section in English. Preserve source quotations, company names, ticker "
            "symbols and standard financial abbreviations in their original form."
        )
    return (
        "输出语言：中文。所有生成的摘要、发现、警告、问题、判断和报告章节均使用中文；"
        "原始引用、公司名称、股票代码及通用财务缩写可保留原文。"
    )


def is_english(language: Language) -> bool:
    return language == Language.EN
