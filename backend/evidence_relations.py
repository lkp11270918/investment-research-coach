from __future__ import annotations

import re
from itertools import combinations

from .models import Confidence, EvidenceGraphEdge, EvidenceGraphNode, EvidenceRelation
from .llm_client import LLMError, OpenAIClient
from .model_pipeline import semantic_rerank


NEGATIVE_CUES = ("下降", "恶化", "承压", "不及", "低于", "减少", "收缩", "亏损", "风险", "无法", "未能", "不成立")
POSITIVE_CUES = ("增长", "改善", "高于", "增加", "扩张", "盈利", "稳定", "支持", "兑现", "可持续")
DEPENDENCY_CUES = ("取决于", "依赖", "前提", "假设", "只有", "如果", "在此基础上")
QUESTION_CUES = ("是否", "为何", "待验证", "不确定", "质疑", "风险", "什么情况下")


def infer_semantic_edges(nodes: list[EvidenceGraphNode]) -> list[EvidenceGraphEdge]:
    candidates = [node for node in nodes if node.node_type not in {"source", "source_document"} and node.label.strip()]
    edges: list[EvidenceGraphEdge] = []
    for left, right in combinations(candidates[:500], 2):
        similarity = _similarity(left.label, right.label)
        if similarity < 0.12:
            continue
        relation, confidence = _relation(left, right, similarity)
        if relation:
            edges.append(EvidenceGraphEdge(from_node_id=left.node_id, to_node_id=right.node_id, relation=relation, rationale=f"启发式语义关系：共同主题相似度 {similarity:.2f}", confidence=confidence, relation_source="heuristic_fallback"))
    return edges


def infer_semantic_edges_nli(nodes: list[EvidenceGraphNode], client: OpenAIClient | None) -> list[EvidenceGraphEdge]:
    fallback = infer_semantic_edges(nodes)
    if not client or not client.available:
        return fallback
    node_by_id = {node.node_id: node for node in nodes}
    candidates = _embedding_candidates(nodes, client) or fallback[:120]
    if not candidates:
        return fallback
    try:
        result = client.generate_json(
            model=client.settings.openai_nli_model,
            system_prompt="你是证据关系NLI分类器。判断两段陈述是supports、contradicts、depends_on、questioned_by还是irrelevant。只判断语义关系，不做投资结论。返回JSON：{\"relations\":[{\"index\":0,\"relation\":\"supports\",\"confidence\":\"high\",\"rationale\":\"...\"}]}。不确定时必须返回irrelevant。",
            user_payload={"pairs": [{"index": index, "left": node_by_id[edge.from_node_id].label, "right": node_by_id[edge.to_node_id].label} for index, edge in enumerate(candidates)]},
            temperature=0,
        )
    except LLMError:
        return fallback
    allowed = {item.value: item for item in (EvidenceRelation.SUPPORTS, EvidenceRelation.CONTRADICTS, EvidenceRelation.DEPENDS_ON, EvidenceRelation.QUESTIONED_BY)}
    confidence_map = {"high": Confidence.HIGH, "medium": Confidence.MEDIUM, "low": Confidence.LOW}
    edges: list[EvidenceGraphEdge] = []
    for raw in result.get("relations", []):
        try:
            candidate = candidates[int(raw["index"])]
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        relation = allowed.get(str(raw.get("relation", "")).lower())
        if relation is None:
            continue
        edges.append(EvidenceGraphEdge(from_node_id=candidate.from_node_id, to_node_id=candidate.to_node_id, relation=relation, rationale=str(raw.get("rationale") or "NLI语义判断"), confidence=confidence_map.get(str(raw.get("confidence", "")).lower(), Confidence.MEDIUM), relation_source="nli_model", model_name=client.settings.openai_nli_model))
    return edges or fallback


def _embedding_candidates(nodes: list[EvidenceGraphNode], client: OpenAIClient) -> list[EvidenceGraphEdge]:
    candidates = [node for node in nodes if node.node_type not in {"source", "source_document"} and node.label.strip()][:160]
    if len(candidates) < 2:
        return []
    try:
        vectors, _ = client.embed([node.label for node in candidates], model=client.settings.openai_embedding_model)
    except (LLMError, AttributeError):
        return []
    scored: list[tuple[float, int, int]] = []
    for left in range(len(candidates)):
        for right in range(left + 1, len(candidates)):
            score = sum(a * b for a, b in zip(vectors[left], vectors[right]))
            if score >= 0.45:
                scored.append((score, left, right))
    raw = [(score, left, right) for score, left, right in sorted(scored, reverse=True)[:120]]
    pair_texts = [f"证据A：{candidates[left].label}\n证据B：{candidates[right].label}" for _, left, right in raw]
    order, reranker = semantic_rerank("筛选存在直接支持、反驳、依赖或质疑关系的证据对；排除仅措辞相似的组合", pair_texts, client)
    selected = [raw[index] for index in order[:60] if index < len(raw)]
    return [EvidenceGraphEdge(from_node_id=candidates[left].node_id, to_node_id=candidates[right].node_id, relation=EvidenceRelation.MENTIONS, rationale=f"Embedding候选相似度 {score:.2f}；经独立Reranker筛选", confidence=Confidence.MEDIUM, relation_source="embedding_reranked_candidate", model_name=reranker) for score, left, right in selected]


def _relation(left: EvidenceGraphNode, right: EvidenceGraphNode, similarity: float) -> tuple[EvidenceRelation | None, Confidence]:
    left_text, right_text = left.label.lower(), right.label.lower()
    if left.node_type == "verification_question":
        return EvidenceRelation.QUESTIONED_BY, Confidence.MEDIUM
    if right.node_type == "verification_question":
        return EvidenceRelation.QUESTIONED_BY, Confidence.MEDIUM
    left_polarity = _polarity(left_text)
    right_polarity = _polarity(right_text)
    if left_polarity and right_polarity and left_polarity != right_polarity:
        return EvidenceRelation.CONTRADICTS, Confidence.HIGH if similarity >= 0.36 else Confidence.MEDIUM
    if left.node_type == "assumption" or right.node_type == "assumption" or _has_any(left_text + right_text, DEPENDENCY_CUES):
        return EvidenceRelation.DEPENDS_ON, Confidence.MEDIUM
    if _has_any(left_text, QUESTION_CUES) or _has_any(right_text, QUESTION_CUES):
        return EvidenceRelation.QUESTIONED_BY, Confidence.MEDIUM
    if similarity >= 0.22:
        return EvidenceRelation.SUPPORTS, Confidence.MEDIUM
    return None, Confidence.LOW


def _polarity(text: str) -> int:
    positive = sum(cue in text for cue in POSITIVE_CUES)
    negative = sum(cue in text for cue in NEGATIVE_CUES)
    return 1 if positive > negative else -1 if negative > positive else 0


def _has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", text.lower())
    chinese = {normalized[index:index + 2] for index in range(max(0, len(normalized) - 1))}
    words = set(re.findall(r"[a-z_]{2,}|\d+(?:\.\d+)?", text.lower()))
    return chinese | words
