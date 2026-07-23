from __future__ import annotations

from collections import defaultdict

from .agents import DISCLAIMER_ZH
from .models import Confidence, MemoSection, ResearchClaim, ResearchMemo, WorkflowState
from .research_agents import _route_claim


STANDARD_SECTIONS = (
    ("company_info", "公司基本信息"),
    ("material_scope_confidence", "资料范围与结论置信度"),
    ("circle_of_competence", "能力圈判断"),
    ("business_model", "商业模式"),
    ("key_variables", "核心经营变量"),
    ("financial_quality", "财务质量"),
    ("cash_flow", "现金流质量"),
    ("dividend", "分红质量与可持续性"),
    ("balance_sheet", "资产负债表安全性"),
    ("earnings_quality", "盈利质量"),
    ("moat", "护城河与竞争优势"),
    ("industry_competition", "行业与竞争格局"),
    ("management_capital_allocation", "管理层与资本配置"),
    ("narrative_vs_financials", "管理层叙事与财务现实"),
    ("view_comparison", "多方观点比较"),
    ("valuation_margin", "估值与安全边际"),
    ("value_trap", "价值陷阱与反证"),
    ("verification_gaps", "待验证问题与资料缺口"),
    ("sources_disclaimer", "来源与免责声明"),
)

SECTION_TITLES=dict(STANDARD_SECTIONS)
RESEARCH_SECTIONS={
    "circle_of_competence","business_model","key_variables","financial_quality",
    "cash_flow","dividend","balance_sheet","earnings_quality","moat",
    "industry_competition","management_capital_allocation",
    "narrative_vs_financials","view_comparison","valuation_margin","value_trap",
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
        "moat":"business_model_moat","financial_quality":"financial_quality_dividend",
        "cash_flow":"financial_quality_dividend","dividend":"financial_quality_dividend",
        "balance_sheet":"financial_quality_dividend","earnings_quality":"financial_quality_dividend",
        "management_capital_allocation":"management_view_comparison",
        "narrative_vs_financials":"management_view_comparison","view_comparison":"management_view_comparison",
        "valuation_margin":"valuation_margin","value_trap":"value_trap_contradiction",
    }
    skill=state.skill_outputs.get(skill_by_section.get(section_id,""))
    missing=list(getattr(skill,"missing_inputs",[])) if skill else []
    if section_id in {"circle_of_competence","business_model","moat"} and skill:
        structured=getattr(skill,"structured_output",{})
        missing.extend(structured.get("missing_information",[]) if isinstance(structured,dict) else [])
    return list(dict.fromkeys(str(item) for item in missing if item))


def _research_section(
    state: WorkflowState,
    section_id: str,
    selected: list[tuple[ResearchClaim,str]],
) -> MemoSection:
    missing=_missing_for(state,section_id)
    if not selected:
        body="当前没有经 Red Team & Judge 批准且证据充分的结论；该部分保留为明确资料缺口。"
        return MemoSection(
            section_id=section_id,title=SECTION_TITLES[section_id],body=body,
            confidence=Confidence.LOW,status="insufficient_data",
            summary=body,missing_information=missing or ["缺少可进入本章的经审查结论。"],
        )
    statements=list(dict.fromkeys(statement.strip() for _,statement in selected if statement.strip()))
    if section_id=="narrative_vs_financials":
        body="对管理层叙事与已披露财务结果进行交叉审查后，当前可保留的判断是："+"；".join(statements)
    elif section_id=="view_comparison":
        body="综合不同观点的共同点、分歧点及其假设来源后，当前可保留的判断是："+"；".join(statements)
    else:
        body="\n\n".join(statements)
    evidence_ids=list(dict.fromkeys(eid for claim,_ in selected for eid in claim.supporting_evidence_ids))
    claim_ids=[claim.claim_id for claim,_ in selected]
    confidence=Confidence.HIGH if selected and all(claim.confidence==Confidence.HIGH for claim,_ in selected) else Confidence.MEDIUM
    return MemoSection(
        section_id=section_id,title=SECTION_TITLES[section_id],body=body,
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
    sections=[]
    for section_id,title in STANDARD_SECTIONS:
        if section_id=="company_info":
            body=f"公司：{profile.company_name}；代码：{profile.ticker or '未提供'}；行业：{profile.industry or '未提供'}。"
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.MEDIUM,status="complete",summary=body))
        elif section_id=="material_scope_confidence":
            conflicts=sum(item.type_conflict for item in state.document_intelligence)
            body=(f"本次研究使用 {len(state.source_documents)} 份资料和 {len(state.evidence_items)} 条证据；"
                  f"识别到 {conflicts} 处资料类型冲突；Evidence Graph 质量得分为 {state.evidence_graph_quality.score:.1f}。"
                  "正文只保留 Judge 批准或降级后的表达。")
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.MEDIUM,status="complete",summary=body))
        elif section_id in RESEARCH_SECTIONS:
            sections.append(_research_section(state,section_id,routed.get(section_id,[])))
        elif section_id=="verification_gaps":
            questions=list(dict.fromkeys(
                ([*state.pre_memo_gate.unsupported_claims,*state.pre_memo_gate.evidence_issues,*state.pre_memo_gate.compliance_warnings] if state.pre_memo_gate and not gate_passed else [])
                +[item for decision in state.judge_decisions for item in decision.missing_evidence]
                +[item for claim,_ in approved for item in claim.falsification_conditions]
                +[item for skill in state.skill_outputs.values() for item in getattr(skill,"missing_inputs",[])]
                +[item for doc in state.document_intelligence for item in doc.warnings]
            ))
            body="\n".join(f"- {item}" for item in questions) or "当前没有新增待验证问题。"
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.LOW,status="partial" if questions else "complete",summary=questions[0] if questions else body,missing_information=questions))
        elif section_id=="sources_disclaimer":
            sources="\n".join(f"- {source.source_id}：{source.title}（{source.source_type.value}）" for source in state.source_documents) or "无来源资料。"
            body=f"{sources}\n\n{DISCLAIMER_ZH}"
            sections.append(MemoSection(section_id=section_id,title=title,body=body,confidence=Confidence.HIGH,status="complete",summary="列示本次使用的来源并声明不构成投资建议。"))

    memo=ResearchMemo(
        company_profile=profile,user_mode=profile.user_mode,confidence=Confidence.MEDIUM if gate_passed else Confidence.LOW,
        sections=sections,source_ids=list(dict.fromkeys(item.source_id for item in state.source_documents)),
        disclaimer=DISCLAIMER_ZH,
    )
    prefix="# 待补证据研究草稿\n\n当前研究未通过证据与合规门禁，不能生成正式研究 Memo；以下固定 19 章仅用于明确待补证据和研究缺口。\n\n" if not gate_passed else ""
    memo.markdown=prefix+"\n\n".join(f"## {item.title}\n\n{item.body}" for item in sections)
    return memo
