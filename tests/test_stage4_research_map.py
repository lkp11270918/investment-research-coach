from __future__ import annotations

import unittest

from backend.models import Confidence, EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode, EvidenceRelation, ResearchQuestionStatus, VerificationStatus
from backend.research_map import generate_research_map


class ResearchMapTest(unittest.TestCase):
    def test_user_intake_changes_plan_and_unverified_evidence_does_not_answer(self) -> None:
        from backend.models import EvidenceGraph, EvidenceGraphNode, VerificationStatus

        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:X", node_type="fact", label="海外业务增长", evidence_id="X", verification_status=VerificationStatus.TO_BE_VERIFIED)])
        plan = generate_research_map("P", "医药", graph, company_name="测试药企", research_objective="验证研发回报", initial_view="海外业务增长", key_question="研发管线能否兑现")
        questions = [item.question for item in plan.questions]
        self.assertEqual(questions[0], "研发管线能否兑现")
        self.assertTrue(any("核心产品生命周期" in item for item in questions))
        self.assertTrue(any("初始判断" in item for item in questions))
        initial = next(item for item in plan.questions if item.category == "initial_view_test")
        self.assertEqual(initial.status.value, "unanswered")
    def test_industry_questions_and_evidence_status(self) -> None:
        nodes = [
            EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="financial_fact", label="经营现金流连续三年稳定", evidence_id="E1", confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED),
            EvidenceGraphNode(node_id="EVIDENCE:E2", node_type="financial_fact", label="自由现金流受到资本开支影响", evidence_id="E2", confidence=Confidence.MEDIUM, verification_status=VerificationStatus.PARTIALLY_SUPPORTED),
            EvidenceGraphNode(node_id="EVIDENCE:E3", node_type="financial_fact", label="产能利用率为80%，资本开支增加", evidence_id="E3", confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED),
        ]
        research_map = generate_research_map("PRJ-1", "制造业", EvidenceGraph(nodes=nodes))
        self.assertTrue(any("产能利用率" in question.question for question in research_map.questions))
        cash_flow = next(question for question in research_map.questions if question.category == "cash_flow")
        self.assertEqual(cash_flow.status, ResearchQuestionStatus.ANSWERED)
        self.assertTrue(cash_flow.evidence_ids)
        self.assertLess(len(research_map.next_questions), 4)

    def test_conflict_cannot_be_marked_answered(self) -> None:
        graph = EvidenceGraph(
            nodes=[
                EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="financial_fact", label="经营现金流100", evidence_id="E1"),
                EvidenceGraphNode(node_id="EVIDENCE:E2", node_type="financial_fact", label="经营现金流50", evidence_id="E2"),
            ],
            edges=[EvidenceGraphEdge(from_node_id="EVIDENCE:E1", to_node_id="EVIDENCE:E2", relation=EvidenceRelation.CONTRADICTS)],
        )
        research_map = generate_research_map("PRJ-1", "制造业", graph)
        cash_flow = next(question for question in research_map.questions if question.category == "cash_flow")
        self.assertEqual(cash_flow.status, ResearchQuestionStatus.CONFLICTED)


if __name__ == "__main__":
    unittest.main()
