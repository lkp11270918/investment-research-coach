from __future__ import annotations

import hashlib
import json

from .llm_client import LLMError, OpenAIClient
from .models import EvidenceGraph, ResearchMap, ResearchQuestion, ResearchQuestionStatus


BASE_QUESTIONS = [
    ("business", "公司靠什么赚钱，主要收入和利润来源是什么？", ("收入", "利润来源", "商业模式"), "收入结构与利润来源"),
    ("cash_flow", "净利润能否转化为稳定经营现金流和自由现金流？", ("经营现金流", "自由现金流", "net_profit"), "现金流量表与资本开支"),
    ("balance_sheet", "资产负债表能否承受行业下行和资本开支？", ("资产负债率", "有息负债", "interest_bearing_debt"), "债务结构与到期分布"),
    ("allocation", "管理层如何配置资本，分红是否由自由现金流覆盖？", ("分红", "资本开支", "dividend"), "分红历史与资本配置记录"),
    ("moat", "竞争优势是否可验证并具有持续性？", ("竞争", "护城河", "市场份额"), "竞争格局与市场份额"),
    ("valuation", "当前估值依赖哪些假设，是否存在真实安全边际？", ("估值", "安全边际", "假设"), "估值假设与情景分析"),
    ("falsification", "什么证据会推翻当前研究判断？", ("风险", "反证", "推翻"), "反方资料与悲观情景"),
]

INDUSTRY_QUESTIONS = {
    "银行": [("industry", "净息差、资产质量和资本充足率如何变化？", ("净息差", "不良率", "资本充足率"), "净息差、资产质量与资本充足率")],
    "制造": [("industry", "产能利用率、原材料和资本开支如何影响回报？", ("产能", "原材料", "资本开支"), "产能、成本与资本开支数据")],
    "消费": [("industry", "品牌、渠道、复购和库存是否支持持续增长？", ("渠道", "复购", "库存"), "渠道、复购与库存数据")],
    "公用事业": [("industry", "监管价格、负债、资本开支和分红能否平衡？", ("电价", "监管", "负债", "分红"), "监管定价与资本开支计划")],
    "保险": [("industry", "新业务价值、投资收益、偿付能力和准备金假设是否稳健？", ("新业务价值", "投资收益", "偿付能力", "准备金"), "新业务价值、偿付能力与准备金数据")],
    "医药": [("industry", "核心产品生命周期、研发管线和医保政策如何影响回报？", ("研发", "管线", "医保", "专利"), "研发管线、专利与医保政策")],
    "软件": [("industry", "续费、客户留存、获客成本和研发投入能否形成规模效应？", ("续费", "留存", "获客", "研发"), "续费、留存与获客数据")],
    "房地产": [("industry", "销售回款、土储质量、融资成本和交付义务是否可承受？", ("回款", "土储", "融资", "交付"), "回款、土储、债务和交付数据")],
}


def generate_research_map(project_id: str, industry: str, graph: EvidenceGraph, *, company_name: str = "", research_objective: str | None = None, initial_view: str | None = None, key_question: str | None = None, investment_horizon: str | None = None, previous: ResearchMap | None = None, client: OpenAIClient | None = None) -> ResearchMap:
    specs = list(BASE_QUESTIONS)
    for keyword, questions in INDUSTRY_QUESTIONS.items():
        if keyword in industry:
            specs.extend(questions)
    if key_question:
        specs.insert(0, ("user_key_question", key_question, _keywords(key_question), "能够回答用户核心问题的公司事实与反证"))
    if initial_view:
        specs.append(("initial_view_test", f"哪些证据支持或推翻初始判断：{initial_view}？", _keywords(initial_view), "与初始判断直接相关的支持证据和反证"))
    company_specs, core_variables = _company_specific_specs(graph)
    specs.extend(company_specs)
    planner_model = "deterministic_company_framework"
    generated = _model_plan(client or OpenAIClient(), company_name, industry, research_objective, investment_horizon, initial_view, key_question, graph, previous)
    if generated:
        planner_model = generated["model"]
        core_variables = list(dict.fromkeys(generated["core_variables"] + core_variables))[:8]
        for item in generated["questions"]:
            specs.append((item["category"], item["question"], tuple(item["keywords"]), item["missing_material"]))
    evidence_nodes = [node for node in graph.nodes if node.evidence_id]
    questions: list[ResearchQuestion] = []
    for index, (category, question, keywords, missing) in enumerate(specs, start=1):
        topic_matches = [node for node in evidence_nodes if any(keyword.lower() in (node.label + str(node.metadata)).lower() for keyword in keywords)]
        matched = [node for node in topic_matches if node.verification_status.value in {"verified", "partially_supported"}]
        matched_ids = [node.evidence_id for node in matched if node.evidence_id]
        topic_nodes = {node.node_id for node in topic_matches}
        conflict = any(edge.relation.value == "contradicts" and edge.from_node_id in topic_nodes and edge.to_node_id in topic_nodes for edge in graph.edges)
        if conflict:
            status = ResearchQuestionStatus.CONFLICTED
        elif len(matched_ids) >= 2:
            status = ResearchQuestionStatus.ANSWERED
        elif matched_ids:
            status = ResearchQuestionStatus.PARTIAL
        else:
            status = ResearchQuestionStatus.UNANSWERED
        context = "、".join(filter(None, [company_name, industry, research_objective]))
        generated_from = "company_evidence" if category.startswith("company_") else "model" if category.startswith("model_") else "framework"
        questions.append(ResearchQuestion(question_id=f"RQ-{index:02d}", category=category, question=question, priority=1 if category in {"user_key_question", "cash_flow", "falsification", "industry"} or generated_from != "framework" else 2, status=status, evidence_ids=matched_ids, missing_materials=[] if status == ResearchQuestionStatus.ANSWERED else [missing], rationale=f"根据{context or '当前研究任务'}及现有证据生成", required_evidence_types=[missing], generated_from=generated_from))
    questions = _deduplicate_questions(questions)
    for index, question in enumerate(questions, start=1):
        question.question_id = f"RQ-{index:02d}"
    answered_weight = sum(1 if q.status == ResearchQuestionStatus.ANSWERED else 0.5 if q.status == ResearchQuestionStatus.PARTIAL else 0 for q in questions)
    next_questions = [q.question for q in sorted(questions, key=lambda item: (item.status == ResearchQuestionStatus.ANSWERED, item.priority))[:3] if q.status != ResearchQuestionStatus.ANSWERED]
    material_requests = list(dict.fromkeys(item for question in questions if question.status != ResearchQuestionStatus.ANSWERED for item in question.missing_materials))
    fingerprint = hashlib.sha256(json.dumps({"industry": industry, "objective": research_objective, "horizon": investment_horizon, "view": initial_view, "key": key_question, "nodes": [(node.node_id, node.label, node.verification_status.value) for node in graph.nodes], "edges": [(edge.from_node_id, edge.to_node_id, edge.relation.value) for edge in graph.edges]}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    version = (previous.version + 1) if previous and previous.context_fingerprint != fingerprint else previous.version if previous else 1
    previous_questions = {item.question for item in previous.questions} if previous else set()
    new_questions = [item.question for item in questions if item.question not in previous_questions]
    summary = f"新增{len(new_questions)}个问题；当前{len(material_requests)}类资料缺口" if previous else f"建立{len(questions)}个公司研究问题"
    return ResearchMap(project_id=project_id, industry=industry, version=version, questions=questions, next_questions=next_questions, core_variables=core_variables[:8], material_requests=material_requests, planner_model=planner_model, context_fingerprint=fingerprint, change_summary=summary, completion_rate=round(answered_weight / max(len(questions), 1) * 100, 1))


def _company_specific_specs(graph: EvidenceGraph) -> tuple[list[tuple], list[str]]:
    specs: list[tuple] = []
    variables: list[str] = []
    candidates = [node for node in graph.nodes if node.node_type in {"risk", "financial_fact", "assumption", "management_opinion"}]
    for node in candidates[:8]:
        label = node.label.strip()
        if not label:
            continue
        variables.append(str(node.metadata.get("metric_name") or label[:30]))
        if node.node_type == "risk" or node.verification_status.value in {"unsupported", "to_be_verified"}:
            specs.append((f"company_{node.node_type}", f"围绕“{label[:80]}”，需要核实哪些事实，什么结果会推翻当前判断？", _keywords(label), f"验证“{label[:50]}”的公司原始资料与反方证据"))
    return specs[:5], list(dict.fromkeys(variables))


def _model_plan(client: OpenAIClient, company_name: str, industry: str, objective: str | None, horizon: str | None, view: str | None, key_question: str | None, graph: EvidenceGraph, previous: ResearchMap | None) -> dict | None:
    if not client.available:
        return None
    evidence = [{"type": node.node_type, "label": node.label, "status": node.verification_status.value} for node in graph.nodes[:60]]
    try:
        result = client.generate_json(model=client.settings.openai_model, system_prompt="你是买方研究规划负责人。根据具体公司、用户目标和现有证据生成公司专属问题，不得只复述行业模板。每个问题必须说明关键词和所需原始资料。返回JSON：{\"core_variables\":[\"...\"],\"questions\":[{\"category\":\"model_specific\",\"question\":\"...\",\"keywords\":[\"...\"],\"missing_material\":\"...\"}]}。最多6个问题。", user_payload={"company": company_name, "industry": industry, "objective": objective, "horizon": horizon, "initial_view": view, "key_question": key_question, "evidence": evidence, "previous_questions": [item.question for item in previous.questions] if previous else []}, temperature=0)
    except LLMError:
        return None
    questions = []
    for item in result.get("questions", [])[:6]:
        if not isinstance(item, dict) or not str(item.get("question", "")).strip():
            continue
        questions.append({"category": "model_" + str(item.get("category") or "specific"), "question": str(item["question"]).strip(), "keywords": [str(value) for value in item.get("keywords", [])[:8]] or list(_keywords(str(item["question"]))), "missing_material": str(item.get("missing_material") or "能够验证该问题的公司原始资料")})
    return {"model": client.settings.openai_model, "core_variables": [str(item) for item in result.get("core_variables", [])[:8]], "questions": questions} if questions else None


def _deduplicate_questions(questions: list[ResearchQuestion]) -> list[ResearchQuestion]:
    result: list[ResearchQuestion] = []
    seen: set[str] = set()
    for question in questions:
        key = "".join(_keywords(question.question)[:3])
        if question.question in seen or key in seen:
            continue
        seen.update({question.question, key})
        result.append(question)
    return result


def _keywords(text: str) -> tuple[str, ...]:
    import re
    stop = {"什么", "哪些", "是否", "如何", "为什么", "当前", "判断", "证据", "公司"}
    chunks = re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z_]{3,}", text)
    keywords = [item for item in chunks if item not in stop]
    return tuple(keywords[:8]) or (text[:8],)
