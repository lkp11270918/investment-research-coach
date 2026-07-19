from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.memo_coauthor import assess_memo_sections, generate_memo_suggestions
from backend.models import CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, MemoSection, MemoVersionCreate, ResearchMemo, ResearchProjectCreate, SourceRef, UserMode, VerificationStatus, WorkflowState
from backend.evidence_graph import build_evidence_graph
from backend.storage import create_research_project, init_research_runs_db, list_memo_versions, save_memo_version, save_user_run


class MemoCoauthorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'memo.db'}"
        init_research_runs_db()
        self.user_id = "USER-A"
        self.profile = CompanyProfile(company_name="测试公司", industry="制造业")
        self.project = create_research_project(self.user_id, ResearchProjectCreate(company_profile=self.profile))
        self.verified = EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="经营现金流稳定", source_refs=[SourceRef(source_id="SRC-1", excerpt="经营现金流稳定")], confidence=Confidence.HIGH, verification_status=VerificationStatus.VERIFIED)
        self.unsupported = EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION, statement="卖方建议买入", source_refs=[SourceRef(source_id="SRC-2")], verification_status=VerificationStatus.TO_BE_VERIFIED)
        state = WorkflowState(company_profile=self.profile, evidence_items=[self.verified, self.unsupported])
        state.evidence_graph = build_evidence_graph(state)
        state.memo = ResearchMemo(company_profile=self.profile, user_mode=UserMode.TO_C, sections=[MemoSection(section_id="cashflow", title="现金流", body="经营现金流稳定，但仍需验证资本开支。", evidence_ids=[self.verified.evidence_id], confidence=Confidence.MEDIUM)], source_ids=["SRC-1"], disclaimer="不构成投资建议")
        save_user_run(user_id=self.user_id, run_type="analysis", state=state, project_id=self.project.project_id)

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.temp_dir.cleanup()

    def test_generated_draft_and_user_versions_are_immutable_history(self) -> None:
        history = list_memo_versions(self.user_id, self.project.project_id)
        self.assertEqual((len(history), history[0].created_by, history[0].version), (1, "ai", 1))
        request = MemoVersionCreate(sections=[MemoSection(section_id="cashflow", title="现金流", body="经营现金流稳定，结论依赖资本开支没有超预期。", evidence_ids=[self.verified.evidence_id], confidence=Confidence.HIGH)], change_summary="增加判断边界", request_formal=True)
        saved = save_memo_version(self.user_id, self.project.project_id, request)
        self.assertEqual((saved.version, saved.gate_status), (2, "formal"))
        self.assertEqual(len(list_memo_versions(self.user_id, self.project.project_id)), 2)

    def test_gate_blocks_ratings_missing_and_unverified_evidence(self) -> None:
        sections = [MemoSection(section_id="view", title="核心观点", body="建议买入，目标价100元", evidence_ids=[self.unsupported.evidence_id])]
        graph = build_evidence_graph(WorkflowState(company_profile=self.profile, evidence_items=[self.unsupported]))
        status, issues = assess_memo_sections(sections, graph, True)
        self.assertEqual(status, "needs_evidence")
        self.assertTrue(any("禁用评级" in item for item in issues))
        self.assertTrue(any("未验证证据" in item for item in issues))

    def test_suggestion_does_not_silently_overwrite_user_text(self) -> None:
        section = MemoSection(section_id="view", title="核心观点", body="现金流改善。", evidence_ids=[])
        graph = build_evidence_graph(WorkflowState(company_profile=self.profile, evidence_items=[self.verified]))
        suggestions = generate_memo_suggestions([section], graph, client=type("Offline", (), {"available": False})())
        self.assertTrue(suggestions)
        self.assertEqual(section.body, "现金流改善。")
        self.assertEqual(suggestions[0].status, "pending")


if __name__ == "__main__":
    unittest.main()
