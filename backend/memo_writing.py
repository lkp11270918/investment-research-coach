from __future__ import annotations

from collections import defaultdict

from .agents import DISCLAIMER_ZH
from .localization import is_english
from .memo_chapters import (
    MEMO_CHAPTERS,
    MEMO_CHAPTERS_EN,
    MEMO_CHAPTER_TITLES,
    MEMO_CHAPTER_TITLES_EN,
    MemoChapter,
)
from .models import Confidence, MemoSection, ResearchClaim, ResearchMemo, WorkflowState
from .research_agents import _route_claim


STANDARD_SECTIONS = MEMO_CHAPTERS
STANDARD_SECTIONS_EN = MEMO_CHAPTERS_EN
SECTION_TITLES = MEMO_CHAPTER_TITLES
SECTION_TITLES_EN = MEMO_CHAPTER_TITLES_EN
DISCLAIMER_EN = (
    "This material is for research training only. It does not constitute investment advice, "
    "a trading instruction, or a guarantee of returns."
)
RESEARCH_SECTIONS={
    "circle_of_competence","business_model","key_variables","financial_earnings_quality",
    "cash_flow","dividend","balance_sheet","business_stability_moat",
    "industry_competition","management_capital_allocation",
    "narrative_vs_financials","sell_side_consensus_divergence","valuation_margin","value_trap",
}


def _approved_claims(state: WorkflowState) -> list[tuple[ResearchClaim, str]]:
    claims={item.claim_id:item for item in state.research_claims}
    return [
        (_route_claim(claims[item.claim_id]),item.approved_statement)
        for item in state.judge_decisions
        if item.claim_id in claims
        and item.decision in {"approved","downgraded"}
        and item.approved_statement
    ]


def _missing_for(state: WorkflowState, section_id: str) -> list[str]:
    skill_by_section={
        "circle_of_competence":"business_model_moat","business_model":"business_model_moat",
        "business_stability_moat":"business_model_moat","financial_earnings_quality":"financial_quality_dividend",
        "cash_flow":"financial_quality_dividend","dividend":"financial_quality_dividend",
        "balance_sheet":"financial_quality_dividend",
        "management_capital_allocation":"management_view_comparison",
        "narrative_vs_financials":"management_view_comparison","sell_side_consensus_divergence":"management_view_comparison",
        "valuation_margin":"valuation_margin","value_trap":"value_trap_contradiction",
    }
    skill=state.skill_outputs.get(skill_by_section.get(section_id,""))
    missing=list(getattr(skill,"missing_inputs",[])) if skill else []
    if section_id in {"circle_of_competence","business_model","business_stability_moat"} and skill:
        structured=getattr(skill,"structured_output",{})
        missing.extend(structured.get("missing_information",[]) if isinstance(structured,dict) else [])
    return list(dict.fromkeys(str(item) for item in missing if item))


def _research_section(
    state: WorkflowState,
    section_id: str,
    selected: list[tuple[ResearchClaim,str]],
) -> MemoSection:
    english = is_english(state.company_profile.research_language)
    title = (SECTION_TITLES_EN if english else SECTION_TITLES)[section_id]
    missing=_missing_for(state,section_id)
    if not selected:
        body=("No evidence-supported conclusion has been approved by the Red Team & Judge; "
              "this section is retained as an explicit information gap.") if english else "当前没有经 Red Team & Judge 批准且证据充分的结论；该部分保留为明确资料缺口。"
        return MemoSection(
            section_id=section_id,title=title,body=body,
            confidence=Confidence.LOW,status="insufficient_data",
            summary=body,missing_information=missing or (["No reviewed conclusion is available for this section."] if english else ["缺少可进入本章的经审查结论。"]),
        )
    statements=list(dict.fromkeys(statement.strip() for _,statement in selected if statement.strip()))
    if section_id=="narrative_vs_financials":
        body=("After cross-checking management narratives against disclosed financial results, the supported conclusions are: " + "; ".join(statements)) if english else "对管理层叙事与已披露财务结果进行交叉审查后，当前可保留的判断是："+"；".join(statements)
    elif section_id=="sell_side_consensus_divergence":
        body=("After comparing consensus, disagreements, and their underlying assumptions, the supported conclusions are: " + "; ".join(statements)) if english else "综合不同观点的共同点、分歧点及其假设来源后，当前可保留的判断是："+"；".join(statements)
    else:
        body="\n\n".join(statements)
    evidence_ids=list(dict.fromkeys(eid for claim,_ in selected for eid in claim.supporting_evidence_ids))
    claim_ids=[claim.claim_id for claim,_ in selected]
    confidence=Confidence.HIGH if selected and all(claim.confidence==Confidence.HIGH for claim,_ in selected) else Confidence.MEDIUM
    return MemoSection(
        section_id=section_id,title=title,body=body,
        evidence_ids=evidence_ids,confidence=confidence,
        status="partial" if missing else "complete",summary=statements[0],
        supporting_claim_ids=claim_ids,missing_information=missing,
    )


def run_memo_writing_skill(state: WorkflowState) -> ResearchMemo:
    """Write the fixed 19-section Memo from Judge-approved claims only."""
    approved=_approved_claims(state)
    gate_passed=bool(state.pre_memo_gate and state.pre_memo_gate.status=="pass")

    routed: dict[str,list[tuple[ResearchClaim,str]]]=defaultdict(list)
    seen_claims=set()
    for claim,statement in approved:
        if claim.claim_id in seen_claims:
            continue
        seen_claims.add(claim.claim_id)
        routed[claim.primary_section or "key_variables"].append((claim,statement))

    profile=state.company_profile
    english=is_english(profile.research_language)
    standard_sections=STANDARD_SECTIONS_EN if english else STANDARD_SECTIONS
    disclaimer=DISCLAIMER_EN if english else DISCLAIMER_ZH
    sections=[]
    for section_id,title in standard_sections:
        if section_id=="company_info":
            body=(f"Company: {profile.company_name}; Ticker: {profile.ticker or 'Not provided'}; Industry: {profile.industry or 'Not provided'}."
                  if english else f"公司：{profile.company_name}；代码：{profile.ticker or '未提供'}；行业：{profile.industry or '未提供'}。")
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.MEDIUM,status="complete",summary=body))
        elif section_id=="scope_doctrine_confidence":
            conflicts=sum(item.type_conflict for item in state.document_intelligence)
            body=(f"This research used {len(state.source_documents)} source documents and {len(state.evidence_items)} evidence items; "
                  f"{conflicts} material-type conflicts were identified; the Evidence Graph quality score is {state.evidence_graph_quality.score:.1f}. "
                  "The memo contains only statements approved or downgraded by the Judge." if english else
                  f"本次研究使用 {len(state.source_documents)} 份资料和 {len(state.evidence_items)} 条证据；"
                  f"识别到 {conflicts} 处资料类型冲突；Evidence Graph 质量得分为 {state.evidence_graph_quality.score:.1f}。"
                  "正文只保留 Judge 批准或降级后的表达。")
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.MEDIUM,status="complete",summary=body))
        elif section_id in RESEARCH_SECTIONS:
            sections.append(_research_section(state,section_id,routed.get(section_id,[])))
        elif section_id=="verification_questions":
            questions=list(dict.fromkeys(
                ([*state.pre_memo_gate.unsupported_claims,*state.pre_memo_gate.evidence_issues,*state.pre_memo_gate.compliance_warnings] if state.pre_memo_gate and not gate_passed else [])
                +[item for decision in state.judge_decisions for item in decision.missing_evidence]
                +[item for claim,_ in approved for item in claim.falsification_conditions]
                +[item for skill in state.skill_outputs.values() for item in getattr(skill,"missing_inputs",[])]
                +[item for doc in state.document_intelligence for item in doc.warnings]
            ))
            body="\n".join(f"- {item}" for item in questions) or ("No new verification questions." if english else "当前没有新增待验证问题。")
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.LOW,status="partial" if questions else "complete",summary=questions[0] if questions else body,missing_information=questions))
        elif section_id=="research_view_uncertainty":
            gaps=list(dict.fromkeys(
                [item for decision in state.judge_decisions for item in decision.missing_evidence]
                +[item for skill in state.skill_outputs.values() for item in getattr(skill,"missing_inputs",[])]
            ))
            body=("Research label: insufficient information to rate. Uncertainty and information gaps: " if english else
                  "研究观点与内部研究标签：资料不足暂不评级。不确定性与资料缺口：") + (
                  "; ".join(gaps) if gaps else ("No material gap identified." if english else "当前未识别新增重大资料缺口。")
            )
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.LOW,status="partial" if gaps else "complete",summary=body,missing_information=gaps))
        elif section_id=="sources_disclaimer":
            sources=(
                "\n".join(f"- {source.source_id}: {source.title} ({source.source_type.value})" for source in state.source_documents)
                if english else
                "\n".join(f"- {source.source_id}：{source.title}（{source.source_type.value}）" for source in state.source_documents)
            ) or ("No source documents." if english else "无来源资料。")
            body=f"{sources}\n\n{disclaimer}"
            summary="Lists the sources used and states the research-training disclaimer." if english else "列示本次使用的来源并声明不构成投资建议。"
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.HIGH,status="complete",summary=summary))

    memo=ResearchMemo(
        company_profile=profile,user_mode=profile.user_mode,confidence=Confidence.MEDIUM if gate_passed else Confidence.LOW,
        sections=sections,source_ids=list(dict.fromkeys(item.source_id for item in state.source_documents)),
        disclaimer=disclaimer,
    )
    prefix=("# Information-Limited Research Report\n\nThis report is based only on the materials provided. "
            "Sections with insufficient evidence state the known information and the specific gaps to verify; the report is not a complete investment conclusion.\n\n"
            if english and not gate_passed else
            "# 信息有限研究报告\n\n本报告仅基于已提供的资料组成。证据不足的章节会同时列出当前已知信息与待验证缺口；本报告不代表完整的投资结论。\n\n"
            if not gate_passed else "")
    memo.markdown=prefix+"\n\n".join(f"## {item.title}\n\n{item.body}" for item in sections)
    return memo
