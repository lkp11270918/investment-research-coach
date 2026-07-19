from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.evidence_graph import build_evidence_graph
from backend.models import (
    CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, EvidenceNodeReview,
    ResearchProjectCreate, SourceDocument, SourceRef, SourceType, VerificationStatus,
    WorkflowState,
)
from backend.storage import create_research_project, get_project_evidence_graph, init_research_runs_db, review_project_evidence_node, save_user_run


class EvidenceGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'graph.db'}"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous
        self.temp_dir.cleanup()

    def test_conflict_persistence_and_user_review(self) -> None:
        profile = CompanyProfile(company_name="测试公司", industry="制造业")
        project = create_research_project("USER-A", ResearchProjectCreate(company_profile=profile))
        source_a = SourceDocument(title="年报", source_type=SourceType.FINANCIAL_TABLE)
        source_b = SourceDocument(title="研报", source_type=SourceType.SELL_SIDE_SUMMARY)
        evidence = [
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="2024营收100亿元", source_refs=[SourceRef(source_id=source_a.source_id)], period="2024", metric_name="revenue", metric_value=100, unit="亿元", confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED),
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="2024营收90亿元", source_refs=[SourceRef(source_id=source_b.source_id)], period="2024", metric_name="revenue", metric_value=90, unit="亿元", confidence=Confidence.MEDIUM, verification_status=VerificationStatus.PARTIALLY_SUPPORTED),
        ]
        state = WorkflowState(company_profile=profile, source_documents=[source_a, source_b], evidence_items=evidence)
        state.evidence_graph = build_evidence_graph(state)
        self.assertEqual(len(state.evidence_graph.conflicts), 1)
        self.assertTrue(any(edge.relation.value == "contradicts" for edge in state.evidence_graph.edges))
        save_user_run(user_id="USER-A", run_type="analysis", state=state, project_id=project.project_id)
        graph = get_project_evidence_graph("USER-A", project.project_id)
        self.assertIsNotNone(graph)
        node_id = f"EVIDENCE:{evidence[1].evidence_id}"
        reviewed = review_project_evidence_node("USER-A", project.project_id, node_id, EvidenceNodeReview(verification_status=VerificationStatus.UNSUPPORTED, note="口径不一致"))
        node = next(item for item in reviewed.nodes if item.node_id == node_id)
        self.assertEqual(node.verification_status, VerificationStatus.UNSUPPORTED)
        self.assertEqual(node.metadata["user_review_note"], "口径不一致")
        self.assertIsNone(get_project_evidence_graph("USER-B", project.project_id))


if __name__ == "__main__":
    unittest.main()
