from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.evidence_graph import build_evidence_graph
from backend.models import AgentStatus, CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, MemoSection, MemoVersion, ResearchMap, ResearchProjectCreate, ResearchQuestion, ResearchQuestionStatus, ResearchTaskUpdate, SourceRef, ThesisAssessment, ThesisDraft, ThesisVersion, VerificationStatus, WorkflowState
from backend.storage import create_research_project, init_research_runs_db, list_research_tasks, save_user_run, update_research_task, upsert_research_tasks
from backend.task_feedback import tasks_from_memo, tasks_from_research_state, tasks_from_thesis


class TaskFeedbackLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'tasks.db'}"
        init_research_runs_db()
        self.user_id = "U1"
        self.profile = CompanyProfile(company_name="测试公司", industry="制造业")
        self.project = create_research_project(self.user_id, ResearchProjectCreate(company_profile=self.profile))
        self.evidence = EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="经营现金流稳定", source_refs=[SourceRef(source_id="S1")], verification_status=VerificationStatus.VERIFIED, confidence=Confidence.HIGH)
        state = WorkflowState(company_profile=self.profile, evidence_items=[self.evidence])
        state.evidence_graph = build_evidence_graph(state)
        save_user_run(user_id=self.user_id, run_type="analysis", state=state, project_id=self.project.project_id)

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.temp_dir.cleanup()

    def test_all_feedback_sources_generate_tasks(self) -> None:
        research_map = ResearchMap(project_id=self.project.project_id, industry="制造业", questions=[ResearchQuestion(question_id="RQ-1", category="cash", question="现金流能否覆盖分红？", status=ResearchQuestionStatus.UNANSWERED, missing_materials=["分红历史"] )])
        map_tasks = tasks_from_research_state(self.project.project_id, research_map, build_evidence_graph(WorkflowState(company_profile=self.profile, evidence_items=[self.evidence])))
        thesis = ThesisVersion(project_id=self.project.project_id, version=1, draft=ThesisDraft(core_view="待验证"), assessment=ThesisAssessment(status=AgentStatus.FAIL, issues=["核心观点缺少最强反证"], confidence=Confidence.LOW))
        memo = MemoVersion(project_id=self.project.project_id, version=1, sections=[MemoSection(section_id="v", title="观点", body="待验证")], gate_issues=["观点：缺少可追溯证据"])
        all_tasks = map_tasks + tasks_from_thesis(thesis) + tasks_from_memo(memo)
        upsert_research_tasks(self.user_id, all_tasks, self.project.project_id)
        self.assertEqual({task.source_type for task in list_research_tasks(self.user_id, self.project.project_id)}, {"research_map", "thesis", "memo"})

    def test_task_requires_verified_evidence_and_stays_completed(self) -> None:
        research_map = ResearchMap(project_id=self.project.project_id, industry="制造业", questions=[ResearchQuestion(question_id="RQ-1", category="cash", question="现金流能否覆盖分红？", status=ResearchQuestionStatus.UNANSWERED)])
        task = upsert_research_tasks(self.user_id, tasks_from_research_state(self.project.project_id, research_map, build_evidence_graph(WorkflowState(company_profile=self.profile, evidence_items=[self.evidence]))), self.project.project_id)[0]
        with self.assertRaises(ValueError):
            update_research_task(self.user_id, self.project.project_id, task.task_id, ResearchTaskUpdate(status="completed", evidence_ids=[]))
        completed = update_research_task(self.user_id, self.project.project_id, task.task_id, ResearchTaskUpdate(status="completed", evidence_ids=[self.evidence.evidence_id]))
        self.assertEqual(completed.status, "completed")
        upsert_research_tasks(self.user_id, tasks_from_research_state(self.project.project_id, research_map, build_evidence_graph(WorkflowState(company_profile=self.profile, evidence_items=[self.evidence]))), self.project.project_id)
        self.assertEqual(list_research_tasks(self.user_id, self.project.project_id)[0].status, "completed")


if __name__ == "__main__":
    unittest.main()
