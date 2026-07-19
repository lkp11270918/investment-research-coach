from __future__ import annotations

from .llm_client import LLMError, OpenAIClient
from .models import EvidenceGraph, MemoSection, MemoSuggestion


PROHIBITED_RATINGS = ("买入", "卖出", "增持", "减持", "强烈推荐", "目标价", "必涨", "稳赚")


def assess_memo_sections(sections: list[MemoSection], graph: EvidenceGraph, request_formal: bool) -> tuple[str, list[str]]:
    valid = {node.evidence_id: node for node in graph.nodes if node.evidence_id}
    issues: list[str] = []
    for section in sections:
        body = section.body.strip()
        if not body:
            issues.append(f"{section.title}：章节内容为空")
            continue
        found = [term for term in PROHIBITED_RATINGS if term in body]
        if found:
            issues.append(f"{section.title}：包含To C禁用评级表达 {', '.join(found)}")
        if not section.evidence_ids:
            issues.append(f"{section.title}：缺少可追溯证据")
            continue
        missing = [item for item in section.evidence_ids if item not in valid]
        if missing:
            issues.append(f"{section.title}：引用不存在的证据 {', '.join(missing)}")
        unsupported = [item for item in section.evidence_ids if item in valid and valid[item].verification_status.value in {"unsupported", "to_be_verified"}]
        if unsupported:
            issues.append(f"{section.title}：引用未验证证据 {', '.join(unsupported)}")
        opinion_types = {"management_opinion", "sell_side_opinion", "news_or_market_opinion", "user_opinion"}
        cited_types = {valid[item].node_type for item in section.evidence_ids if item in valid}
        if cited_types and cited_types.issubset(opinion_types):
            issues.append(f"{section.title}：仅引用观点材料，缺少独立事实证据")
        cited_nodes = {f"EVIDENCE:{item}" for item in section.evidence_ids}
        if any(edge.relation.value == "contradicts" and edge.from_node_id in cited_nodes and edge.to_node_id in cited_nodes for edge in graph.edges):
            issues.append(f"{section.title}：引用证据之间存在未解决冲突")
        unconfirmed_blocks = [item for item in section.evidence_ids if item in valid and any(ref.get("requires_confirmation") for ref in valid[item].metadata.get("source_refs", []) if isinstance(ref, dict))]
        if unconfirmed_blocks:
            issues.append(f"{section.title}：包含尚未确认的多模态证据 {', '.join(unconfirmed_blocks)}")
    critical_open = [node.label for node in graph.nodes if node.node_type == "red_team_challenge" and node.metadata.get("severity") == "critical" and node.metadata.get("status") == "open"]
    if request_formal and critical_open:
        issues.append("关键反证尚未解决：" + "；".join(critical_open[:3]))
    if request_formal and not sections:
        issues.append("正式 Memo 不能为空")
    return ("formal" if request_formal and not issues else "needs_evidence" if issues else "draft"), list(dict.fromkeys(issues))


def generate_memo_suggestions(sections: list[MemoSection], graph: EvidenceGraph, client: OpenAIClient | None = None) -> list[MemoSuggestion]:
    client = client or OpenAIClient()
    _, issues = assess_memo_sections(sections, graph, False)
    evidence = [{"evidence_id": node.evidence_id, "label": node.label, "status": node.verification_status.value} for node in graph.nodes if node.evidence_id][:120]
    if client.available:
        try:
            result = client.generate_json(system_prompt="你是买方研究共同写作教练。只提出修改建议，不直接覆盖用户原文。每条建议必须绑定证据，区分事实、假设和未知，不得给买卖评级。返回JSON：{\"suggestions\":[{\"section_id\":\"...\",\"proposed_body\":\"...\",\"rationale\":\"...\",\"evidence_ids\":[]}]}。", user_payload={"sections": [item.model_dump(mode="json") for item in sections], "evidence": evidence, "gate_issues": issues}, temperature=0)
            valid_ids = {item["evidence_id"] for item in evidence}
            suggestions = []
            section_ids = {item.section_id for item in sections}
            for raw in result.get("suggestions", []):
                if raw.get("section_id") not in section_ids: continue
                suggestions.append(MemoSuggestion(section_id=str(raw["section_id"]), proposed_body=str(raw.get("proposed_body") or ""), rationale=str(raw.get("rationale") or "补强证据与判断边界"), evidence_ids=[item for item in raw.get("evidence_ids", []) if item in valid_ids]))
            if suggestions: return suggestions
        except (LLMError, TypeError, ValueError):
            pass
    suggestions = []
    for section in sections:
        section_issues = [issue for issue in issues if issue.startswith(section.title + "：")]
        if section_issues:
            suggestions.append(MemoSuggestion(section_id=section.section_id, proposed_body=section.body, rationale="；".join(section_issues), evidence_ids=[item for item in section.evidence_ids if any(node.evidence_id == item for node in graph.nodes)]))
    return suggestions
