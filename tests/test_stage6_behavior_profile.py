from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.capability_profile import build_capability_profile
from backend.models import ResearchBehaviorEvent
from backend.storage import init_research_runs_db, list_behavior_events, record_behavior_event


class BehaviorProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'behavior.db'}"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.temp_dir.cleanup()

    def test_behavior_events_are_user_isolated_and_explain_scores(self) -> None:
        event = ResearchBehaviorEvent(user_id="U1", project_id="P1", action="review_evidence", dimension="evidence_awareness", outcome="verified", score=90)
        record_behavior_event(event)
        self.assertEqual(list_behavior_events("U1")[0].event_id, event.event_id)
        self.assertEqual(list_behavior_events("U2"), [])
        profile = build_capability_profile("U1", [], [], [], list_behavior_events("U1"))
        dimension = next(item for item in profile.dimensions if item.dimension == "evidence_awareness")
        self.assertEqual((dimension.score, dimension.sample_count), (90, 1))
        self.assertIn(event.event_id, dimension.evidence[0])

    def test_repeated_error_requires_three_distinct_projects(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = [ResearchBehaviorEvent(user_id="U1", project_id=f"P{index}", action="save_memo_version", dimension="memo_writing", outcome="needs_evidence", score=score, metadata={"error_code": "经常遗漏资本开支"}, created_at=start + timedelta(days=index)) for index, score in enumerate((40, 50, 75), start=1)]
        profile = build_capability_profile("U1", [], [], [], events)
        dimension = next(item for item in profile.dimensions if item.dimension == "memo_writing")
        self.assertIn("经常遗漏资本开支", dimension.repeated_errors)
        self.assertEqual(dimension.trend, "improving")
        two_project_profile = build_capability_profile("U1", [], [], [], events[:2])
        two_project_dimension = next(item for item in two_project_profile.dimensions if item.dimension == "memo_writing")
        self.assertNotIn("经常遗漏资本开支", two_project_dimension.repeated_errors)


if __name__ == "__main__":
    unittest.main()
