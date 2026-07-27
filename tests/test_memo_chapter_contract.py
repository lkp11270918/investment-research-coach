import json
import unittest
from pathlib import Path

from backend.agents import run_research_coach_review
from backend.memo_chapters import MEMO_CHAPTERS, MEMO_CHAPTER_IDS, MEMO_CHAPTER_TITLES
from backend.memo_writing import run_memo_writing_skill
from backend.models import CompanyProfile, ComplianceGateOutput, WorkflowState


class MemoChapterContractTest(unittest.TestCase):
    def test_schema_and_runtime_share_the_same_19_chapter_enum(self):
        schema = json.loads(Path("schemas/research_memo.schema.json").read_text())
        schema_ids = schema["properties"]["sections"]["items"]["properties"]["section_id"]["enum"]
        self.assertEqual(schema_ids, list(MEMO_CHAPTER_IDS))
        self.assertEqual(len(schema_ids), 19)

    def test_generated_memo_uses_exact_titles_and_order(self):
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="章节契约测试", industry="测试行业"),
            pre_memo_gate=ComplianceGateOutput(gate_name="pre", status="pass"),
        )
        memo = run_memo_writing_skill(state)
        self.assertEqual(
            [(section.section_id, section.title) for section in memo.sections],
            list(MEMO_CHAPTERS),
        )

    def test_review_mode_scores_all_19_chapters(self):
        state = WorkflowState(company_profile=CompanyProfile(company_name="批改章节测试", industry="测试行业"))
        review = run_research_coach_review("公司基本信息\n不构成投资建议", state)
        scores = review.structured_output["chapter_scores"]
        self.assertEqual(len(scores), 19)
        self.assertEqual([item["section_id"] for item in scores], list(MEMO_CHAPTER_IDS))
        self.assertEqual([item["title"] for item in scores], [MEMO_CHAPTER_TITLES[item] for item in MEMO_CHAPTER_IDS])


if __name__ == "__main__":
    unittest.main()
