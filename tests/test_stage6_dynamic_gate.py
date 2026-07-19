from __future__ import annotations

import unittest

from backend.agents import run_compliance_gate
from backend.evidence_graph import build_evidence_graph
from backend.models import AgentFinding, AgentOutput, AgentStatus, CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, SourceDocument, SourceRef, SourceType, VerificationStatus, WorkflowState


class DynamicGateTest(unittest.TestCase):
    def test_conflict_and_missing_red_team_block_gate(self) -> None:
        source_a = SourceDocument(title="A", source_type=SourceType.FINANCIAL_TABLE)
        source_b = SourceDocument(title="B", source_type=SourceType.FINANCIAL_TABLE)
        state = WorkflowState(company_profile=CompanyProfile(company_name="测试", industry="制造业"), source_documents=[source_a, source_b], evidence_items=[
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="营收100", source_refs=[SourceRef(source_id=source_a.source_id)], metric_name="revenue", metric_value=100, unit="亿元", period="2024", verification_status=VerificationStatus.VERIFIED),
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="营收90", source_refs=[SourceRef(source_id=source_b.source_id)], metric_name="revenue", metric_value=90, unit="亿元", period="2024", verification_status=VerificationStatus.VERIFIED),
        ])
        state.evidence_graph = build_evidence_graph(state)
        gate = run_compliance_gate(state, "pre_memo_gate")
        self.assertEqual(gate.status, "fail")
        self.assertTrue(any("数据冲突" in issue for issue in gate.evidence_issues))
        self.assertTrue(any("价值陷阱" in issue for issue in gate.evidence_issues))

    def test_fact_evidence_and_red_team_allow_gate(self) -> None:
        source = SourceDocument(title="年报", source_type=SourceType.ANNUAL_REPORT_SUMMARY)
        evidence = EvidenceItem(category=EvidenceCategory.FACT, statement="公司披露产能", source_refs=[SourceRef(source_id=source.source_id)], verification_status=VerificationStatus.VERIFIED)
        state = WorkflowState(company_profile=CompanyProfile(company_name="测试", industry="制造业"), source_documents=[source], evidence_items=[evidence])
        state.agent_outputs["value_trap_contradiction"] = AgentOutput(agent_name="Value Trap", status=AgentStatus.PASS, summary="已检查", findings=[AgentFinding(title="需求下行", detail="需要验证", classification="risk", evidence_ids=[evidence.evidence_id], confidence=Confidence.LOW)])
        state.evidence_graph = build_evidence_graph(state)
        gate = run_compliance_gate(state, "pre_memo_gate")
        self.assertEqual(gate.status, "pass")


if __name__ == "__main__": unittest.main()
