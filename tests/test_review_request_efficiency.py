import unittest
from unittest.mock import patch

from backend.models import AgentOutput, AgentStatus, CompanyProfile, Confidence, RawMaterial, ReviewRequest
from backend.workflow_runner import run_review_workflow


class ReviewRequestEfficiencyTest(unittest.TestCase):
    def test_review_uses_deterministic_preprocessing_and_one_deep_review(self) -> None:
        request = ReviewRequest(
            company_profile=CompanyProfile(company_name="测试公司", industry="消费"),
            memo_text="卖方预计公司利润必然增长，因此当前估值具有安全边际。",
            materials=[RawMaterial(title="人工 Memo", content="卖方预计公司利润必然增长，因此当前估值具有安全边际。")],
        )
        review = AgentOutput(
            agent_name="Research Coach Review",
            status=AgentStatus.PARTIAL,
            summary="已完成深度批改。",
            confidence=Confidence.MEDIUM,
        )

        with (
            patch("backend.workflow_runner.run_material_organizer_llm", side_effect=AssertionError("不应调用资料整理模型")),
            patch("backend.workflow_runner.run_evidence_extractor_llm", side_effect=AssertionError("不应调用证据抽取模型")),
            patch("backend.workflow_runner.run_research_coach_review_llm", return_value=review) as deep_review,
        ):
            state = run_review_workflow(request)

        deep_review.assert_called_once()
        self.assertTrue(state.source_documents)
        self.assertTrue(state.evidence_items)
        self.assertEqual(state.agent_outputs["red_team_judge"].summary, "已完成深度批改。")


if __name__ == "__main__":
    unittest.main()
