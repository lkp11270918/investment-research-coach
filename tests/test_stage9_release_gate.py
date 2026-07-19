from __future__ import annotations

import os
import unittest

from backend.models import AnalyzeRequest, CompanyProfile, RawMaterial, SourceType
from backend.workflow_runner import run_analysis_workflow


class ReleaseGateTest(unittest.TestCase):
    def test_failed_pre_gate_returns_blocked_draft(self) -> None:
        previous = os.environ.get("USE_LLM_AGENTS")
        os.environ["USE_LLM_AGENTS"] = "false"
        try:
            state = run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="测试", industry="制造业"), materials=[RawMaterial(title="简单材料", source_type=SourceType.USER_NOTE, content="管理层认为未来会增长")]))
        finally:
            if previous is None:
                os.environ.pop("USE_LLM_AGENTS", None)
            else:
                os.environ["USE_LLM_AGENTS"] = previous
        self.assertEqual(state.workflow_status, "needs_evidence")
        self.assertIn("待补证据研究草稿", state.memo.markdown)
        self.assertIn("不能生成正式研究 Memo", state.memo.markdown)
        self.assertIsNotNone(state.post_memo_gate)


if __name__ == "__main__":
    unittest.main()
