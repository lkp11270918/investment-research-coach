from __future__ import annotations

import unittest

from backend.capability_profile import build_capability_profile
from backend.models import AgentStatus, Confidence, DefenseRole, DefenseSession, DefenseTurn, ThesisAssessment, ThesisDraft, ThesisVersion


class CapabilityProfileTest(unittest.TestCase):
    def test_profile_uses_behavior_and_detects_repeated_errors(self) -> None:
        thesis_one = ThesisVersion(project_id="P1", version=1, draft=ThesisDraft(core_view="观点"), assessment=ThesisAssessment(status=AgentStatus.FAIL, issues=["核心观点缺少最强反证"], evidence_coverage=20, confidence=Confidence.LOW))
        thesis_two = ThesisVersion(project_id="P1", version=2, draft=ThesisDraft(core_view="观点"), assessment=ThesisAssessment(status=AgentStatus.FAIL, issues=["核心观点缺少最强反证"], evidence_coverage=30, confidence=Confidence.LOW))
        defense = DefenseSession(project_id="P1", thesis_id=thesis_two.thesis_id, status="completed", overall_score=40, turns=[DefenseTurn(role=DefenseRole.RISK_MANAGER, question="风险？", answer="不知道", score=30, feedback="缺少推翻条件", passed=False)])
        profile = build_capability_profile("U1", [], [thesis_one, thesis_two], [defense])
        counter = next(item for item in profile.dimensions if item.dimension == "counter_evidence")
        self.assertIn("核心观点缺少最强反证", counter.repeated_errors)
        self.assertLess(counter.score, 60)
        self.assertEqual(counter.trend, "improving")
        self.assertGreaterEqual(counter.sample_count, 2)
        self.assertIn("counter_evidence", profile.priorities)
        self.assertEqual(profile.sample_count, 3)

    def test_missing_dimension_is_not_a_fake_fifty(self) -> None:
        profile = build_capability_profile("U1", [], [], [])
        self.assertTrue(all(item.score is None for item in profile.dimensions))
        self.assertTrue(all(item.trend == "insufficient_data" for item in profile.dimensions))


if __name__ == "__main__": unittest.main()
