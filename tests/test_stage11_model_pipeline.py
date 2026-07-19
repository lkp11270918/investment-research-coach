from __future__ import annotations

import unittest

from backend.model_pipeline import classify_material, classify_statement, detect_financial_anomalies, rerank
from backend.models import EvidenceCategory, EvidenceItem, RawMaterial, SourceType


class ModelPipelineTest(unittest.TestCase):
    def test_layers_have_real_deterministic_behaviour(self) -> None:
        material = RawMaterial(title="业绩会纪要", content="管理层回答投资者问题")
        self.assertEqual(classify_material(material)[0], SourceType.MANAGEMENT_NOTE)
        self.assertEqual(classify_statement("经营现金流同比增长20%并覆盖分红")[0], EvidenceCategory.FINANCIAL_FACT)
        self.assertEqual(rerank("经营现金流", ["品牌渠道", "经营现金流改善", "行业政策"])[0], 1)
        anomalies = detect_financial_anomalies([
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="A", metric_name="revenue", period="2024", metric_value=100),
            EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT, statement="B", metric_name="revenue", period="2024", metric_value=80),
        ])
        self.assertTrue(anomalies)


if __name__ == "__main__": unittest.main()
