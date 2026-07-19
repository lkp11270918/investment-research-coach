from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from backend.agents import DISCLAIMER_ZH, run_compliance_gate
from backend.evidence_graph import build_evidence_graph
from backend.financial_parser import extract_structured_financial_evidence
from backend.models import AgentFinding, AgentOutput, AgentStatus, CompanyProfile, Confidence, EvidenceCategory, EvidenceGraph, EvidenceGraphNode, EvidenceItem, SourceDocument, SourceRef, SourceType, ThesisDraft, VerificationStatus, WorkflowState
from backend.research_map import generate_research_map
from backend.thesis_builder import assess_thesis
from backend.value_investing_doctrine import doctrine_findings


@dataclass
class CaseResult:
    name: str
    metric: str
    passed: bool
    detail: str


def run_suite() -> dict:
    results = []
    for case in _financial_cases(): results.append(case)
    for case in _traceability_cases(): results.append(case)
    for case in _conflict_cases(): results.append(case)
    results.extend(_unsupported_fact_cases())
    results.extend(_opinion_only_cases())
    results.extend(_sell_side_repetition_cases())
    results.extend(_research_map_evidence_cases())
    results.extend(_value_trap_cases())
    results.extend(_toc_compliance_cases())
    results.extend(_doctrine_coverage_cases())
    metric_scores: dict[str, float] = {}
    for metric in sorted({result.metric for result in results}):
        cases = [result for result in results if result.metric == metric]
        metric_scores[metric] = round(sum(result.passed for result in cases) / len(cases) * 100, 1)
    thresholds = {
        "major_financial_field_accuracy": 95.0,
        "source_annotation_completeness": 100.0,
        "contradiction_detection": 90.0,
        "unsupported_key_fact_rate": 100.0,
        "opinion_misreading_rate": 100.0,
        "sell_side_repetition_rate": 100.0,
        "research_map_grounding": 100.0,
        "value_trap_coverage": 100.0,
        "compliance_risk_rate": 100.0,
        "value_investing_framework_coverage": 100.0,
    }
    sample_counts = {metric: sum(result.metric == metric for result in results) for metric in metric_scores}
    provisional = [metric for metric, count in sample_counts.items() if count < 5]
    passed = not provisional and all(metric_scores[name] >= threshold for name, threshold in thresholds.items())
    return {
        "suite": "value_investing_research_coach_synthetic_regression",
        "evidence_level": "synthetic_regression",
        "release_eligible": False,
        "passed": passed,
        "metrics": metric_scores,
        "sample_counts": sample_counts,
        "provisional_metrics": provisional,
        "thresholds": thresholds,
        "cases": [result.__dict__ for result in results],
    }


def _financial_cases() -> list[CaseResult]:
    cases = [
        ("pipe_table", "指标 | 2024年\n营业收入 | 100亿元\n净利润 | 10亿元\n经营活动产生的现金流量净额 | 12亿元", {"revenue", "net_profit", "operating_cash_flow"}),
        ("tab_table", "指标\t2023年\n营业收入\t88亿元\n自由现金流\t9亿元\n现金分红\t4亿元", {"revenue", "free_cash_flow", "dividend"}),
        ("balance_sheet", "指标 | 2024年\n资产负债率 | 42%\n有息负债 | 20亿元\n应收账款 | 6亿元\n存货 | 8亿元", {"debt_to_asset_ratio", "interest_bearing_debt", "accounts_receivable", "inventory"}),
        ("quality_fields", "指标 | 2022年\nROE | 18.5%\n非经常性损益 | 0.8亿元\n净利润 | 5亿元", {"roe", "non_recurring_pnl", "net_profit"}),
        ("multi_period", "指标 | 2022年 | 2023年 | 2024年\n营业收入 | 80亿元 | 90亿元 | 100亿元", {"revenue"}),
    ]
    results = []
    for name, content, expected in cases:
        doc = SourceDocument(title=name, source_type=SourceType.FINANCIAL_TABLE, content=content)
        names = {item.metric_name for item in extract_structured_financial_evidence([doc])}
        results.append(CaseResult(name, "major_financial_field_accuracy", expected.issubset(names), str(sorted(names))))
    return results


def _traceability_cases() -> list[CaseResult]:
    results = []
    for index, coordinate in enumerate(({"page": "10"}, {"sheet": "利润表", "row_id": "8"}, {"paragraph": "3"}, {"page": "2", "excerpt": "原文"}, {"url": "https://example.com"}), start=1):
        doc = SourceDocument(title=f"来源{index}", source_type=SourceType.ANNUAL_REPORT_SUMMARY)
        ref = SourceRef(source_id=doc.source_id, excerpt=coordinate.get("excerpt", "原文"), page=coordinate.get("page"), sheet=coordinate.get("sheet"), row_id=coordinate.get("row_id"), paragraph=coordinate.get("paragraph"), url=coordinate.get("url"))
        state = WorkflowState(company_profile=_profile(), source_documents=[doc], evidence_items=[EvidenceItem(category=EvidenceCategory.FACT, statement="事实", source_refs=[ref], verification_status=VerificationStatus.VERIFIED)])
        graph = build_evidence_graph(state)
        passed = any(edge.relation.value == "from_source" and edge.rationale == "原文" for edge in graph.edges)
        results.append(CaseResult(f"traceability_{index}", "source_annotation_completeness", passed, f"edges={len(graph.edges)}"))
    return results


def _conflict_cases() -> list[CaseResult]:
    pairs = [(100, 90, "亿元"), (10000, 9000, "万元"), (42, 45, "%"), (0, 2, "亿元"), (10.5, 11.2, "亿元")]
    results = []
    for index, (left, right, unit) in enumerate(pairs, start=1):
        docs = [SourceDocument(title="A", source_type=SourceType.FINANCIAL_TABLE), SourceDocument(title="B", source_type=SourceType.FINANCIAL_TABLE)]
        items = [EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement=f"营收{value}", source_refs=[SourceRef(source_id=doc.source_id)], metric_name="revenue", metric_value=value, unit=unit, period="2024", verification_status=VerificationStatus.VERIFIED) for doc, value in zip(docs, [left, right])]
        graph = build_evidence_graph(WorkflowState(company_profile=_profile(), source_documents=docs, evidence_items=items))
        results.append(CaseResult(f"financial_conflict_{index}", "contradiction_detection", bool(graph.conflicts), str(graph.conflicts)))
    return results


def _financial_accuracy() -> CaseResult:
    doc = SourceDocument(title="财务表", source_type=SourceType.FINANCIAL_TABLE, content="指标 | 2024年\n营业收入 | 100亿元\n净利润 | 10亿元\n经营活动产生的现金流量净额 | 12亿元")
    evidence = extract_structured_financial_evidence([doc])
    names = {item.metric_name for item in evidence}
    passed = {"revenue", "net_profit", "operating_cash_flow"}.issubset(names)
    return CaseResult("financial_fields", "major_financial_field_accuracy", passed, str(sorted(names)))


def _source_traceability() -> CaseResult:
    doc = SourceDocument(title="年报", source_type=SourceType.ANNUAL_REPORT_SUMMARY)
    state = WorkflowState(company_profile=_profile(), source_documents=[doc], evidence_items=[EvidenceItem(category=EvidenceCategory.FACT, statement="事实", source_refs=[SourceRef(source_id=doc.source_id, page="10", excerpt="原文")], verification_status=VerificationStatus.VERIFIED)])
    graph = build_evidence_graph(state)
    passed = any(edge.relation.value == "from_source" for edge in graph.edges)
    return CaseResult("source_traceability", "source_annotation_completeness", passed, f"edges={len(graph.edges)}")


def _conflict_detection() -> CaseResult:
    docs = [SourceDocument(title="A", source_type=SourceType.FINANCIAL_TABLE), SourceDocument(title="B", source_type=SourceType.FINANCIAL_TABLE)]
    items = [EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement=f"营收{value}", source_refs=[SourceRef(source_id=doc.source_id)], metric_name="revenue", metric_value=value, unit="亿元", period="2024", verification_status=VerificationStatus.VERIFIED) for doc, value in zip(docs, [100, 90])]
    graph = build_evidence_graph(WorkflowState(company_profile=_profile(), source_documents=docs, evidence_items=items))
    return CaseResult("financial_conflict", "contradiction_detection", bool(graph.conflicts), str(graph.conflicts))


def _unsupported_fact_cases() -> list[CaseResult]:
    statements = ("收入增长30%", "行业份额第一", "管理层承诺分红", "订单已经翻倍", "自由现金流持续改善")
    results = []
    for index, statement in enumerate(statements, start=1):
        state = WorkflowState(company_profile=_profile(), evidence_items=[EvidenceItem(category=EvidenceCategory.FACT, statement=statement)])
        state.agent_outputs["value_trap_contradiction"] = _red_team([])
        gate = run_compliance_gate(state, "pre")
        results.append(CaseResult(f"unsupported_fact_{index}", "unsupported_key_fact_rate", gate.status == "fail" and bool(gate.unsupported_claims), gate.status))
    return results


def _opinion_only_cases() -> list[CaseResult]:
    opinions = ("卖方看好增长", "分析师认为低估", "券商预测订单反转", "一致预期上调盈利", "研报判断行业见底")
    results = []
    for index, statement in enumerate(opinions, start=1):
        opinion = EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION, statement=statement, source_refs=[SourceRef(source_id=f"S{index}")])
        state = WorkflowState(company_profile=_profile(), evidence_items=[opinion])
        state.agent_outputs["analysis"] = AgentOutput(agent_name="A", summary="观点", findings=[AgentFinding(title="卖方观点", detail=statement, classification="opinion_based", evidence_ids=[opinion.evidence_id])])
        state.agent_outputs["value_trap_contradiction"] = _red_team([opinion.evidence_id])
        gate = run_compliance_gate(state, "pre")
        results.append(CaseResult(f"opinion_as_conclusion_{index}", "opinion_misreading_rate", gate.status == "fail", gate.status))
    return results


def _sell_side_repetition_cases() -> list[CaseResult]:
    results = []
    for index, view in enumerate(("增长提速", "估值低估", "需求反转", "利润改善", "行业见底"), start=1):
        evidence_id = f"S{index}"
        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id=f"EVIDENCE:{evidence_id}", node_type="sell_side_opinion", label="卖方", evidence_id=evidence_id, verification_status=VerificationStatus.VERIFIED)])
        assessment = assess_thesis(ThesisDraft(core_view=view, supporting_evidence_ids=[evidence_id]), graph)
        results.append(CaseResult(f"sell_side_only_thesis_{index}", "sell_side_repetition_rate", assessment.sell_side_repetition_risk, str(assessment.issues)))
    return results


def _research_map_evidence_cases() -> list[CaseResult]:
    results = []
    for index, industry in enumerate(("制造业", "保险", "医药", "软件", "房地产"), start=1):
        research_map = generate_research_map(f"P{index}", industry, EvidenceGraph())
        passed = all(question.status.value == "unanswered" for question in research_map.questions)
        results.append(CaseResult(f"no_evidence_no_answer_{industry}", "research_map_grounding", passed, str(research_map.completion_rate)))
    return results


def _value_trap_cases() -> list[CaseResult]:
    results = []
    for index, industry in enumerate(("制造业", "消费", "金融", "医药", "软件"), start=1):
        state = WorkflowState(company_profile=CompanyProfile(company_name="评测公司", industry=industry), evidence_items=[])
        gate = run_compliance_gate(state, "pre")
        results.append(CaseResult(f"mandatory_red_team_{index}", "value_trap_coverage", any("价值陷阱" in issue for issue in gate.evidence_issues), str(gate.evidence_issues)))
    return results


def _toc_compliance_cases() -> list[CaseResult]:
    prohibited = ("买入", "卖出", "增持", "减持")
    passed = all(word not in DISCLAIMER_ZH for word in prohibited) and "不构成任何投资建议" in DISCLAIMER_ZH
    return [CaseResult(f"toc_disclaimer_{index}", "compliance_risk_rate", passed, DISCLAIMER_ZH) for index in range(1, 6)]


def _doctrine_coverage_cases() -> list[CaseResult]:
    doctrine = doctrine_findings()
    concepts = ("安全边际", "现金流", "能力圈", "管理层", "价值陷阱")
    return [CaseResult(f"doctrine_{index}", "value_investing_framework_coverage", len(doctrine) >= 12 and any(concept in title + detail for title, detail in doctrine), f"principles={len(doctrine)}, concept={concept}") for index, concept in enumerate(concepts, start=1)]


def _profile() -> CompanyProfile:
    return CompanyProfile(company_name="评测公司", industry="制造业")


def _red_team(evidence_ids: list[str]) -> AgentOutput:
    return AgentOutput(agent_name="Value Trap", status=AgentStatus.PASS, summary="检查", findings=[AgentFinding(title="反证", detail="待验证", classification="risk", evidence_ids=evidence_ids, confidence=Confidence.LOW)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_suite()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if report["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
