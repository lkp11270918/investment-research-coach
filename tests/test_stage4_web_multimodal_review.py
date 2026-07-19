from __future__ import annotations

import os
import tempfile
import unittest
from email.message import Message
from pathlib import Path

from backend.models import CompanyProfile, ContentBlock, MaterialBlockReview, MaterialModality, RawMaterial, ResearchProjectCreate, SourceType, WorkflowState
from backend.storage import create_research_project, init_research_runs_db, list_project_materials, review_project_material_block, save_user_run
from backend.web_ingestion import WebIngestionError, ingest_web_url


class FakeResponse:
    def __init__(self, html: str, url: str = "https://example.com/report") -> None:
        self.data = html.encode()
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, limit): return self.data[:limit]
    def geturl(self): return self.url


def public_resolver(*args, **kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 443))]


class WebAndMultimodalReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp_dir.name) / 'multimodal.db'}"
        init_research_runs_db()

    def tearDown(self) -> None:
        if self.previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.previous
        self.temp_dir.cleanup()

    def test_web_ingestion_preserves_provenance_and_blocks_private_networks(self) -> None:
        html = """<html><head><title>年度经营报告</title><meta property="og:site_name" content="交易所"><meta property="article:published_time" content="2026-03-30T08:00:00+08:00"></head><body><nav>菜单</nav><article><p>公司2025年营业收入增长，经营现金流保持稳定。</p><p>资本开支上升，自由现金流仍需持续验证。</p></article></body></html>"""
        material = ingest_web_url("https://example.com/report", opener=lambda *args, **kwargs: FakeResponse(html), resolver=public_resolver)
        self.assertEqual(material.title, "年度经营报告")
        self.assertEqual(material.publisher, "交易所")
        self.assertEqual(material.url, "https://example.com/report")
        self.assertTrue(material.blocks)
        self.assertNotIn("菜单", material.content)
        with self.assertRaises(WebIngestionError):
            ingest_web_url("http://127.0.0.1/private", resolver=lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))])

    def test_user_can_confirm_or_reject_model_inference(self) -> None:
        user_id = "USER-A"
        project = create_research_project(user_id, ResearchProjectCreate(company_profile=CompanyProfile(company_name="测试公司", industry="制造业")))
        block = ContentBlock(modality=MaterialModality.IMAGE, content="图表似乎显示需求下降", extraction_method="vision_inference", requires_confirmation=True)
        state = WorkflowState(company_profile=project.company_profile, raw_materials=[RawMaterial(title="图表", file_name="chart.png", source_type=SourceType.INDUSTRY_MATERIAL, content="图表", modality=MaterialModality.IMAGE, blocks=[block])])
        save_user_run(user_id=user_id, run_type="analysis", state=state, project_id=project.project_id)
        material = list_project_materials(user_id, project.project_id)[0]
        updated = review_project_material_block(user_id, project.project_id, material.material_id, block.block_id, MaterialBlockReview(confirmed=False, note="图例口径不一致"))
        reviewed = updated.blocks[0]
        self.assertEqual(reviewed.review_status, "rejected")
        self.assertFalse(reviewed.requires_confirmation)
        self.assertEqual(reviewed.review_note, "图例口径不一致")


if __name__ == "__main__":
    unittest.main()
