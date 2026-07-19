from __future__ import annotations

from .models import EvidenceCategory, RedTeamChallenge, ResearchJudgment, SourceType, ViewComparisonPoint, WorkflowState


def build_research_judgment(state: WorkflowState) -> ResearchJudgment:
    source_by_id = {source.source_id: source for source in state.source_documents}
    evidence_by_id = {item.evidence_id: item for item in state.evidence_items}
    sell_side_sources = {source.source_id for source in state.source_documents if source.source_type == SourceType.SELL_SIDE_SUMMARY}
    view_output = state.agent_outputs.get("management_view_comparison")
    points: list[ViewComparisonPoint] = []
    if view_output:
        for finding in view_output.findings:
            source_ids = list(dict.fromkeys(ref.source_id for evidence_id in finding.evidence_ids if evidence_id in evidence_by_id for ref in evidence_by_id[evidence_id].source_refs))
            title = finding.title
            point_type = "consensus" if "共同" in title or "共识" in title else "divergence" if "分歧" in title else "buyer_question" if "验证" in title else "narrative_gap"
            points.append(ViewComparisonPoint(point_type=point_type, topic=title, detail=finding.detail, evidence_ids=finding.evidence_ids, source_ids=source_ids, assumption_difference=finding.detail if "假设" in title or "分歧来源" in title else None, buyer_verification_question=f"哪些公司原始事实能够验证：{title}？" if point_type in {"divergence", "buyer_question"} else None))
    sell_side_evidence = [item for item in state.evidence_items if item.category == EvidenceCategory.SELL_SIDE_OPINION]
    represented_sources = {ref.source_id for item in sell_side_evidence for ref in item.source_refs}
    if len(represented_sources) >= 2 and not any(point.point_type == "divergence" for point in points):
        points.append(ViewComparisonPoint(point_type="divergence", topic="卖方假设尚未形成可比口径", detail="已存在多份卖方来源，但尚未识别可验证的预测假设差异。不能把并列摘要当作观点比较。", evidence_ids=[item.evidence_id for item in sell_side_evidence], source_ids=sorted(represented_sources), buyer_verification_question="统一各家收入增速、利润率、资本开支和估值期间后重新比较。"))

    trap_output = state.agent_outputs.get("value_trap_contradiction")
    challenges: list[RedTeamChallenge] = []
    if trap_output:
        for finding in trap_output.findings:
            valid_ids = [item for item in finding.evidence_ids if item in evidence_by_id]
            severity = "critical" if any(term in finding.title + finding.detail for term in ("现金流", "债", "衰退", "造假", "推翻", "价值陷阱")) else "medium"
            challenges.append(RedTeamChallenge(title=finding.title, mechanism=finding.detail, severity=severity, evidence_ids=valid_ids, missing_evidence=[] if valid_ids else ["能够验证该风险机制的公司原始事实"], falsification_test=f"若“{finding.title}”对应变量连续恶化或突破用户设定阈值，则重新评估当前观点。", status="evidence_found" if valid_ids else "open"))
    independent = [item for item in state.evidence_items if item.category in {EvidenceCategory.FACT, EvidenceCategory.FINANCIAL_FACT} and item.source_refs and all(ref.source_id not in sell_side_sources for ref in item.source_refs)]
    unresolved = sum(item.severity == "critical" and item.status == "open" for item in challenges)
    return ResearchJudgment(view_points=points, red_team_challenges=challenges, sell_side_source_count=len(sell_side_sources), independent_fact_count=len(independent), unresolved_critical_count=unresolved)
