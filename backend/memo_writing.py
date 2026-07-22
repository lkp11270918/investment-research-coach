from __future__ import annotations

from .agents import DISCLAIMER_ZH, run_gate_blocked_memo
from .models import Confidence, MemoSection, ResearchMemo, WorkflowState

SECTION_TOPICS = {
    "business_model": ("公司靠什么赚钱", ("商业", "收入", "利润", "产能", "渠道", "净息差")),
    "cash_flow_quality": ("现金流与财务质量", ("现金流", "财务", "负债", "ROE", "分红")),
    "management_views": ("管理层与多方观点", ("管理层", "卖方", "观点", "分歧", "资本配置")),
    "valuation_margin": ("估值与安全边际", ("估值", "安全边际", "FCFF", "FCFE", "PE", "PB")),
    "value_trap": ("价值陷阱与反证", ("风险", "陷阱", "反证", "推翻", "下行")),
}


def run_memo_writing_skill(state: WorkflowState) -> ResearchMemo:
    """Deterministically format only claim text explicitly approved by Judge."""
    if not state.pre_memo_gate or state.pre_memo_gate.status != "pass":
        return run_gate_blocked_memo(state)
    claims={item.claim_id:item for item in state.research_claims}
    approved=[(claims[item.claim_id],item.approved_statement) for item in state.judge_decisions if item.claim_id in claims and item.decision in {"approved","downgraded"} and item.approved_statement]
    if not approved:
        return run_gate_blocked_memo(state)
    sections=[]; used=set()
    for section_id,(title,keywords) in SECTION_TOPICS.items():
        selected=[]
        for claim,statement in approved:
            if claim.claim_id in used: continue
            haystack=f"{claim.topic}{statement}"
            if any(keyword.lower() in haystack.lower() for keyword in keywords): selected.append((claim,statement)); used.add(claim.claim_id)
        if selected:
            sections.append(MemoSection(section_id=section_id,title=title,body="\n\n".join(statement for _,statement in selected),evidence_ids=list(dict.fromkeys(eid for claim,_ in selected for eid in claim.supporting_evidence_ids)),confidence=Confidence.MEDIUM))
    remaining=[(claim,statement) for claim,statement in approved if claim.claim_id not in used]
    if remaining:
        sections.append(MemoSection(section_id="research_view",title="经审查研究判断",body="\n\n".join(statement for _,statement in remaining),evidence_ids=list(dict.fromkeys(eid for claim,_ in remaining for eid in claim.supporting_evidence_ids)),confidence=Confidence.MEDIUM))
    rejected=[item for item in state.judge_decisions if item.decision not in {"approved","downgraded"}]
    sections.append(MemoSection(section_id="uncertainty",title="不确定性与资料缺口",body="\n".join(f"- {item.reason}" for item in rejected) or "未发现额外未批准结论。",confidence=Confidence.LOW))
    sections.append(MemoSection(section_id="disclaimer",title="不构成投资建议声明",body=DISCLAIMER_ZH,confidence=Confidence.HIGH))
    memo=ResearchMemo(company_profile=state.company_profile,user_mode=state.company_profile.user_mode,confidence=Confidence.MEDIUM,sections=sections,source_ids=list(dict.fromkeys(ref.source_id for item in state.evidence_items for ref in item.source_refs)),disclaimer=DISCLAIMER_ZH)
    memo.markdown="\n\n".join(f"## {section.title}\n\n{section.body}" for section in sections)
    return memo
