from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.evals.comparative_eval import evaluate_pilot
from backend.evals.real_world import validate_manifest
from backend.evals.run_sec_financial_eval import run as run_sec_financial


class RealReleaseGateTest(unittest.TestCase):
    def test_sec_official_financial_corpus_passes(self) -> None:
        report = run_sec_financial()
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["case_count"], 20)
        self.assertGreaterEqual(report["score"], 95)

    def test_partial_corpus_and_missing_real_users_block_release(self) -> None:
        corpus = validate_manifest(Path("evals/real_cases/manifest.json"))
        self.assertFalse(corpus["passed"])
        self.assertIn("missing required metrics", " ".join(corpus["errors"]))
        pilot = evaluate_pilot()
        self.assertFalse(pilot["passed"])
        self.assertIn("at least ten real target users are required", pilot["errors"])

    def test_comparative_gate_accepts_real_complete_shape_only(self) -> None:
        rows = []
        for index in range(10):
            common = {"participant_id": f"P{index}", "case_pair_id": f"PAIR{index}", "minutes": 60, "return_intent": 3, "completed": True, "blinded_review": True, "reviewer_ids": ["R1", "R2"]}
            rows.append({**common, "case_id": f"G{index}", "condition": "generic_agent", "condition_order": 1 if index % 2 == 0 else 2, "report_quality": 60, "unsupported_fact_count": 2, "traceability_rate": 70, "counter_evidence_score": 55, "explanation_score": 60})
            rows.append({**common, "case_id": f"R{index}", "condition": "research_coach", "condition_order": 2 if index % 2 == 0 else 1, "report_quality": 80, "unsupported_fact_count": 0, "traceability_rate": 95, "counter_evidence_score": 85, "explanation_score": 80})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.json"
            path.write_text(json.dumps({"results": rows}), encoding="utf-8")
            report = evaluate_pilot(path)
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
