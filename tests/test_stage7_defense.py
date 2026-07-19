from __future__ import annotations

import unittest

from backend.defense import answer_defense, start_defense
from backend.models import AgentStatus, Confidence, EvidenceGraph, EvidenceGraphNode, ThesisAssessment, ThesisDraft, ThesisVariable, ThesisVersion


class NoLLM:
    available = False


class DefenseTest(unittest.TestCase):
    def test_four_roles_and_dynamic_followup(self) -> None:
        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="financial_fact", label="经营现金流", evidence_id="E1")])
        draft = ThesisDraft(core_view="现金流质量需要验证", core_variables=[ThesisVariable(name=str(i), rationale="关键") for i in range(3)], supporting_evidence_ids=["E1"], counter_evidence_ids=["E1"], assumptions=["需求稳定"], falsification_conditions=["自由现金流下降"], unknowns=["资本开支"])
        thesis = ThesisVersion(project_id="P1", version=1, draft=draft, assessment=ThesisAssessment(status=AgentStatus.PASS, confidence=Confidence.HIGH))
        session = start_defense("P1", thesis, graph)
        session = answer_defense(session, thesis, graph, "不知道", [], NoLLM())
        self.assertEqual(len(session.turns), 2)
        self.assertEqual(session.turns[0].role, session.turns[1].role)
        for _ in range(4):
            if session.status == "completed": break
            session = answer_defense(session, thesis, graph, "根据证据E1，当前判断依赖需求稳定这一假设。如果经营现金流持续下降或自由现金流无法覆盖资本开支，该观点将被推翻，目前仍存在不确定性并需要后续验证。", ["E1"], NoLLM())
        self.assertEqual(session.status, "completed")
        self.assertEqual({turn.role.value for turn in session.turns}, {"portfolio_manager", "investment_director", "industry_researcher", "risk_manager"})
        self.assertIsNotNone(session.overall_score)
        self.assertTrue(session.improvement_tasks)
        self.assertTrue(all(turn.score_breakdown for turn in session.turns if turn.answer))


if __name__ == "__main__": unittest.main()
