from __future__ import annotations

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
}


def generate_research_map(project_id: str, industry: str, graph: EvidenceGraph) -> ResearchMap:
    specs = list(BASE_QUESTIONS)
    for keyword, questions in INDUSTRY_QUESTIONS.items():
        if keyword in industry:
            specs.extend(questions)
    evidence_nodes = [node for node in graph.nodes if node.evidence_id]
    questions: list[ResearchQuestion] = []
    for index, (category, question, keywords, missing) in enumerate(specs, start=1):
        matched = [node for node in evidence_nodes if any(keyword.lower() in (node.label + str(node.metadata)).lower() for keyword in keywords)]
        matched_ids = [node.evidence_id for node in matched if node.evidence_id]
        matched_nodes = {f"EVIDENCE:{evidence_id}" for evidence_id in matched_ids}
        conflict = any(edge.relation.value == "contradicts" and (edge.from_node_id in matched_nodes or edge.to_node_id in matched_nodes) for edge in graph.edges)
        if conflict:
            status = ResearchQuestionStatus.CONFLICTED
        elif len(matched_ids) >= 2:
            status = ResearchQuestionStatus.ANSWERED
        elif matched_ids:
            status = ResearchQuestionStatus.PARTIAL
        else:
            status = ResearchQuestionStatus.UNANSWERED
        questions.append(ResearchQuestion(question_id=f"RQ-{index:02d}", category=category, question=question, priority=1 if category in {"cash_flow", "falsification", "industry"} else 2, status=status, evidence_ids=matched_ids, missing_materials=[] if status == ResearchQuestionStatus.ANSWERED else [missing]))
    answered_weight = sum(1 if q.status == ResearchQuestionStatus.ANSWERED else 0.5 if q.status == ResearchQuestionStatus.PARTIAL else 0 for q in questions)
    next_questions = [q.question for q in sorted(questions, key=lambda item: (item.status == ResearchQuestionStatus.ANSWERED, item.priority))[:3] if q.status != ResearchQuestionStatus.ANSWERED]
    return ResearchMap(project_id=project_id, industry=industry, questions=questions, next_questions=next_questions, completion_rate=round(answered_weight / max(len(questions), 1) * 100, 1))
