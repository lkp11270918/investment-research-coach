from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import storage
from backend.auth import init_auth_db
from backend.main import analyze, create_defense, create_project, create_thesis_version, project_detail, project_evidence_graph, project_research_map, project_tasks, refresh_capability_profile, register, submit_defense_answer
from backend.models import AnalyzeRequest, DefenseAnswerRequest, RegisterRequest, ResearchProjectCreate, ThesisDraft
from backend.storage import init_research_runs_db


class ReleaseLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = {key: os.environ.get(key) for key in ("DATABASE_URL", "AUTH_SECRET_KEY", "USE_LLM_AGENTS")}
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'release.db'}"
        os.environ["AUTH_SECRET_KEY"] = "release-test-secret"
        os.environ["USE_LLM_AGENTS"] = "false"
        self.runs_patch = patch.object(storage, "RUNS_DIR", Path(self.temp_dir.name) / "runs")
        self.runs_patch.start()
        init_auth_db()
        init_research_runs_db()

    def tearDown(self) -> None:
        self.runs_patch.stop()
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_authenticated_project_research_training_lifecycle(self) -> None:
        auth = register(RegisterRequest(email="release@example.com", password="ReleaseTest123!", name="发布验收"))
        user = auth.user
        project = create_project(ResearchProjectCreate.model_validate({
            "company_profile": {"ticker": "600001", "company_name": "发布验收制造公司", "industry": "制造业"},
            "research_objective": "验证利润、现金流和竞争优势是否一致",
            "investment_horizon": "3-5年",
            "initial_view": "利润改善可能依赖需求和资本开支假设",
            "key_question": "自由现金流能否持续覆盖资本开支和分红",
        }), user)
        project_id = project.project_id

        analysis = analyze(AnalyzeRequest.model_validate({
            "project_id": project_id,
            "company_profile": project.company_profile.model_dump(mode="json"),
            "materials": [
                {"title": "2024财务数据", "file_name": "financial-2024.xlsx", "source_type": "financial_table", "content": "指标 | 2024年\n营业收入 | 100亿元\n净利润 | 10亿元\n经营现金流 | 14亿元\n自由现金流 | 8亿元\n现金分红 | 4亿元\n资产负债率 | 42%\nROE | 15%"},
                {"title": "经营与风险资料", "source_type": "annual_report_summary", "content": "公司依靠核心产品销售获得收入。管理层认为需求稳定，但客户集中度较高。若原材料价格上涨且无法转嫁，利润率和自由现金流可能下降。"},
            ],
        }), user)
        self.assertIn(analysis.status, {"completed", "needs_evidence", "needs_revision"})
        self.assertGreater(len(analysis.state.evidence_items), 0)
        self.assertGreater(len(analysis.state.processing_records), 0)

        detail = project_detail(project_id, user)
        self.assertEqual(detail.project.run_count, 1)
        self.assertEqual(len(detail.materials), 2)
        graph = project_evidence_graph(project_id, user)
        evidence_ids = [node.evidence_id for node in graph.nodes if node.evidence_id]
        self.assertGreaterEqual(len(evidence_ids), 3)
        research_map = project_research_map(project_id, user)
        self.assertTrue(research_map.questions)
        self.assertTrue(research_map.next_questions)

        chosen = evidence_ids[:3]
        thesis = create_thesis_version(project_id, ThesisDraft.model_validate({
            "core_view": "自由现金流质量取决于需求稳定、利润率和资本开支",
            "core_variables": [
                {"name": "需求稳定", "rationale": "决定收入持续性", "evidence_ids": [chosen[0]]},
                {"name": "利润率", "rationale": "决定利润兑现", "evidence_ids": [chosen[1]]},
                {"name": "资本开支", "rationale": "决定自由现金流", "evidence_ids": [chosen[2]]},
            ],
            "supporting_evidence_ids": chosen,
            "counter_evidence_ids": [chosen[-1]],
            "assumptions": ["需求保持稳定"],
            "falsification_conditions": ["经营现金流下降且无法覆盖资本开支"],
            "unknowns": ["客户集中度变化"],
            "scenarios": [
                {"name": "bull", "assumptions": ["需求改善"], "outcome": "自由现金流改善", "trigger_conditions": ["收入和现金流同步增长"]},
                {"name": "base", "assumptions": ["需求稳定"], "outcome": "自由现金流稳定", "trigger_conditions": ["现金流覆盖分红"]},
                {"name": "bear", "assumptions": ["成本上涨"], "outcome": "自由现金流承压", "trigger_conditions": ["利润率和现金流下降"]},
            ],
        }), user)
        self.assertEqual(thesis.version, 1)

        defense = create_defense(project_id, user)
        failed_answer = submit_defense_answer(defense.session_id, DefenseAnswerRequest(answer="目前不知道，需要补充材料。", evidence_ids=[]), user)
        self.assertFalse(failed_answer.turns[0].passed)
        tasks = project_tasks(project_id, user)
        self.assertTrue(tasks)
        profile = refresh_capability_profile(user)
        self.assertGreaterEqual(profile.sample_count, 1)
        self.assertTrue(any(item.sample_count > 0 for item in profile.dimensions))


if __name__ == "__main__":
    unittest.main()
