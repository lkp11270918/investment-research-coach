from __future__ import annotations

import re
from itertools import combinations

from .models import Confidence, EvidenceGraphEdge, EvidenceGraphNode, EvidenceRelation


NEGATIVE_CUES = ("下降", "恶化", "承压", "不及", "低于", "减少", "收缩", "亏损", "风险", "无法", "未能", "不成立")
POSITIVE_CUES = ("增长", "改善", "高于", "增加", "扩张", "盈利", "稳定", "支持", "兑现", "可持续")
DEPENDENCY_CUES = ("取决于", "依赖", "前提", "假设", "只有", "如果", "在此基础上")
QUESTION_CUES = ("是否", "为何", "待验证", "不确定", "质疑", "风险", "什么情况下")


def infer_semantic_edges(nodes: list[EvidenceGraphNode]) -> list[EvidenceGraphEdge]:
    candidates = [node for node in nodes if node.node_type != "source" and node.label.strip()]
    edges: list[EvidenceGraphEdge] = []
    for left, right in combinations(candidates[:500], 2):
        similarity = _similarity(left.label, right.label)
        if similarity < 0.12:
            continue
        relation, confidence = _relation(left, right, similarity)
        if relation:
            edges.append(EvidenceGraphEdge(from_node_id=left.node_id, to_node_id=right.node_id, relation=relation, rationale=f"语义关系：共同主题相似度 {similarity:.2f}", confidence=confidence))
    return edges


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
