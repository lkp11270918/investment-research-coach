import unittest

from backend.localization import detect_language, resolve_language
from backend.memo_writing import run_memo_writing_skill
from backend.models import (
    ComplianceGateOutput,
    CompanyProfile,
    EvidenceGraphQuality,
    JudgeDecision,
    Language,
    ResearchClaim,
    WorkflowState,
)
from backend.workflow_runner import run_analysis_workflow
from backend.models import AnalyzeRequest, RawMaterial, SourceType


class OutputLanguageTest(unittest.TestCase):
    def test_auto_detection_prioritizes_key_question(self) -> None:
        language, source = resolve_language(
            Language.AUTO,
            key_question="Can free cash flow support the dividend?",
            research_objective="验证分红",
            materials=["大量中文材料"],
        )
        self.assertEqual(language, Language.EN)
        self.assertEqual(source, "key_question")

    def test_chinese_and_english_detection(self) -> None:
        self.assertEqual(detect_language(["请分析公司的现金流质量"]), Language.ZH)
        self.assertEqual(detect_language(["Please assess the company's cash flow quality."]), Language.EN)

    def test_manual_selection_overrides_detected_language(self) -> None:
        language, source = resolve_language(Language.ZH, key_question="Write the report in English")
        self.assertEqual(language, Language.ZH)
        self.assertEqual(source, "user_selected")

    def test_english_memo_uses_english_fixed_sections_and_disclaimer(self) -> None:
        claim = ResearchClaim(
            topic="Cash flow",
            statement="Operating cash flow covers the current dividend.",
            supporting_evidence_ids=["E1"],
            source_skill_ids=["financial_quality_dividend"],
            primary_section="cash_flow",
        )
        state = WorkflowState(
            company_profile=CompanyProfile(
                company_name="Example Corp",
                industry="Manufacturing",
                research_language=Language.EN,
            ),
            research_claims=[claim],
            judge_decisions=[
                JudgeDecision(
                    claim_id=claim.claim_id,
                    decision="approved",
                    reason="Supported by verified evidence.",
                    approved_statement=claim.statement,
                )
            ],
            pre_memo_gate=ComplianceGateOutput(gate_name="pre_memo_gate", status="pass"),
            evidence_graph_quality=EvidenceGraphQuality(score=80),
        )
        memo = run_memo_writing_skill(state)
        self.assertEqual(len(memo.sections), 19)
        self.assertEqual(memo.sections[0].title, "Company Information")
        self.assertIn("does not constitute investment advice", memo.disclaimer)
        self.assertNotIn("公司基本信息", memo.markdown)

    def test_workflow_resolves_and_records_english_language(self) -> None:
        request = AnalyzeRequest(
            company_profile=CompanyProfile(
                company_name="Example Corp",
                industry="Manufacturing",
                research_language=Language.AUTO,
            ),
            key_question="What evidence would invalidate the current thesis?",
            materials=[
                RawMaterial(
                    title="Annual report",
                    source_type=SourceType.ANNUAL_REPORT_SUMMARY,
                    content="Revenue increased, while capital expenditure also rose.",
                )
            ],
        )
        state = run_analysis_workflow(request)
        self.assertEqual(state.company_profile.research_language, Language.EN)
        self.assertEqual(state.company_profile.language_source, "key_question")
        self.assertEqual(state.memo.sections[0].title, "Company Information")


if __name__ == "__main__":
    unittest.main()
