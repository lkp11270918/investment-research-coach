import json
import unittest
from pathlib import Path

from backend.agents import run_research_coach_review
from backend.memo_chapters import MEMO_CHAPTERS, MEMO_CHAPTER_IDS, MEMO_CHAPTER_TITLES
from backend.memo_writing import run_memo_writing_skill
from backend.models import (
    CompanyProfile,
    ComplianceGateOutput,
    Confidence,
    EvidenceCategory,
    EvidenceItem,
    JudgeDecision,
    ResearchClaim,
    VerificationStatus,
    WorkflowState,
)


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

    def test_unapproved_chapter_shows_available_results_before_final_caveat(self):
        evidence = EvidenceItem(
            category=EvidenceCategory.FINANCIAL_FACT,
            statement="经营现金流同比增长，但应收账款增速更快。",
            metric_name="经营现金流",
            confidence=Confidence.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        )
        claim = ResearchClaim(
            topic="现金流质量",
            statement="利润现金转化改善仍需排除营运资金波动影响。",
            supporting_evidence_ids=[evidence.evidence_id],
            primary_section="cash_flow",
            falsification_conditions=["核对下一期应收账款与经营现金流是否同步改善。"],
        )
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="有限资料测试", industry="测试行业"),
            evidence_items=[evidence],
            research_claims=[claim],
            judge_decisions=[JudgeDecision(
                claim_id=claim.claim_id,
                decision="needs_evidence",
                reason="仍需交叉验证",
                missing_evidence=["下一期现金流量表"],
            )],
            pre_memo_gate=ComplianceGateOutput(gate_name="pre", status="pass"),
        )
        section = next(item for item in run_memo_writing_skill(state).sections if item.section_id == "cash_flow")
        self.assertIn(evidence.statement, section.body)
        self.assertIn(claim.statement, section.body)
        self.assertIn("下一步验证问题", section.body)
        self.assertTrue(section.body.endswith("当前没有经 Red Team & Judge 批准且证据充分的结论；该部分保留为明确资料缺口。"))
        self.assertEqual(section.evidence_ids, [evidence.evidence_id])

    def test_approved_chapter_does_not_append_unapproved_caveat(self):
        evidence = EvidenceItem(
            category=EvidenceCategory.FACT,
            statement="订阅收入占比提升。",
            confidence=Confidence.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        )
        claim = ResearchClaim(
            topic="商业模式",
            statement="订阅收入占比提升增强了收入可见度。",
            supporting_evidence_ids=[evidence.evidence_id],
            primary_section="business_model",
        )
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="获批测试", industry="软件"),
            evidence_items=[evidence],
            research_claims=[claim],
            judge_decisions=[JudgeDecision(
                claim_id=claim.claim_id,
                decision="approved",
                reason="证据充分",
                approved_statement=claim.statement,
            )],
            pre_memo_gate=ComplianceGateOutput(gate_name="pre", status="pass"),
        )
        section = next(item for item in run_memo_writing_skill(state).sections if item.section_id == "business_model")
        self.assertIn(claim.statement, section.body)
        self.assertNotIn("当前没有经 Red Team & Judge 批准", section.body)

    def test_review_mode_scores_all_19_chapters(self):
        state = WorkflowState(company_profile=CompanyProfile(company_name="批改章节测试", industry="测试行业"))
        review = run_research_coach_review("公司基本信息\n不构成投资建议", state)
        scores = review.structured_output["chapter_scores"]
        self.assertEqual(len(scores), 19)
        self.assertEqual([item["section_id"] for item in scores], list(MEMO_CHAPTER_IDS))
        self.assertEqual([item["title"] for item in scores], [MEMO_CHAPTER_TITLES[item] for item in MEMO_CHAPTER_IDS])


if __name__ == "__main__":
    unittest.main()
