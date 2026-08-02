from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.agents import run_evidence_extractor, run_management_view_comparison
from backend.file_parsers import parse_uploaded_file
from backend.models import AnalyzeRequest, CompanyProfile, RawMaterial, SourceType
from backend.workflow_runner import run_analysis_workflow


class MaterialAnalysisSpeedTest(unittest.TestCase):
    def test_fast_mode_preserves_material_analysis_outputs_without_full_memo(self) -> None:
        materials = [
            RawMaterial(
                title="券商A研报",
                source_type=SourceType.SELL_SIDE_SUMMARY,
                content="证券研究报告。分析师认为收入将增长，但利润率可能承压。",
            ),
            RawMaterial(
                title="券商B研报",
                source_type=SourceType.SELL_SIDE_SUMMARY,
                content="证券研究报告。分析师认为收入增速将放缓，但利润率可能改善。",
            ),
        ]

        def evidence_without_network(state, *_args, **_kwargs):
            return run_evidence_extractor(state)

        def comparison_without_network(state, *_args, **_kwargs):
            return run_management_view_comparison(state)

        with (
            patch("backend.workflow_runner.run_evidence_extractor_llm", side_effect=evidence_without_network),
            patch("backend.workflow_runner.run_management_view_comparison_llm", side_effect=comparison_without_network),
        ):
            state = run_analysis_workflow(
                AnalyzeRequest(
                    company_profile=CompanyProfile(company_name="测试公司", industry=""),
                    materials=materials,
                    research_mode="material_analysis",
                )
            )

        self.assertEqual(set(state.agent_outputs), {"research_planner", "evidence", "research_analyst", "red_team_judge"})
        self.assertIn("management_view_comparison", state.skill_outputs)
        self.assertIn("value_trap_contradiction", state.skill_outputs)
        self.assertGreaterEqual(state.research_judgment.sell_side_source_count, 2)
        self.assertTrue(any(point.point_type == "divergence" for point in state.research_judgment.view_points))
        self.assertTrue(state.research_claims)
        self.assertTrue(state.judge_decisions)
        self.assertIsNone(state.memo)
        self.assertNotIn("financial_quality_dividend", state.skill_outputs)
        self.assertNotIn("valuation_margin", state.skill_outputs)

    def test_identical_file_uses_parse_cache(self) -> None:
        payload = f"cache-test-{next(tempfile._get_candidate_names())}".encode()
        first = parse_uploaded_file(filename="sample.txt", data=payload, material_id="notes")
        with patch("backend.file_parsers._decode_text", side_effect=AssertionError("cache miss")):
            second = parse_uploaded_file(filename="renamed.txt", data=payload, material_id="sellside")
        self.assertEqual(first.content, second.content)
        self.assertEqual(second.title, "renamed.txt")
        self.assertEqual(second.source_type, SourceType.SELL_SIDE_SUMMARY)


if __name__ == "__main__":
    unittest.main()
