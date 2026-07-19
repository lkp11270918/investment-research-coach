from __future__ import annotations

from .models import AgentStatus, Confidence, EvidenceGraph, ThesisAssessment, ThesisDraft


PROHIBITED_PUBLIC_LABELS = ("买入", "卖出", "增持", "减持", "overweight", "underweight", "buy", "sell")


def assess_thesis(draft: ThesisDraft, graph: EvidenceGraph) -> ThesisAssessment:
    issues: list[str] = []
    evidence_nodes = {node.evidence_id: node for node in graph.nodes if node.evidence_id}
    valid_support = [item for item in draft.supporting_evidence_ids if item in evidence_nodes]
    valid_counter = [item for item in draft.counter_evidence_ids if item in evidence_nodes]
    if not draft.core_view.strip():
        issues.append("核心观点不能为空")
    if len(draft.core_variables) != 3:
        issues.append("需要明确三个核心变量")
    if not valid_support:
        issues.append("核心观点缺少可回溯支持证据")
    if not valid_counter:
        issues.append("核心观点缺少最强反证")
    if not draft.assumptions:
        issues.append("尚未明确结论成立的关键假设")
    if not draft.falsification_conditions:
        issues.append("尚未定义可操作的观点推翻条件")
    if not draft.unknowns:
        issues.append("尚未记录当前未知事项")
    if draft.user_internal_label and any(term in draft.user_internal_label.lower() for term in PROHIBITED_PUBLIC_LABELS):
        issues.append("To C内部判断不能使用买入、卖出、增持或减持等公开投资评级")
    sell_side_ids = {node.evidence_id for node in graph.nodes if node.evidence_id and node.node_type == "sell_side_opinion"}
    repetition = bool(valid_support) and set(valid_support).issubset(sell_side_ids)
    if repetition:
        issues.append("支持证据全部来自卖方观点，存在卖方复读风险")
    required_parts = 6
    completed = sum([bool(valid_support), bool(valid_counter), bool(draft.assumptions), bool(draft.falsification_conditions), bool(draft.unknowns), len(draft.core_variables) == 3])
    coverage = round(completed / required_parts * 100, 1)
    if not issues:
        status, confidence = AgentStatus.PASS, Confidence.HIGH
    elif coverage >= 50:
        status, confidence = AgentStatus.PARTIAL, Confidence.MEDIUM
    else:
        status, confidence = AgentStatus.FAIL, Confidence.LOW
    return ThesisAssessment(status=status, issues=issues, evidence_coverage=coverage, sell_side_repetition_risk=repetition, confidence=confidence)
