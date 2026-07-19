import unittest

from backend.memo_coauthor import assess_memo_sections
from backend.thesis_builder import assess_thesis
from backend.models import Confidence, EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode, EvidenceRelation, MemoSection, ThesisDraft, ThesisScenario, ThesisVariable, VerificationStatus


class StrongGateTest(unittest.TestCase):
    def test_opinion_only_conflict_and_open_critical_red_team_block_formal_memo(self) -> None:
        graph = EvidenceGraph(nodes=[
            EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="sell_side_opinion", label="预计增长", evidence_id="E1", verification_status=VerificationStatus.VERIFIED),
            EvidenceGraphNode(node_id="EVIDENCE:E2", node_type="sell_side_opinion", label="预计下降", evidence_id="E2", verification_status=VerificationStatus.VERIFIED),
            EvidenceGraphNode(node_id="REDTEAM:R1", node_type="red_team_challenge", label="现金流无法覆盖", verification_status=VerificationStatus.UNSUPPORTED, metadata={"severity":"critical","status":"open"}),
        ], edges=[EvidenceGraphEdge(from_node_id="EVIDENCE:E1", to_node_id="EVIDENCE:E2", relation=EvidenceRelation.CONTRADICTS)])
        status, issues = assess_memo_sections([MemoSection(section_id="s", title="观点", body="增长", evidence_ids=["E1", "E2"])], graph, True)
        self.assertEqual(status, "needs_evidence")
        self.assertTrue(any("仅引用观点" in issue for issue in issues))
        self.assertTrue(any("未解决冲突" in issue for issue in issues))
        self.assertTrue(any("关键反证" in issue for issue in issues))

    def test_unverified_evidence_cannot_pass_thesis(self) -> None:
        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="fact", label="现金流改善", evidence_id="E1", verification_status=VerificationStatus.TO_BE_VERIFIED)])
        draft = ThesisDraft(core_view="现金流改善", core_variables=[ThesisVariable(name=str(i), rationale="现金流", evidence_ids=["E1"]) for i in range(3)], supporting_evidence_ids=["E1"], counter_evidence_ids=["E1"], assumptions=["需求稳定"], falsification_conditions=["现金流下降"], unknowns=["价格"], scenarios=[ThesisScenario(name=name, assumptions=["A"], outcome="B", trigger_conditions=["C"]) for name in ("bull","base","bear")])
        assessment = assess_thesis(draft, graph)
        self.assertNotEqual(assessment.status.value, "pass")
        self.assertTrue(any("尚未确认" in issue for issue in assessment.issues))


if __name__ == "__main__": unittest.main()
