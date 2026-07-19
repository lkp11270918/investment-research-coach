from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.model_pipeline import classify_material, classify_statement, detect_financial_anomalies, execute_model_pipeline, rerank, semantic_rerank
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

    def test_real_model_layers_record_provider_model_and_latency(self) -> None:
        class FakeClient:
            available = True
            settings = SimpleNamespace(openai_small_model="small-real", openai_embedding_model="embedding-real")

            def generate_json(self, **kwargs):
                return {"labels": [{"index": 0, "label": "management_note", "confidence": 0.9}]}

            def embed(self, texts, **kwargs):
                return [[0.1, 0.2] for _ in texts], 12

        records = execute_model_pipeline(
            [RawMaterial(title="业绩会", content="管理层发言")],
            [EvidenceItem(category=EvidenceCategory.MANAGEMENT_OPINION, statement="管理层预计需求稳定")],
            FakeClient(),
        )
        small = next(item for item in records if item.layer.value == "lightweight_classifier")
        embedding = next(item for item in records if item.component == "semantic_embedding")
        self.assertEqual((small.provider, small.model_name, small.status), ("openai", "small-real", "completed"))
        self.assertEqual((embedding.model_name, embedding.latency_ms), ("embedding-real", 12))

    def test_model_outputs_change_production_objects_and_real_reranking(self) -> None:
        class FakeClient:
            available = True
            settings = SimpleNamespace(openai_small_model="small-real", openai_embedding_model="embedding-real")
            def generate_json(self, **kwargs):
                return {"labels": [{"index": 0, "label": "management_note", "confidence": 0.95}, {"index": 1, "label": "risk", "confidence": 0.91}]}
            def embed(self, texts, **kwargs):
                vectors = {"现金流": [1.0, 0.0], "品牌": [0.0, 1.0], "经营现金流改善": [0.9, 0.1]}
                return [vectors.get(text, [1.0, 0.0]) for text in texts], 3
        material = RawMaterial(title="未分类", content="问答")
        item = EvidenceItem(category=EvidenceCategory.FACT, statement="风险")
        execute_model_pipeline([material], [item], FakeClient())
        self.assertEqual(material.source_type, SourceType.MANAGEMENT_NOTE)
        self.assertEqual(item.category, EvidenceCategory.RISK)
        order, model = semantic_rerank("现金流", ["品牌", "经营现金流改善"], FakeClient())
        self.assertEqual(order[0], 1)
        self.assertEqual(model, "embedding-real+small-real:cross_encoder_rerank")

    def test_fallback_is_never_reported_as_specialized_model_success(self) -> None:
        class OfflineClient:
            available = False

        records = execute_model_pipeline([], [], OfflineClient())
        fallback = next(item for item in records if item.component == "hashed_embedding_fallback")
        self.assertEqual(fallback.status, "fallback")
        self.assertTrue(fallback.fallback_reason)


if __name__ == "__main__": unittest.main()
