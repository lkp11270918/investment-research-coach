from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from .models import EvidenceCategory, EvidenceItem, ModelExecutionRecord, ModelLayer, RawMaterial, SourceType


MATERIAL_LABELS = {
    SourceType.FINANCIAL_TABLE: ("资产负债表", "利润表", "现金流", "营业收入", "净利润", "roe"),
    SourceType.MANAGEMENT_NOTE: ("业绩会", "管理层", "董事长", "问答", "路演"),
    SourceType.SELL_SIDE_SUMMARY: ("目标价", "券商", "分析师", "评级", "盈利预测"),
    SourceType.NEWS_SUMMARY: ("记者", "新闻", "报道", "消息"),
    SourceType.USER_NOTE: ("我的判断", "初步观点", "研究笔记", "待验证"),
}

STATEMENT_LABELS = {
    EvidenceCategory.FINANCIAL_FACT: ("营收", "净利润", "现金流", "负债", "roe", "分红"),
    EvidenceCategory.MANAGEMENT_OPINION: ("管理层", "预计", "目标", "计划", "我们认为"),
    EvidenceCategory.SELL_SIDE_OPINION: ("券商", "分析师", "目标价", "评级", "预测"),
    EvidenceCategory.RISK: ("风险", "下降", "恶化", "不确定", "承压"),
    EvidenceCategory.ASSUMPTION: ("假设", "取决于", "前提", "如果"),
}


def classify_material(material: RawMaterial) -> tuple[SourceType, float]:
    text = (material.title + " " + material.content[:4000]).lower()
    scores = {label: sum(cue in text for cue in cues) for label, cues in MATERIAL_LABELS.items()}
    label, score = max(scores.items(), key=lambda item: item[1])
    return (label, min(0.99, 0.55 + score * 0.1)) if score else (material.source_type, 0.5)


def classify_statement(text: str) -> tuple[EvidenceCategory, float]:
    lowered = text.lower()
    scores = {label: sum(cue in lowered for cue in cues) for label, cues in STATEMENT_LABELS.items()}
    label, score = max(scores.items(), key=lambda item: item[1])
    return (label, min(0.98, 0.5 + score * 0.12)) if score else (EvidenceCategory.FACT, 0.5)


def embed_text(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    normalized = re.sub(r"\s+", "", text.lower())
    tokens = [normalized[index:index + 2] for index in range(max(0, len(normalized) - 1))] + re.findall(r"[a-z_]{2,}|\d+(?:\.\d+)?", text.lower())
    for token, count in Counter(tokens).items():
        index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % dimensions
        vector[index] += float(count)
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def rerank(query: str, candidates: list[str]) -> list[int]:
    query_vector = embed_text(query)
    scored = []
    for index, candidate in enumerate(candidates):
        vector = embed_text(candidate)
        scored.append((sum(left * right for left, right in zip(query_vector, vector)), index))
    return [index for _, index in sorted(scored, reverse=True)]


def detect_financial_anomalies(evidence: list[EvidenceItem]) -> list[str]:
    groups: dict[tuple[str, str], list[float]] = {}
    for item in evidence:
        if item.metric_name and item.period and isinstance(item.metric_value, (int, float)):
            groups.setdefault((item.metric_name, item.period), []).append(float(item.metric_value))
    findings = []
    for (metric, period), values in groups.items():
        if len(values) > 1 and max(values) != min(values):
            spread = abs(max(values) - min(values)) / max(abs(max(values)), 1)
            if spread >= 0.05:
                findings.append(f"{period} {metric} 多来源差异 {spread:.1%}")
    return findings


def pipeline_records(materials: list[RawMaterial], evidence: list[EvidenceItem], llm_available: bool) -> list[ModelExecutionRecord]:
    return [
        ModelExecutionRecord(layer=ModelLayer.RULES, component="financial_parser", purpose="财务字段、单位、期间和确定性计算", deterministic=True, input_count=len(materials), output_count=sum(item.category == EvidenceCategory.FINANCIAL_FACT for item in evidence)),
        ModelExecutionRecord(layer=ModelLayer.LIGHTWEIGHT_CLASSIFIER, component="local_feature_classifier", purpose="材料与陈述高频分类", deterministic=True, input_count=len(materials) + len(evidence), output_count=len(materials) + len(evidence)),
        ModelExecutionRecord(layer=ModelLayer.SPECIALIZED_MODEL, component="embedding_reranker_nli_anomaly", purpose="相似召回、重排、语义关系与财务异常", deterministic=True, input_count=len(evidence), output_count=len(detect_financial_anomalies(evidence))),
        ModelExecutionRecord(layer=ModelLayer.LARGE_MODEL, component="research_judgment", purpose="商业模式、观点比较、反证与写作", input_count=len(evidence), output_count=0, status="completed" if llm_available else "fallback"),
        ModelExecutionRecord(layer=ModelLayer.EVIDENCE_GATE, component="evidence_compliance_gate", purpose="来源、冲突、观点误读与To C边界", deterministic=True, input_count=len(evidence), output_count=len(evidence)),
    ]
