from __future__ import annotations

import hashlib
import json

from .agent_architecture import build_research_plan
from .llm_client import LLMError, OpenAIClient
from .models import AgentFinding, AgentOutput, AgentStatus, Confidence, JudgeDecision, ResearchClaim, ResearchExecutionPlan, SkillResult, SourceType, WorkflowState
from .value_investing_doctrine import doctrine_text

ALLOWED_SKILLS = {
    "financial_quality_dividend", "business_model_moat", "valuation_margin", "management_view_comparison",
    "bank_analysis", "manufacturing_analysis", "consumer_analysis", "utility_analysis", "general_business_analysis",
}
INDUSTRY_SKILLS={"bank_analysis","manufacturing_analysis","consumer_analysis","utility_analysis","general_business_analysis"}
MEMO_SECTIONS={
    "company_info","material_scope_confidence","circle_of_competence","business_model",
    "key_variables","financial_quality","cash_flow","dividend","balance_sheet",
    "earnings_quality","moat","industry_competition","management_capital_allocation",
    "narrative_vs_financials","view_comparison","valuation_margin","value_trap",
    "verification_gaps","sources_disclaimer",
}


def _route_claim(claim: ResearchClaim) -> ResearchClaim:
    """Assign one primary chapter from provenance, then refine inside that Skill family."""
    if claim.primary_section in MEMO_SECTIONS:
        return claim
    skill=claim.source_skill_ids[0] if claim.source_skill_ids else ""
    text=f"{claim.topic} {claim.statement}"
    if skill=="business_model_moat":
        section="moat" if any(term in text for term in ("护城河","竞争优势","壁垒","侵蚀")) else "circle_of_competence" if "能力圈" in text else "business_model"
    elif skill=="financial_quality_dividend":
        section="cash_flow" if "现金流" in text else "dividend" if any(term in text for term in ("分红","股息","派息")) else "balance_sheet" if any(term in text for term in ("负债","杠杆","偿债","资本充足","拨备")) else "earnings_quality" if any(term in text for term in ("盈利质量","非经常","应收","存货","利润")) else "financial_quality"
    elif skill=="management_view_comparison":
        section="narrative_vs_financials" if any(term in text for term in ("管理层叙事","财务现实","财务事实","是否冲突","乐观偏差")) else "management_capital_allocation" if any(term in text for term in ("资本配置","资本开支","并购","回购","扩产")) else "view_comparison"
    elif skill=="valuation_margin":
        section="valuation_margin"
    elif skill=="value_trap_contradiction" or claim.claim_type=="risk":
        section="value_trap"
    elif skill in INDUSTRY_SKILLS:
        section="key_variables" if any(term in text for term in ("变量","驱动","敏感")) else "industry_competition"
    else:
        section="key_variables"
    claim.primary_section=section
    claim.topics=list(dict.fromkeys([*claim.topics,section]))
    return claim


def _structured_business_claims(results: list[SkillResult]) -> list[ResearchClaim]:
    result=next((item for item in results if item.skill_id=="business_model_moat"),None)
    if not result or not result.structured_output:
        return []
    data=result.structured_output
    evidence=[str(item) for item in data.get("evidence_ids",[])]
    claims=[]
    business_parts=[
        str(data.get("value_proposition") or ""),
        f"客户：{'、'.join(data.get('customers',[]))}" if data.get("customers") else "",
        f"收入来源：{'、'.join(data.get('revenue_sources',[]))}" if data.get("revenue_sources") else "",
        f"利润池：{'、'.join(data.get('profit_pools',[]))}" if data.get("profit_pools") else "",
        f"资本强度：{data.get('capital_intensity')}" if data.get("capital_intensity") else "",
    ]
    business="；".join(item for item in business_parts if item)
    if business:
        claims.append(ResearchClaim(topic="商业模式",statement=business,claim_type="reasoning",supporting_evidence_ids=evidence,confidence=Confidence.MEDIUM,source_skill_ids=[result.skill_id],topics=["business_model"],primary_section="business_model",falsification_conditions=["若收入来源、利润池或资本强度的一手披露与当前资料不符，需重建商业模式判断。"]))
    moat_parts=[
        f"竞争优势：{'、'.join(data.get('competitive_advantages',[]))}" if data.get("competitive_advantages") else "",
        f"护城河类型：{'、'.join(data.get('moat_types',[]))}" if data.get("moat_types") else "",
        f"持续性：{data.get('moat_durability')}" if data.get("moat_durability") else "",
        f"侵蚀风险：{'、'.join(data.get('moat_erosion_risks',[]))}" if data.get("moat_erosion_risks") else "",
    ]
    moat="；".join(item for item in moat_parts if item)
    if moat:
        claims.append(ResearchClaim(topic="护城河",statement=moat,claim_type="reasoning",supporting_evidence_ids=evidence,confidence=Confidence.MEDIUM,source_skill_ids=[result.skill_id],topics=["moat"],primary_section="moat",falsification_conditions=["若竞争优势缺少可持续的经营或财务证据，护城河结论应降级。"]))
    circle=data.get("circle_of_competence",{})
    if isinstance(circle,dict) and (circle.get("reasoning") or circle.get("unknowns")):
        statement=f"能力圈状态：{circle.get('status','insufficient_data')}；{circle.get('reasoning','')}；未知项：{'、'.join(circle.get('unknowns',[]))}"
        claims.append(ResearchClaim(topic="能力圈",statement=statement,claim_type="reasoning",supporting_evidence_ids=evidence,confidence=Confidence.LOW if circle.get("status")=="insufficient_data" else Confidence.MEDIUM,source_skill_ids=[result.skill_id],topics=["circle_of_competence"],primary_section="circle_of_competence",falsification_conditions=["补齐未知经营变量后重新判断是否处于能力圈内。"]))
    return claims


def run_planner_agent(state: WorkflowState, objective: str | None = None, horizon: str | None = None, initial_view: str | None = None, key_question: str | None = None, client: OpenAIClient | None = None) -> tuple[ResearchExecutionPlan, AgentOutput]:
    fallback = build_research_plan(state)
    focus=" ".join(filter(None,[objective,key_question]))
    if focus:
        industry_skills=[item for item in fallback.required_skills if item.endswith("_analysis")]
        focused=[]
        if any(word in focus for word in ("现金流","分红","财务","负债")): focused.append("financial_quality_dividend")
        if any(word in focus for word in ("估值","安全边际","价格")): focused.extend(["financial_quality_dividend","valuation_margin"])
        if any(word in focus for word in ("管理层","卖方","观点","分歧")): focused.append("management_view_comparison")
        fallback.required_skills=list(dict.fromkeys([*industry_skills,"business_model_moat",*focused])) or fallback.required_skills
        fallback.skipped_skills=sorted(ALLOWED_SKILLS-set(fallback.required_skills))
        fallback.parallel_groups=[fallback.required_skills]
        fallback.minimum_evidence={item:1 for item in fallback.required_skills}
        fallback.priority_questions=[key_question] if key_question else [f"研究目标：{objective}",*fallback.priority_questions]
    client = client or OpenAIClient()
    if client.available:
        try:
            result = client.generate_json(system_prompt=f"""You are the Research Planner Agent. Decide WHAT to research, never execute tools or write conclusions. Return JSON with company_type, research_questions, required_skills, skipped_skills, dependencies, parallel_groups, minimum_evidence, missing_materials, priorities, replan_triggers, rationale. required_skills may only use the supplied allowed_skills. Different industries and objectives must produce materially different execution plans. The plan must cover every supplied value-investing principle that is material to this company and must not equate low valuation or high dividend with safety.

{doctrine_text()}""", user_payload={"company":state.company_profile.model_dump(mode="json"),"objective":objective,"horizon":horizon,"initial_view":initial_view,"key_question":key_question,"materials":[{"type":m.source_type.value,"title":m.title,"has_content":bool(m.content)} for m in state.raw_materials],"allowed_skills":sorted(ALLOWED_SKILLS)}, temperature=0)
            if not isinstance(result,dict): raise TypeError("planner response must be an object")
            fallback_industry=next((item for item in fallback.required_skills if item in INDUSTRY_SKILLS),"general_business_analysis")
            required=[item for item in result.get("required_skills",[]) if item in ALLOWED_SKILLS and (item not in INDUSTRY_SKILLS or item==fallback_industry)]
            if fallback_industry not in required: required.append(fallback_industry)
            if "business_model_moat" not in required: required.append("business_model_moat")
            if required:
                fallback.required_skills=required
                fallback.skipped_skills=[item for item in ALLOWED_SKILLS if item not in required]
                fallback.priority_questions=[str(item) for item in result.get("research_questions",[])[:12]] or fallback.priority_questions
                raw_dependencies=result.get("dependencies",{})
                if isinstance(raw_dependencies,dict): fallback.dependencies={str(k):[x for x in v if x in required] for k,v in raw_dependencies.items() if k in required and isinstance(v,list)}
                raw_groups=result.get("parallel_groups",[])
                if isinstance(raw_groups,list): fallback.parallel_groups=[[x for x in group if x in required] for group in raw_groups if isinstance(group,list)] or [required]
                raw_minimum=result.get("minimum_evidence",{})
                if isinstance(raw_minimum,dict): fallback.minimum_evidence={str(k):int(v) for k,v in raw_minimum.items() if k in required and isinstance(v,(int,float))}
                fallback.missing_materials=[str(item) for item in result.get("missing_materials",[])]
                fallback.replan_triggers=[str(item) for item in result.get("replan_triggers",[])] or fallback.replan_triggers
                fallback.rationale=str(result.get("rationale") or fallback.rationale)
                fallback.planner_model=client.settings.openai_model
        except (LLMError, TimeoutError, OSError, TypeError, ValueError):
            pass
    finding=AgentFinding(title="研究问题树",detail="；".join(fallback.priority_questions),classification="research_plan",confidence=Confidence.MEDIUM)
    output=AgentOutput(agent_name="Research Planner Agent",status=AgentStatus.PASS if fallback.required_skills else AgentStatus.PARTIAL,summary=f"计划执行 {len(fallback.required_skills)} 个 Skills，跳过 {len(fallback.skipped_skills)} 个。",findings=[finding],missing_materials=fallback.missing_materials,confidence=Confidence.MEDIUM)
    return fallback,output


def to_skill_result(skill_id: str, output: AgentOutput, fingerprint_payload: object, duration_ms: int = 0, attempt: int = 1, failure_code: str | None = None, execution_mode: str = "deterministic", model_name: str | None = None) -> SkillResult:
    fingerprint=hashlib.sha256(json.dumps(fingerprint_payload,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
    return SkillResult(skill_id=skill_id,status=output.status.value,inputs_fingerprint=fingerprint,findings=output.findings,evidence_ids=list(dict.fromkeys([item for finding in output.findings for item in finding.evidence_ids])),missing_inputs=output.missing_materials,warnings=output.warnings,duration_ms=duration_ms,failure_code=failure_code,attempt=attempt,execution_mode=execution_mode,model_name=model_name,structured_output=output.structured_output)


def run_analyst_agent(state: WorkflowState, client: OpenAIClient | None = None) -> tuple[list[ResearchClaim],AgentOutput]:
    skill_results=[item for item in state.skill_outputs.values() if isinstance(item,SkillResult) and item.skill_id in ALLOWED_SKILLS]
    claims=_fallback_claims(skill_results)
    client=client or OpenAIClient()
    if client.available and skill_results:
        try:
            result=client.generate_json(system_prompt=f"""You are the Research Analyst Agent. Synthesize Skill results into non-duplicative buy-side ResearchClaims. Reconcile conflicts instead of concatenating text. Every claim needs topic, statement, claim_type, supporting_evidence_ids, counter_evidence_ids, assumptions, scenarios, confidence, falsification_conditions, source_skill_ids, topics, primary_section and secondary_sections. primary_section must be one of: {", ".join(sorted(MEMO_SECTIONS))}. Use only supplied evidence IDs and Skill content. Apply the supplied value-investing doctrine as a reasoning constraint; never treat low valuation, high dividend, high ROE, management targets, or sell-side consensus as sufficient conclusions.

{doctrine_text()}""",user_payload={"plan":state.research_plan.model_dump(mode="json") if state.research_plan else None,"doctrine_context":state.skill_outputs.get("doctrine_context").model_dump(mode="json") if state.skill_outputs.get("doctrine_context") else None,"skills":[item.model_dump(mode="json") for item in skill_results]},temperature=0)
            if not isinstance(result,dict): raise TypeError("analyst response must be an object")
            parsed=[]; valid_evidence={item.evidence_id for item in state.evidence_items}; valid_skills={item.skill_id for item in skill_results}
            for raw in result.get("claims",[])[:30]:
                if not isinstance(raw,dict) or not str(raw.get("statement","")).strip(): continue
                parsed.append(ResearchClaim(topic=str(raw.get("topic") or "研究判断"),statement=str(raw["statement"]),claim_type=raw.get("claim_type") if raw.get("claim_type") in {"fact","opinion","assumption","reasoning","risk"} else "reasoning",supporting_evidence_ids=[x for x in raw.get("supporting_evidence_ids",[]) if x in valid_evidence],counter_evidence_ids=[x for x in raw.get("counter_evidence_ids",[]) if x in valid_evidence],assumptions=[str(x) for x in raw.get("assumptions",[])],scenarios=[str(x) for x in raw.get("scenarios",[])],confidence=Confidence(str(raw.get("confidence"))) if str(raw.get("confidence")) in {"high","medium","low"} else Confidence.LOW,falsification_conditions=[str(x) for x in raw.get("falsification_conditions",[])],source_skill_ids=[x for x in raw.get("source_skill_ids",[]) if x in valid_skills],topics=[str(x) for x in raw.get("topics",[])],primary_section=str(raw.get("primary_section")) if raw.get("primary_section") in MEMO_SECTIONS else None,secondary_sections=[str(x) for x in raw.get("secondary_sections",[]) if x in MEMO_SECTIONS]))
            if parsed: claims=parsed
        except (LLMError,TimeoutError,OSError,TypeError,ValueError): pass
    structured=_structured_business_claims(skill_results)
    structured_sections={item.primary_section for item in structured}
    claims=[item for item in claims if not (item.source_skill_ids==["business_model_moat"] and _route_claim(item).primary_section in structured_sections)]
    claims=[_route_claim(item) for item in [*claims,*structured]]
    findings=[AgentFinding(title=c.topic,detail=c.statement,classification=c.claim_type,evidence_ids=c.supporting_evidence_ids,confidence=c.confidence) for c in claims]
    return claims,AgentOutput(agent_name="Research Analyst Agent",status=AgentStatus.PASS if claims else AgentStatus.PARTIAL,summary=f"综合形成 {len(claims)} 条可审查 Research Claims。",findings=findings,confidence=Confidence.MEDIUM if claims else Confidence.LOW)


def _fallback_claims(results: list[SkillResult]) -> list[ResearchClaim]:
    claims=[]
    for result in results:
        for finding in result.findings:
            if not finding.detail: continue
            claims.append(_route_claim(ResearchClaim(topic=finding.title,statement=finding.detail,claim_type="risk" if finding.classification in {"risk","missing_data"} else "reasoning",supporting_evidence_ids=finding.evidence_ids,confidence=finding.confidence,source_skill_ids=[result.skill_id],falsification_conditions=["若后续一手证据与当前证据相反，需重新评估。"])))
    return claims[:30]


def run_judge_agent(state: WorkflowState, hard_gate_status: str, client: OpenAIClient | None = None) -> tuple[list[JudgeDecision],AgentOutput]:
    valid={item.evidence_id:item for item in state.evidence_items}; decisions=[]
    for claim in state.research_claims:
        unsupported=not claim.supporting_evidence_ids or any(eid not in valid for eid in claim.supporting_evidence_ids)
        unverified=any(valid[eid].verification_status.value in {"unsupported","to_be_verified"} for eid in claim.supporting_evidence_ids if eid in valid)
        support_categories={valid[eid].category.value for eid in claim.supporting_evidence_ids if eid in valid}
        opinion_only=bool(support_categories) and support_categories.issubset({"management_opinion","sell_side_opinion","news_or_market_opinion","user_opinion"})
        forbidden=state.company_profile.user_mode.value=="to_c" and any(word in claim.statement for word in ("买入","卖出","增持","减持","目标价","必涨","稳赚"))
        doctrine_mismatch=any(pattern in claim.statement.replace(" ", "") for pattern in ("低PE就是安全边际","低PB就是安全边际","低估值就是安全边际","高股息就是安全","高分红就是安全","高ROE就是优秀公司"))
        if forbidden:
            decision="rejected"; approved=None; reason="To C 结论包含评级、目标价或确定性交易表达。"
        elif doctrine_mismatch:
            decision="rejected"; approved=None; reason="结论违反通用价值投资准则，把单一估值、股息或ROE指标直接等同于安全或质量。"
        elif hard_gate_status=="fail" or unsupported or unverified:
            decision="needs_evidence"; approved=None; reason="缺少已核验支持证据或硬门禁未通过。"
        elif claim.claim_type in {"opinion","assumption"} or opinion_only:
            decision="downgraded"; approved=f"当前资料中的观点或待验证假设：{claim.statement}"; reason="不得将观点或假设写成已发生事实。"
        else:
            decision="approved"; approved=claim.statement; reason="有已核验证据支持且未触发硬门禁。"
        decisions.append(JudgeDecision(claim_id=claim.claim_id,decision=decision,reason=reason,approved_statement=approved,missing_evidence=[] if approved else ["可核验的一手证据"]))
    client=client or OpenAIClient()
    if client.available and decisions:
        try:
            result=client.generate_json(system_prompt=f"""You are the Red Team & Judge Agent. Review each ResearchClaim for unsupported conclusions, management targets treated as facts, sell-side forecasts treated as outcomes, selective citation, value traps, doctrine violations, and compliance. Return decisions with claim_id, decision, reason, approved_statement, missing_evidence. You may only keep or make the deterministic decision stricter; never approve a deterministically rejected/needs_evidence claim.

{doctrine_text()}""",user_payload={"claims":[item.model_dump(mode="json") for item in state.research_claims],"deterministic_decisions":[item.model_dump(mode="json") for item in decisions],"doctrine_context":state.skill_outputs.get("doctrine_context").model_dump(mode="json") if state.skill_outputs.get("doctrine_context") else None,"evidence":[{"id":item.evidence_id,"category":item.category.value,"statement":item.statement,"status":item.verification_status.value} for item in state.evidence_items]},temperature=0)
            if not isinstance(result,dict): raise TypeError("judge response must be an object")
            rank={"approved":0,"downgraded":1,"needs_recalculation":2,"needs_evidence":3,"rejected":4}; by_id={item.claim_id:item for item in decisions}
            for raw in result.get("decisions",[]):
                if not isinstance(raw,dict) or raw.get("claim_id") not in by_id or raw.get("decision") not in rank: continue
                current=by_id[raw["claim_id"]]
                if rank[raw["decision"]] < rank[current.decision]: continue
                current.decision=raw["decision"]; current.reason=str(raw.get("reason") or current.reason); current.missing_evidence=[str(x) for x in raw.get("missing_evidence",current.missing_evidence)]
                current.approved_statement=str(raw.get("approved_statement")) if current.decision in {"approved","downgraded"} and raw.get("approved_statement") else None
        except (LLMError,TimeoutError,OSError,TypeError,ValueError): pass
    findings=[AgentFinding(title=d.decision,detail=f"{d.claim_id}：{d.reason}",classification="quality_gate",confidence=Confidence.HIGH) for d in decisions]
    passed=any(d.decision in {"approved","downgraded"} for d in decisions) and hard_gate_status=="pass"
    return decisions,AgentOutput(agent_name="Red Team & Judge Agent",status=AgentStatus.PASS if passed else AgentStatus.FAIL,summary=f"审查 {len(decisions)} 条 Claim，允许 {sum(d.decision in {'approved','downgraded'} for d in decisions)} 条进入 Memo。",findings=findings,confidence=Confidence.HIGH)
