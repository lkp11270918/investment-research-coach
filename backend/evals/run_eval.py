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
    results = [
        _financial_accuracy(), _source_traceability(), _conflict_detection(),
        _unsupported_fact_gate(), _opinion_only_gate(), _sell_side_repetition(),
        _research_map_evidence_rule(), _value_trap_gate(), _toc_compliance(),
        _doctrine_coverage(),
    ]
    metric_scores: dict[str, float] = {}
    for metric in sorted({result.metric for result in results}):
        cases = [result for result in results if result.metric == metric]
        metric_scores[metric] = round(sum(result.passed for result in cases) / len(cases) * 100, 1)
    thresholds = {metric: 100.0 for metric in metric_scores}
    passed = all(metric_scores[name] >= threshold for name, threshold in thresholds.items())
    return {"suite": "value_investing_research_coach_prd", "passed": passed, "metrics": metric_scores, "thresholds": thresholds, "cases": [result.__dict__ for result in results]}


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


def _unsupported_fact_gate() -> CaseResult:
    state = WorkflowState(company_profile=_profile(), evidence_items=[EvidenceItem(category=EvidenceCategory.FACT, statement="无来源事实")])
    state.agent_outputs["value_trap_contradiction"] = _red_team([])
    gate = run_compliance_gate(state, "pre")
    return CaseResult("unsupported_fact", "unsupported_key_fact_rate", gate.status == "fail" and bool(gate.unsupported_claims), gate.status)


def _opinion_only_gate() -> CaseResult:
    opinion = EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION, statement="卖方看好", source_refs=[SourceRef(source_id="S1")])
    state = WorkflowState(company_profile=_profile(), evidence_items=[opinion])
    state.agent_outputs["analysis"] = AgentOutput(agent_name="A", summary="观点", findings=[AgentFinding(title="看好", detail="增长", classification="opinion_based", evidence_ids=[opinion.evidence_id])])
    state.agent_outputs["value_trap_contradiction"] = _red_team([opinion.evidence_id])
    gate = run_compliance_gate(state, "pre")
    return CaseResult("opinion_as_conclusion", "opinion_misreading_rate", gate.status == "fail", gate.status)


def _sell_side_repetition() -> CaseResult:
    graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:S1", node_type="sell_side_opinion", label="卖方", evidence_id="S1")])
    assessment = assess_thesis(ThesisDraft(core_view="增长", supporting_evidence_ids=["S1"]), graph)
    return CaseResult("sell_side_only_thesis", "sell_side_repetition_rate", assessment.sell_side_repetition_risk, str(assessment.issues))


def _research_map_evidence_rule() -> CaseResult:
    research_map = generate_research_map("P", "制造业", EvidenceGraph())
    passed = all(question.status.value == "unanswered" for question in research_map.questions)
    return CaseResult("no_evidence_no_answer", "research_map_grounding", passed, str(research_map.completion_rate))


def _value_trap_gate() -> CaseResult:
    state = WorkflowState(company_profile=_profile(), evidence_items=[])
    gate = run_compliance_gate(state, "pre")
    return CaseResult("mandatory_red_team", "value_trap_coverage", any("价值陷阱" in issue for issue in gate.evidence_issues), str(gate.evidence_issues))


def _toc_compliance() -> CaseResult:
    prohibited = ("买入", "卖出", "增持", "减持")
    passed = all(word not in DISCLAIMER_ZH for word in prohibited) and "不构成任何投资建议" in DISCLAIMER_ZH
    return CaseResult("toc_disclaimer", "compliance_risk_rate", passed, DISCLAIMER_ZH)


def _doctrine_coverage() -> CaseResult:
    doctrine = doctrine_findings()
    passed = len(doctrine) >= 12 and any("安全边际" in title + detail for title, detail in doctrine) and any("现金流" in title + detail for title, detail in doctrine)
    return CaseResult("doctrine", "value_investing_framework_coverage", passed, f"principles={len(doctrine)}")


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
