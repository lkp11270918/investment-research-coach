from __future__ import annotations

import unittest

from backend.financial_calculations import calculate_financial_metrics
from backend.financial_parser import extract_structured_financial_evidence
from backend.models import SourceDocument, SourceType


class FinancialCalculationTest(unittest.TestCase):
    def setUp(self) -> None:
        content = """指标 | 2022年 | 2023年 | 2024年
营业收入 | 80亿元 | 100亿元 | 121亿元
净利润 | 8亿元 | 10亿元 | 11亿元
经营现金流 | 10亿元 | 14亿元 | 16亿元
资本开支 | 3亿元 | 4亿元 | 5亿元
现金分红 | 2亿元 | 3亿元 | 4亿元
负债合计 | 40亿元 | 42亿元 | 45亿元
资产总计 | 100亿元 | 110亿元 | 120亿元
股东权益合计 | 60亿元 | 68亿元 | 75亿元
总市值 | 160亿元 | 180亿元 | 200亿元
每股分红 | 0.2元/股 | 0.3元/股 | 0.4元/股
股价 | 10元/股 | 12元/股 | 16元/股"""
        document = SourceDocument(title="真实口径财务表", source_type=SourceType.FINANCIAL_TABLE, content=content)
        self.evidence = extract_structured_financial_evidence([document])
        self.records, self.derived = calculate_financial_metrics(self.evidence)

    def _record(self, metric: str, period: str):
        return next(item for item in self.records if item.metric_name == metric and item.period == period)

    def test_formula_outputs_and_unit_normalization(self) -> None:
        self.assertEqual(self._record("free_cash_flow_calculated", "2024年").value, 1_100_000_000)
        self.assertAlmostEqual(self._record("dividend_payout_ratio", "2024年").value, 36.363636, places=5)
        self.assertAlmostEqual(self._record("cash_conversion_ratio", "2024年").value, 145.454545, places=5)
        self.assertEqual(self._record("debt_to_asset_ratio_calculated", "2024年").value, 37.5)
        self.assertAlmostEqual(self._record("roe_calculated", "2024年").value, 14.666667, places=5)
        self.assertEqual(self._record("dividend_yield", "2024年").value, 2.0)
        self.assertEqual(self._record("dividend_yield_per_share", "2024年").value, 2.5)

    def test_growth_cagr_and_provenance(self) -> None:
        self.assertEqual(self._record("revenue_yoy", "2024").value, 21.0)
        self.assertAlmostEqual(self._record("revenue_cagr", "2022-2024").value, 22.983739, places=4)
        calculated = self._record("free_cash_flow_calculated", "2024年")
        self.assertEqual(len(calculated.input_evidence_ids), 2)
        evidence = next(item for item in self.derived if item.metric_name == "free_cash_flow_calculated" and item.period == "2024年")
        self.assertIn("公式：operating_cash_flow - capital_expenditure", evidence.notes or "")
        self.assertTrue(evidence.source_refs)

    def test_zero_denominator_is_reported_not_invented(self) -> None:
        document = SourceDocument(title="零利润", source_type=SourceType.FINANCIAL_TABLE, content="指标 | 2024年\n净利润 | 0亿元\n现金分红 | 1亿元")
        records, derived = calculate_financial_metrics(extract_structured_financial_evidence([document]))
        failed = next(item for item in records if item.metric_name == "dividend_payout_ratio")
        self.assertEqual(failed.status, "failed")
        self.assertIn("zero", failed.error or "")
        self.assertFalse(any(item.metric_name == "dividend_payout_ratio" for item in derived))


if __name__ == "__main__":
    unittest.main()
