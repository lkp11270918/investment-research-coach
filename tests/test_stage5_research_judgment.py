import unittest

from backend.models import AgentFinding, AgentOutput, AgentStatus, CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, SourceDocument, SourceRef, SourceType, WorkflowState
from backend.research_judgment import build_research_judgment


class ResearchJudgmentTest(unittest.TestCase):
    def test_multiple_sell_side_sources_produce_structured_divergence_and_red_team(self) -> None:
        left = SourceDocument(title="券商A", source_type=SourceType.SELL_SIDE_SUMMARY)
        right = SourceDocument(title="券商B", source_type=SourceType.SELL_SIDE_SUMMARY)
        annual = SourceDocument(title="年报", source_type=SourceType.ANNUAL_REPORT_SUMMARY)
        items = [
            EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION, statement="A预计增长20%", source_refs=[SourceRef(source_id=left.source_id)]),
            EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION, statement="B预计增长5%", source_refs=[SourceRef(source_id=right.source_id)]),
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="实际增长8%", source_refs=[SourceRef(source_id=annual.source_id)]),
        ]
        state = WorkflowState(company_profile=CompanyProfile(company_name="甲", industry="消费"), source_documents=[left, right, annual], evidence_items=items)
        state.agent_outputs["management_view_comparison"] = AgentOutput(agent_name="View", status=AgentStatus.PASS, summary="比较", findings=[AgentFinding(title="分歧来源", detail="销量假设不同", classification="ai_reasoning", evidence_ids=[items[0].evidence_id, items[1].evidence_id])])
        state.agent_outputs["value_trap_contradiction"] = AgentOutput(agent_name="Red", status=AgentStatus.PARTIAL, summary="反证", findings=[AgentFinding(title="现金流价值陷阱", detail="利润未转化为现金", classification="risk", confidence=Confidence.HIGH)])
        report = build_research_judgment(state)
        self.assertEqual(report.sell_side_source_count, 2)
        self.assertEqual(report.view_points[0].point_type, "divergence")
        self.assertEqual(len(report.view_points[0].source_ids), 2)
        self.assertEqual(report.unresolved_critical_count, 1)


if __name__ == "__main__": unittest.main()
