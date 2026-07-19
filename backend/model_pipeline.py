from __future__ import annotations

import hashlib
import math
import re
from time import perf_counter
from collections import Counter

from .models import EvidenceCategory, EvidenceItem, ModelExecutionRecord, ModelLayer, RawMaterial, SourceType
from .llm_client import LLMError, OpenAIClient


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
        ModelExecutionRecord(layer=ModelLayer.LIGHTWEIGHT_CLASSIFIER, component="keyword_fallback_classifier", purpose="材料与陈述高频分类", deterministic=True, input_count=len(materials) + len(evidence), output_count=len(materials) + len(evidence), status="fallback", fallback_reason="real lightweight model was not executed"),
        ModelExecutionRecord(layer=ModelLayer.SPECIALIZED_MODEL, component="hashed_embedding_fallback", purpose="相似召回、重排与财务异常", deterministic=True, input_count=len(evidence), output_count=len(detect_financial_anomalies(evidence)), status="fallback", fallback_reason="real embedding model was not executed"),
        ModelExecutionRecord(layer=ModelLayer.LARGE_MODEL, component="research_judgment", purpose="商业模式、观点比较、反证与写作", input_count=len(evidence), output_count=0, status="completed" if llm_available else "fallback"),
        ModelExecutionRecord(layer=ModelLayer.EVIDENCE_GATE, component="evidence_compliance_gate", purpose="来源、冲突、观点误读与To C边界", deterministic=True, input_count=len(evidence), output_count=len(evidence)),
    ]


def execute_model_pipeline(materials: list[RawMaterial], evidence: list[EvidenceItem], client: OpenAIClient | None = None) -> list[ModelExecutionRecord]:
    client = client or OpenAIClient()
    records = [
        ModelExecutionRecord(layer=ModelLayer.RULES, component="financial_calculation_engine", purpose="财务字段、单位、期间和确定性公式", deterministic=True, input_count=len(materials), output_count=sum(item.category == EvidenceCategory.FINANCIAL_FACT for item in evidence)),
    ]
    if not client.available:
        return records + pipeline_records(materials, evidence, False)[1:]

    settings = client.settings
    classification_input = [material.title + "\n" + material.content[:1000] for material in materials] + [item.statement for item in evidence[:100]]
    started = perf_counter()
    try:
        result = client.generate_json(
            model=settings.openai_small_model,
            system_prompt="你是高频投研文本分类器。仅分类，不进行研究推理。返回JSON：{\"labels\":[{\"index\":0,\"label\":\"...\",\"confidence\":0.0}]}。材料标签使用financial_table,management_note,sell_side_summary,news_summary,user_note,other；陈述标签使用fact,financial_fact,management_opinion,sell_side_opinion,risk,assumption。",
            user_payload={"items": [{"index": index, "text": text} for index, text in enumerate(classification_input)]},
            temperature=0,
        )
        labels = result.get("labels", [])
        _apply_classification_labels(labels, materials, evidence, settings.openai_small_model)
        records.append(ModelExecutionRecord(layer=ModelLayer.LIGHTWEIGHT_CLASSIFIER, component="model_text_classifier", purpose="材料与陈述高频分类", input_count=len(classification_input), output_count=len(labels), provider="openai", model_name=settings.openai_small_model, latency_ms=round((perf_counter() - started) * 1000)))
    except LLMError as exc:
        records.append(ModelExecutionRecord(layer=ModelLayer.LIGHTWEIGHT_CLASSIFIER, component="keyword_fallback_classifier", purpose="材料与陈述高频分类", deterministic=True, input_count=len(classification_input), output_count=len(classification_input), status="fallback", fallback_reason=str(exc)))

    texts = [item.statement for item in evidence[:200]]
    try:
        vectors, latency = client.embed(texts, model=settings.openai_embedding_model) if texts else ([], 0)
        _apply_semantic_neighbors(evidence[:200], vectors)
        records.append(ModelExecutionRecord(layer=ModelLayer.SPECIALIZED_MODEL, component="semantic_embedding", purpose="跨文档语义召回与重排", input_count=len(texts), output_count=len(vectors), provider="openai", model_name=settings.openai_embedding_model, latency_ms=latency))
    except LLMError as exc:
        records.append(ModelExecutionRecord(layer=ModelLayer.SPECIALIZED_MODEL, component="hashed_embedding_fallback", purpose="跨文档相似召回", deterministic=True, input_count=len(texts), output_count=len(texts), status="fallback", fallback_reason=str(exc)))
    records.append(ModelExecutionRecord(layer=ModelLayer.SPECIALIZED_MODEL, component="financial_anomaly_rules", purpose="多来源财务异常", deterministic=True, input_count=len(evidence), output_count=len(detect_financial_anomalies(evidence))))
    records.extend(pipeline_records(materials, evidence, True)[3:])
    return records


def semantic_rerank(query: str, candidates: list[str], client: OpenAIClient | None = None) -> tuple[list[int], str]:
    if not candidates:
        return [], "empty"
    client = client or OpenAIClient()
    if client.available:
        try:
            vectors, _ = client.embed([query, *candidates], model=client.settings.openai_embedding_model)
            query_vector = vectors[0]
            scored = [(sum(a * b for a, b in zip(query_vector, vector)), index) for index, vector in enumerate(vectors[1:])]
            recalled = [index for _, index in sorted(scored, reverse=True)[:20]]
            result = client.generate_json(
                model=client.settings.openai_small_model,
                system_prompt="你是独立于Embedding的投研证据重排器。按证据是否直接回答问题、期间口径是否一致、来源是否原始进行0-100评分。仅返回JSON：{\"ranking\":[{\"index\":0,\"score\":90,\"reason\":\"...\"}]}。不得按措辞相似度代替证据相关性。",
                user_payload={"query":query,"candidates":[{"index":i,"text":candidates[i]} for i in recalled]},
                temperature=0,
            )
            ranking=[]
            for item in result.get("ranking",[]):
                try:
                    index=int(item["index"]); score=float(item["score"])
                    if index in recalled: ranking.append((score,index))
                except (KeyError,TypeError,ValueError): continue
            ranked=[index for _,index in sorted(ranking,reverse=True)]
            ranked.extend(index for index in recalled if index not in ranked)
            ranked.extend(index for index in range(len(candidates)) if index not in ranked)
            return ranked, f"{client.settings.openai_embedding_model}+{client.settings.openai_small_model}:cross_encoder_rerank"
        except LLMError:
            pass
    return rerank(query, candidates), "hashed_embedding_fallback"


def _apply_classification_labels(labels: list[dict], materials: list[RawMaterial], evidence: list[EvidenceItem], model: str) -> None:
    material_labels = {item.value: item for item in SourceType}
    evidence_labels = {item.value: item for item in EvidenceCategory}
    for raw in labels:
        try:
            index = int(raw["index"])
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0))))
        except (KeyError, TypeError, ValueError):
            continue
        label = str(raw.get("label", "")).lower()
        if index < len(materials):
            material = materials[index]
            if label in material_labels and confidence >= 0.7:
                material.source_type = material_labels[label]
                material.classification_model = model
                material.classification_confidence = confidence
        else:
            evidence_index = index - len(materials)
            if 0 <= evidence_index < len(evidence) and label in evidence_labels and confidence >= 0.7:
                item = evidence[evidence_index]
                item.category = evidence_labels[label]
                item.classification_model = model
                item.classification_confidence = confidence


def _apply_semantic_neighbors(evidence: list[EvidenceItem], vectors: list[list[float]]) -> None:
    if len(evidence) != len(vectors):
        return
    for index, item in enumerate(evidence):
        scores = []
        for other_index, other_vector in enumerate(vectors):
            if index == other_index:
                continue
            score = sum(left * right for left, right in zip(vectors[index], other_vector))
            if score >= 0.65:
                scores.append((score, evidence[other_index].evidence_id))
        item.semantic_neighbor_ids = [evidence_id for _, evidence_id in sorted(scores, reverse=True)[:5]]
