from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.evals.real_world import validate_manifest
from backend.evals.run_eval import run_suite


class EvalGovernanceTest(unittest.TestCase):
    def test_synthetic_suite_cannot_claim_release_quality(self) -> None:
        report = run_suite()
        self.assertTrue(report["passed"])
        self.assertEqual(report["evidence_level"], "synthetic_regression")
        self.assertFalse(report["release_eligible"])

    def test_empty_or_undersized_real_corpus_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"minimum_cases_per_metric": 20, "cases": []}), encoding="utf-8")
            report = validate_manifest(path)
        self.assertFalse(report["passed"])
        self.assertIn("real-world corpus is empty", report["errors"])


if __name__ == "__main__":
    unittest.main()
