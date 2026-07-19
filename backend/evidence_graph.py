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


def build_evidence_graph(state: WorkflowState) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    conflicts: list[str] = []
    source_nodes: set[str] = set()
    for source in state.source_documents:
        node_id = f"SOURCE:{source.source_id}"
        source_nodes.add(node_id)
        nodes.append(EvidenceGraphNode(node_id=node_id, node_type="source", label=source.title, source_id=source.source_id, confidence=Confidence.MEDIUM, verification_status=VerificationStatus.VERIFIED if source.provided_by_user else VerificationStatus.TO_BE_VERIFIED, metadata={"source_type": source.source_type.value, "file_name": source.file_name, "url": source.url}))

    metric_groups: dict[tuple[str, str], list] = defaultdict(list)
    for item in state.evidence_items:
        node_id = f"EVIDENCE:{item.evidence_id}"
        nodes.append(EvidenceGraphNode(node_id=node_id, node_type=item.category.value, label=item.statement, evidence_id=item.evidence_id, confidence=item.confidence, verification_status=item.verification_status, metadata={"period": item.period, "metric_name": item.metric_name, "metric_value": item.metric_value, "unit": item.unit, "notes": item.notes}))
        for ref in item.source_refs:
            source_node = f"SOURCE:{ref.source_id}"
            if source_node in source_nodes:
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

    for output_key, output in state.agent_outputs.items():
        for index, finding in enumerate(output.findings):
            claim_id = f"CLAIM:{output_key}:{index}"
            nodes.append(EvidenceGraphNode(node_id=claim_id, node_type="analysis_claim", label=finding.detail, confidence=finding.confidence, verification_status=VerificationStatus.PARTIALLY_SUPPORTED if finding.evidence_ids else VerificationStatus.UNSUPPORTED, metadata={"title": finding.title, "classification": finding.classification, "agent": output.agent_name}))
            for evidence_id in finding.evidence_ids:
                edges.append(EvidenceGraphEdge(from_node_id=f"EVIDENCE:{evidence_id}", to_node_id=claim_id, relation=EvidenceRelation.SUPPORTS, rationale=finding.title, confidence=finding.confidence))
    return EvidenceGraph(nodes=nodes, edges=_dedupe_edges(edges), conflicts=conflicts)


def merge_evidence_graphs(existing: EvidenceGraph | None, incoming: EvidenceGraph) -> EvidenceGraph:
    if existing is None:
        return incoming
    nodes = {node.node_id: node for node in existing.nodes}
    nodes.update({node.node_id: node for node in incoming.nodes})
    return EvidenceGraph(nodes=list(nodes.values()), edges=_dedupe_edges([*existing.edges, *incoming.edges]), conflicts=list(dict.fromkeys([*existing.conflicts, *incoming.conflicts])))


def _normalized_value(value, unit: str | None):
    if not isinstance(value, (int, float)):
        return f"{value}|{unit}"
    multipliers = {"元": 1, "千元": 1_000, "万元": 10_000, "百万元": 1_000_000, "亿元": 100_000_000, "%": 1}
    return round(float(value) * multipliers.get(unit or "", 1), 6)


def _dedupe_edges(edges: list[EvidenceGraphEdge]) -> list[EvidenceGraphEdge]:
    seen: set[tuple[str, str, str]] = set()
    result: list[EvidenceGraphEdge] = []
    for edge in edges:
        key = (edge.from_node_id, edge.to_node_id, edge.relation.value)
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result
