from __future__ import annotations

from .models import AgentStatus, Confidence, EvidenceGraph, ThesisAssessment, ThesisDraft
from .model_pipeline import embed_text


PROHIBITED_PUBLIC_LABELS = ("买入", "卖出", "增持", "减持", "overweight", "underweight", "buy", "sell")


def assess_thesis(draft: ThesisDraft, graph: EvidenceGraph) -> ThesisAssessment:
    issues: list[str] = []
    evidence_nodes = {node.evidence_id: node for node in graph.nodes if node.evidence_id}
    valid_support = [item for item in draft.supporting_evidence_ids if item in evidence_nodes]
    valid_counter = [item for item in draft.counter_evidence_ids if item in evidence_nodes]
    thesis_context = " ".join([draft.core_view, *(variable.name + " " + variable.rationale for variable in draft.core_variables), *draft.assumptions])
    relevant_support = [item for item in valid_support if _relevance(thesis_context, evidence_nodes[item].label) >= 0.2]
    relevant_counter = [item for item in valid_counter if evidence_nodes[item].node_type in {"risk", "verification_question"} or _has_contradiction(item, valid_support, graph) or _relevance(thesis_context, evidence_nodes[item].label) >= 0.2]
    if not draft.core_view.strip():
        issues.append("核心观点不能为空")
    if len(draft.core_variables) != 3:
        issues.append("需要明确三个核心变量")
    if not valid_support:
        issues.append("核心观点缺少可回溯支持证据")
    elif not relevant_support:
        issues.append("所选支持证据与核心观点缺少语义关联")
    if not valid_counter:
        issues.append("核心观点缺少最强反证")
    elif not relevant_counter:
        issues.append("所选反证没有形成风险、质疑或反驳关系")
    variable_ids = {item for variable in draft.core_variables for item in variable.evidence_ids if item in evidence_nodes}
    if draft.core_variables and len(variable_ids) < len(draft.core_variables):
        issues.append("部分核心变量缺少独立证据")
    if not draft.assumptions:
        issues.append("尚未明确结论成立的关键假设")
    if not draft.falsification_conditions:
        issues.append("尚未定义可操作的观点推翻条件")
    if not draft.unknowns:
        issues.append("尚未记录当前未知事项")
    scenario_names = {scenario.name.lower() for scenario in draft.scenarios}
    if not ({"bull", "base", "bear"}.issubset(scenario_names) or {"乐观", "基准", "悲观"}.issubset(scenario_names)):
        issues.append("需要完成乐观、基准和悲观三种情景")
    if any(not scenario.assumptions or not scenario.trigger_conditions for scenario in draft.scenarios):
        issues.append("每种情景都需要关键假设和可观察触发条件")
    if draft.user_internal_label and any(term in draft.user_internal_label.lower() for term in PROHIBITED_PUBLIC_LABELS):
        issues.append("To C内部判断不能使用买入、卖出、增持或减持等公开投资评级")
    sell_side_ids = {node.evidence_id for node in graph.nodes if node.evidence_id and node.node_type == "sell_side_opinion"}
    repetition = bool(valid_support) and set(valid_support).issubset(sell_side_ids)
    if repetition:
        issues.append("支持证据全部来自卖方观点，存在卖方复读风险")
    required_parts = 8
    completed = sum([bool(relevant_support), bool(relevant_counter), bool(draft.assumptions), bool(draft.falsification_conditions), bool(draft.unknowns), len(draft.core_variables) == 3, len(variable_ids) >= 3, len(draft.scenarios) >= 3])
    coverage = round(completed / required_parts * 100, 1)
    if not issues:
        status, confidence = AgentStatus.PASS, Confidence.HIGH
    elif coverage >= 50:
        status, confidence = AgentStatus.PARTIAL, Confidence.MEDIUM
    else:
        status, confidence = AgentStatus.FAIL, Confidence.LOW
    suggestions = [_suggestion(issue) for issue in issues]
    return ThesisAssessment(status=status, issues=issues, evidence_coverage=coverage, sell_side_repetition_risk=repetition, confidence=confidence, ai_suggestions=suggestions, relevant_support_ids=relevant_support, relevant_counter_ids=relevant_counter)


def _relevance(left: str, right: str) -> float:
    a, b = embed_text(left), embed_text(right)
    return sum(x * y for x, y in zip(a, b))


def _has_contradiction(evidence_id: str, support_ids: list[str], graph: EvidenceGraph) -> bool:
    node_id = f"EVIDENCE:{evidence_id}"
    support_nodes = {f"EVIDENCE:{item}" for item in support_ids}
    return any(edge.relation.value == "contradicts" and {edge.from_node_id, edge.to_node_id} == {node_id, support} for edge in graph.edges for support in support_nodes)


def _suggestion(issue: str) -> str:
    if "语义关联" in issue: return "选择能直接证明核心变量方向、期间和幅度的事实证据。"
    if "反证" in issue: return "优先选择能改变核心变量或推翻结论的事实，而不是一般性风险。"
    if "情景" in issue: return "为乐观、基准、悲观情景分别写出假设、结果和可观察触发条件。"
    if "核心变量" in issue: return "为每个核心变量绑定至少一条独立、可回溯的证据。"
    return f"补充并验证：{issue}"
