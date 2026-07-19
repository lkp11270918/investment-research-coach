from __future__ import annotations

import os
import tempfile
import unittest

from backend.models import CompanyProfile, RawMaterial, ResearchProjectCreate, SourceType, WorkflowState
from backend.storage import create_research_project, get_research_project, init_research_runs_db, list_project_materials, save_user_run


class ProjectMaterialLibraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.tmp.name}/app.db"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.tmp.cleanup()

    def test_incremental_material_versions_and_deduplication(self) -> None:
        profile = CompanyProfile(company_name="测试公司", industry="制造业")
        project = create_research_project("U1", ResearchProjectCreate(company_profile=profile, research_objective="验证现金流", investment_horizon="3年", initial_view="中性", key_question="资本开支是否侵蚀现金流"))
        first = WorkflowState(company_profile=profile, raw_materials=[RawMaterial(title="年报", file_name="年报.pdf", source_type=SourceType.ANNUAL_REPORT_SUMMARY, content="2023版本")])
        save_user_run(user_id="U1", run_type="analysis", state=first, project_id=project.project_id)
        save_user_run(user_id="U1", run_type="analysis", state=first, project_id=project.project_id)
        second = WorkflowState(company_profile=profile, raw_materials=[RawMaterial(title="年报", file_name="年报.pdf", source_type=SourceType.ANNUAL_REPORT_SUMMARY, content="2024版本")])
        save_user_run(user_id="U1", run_type="analysis", state=second, project_id=project.project_id)
        materials = list_project_materials("U1", project.project_id)
        self.assertEqual([item.version for item in materials], [1, 2])
        self.assertEqual(len(get_research_project("U1", project.project_id).timeline), 2)
        self.assertEqual(get_research_project("U1", project.project_id).project.key_question, "资本开支是否侵蚀现金流")
        self.assertEqual(list_project_materials("U2", project.project_id), [])


if __name__ == "__main__": unittest.main()
