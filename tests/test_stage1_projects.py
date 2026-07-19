from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.models import (
    CompanyProfile,
    ResearchProjectCreate,
    ResearchProjectStatus,
    ResearchProjectUpdate,
    WorkflowState,
)
from backend.storage import (
    create_research_project,
    get_research_project,
    init_research_runs_db,
    list_research_projects,
    save_user_run,
    update_research_project,
)


class ResearchProjectStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "stage1.db"
        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        self.temp_dir.cleanup()

    def _create_project(self, user_id: str = "USER-A"):
        return create_research_project(
            user_id,
            ResearchProjectCreate(
                company_profile=CompanyProfile(
                    ticker="600000",
                    company_name="测试公司",
                    industry="制造业",
                ),
                research_objective="验证现金流质量",
                investment_horizon="3-5年",
                initial_view="现金流可能改善",
                key_question="资本开支是否可持续",
            ),
        )

    def test_project_lifecycle_and_user_isolation(self) -> None:
        project = self._create_project()
        self.assertEqual(len(list_research_projects("USER-A")), 1)
        self.assertEqual(list_research_projects("USER-B"), [])
        self.assertIsNone(get_research_project("USER-B", project.project_id))

        updated = update_research_project(
            "USER-A",
            project.project_id,
            ResearchProjectUpdate(initial_view="现金流结论待验证"),
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.project.initial_view, "现金流结论待验证")
        self.assertEqual(updated.project.research_objective, "验证现金流质量")

        archived = update_research_project(
            "USER-A",
            project.project_id,
            ResearchProjectUpdate(status=ResearchProjectStatus.ARCHIVED),
        )
        self.assertEqual(archived.project.status, ResearchProjectStatus.ARCHIVED)
        self.assertEqual(list_research_projects("USER-A"), [])
        self.assertEqual(len(list_research_projects("USER-A", include_archived=True)), 1)

    def test_project_timeline_preserves_multiple_runs(self) -> None:
        project = self._create_project()
        profile = project.company_profile
        first = WorkflowState(company_profile=profile)
        second = WorkflowState(company_profile=profile)
        save_user_run(user_id="USER-A", run_type="analysis", state=first, project_id=project.project_id)
        save_user_run(user_id="USER-A", run_type="review", state=second, project_id=project.project_id)

        detail = get_research_project("USER-A", project.project_id)
        self.assertEqual(detail.project.run_count, 2)
        self.assertEqual([item.run_type for item in detail.timeline], ["analysis", "review"])
        self.assertEqual({item.run_id for item in detail.timeline}, {first.run_id, second.run_id})

    def test_existing_runs_table_is_migrated(self) -> None:
        migrated_path = Path(self.temp_dir.name) / "legacy.db"
        with sqlite3.connect(migrated_path) as conn:
            conn.execute(
                """CREATE TABLE research_runs (
                    run_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, run_type TEXT NOT NULL,
                    company_name TEXT NOT NULL, ticker TEXT, industry TEXT, memo_confidence TEXT,
                    material_count INTEGER NOT NULL, evidence_count INTEGER NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL
                )"""
            )
        os.environ["DATABASE_URL"] = f"sqlite:///{migrated_path}"
        init_research_runs_db()
        with sqlite3.connect(migrated_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(research_runs)")}
            project_table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='research_projects'"
            ).fetchone()
        self.assertIn("project_id", columns)
        self.assertIsNotNone(project_table)


if __name__ == "__main__":
    unittest.main()
