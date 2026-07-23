from __future__ import annotations

from collections import defaultdict

from .models import (
    Confidence,
    EvidenceCategory,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceRelation,
    VerificationStatus,
    WorkflowState,
)
from .evidence_relations import infer_semantic_edges, infer_semantic_edges_nli
from .llm_client import OpenAIClient


def build_evidence_graph(
    state: WorkflowState,
    semantic_client: OpenAIClient | None = None,
    include_semantic: bool = True,
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    conflicts: list[str] = []
    source_nodes: set[str] = set()
    for source in state.source_documents:
        node_id = f"SOURCE:{source.source_id}"
        source_nodes.add(node_id)
        nodes.append(EvidenceGraphNode(node_id=node_id, node_type="source_document", label=source.title, source_id=source.source_id, confidence=Confidence.MEDIUM, verification_status=VerificationStatus.VERIFIED if source.provided_by_user else VerificationStatus.TO_BE_VERIFIED, metadata={"source_type": source.source_type.value, "file_name": source.file_name, "url": source.url}))

    metric_groups: dict[tuple[str, str], list] = defaultdict(list)
    for item in state.evidence_items:
        node_id = f"EVIDENCE:{item.evidence_id}"
        semantic_types = {
            EvidenceCategory.FACT: "evidence",
            EvidenceCategory.MANAGEMENT_OPINION: "management_claim",
            EvidenceCategory.SELL_SIDE_OPINION: "sell_side_claim",
            EvidenceCategory.USER_OPINION: "user_claim",
        }
        node_type = semantic_types.get(item.category, item.category.value)
        nodes.append(EvidenceGraphNode(node_id=node_id, node_type=node_type, label=item.statement, evidence_id=item.evidence_id, confidence=item.confidence, verification_status=item.verification_status, metadata={"evidence_category": item.category.value, "period": item.period, "metric_name": item.metric_name, "metric_value": item.metric_value, "unit": item.unit, "notes": item.notes, "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs]}))
        if item.metric_name:
            metric_node_id = f"METRIC:{item.metric_name}"
            if not any(node.node_id == metric_node_id for node in nodes):
                nodes.append(EvidenceGraphNode(node_id=metric_node_id, node_type="financial_metric", label=item.metric_name, confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED))
            edges.append(EvidenceGraphEdge(from_node_id=node_id, to_node_id=metric_node_id, relation=EvidenceRelation.MENTIONS, rationale="标准化财务指标", confidence=Confidence.HIGH))
            if item.period:
                entity_node_id = f"ENTITY:metric:{item.metric_name}:{item.period}"
                if not any(node.node_id == entity_node_id for node in nodes):
                    nodes.append(EvidenceGraphNode(node_id=entity_node_id, node_type="metric_period_entity", label=f"{item.period} {item.metric_name}", confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED, metadata={"entity_type": "financial_metric_period", "metric_name": item.metric_name, "period": item.period}))
                edges.append(EvidenceGraphEdge(from_node_id=node_id, to_node_id=entity_node_id, relation=EvidenceRelation.MENTIONS, rationale="统一指标与期间实体", confidence=Confidence.HIGH))
        for ref in item.source_refs:
            source_node = f"SOURCE:{ref.source_id}"
            if source_node in source_nodes:
                edges.append(EvidenceGraphEdge(from_node_id=node_id, to_node_id=source_node, relation=EvidenceRelation.EXTRACTED_FROM, rationale=ref.excerpt, confidence=item.confidence))
                edges.append(EvidenceGraphEdge(from_node_id=node_id, to_node_id=source_node, relation=EvidenceRelation.FROM_SOURCE, rationale=ref.excerpt, confidence=item.confidence))
        if item.metric_name and item.period:
            metric_groups[(item.metric_name, item.period)].append(item)

    for (metric_name, period), items in metric_groups.items():
        values = {_normalized_value(item.metric_value, item.unit) for item in items if item.metric_value is not None}
        if len(values) > 1:
            message = f"{period} {metric_name} 在不同来源存在冲突：{', '.join(sorted(str(value) for value in values))}"
            conflicts.append(message)
            for left in items:
                for right in items:
                    if left.evidence_id < right.evidence_id and _normalized_value(left.metric_value, left.unit) != _normalized_value(right.metric_value, right.unit):
                        edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{left.evidence_id}", to_node_id=f"EVIDENCE:{right.evidence_id}", relation=EvidenceRelation.CONTRADICTS, rationale=message, confidence=Confidence.HIGH))

    statement_groups: dict[str, list] = defaultdict(list)
    for item in state.evidence_items:
        key = "".join(item.statement.lower().split())[:160]
        if key:
            statement_groups[key].append(item)
    for items in statement_groups.values():
        if len(items) > 1:
            anchor = items[0]
            for duplicate in items[1:]:
                edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{duplicate.evidence_id}", to_node_id=f"EVIDENCE:{anchor.evidence_id}", relation=EvidenceRelation.DUPLICATES, rationale="跨文档标准化后内容重复", confidence=Confidence.MEDIUM))

    question_ids = []
    if state.research_plan:
        for index, question in enumerate(state.research_plan.priority_questions):
            question_id = f"QUESTION:{index}"
            question_ids.append(question_id)
            nodes.append(EvidenceGraphNode(node_id=question_id, node_type="research_question", label=question, confidence=Confidence.MEDIUM, verification_status=VerificationStatus.TO_BE_VERIFIED))

    claim_node_ids = []
    for claim in state.research_claims:
        claim_id = f"CLAIM:{claim.claim_id}"
        claim_node_ids.append(claim_id)
        nodes.append(EvidenceGraphNode(node_id=claim_id, node_type="analysis_claim", label=claim.statement, confidence=claim.confidence, verification_status=VerificationStatus.PARTIALLY_SUPPORTED if claim.supporting_evidence_ids else VerificationStatus.UNSUPPORTED, metadata={"claim_id": claim.claim_id, "topic": claim.topic, "claim_type": claim.claim_type, "source_skill_ids": claim.source_skill_ids, "primary_section": claim.primary_section}))
        for evidence_id in claim.supporting_evidence_ids:
            edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{evidence_id}", to_node_id=claim_id, relation=EvidenceRelation.SUPPORTS, rationale=claim.topic, confidence=claim.confidence))
        for evidence_id in claim.counter_evidence_ids:
            edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{evidence_id}", to_node_id=claim_id, relation=EvidenceRelation.CONTRADICTS, rationale=f"反证：{claim.topic}", confidence=claim.confidence))
        variable_id = f"KEYVAR:{claim.claim_id}"
        nodes.append(EvidenceGraphNode(node_id=variable_id, node_type="key_variable", label=claim.topic, confidence=claim.confidence, verification_status=VerificationStatus.PARTIALLY_SUPPORTED, metadata={"claim_id": claim.claim_id}))
        edges.append(EvidenceGraphEdge(from_node_id=claim_id, to_node_id=variable_id, relation=EvidenceRelation.DEPENDS_ON, rationale="研究结论依赖该核心变量", confidence=claim.confidence))
        if question_ids:
            edges.append(EvidenceGraphEdge(from_node_id=claim_id, to_node_id=question_ids[0], relation=EvidenceRelation.RESPONDS_TO, rationale="回应研究问题", confidence=Confidence.MEDIUM))
    for challenge in state.research_judgment.red_team_challenges:
        challenge_id = f"REDTEAM:{challenge.challenge_id}"
        nodes.append(EvidenceGraphNode(node_id=challenge_id, node_type="red_team_challenge", label=challenge.title + "：" + challenge.mechanism, confidence=Confidence.HIGH if challenge.severity == "critical" else Confidence.MEDIUM, verification_status=VerificationStatus.UNSUPPORTED if challenge.status == "open" else VerificationStatus.PARTIALLY_SUPPORTED, metadata={"severity": challenge.severity, "status": challenge.status, "falsification_test": challenge.falsification_test, "missing_evidence": challenge.missing_evidence}))
        for evidence_id in challenge.evidence_ids:
            edges.append(EvidenceGraphEdge(from_node_id=challenge_id, to_node_id=f"EVIDENCE:{evidence_id}", relation=EvidenceRelation.QUESTIONED_BY, rationale=challenge.falsification_test, confidence=Confidence.HIGH))
        target = _challenge_target(challenge.evidence_ids, state.research_claims)
        if target:
            edges.append(EvidenceGraphEdge(from_node_id=challenge_id, to_node_id=f"CLAIM:{target}", relation=EvidenceRelation.CHALLENGES, rationale=challenge.mechanism, confidence=Confidence.HIGH))
        if challenge.missing_evidence:
            missing_id = f"MISSING:{challenge.challenge_id}"
            nodes.append(EvidenceGraphNode(node_id=missing_id, node_type="missing_evidence", label="；".join(challenge.missing_evidence), confidence=Confidence.LOW, verification_status=VerificationStatus.UNSUPPORTED))
            edges.append(EvidenceGraphEdge(from_node_id=missing_id, to_node_id=challenge_id, relation=EvidenceRelation.MISSING_EVIDENCE_FOR, rationale="关键反证仍缺验证材料", confidence=Confidence.HIGH))

    for decision in state.judge_decisions:
        judge_id = f"JUDGE:{decision.claim_id}"
        nodes.append(EvidenceGraphNode(node_id=judge_id, node_type="judge_finding", label=decision.reason, confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED, metadata={"claim_id": decision.claim_id, "decision": decision.decision, "approved_statement": decision.approved_statement, "missing_evidence": decision.missing_evidence}))
        relation = EvidenceRelation.VALIDATED_BY if decision.decision in {"approved", "downgraded"} else EvidenceRelation.REJECTED_BY
        edges.append(EvidenceGraphEdge(from_node_id=f"CLAIM:{decision.claim_id}", to_node_id=judge_id, relation=relation, rationale=decision.reason, confidence=Confidence.HIGH))

    review_output = state.output_for("research_coach_review")
    if review_output:
        user_memo_id = "USER_MEMO:current"
        nodes.append(EvidenceGraphNode(node_id=user_memo_id, node_type="user_claim", label="用户提交的待批改 Memo", confidence=Confidence.MEDIUM, verification_status=VerificationStatus.TO_BE_VERIFIED))
        for index, finding in enumerate(review_output.findings):
            review_id = f"REVIEW:{index}"
            nodes.append(EvidenceGraphNode(node_id=review_id, node_type="review_finding", label=finding.detail, confidence=finding.confidence, verification_status=VerificationStatus.PARTIALLY_SUPPORTED if finding.evidence_ids else VerificationStatus.UNSUPPORTED, metadata={"title": finding.title, "classification": finding.classification}))
            edges.append(EvidenceGraphEdge(from_node_id=review_id, to_node_id=user_memo_id, relation=EvidenceRelation.RESPONDS_TO, rationale=finding.title, confidence=finding.confidence))
            for evidence_id in finding.evidence_ids:
                edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{evidence_id}", to_node_id=review_id, relation=EvidenceRelation.SUPPORTS, rationale=finding.title, confidence=finding.confidence))

    if state.memo:
        for section in state.memo.sections:
            section_id = f"MEMO:{section.section_id}"
            nodes.append(EvidenceGraphNode(node_id=section_id, node_type="memo_section", label=section.title, confidence=section.confidence, verification_status=VerificationStatus.PARTIALLY_SUPPORTED, metadata={"section_id": section.section_id, "status": section.status}))
            for claim_id in section.supporting_claim_ids:
                edges.append(EvidenceGraphEdge(from_node_id=f"CLAIM:{claim_id}", to_node_id=section_id, relation=EvidenceRelation.INCLUDED_IN, rationale=section.title, confidence=section.confidence))
    node_by_id = {node.node_id: node for node in nodes}
    semantic_edges = [
        edge
        for edge in infer_semantic_edges_nli(nodes, semantic_client)
        if not _invalid_temporal_contradiction(edge, node_by_id)
    ] if include_semantic else []
    edges.extend(semantic_edges)
    semantic_conflicts = [edge.rationale or "语义冲突" for edge in edges if edge.relation == EvidenceRelation.CONTRADICTS and edge.relation_source in {"nli_model", "heuristic_fallback"}]
    return EvidenceGraph(nodes=nodes, edges=_dedupe_edges(edges), conflicts=list(dict.fromkeys([*conflicts, *semantic_conflicts])))


def merge_evidence_graphs(existing: EvidenceGraph | None, incoming: EvidenceGraph) -> EvidenceGraph:
    if existing is None:
        return incoming
    nodes = {node.node_id: node for node in incoming.nodes}
    for node in existing.nodes:
        if node.metadata.get("user_review_note") is not None:
            nodes[node.node_id] = node
        else:
            nodes.setdefault(node.node_id, node)
    merged_nodes = list(nodes.values())
    semantic_edges = infer_semantic_edges(merged_nodes)
    reviewed_edges = [edge for edge in existing.edges if edge.reviewed_by_user]
    reviewed_pairs = {(edge.from_node_id, edge.to_node_id) for edge in reviewed_edges}
    generated = [edge for edge in [*existing.edges, *incoming.edges, *semantic_edges] if not edge.reviewed_by_user and (edge.from_node_id, edge.to_node_id) not in reviewed_pairs]
    old_ids = {node.node_id for node in existing.nodes}
    incoming_ids = {node.node_id for node in incoming.nodes}
    added = incoming_ids - old_ids
    removed = [node_id for node_id in old_ids - incoming_ids if not nodes[node_id].metadata.get("user_review_note")]
    return EvidenceGraph(version=existing.version + 1, parent_version=existing.version, nodes=merged_nodes, edges=_dedupe_edges([*reviewed_edges, *generated]), conflicts=list(dict.fromkeys([*existing.conflicts, *incoming.conflicts])), change_summary=f"新增{len(added)}个节点，保留{len(old_ids)}个历史节点，发现{len(incoming.conflicts)}项当前冲突", removed_node_ids=removed)


def _normalized_value(value, unit: str | None):
    if not isinstance(value, (int, float)):
        return f"{value}|{unit}"
    multipliers = {"元": 1, "千元": 1_000, "万元": 10_000, "百万元": 1_000_000, "亿元": 100_000_000, "USD": 1, "USD/shares": 1, "%": 1}
    return round(float(value) * multipliers.get(unit or "", 1), 6)


def _challenge_target(evidence_ids: list[str], claims) -> str | None:
    evidence = set(evidence_ids)
    ranked = sorted(
        claims,
        key=lambda claim: len(evidence.intersection(claim.supporting_evidence_ids)),
        reverse=True,
    )
    if ranked and evidence.intersection(ranked[0].supporting_evidence_ids):
        return ranked[0].claim_id
    return ranked[0].claim_id if ranked else None


def _invalid_temporal_contradiction(
    edge: EvidenceGraphEdge,
    node_by_id: dict[str, EvidenceGraphNode],
) -> bool:
    if edge.relation != EvidenceRelation.CONTRADICTS:
        return False
    left = node_by_id.get(edge.from_node_id)
    right = node_by_id.get(edge.to_node_id)
    if left is None or right is None:
        return False
    left_metric, right_metric = left.metadata.get("metric_name"), right.metadata.get("metric_name")
    left_period, right_period = left.metadata.get("period"), right.metadata.get("period")
    return bool(
        left_metric
        and left_metric == right_metric
        and left_period
        and right_period
        and left_period != right_period
    )


def _dedupe_edges(edges: list[EvidenceGraphEdge]) -> list[EvidenceGraphEdge]:
    seen: set[tuple[str, str, str]] = set()
    result: list[EvidenceGraphEdge] = []
    for edge in edges:
        key = (edge.from_node_id, edge.to_node_id, edge.relation.value)
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result
