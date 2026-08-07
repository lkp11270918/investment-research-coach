from __future__ import annotations

import re

from .models import DocumentView, EvidenceCategory, RedTeamChallenge, ResearchAssumption, ResearchJudgment, SourceType, ViewComparisonPoint, WorkflowState


_VIEW_TERMS = ("我们认为", "核心观点", "核心结论", "预计", "有望", "增长", "商业化", "竞争", "战略", "风险")
_ASSUMPTION_TERMS = ("假设", "预计", "有望", "取决于", "依赖", "若", "如果", "将会", "潜力")


def _clean_sentences(content: str) -> list[str]:
    compact = re.sub(r"[\t\r ]+", " ", content or "")
    candidates = re.split(r"(?<=[。！？!?])\s*|\n+", compact)
    sentences: list[str] = []
    for candidate in candidates:
        text = re.sub(r"^\s*(?:第?\s*\d+\s*页|page\s*\d+|\d+)\s*$", "", candidate.strip(), flags=re.I)
        if 18 <= len(text) <= 420 and text not in sentences:
            sentences.append(text)
    return sentences


def _ranked_sentences(content: str, terms: tuple[str, ...], limit: int) -> list[str]:
    sentences = _clean_sentences(content)
    ranked = sorted(enumerate(sentences), key=lambda item: (-sum(term in item[1] for term in terms), item[0]))
    selected = [sentence for _, sentence in ranked if any(term in sentence for term in terms)][:limit]
    return selected or sentences[:limit]


def _build_document_views(state: WorkflowState) -> list[DocumentView]:
    views: list[DocumentView] = []
    sources = [
        (source.source_id, source.title or source.file_name or "未命名资料", source.content)
        for source in state.source_documents
    ] or [
        (f"RAW-{index + 1}", material.title or material.file_name or f"资料 {index + 1}", material.content)
        for index, material in enumerate(state.raw_materials)
    ]
    for source_id, title, content in sources:
        source_evidence = [item for item in state.evidence_items if any(ref.source_id == source_id for ref in item.source_refs)]
        evidence_points = list(dict.fromkeys(item.statement.strip() for item in source_evidence if item.statement.strip()))
        fallback_points = _ranked_sentences(content, _VIEW_TERMS, 3)
        points = (evidence_points or fallback_points)[:3]
        if not points:
            points = ["该资料已完成解析，但没有识别出可靠的实质性观点。"]
        views.append(DocumentView(
            source_id=source_id,
            title=title,
            main_view=points[0],
            supporting_points=points[1:],
            evidence_ids=[item.evidence_id for item in source_evidence[:6]],
        ))
    return views


def _build_core_assumptions(state: WorkflowState, document_views: list[DocumentView]) -> list[ResearchAssumption]:
    assumptions: list[ResearchAssumption] = []
    seen: set[str] = set()
    source_by_id = {source.source_id: source for source in state.source_documents}
    raw_content_by_id = {f"RAW-{index + 1}": material.content for index, material in enumerate(state.raw_materials)}
    for view in document_views:
        source = source_by_id.get(view.source_id)
        candidates = _ranked_sentences(source.content if source else raw_content_by_id.get(view.source_id, ""), _ASSUMPTION_TERMS, 3)
        if not candidates:
            candidates = [point for point in [view.main_view, *view.supporting_points] if any(term in point for term in _ASSUMPTION_TERMS)]
        for statement in candidates:
            normalized = re.sub(r"\s+", "", statement)
            if normalized in seen:
                continue
            seen.add(normalized)
            assumptions.append(ResearchAssumption(
                statement=statement,
                source_ids=[view.source_id],
                evidence_ids=view.evidence_ids,
                verification_question=f"需要验证：支撑“{statement[:50]}”的关键事实是否持续成立？",
            ))
            if len(assumptions) >= 8:
                return assumptions
    return assumptions


def build_research_judgment(state: WorkflowState) -> ResearchJudgment:
    source_by_id = {source.source_id: source for source in state.source_documents}
    evidence_by_id = {item.evidence_id: item for item in state.evidence_items}
    sell_side_sources = {source.source_id for source in state.source_documents if source.source_type == SourceType.SELL_SIDE_SUMMARY}
    view_output = state.output_for("management_view_comparison")
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

    trap_output = state.output_for("value_trap_contradiction")
    challenges: list[RedTeamChallenge] = []
    if trap_output:
        for finding in trap_output.findings:
            valid_ids = [item for item in finding.evidence_ids if item in evidence_by_id]
            severity = "critical" if any(term in finding.title + finding.detail for term in ("现金流", "债", "衰退", "造假", "推翻", "价值陷阱")) else "medium"
            challenges.append(RedTeamChallenge(title=finding.title, mechanism=finding.detail, severity=severity, evidence_ids=valid_ids, missing_evidence=[] if valid_ids else ["能够验证该风险机制的公司原始事实"], falsification_test=f"若“{finding.title}”对应变量连续恶化或突破用户设定阈值，则重新评估当前观点。", status="evidence_found" if valid_ids else "open"))
    independent = [item for item in state.evidence_items if item.category in {EvidenceCategory.FACT, EvidenceCategory.FINANCIAL_FACT} and item.source_refs and all(ref.source_id not in sell_side_sources for ref in item.source_refs)]
    unresolved = sum(item.severity == "critical" and item.status == "open" for item in challenges)
    document_views = _build_document_views(state)
    core_assumptions = _build_core_assumptions(state, document_views)
    return ResearchJudgment(document_views=document_views, core_assumptions=core_assumptions, view_points=points, red_team_challenges=challenges, sell_side_source_count=len(sell_side_sources), independent_fact_count=len(independent), unresolved_critical_count=unresolved)
