from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.models import CompanyProfile, EvidenceGraph, EvidenceGraphNode, ResearchProjectCreate, ThesisDraft, ThesisScenario, ThesisVariable, ThesisVersion
from backend.storage import create_research_project, init_research_runs_db, list_thesis_versions, save_thesis_version
from backend.thesis_builder import assess_thesis


class ThesisBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp.name) / 'thesis.db'}"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.temp.cleanup()

    def test_complete_thesis_passes_and_versions_persist(self) -> None:
        graph = EvidenceGraph(nodes=[
            EvidenceGraphNode(node_id="EVIDENCE:E1", node_type="financial_fact", label="现金流稳定", evidence_id="E1"),
            EvidenceGraphNode(node_id="EVIDENCE:E2", node_type="risk", label="资本开支上升", evidence_id="E2"),
            EvidenceGraphNode(node_id="EVIDENCE:E3", node_type="fact", label="需求保持稳定", evidence_id="E3"),
            EvidenceGraphNode(node_id="EVIDENCE:E4", node_type="financial_fact", label="自由现金流覆盖分红", evidence_id="E4"),
        ])
        draft = ThesisDraft(core_view="现金流稳定但资本开支需要验证", core_variables=[ThesisVariable(name=f"变量{i}", rationale="影响自由现金流", evidence_ids=[["E1"], ["E3"], ["E4"]][i]) for i in range(3)], supporting_evidence_ids=["E1"], counter_evidence_ids=["E2"], assumptions=["需求稳定"], falsification_conditions=["自由现金流连续两期无法覆盖分红"], unknowns=["未来资本开支"], scenarios=[ThesisScenario(name=name, assumptions=["需求变化"], outcome="现金流变化", trigger_conditions=["收入增速变化"]) for name in ("bull", "base", "bear")], user_internal_label="观察")
        assessment = assess_thesis(draft, graph)
        self.assertEqual(assessment.status.value, "pass")
        project = create_research_project("USER-A", ResearchProjectCreate(company_profile=CompanyProfile(company_name="测试公司", industry="制造业")))
        save_thesis_version("USER-A", ThesisVersion(project_id=project.project_id, version=1, draft=draft, assessment=assessment))
        save_thesis_version("USER-A", ThesisVersion(project_id=project.project_id, version=2, draft=draft, assessment=assessment))
        self.assertEqual([v.version for v in list_thesis_versions("USER-A", project.project_id)], [1, 2])
        self.assertEqual(list_thesis_versions("USER-B", project.project_id), [])

    def test_sell_side_only_and_public_rating_fail(self) -> None:
        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:S1", node_type="sell_side_opinion", label="卖方看好", evidence_id="S1")])
        draft = ThesisDraft(core_view="增长", supporting_evidence_ids=["S1"], user_internal_label="买入")
        assessment = assess_thesis(draft, graph)
        self.assertTrue(assessment.sell_side_repetition_risk)
        self.assertTrue(any("公开投资评级" in issue for issue in assessment.issues))

    def test_irrelevant_evidence_cannot_create_false_coverage(self) -> None:
        graph = EvidenceGraph(nodes=[EvidenceGraphNode(node_id="EVIDENCE:X", node_type="fact", label="办公地址位于上海", evidence_id="X")])
        draft = ThesisDraft(core_view="经营现金流改善能够持续覆盖分红", supporting_evidence_ids=["X"], counter_evidence_ids=["X"])
        assessment = assess_thesis(draft, graph)
        self.assertNotIn("X", assessment.relevant_support_ids)
        self.assertTrue(any("语义关联" in issue for issue in assessment.issues))


if __name__ == "__main__": unittest.main()
