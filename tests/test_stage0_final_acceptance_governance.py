import unittest

from backend.evals.acceptance_matrix import validate_acceptance_matrix


class FinalAcceptanceGovernanceTest(unittest.TestCase):
    def test_all_final_product_outcomes_have_implementation_tests_and_gates(self) -> None:
        report = validate_acceptance_matrix()
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["requirement_count"], 20)


if __name__ == "__main__":
    unittest.main()
