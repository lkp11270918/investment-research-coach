import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.llm_agents import (
    _is_blocking_warning,
    run_business_model_moat_llm,
    run_financial_quality_dividend_llm,
    run_management_view_comparison_llm,
    run_value_trap_contradiction_llm,
)
from backend.industry_skills import run_industry_analysis_skill
from backend.evidence_graph import _invalid_temporal_contradiction
from backend.memo_writing import STANDARD_SECTIONS, run_memo_writing_skill
from backend.models import (
    AgentFinding,
    ComplianceGateOutput,
    CompanyProfile,
    Confidence,
    EvidenceCategory,
    EvidenceItem,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceRelation,
    SourceDocument,
    SourceRef,
    SourceType,
    VerificationStatus,
    WorkflowState,
    ResearchClaim,
    ReviewRequest,
    JudgeDecision,
    SkillResult,
)
from backend.research_agents import run_judge_agent, run_planner_agent
from backend.workflow_runner import _runner, run_analysis_workflow, run_review_workflow
from backend.models import AnalyzeRequest
from tests.functional_parity_fixtures import parity_materials


class DeepSkillClient:
    available = True

    def generate_json(self, system_prompt, user_payload, **_kwargs):
        evidence_ids = [
            item["evidence_id"] for item in user_payload.get("evidence_items", [])
        ]
        if "Financial Quality" in system_prompt:
            title = "利润增长但现金转化恶化"
            detail = "2025年经营现金流下降，不能把净利润增长直接解释为盈利质量改善。"
        elif "Management & View Comparison" in system_prompt:
            title = "卖方分歧点"
            detail = "乐观报告假设需求增长20%，谨慎报告假设需求增长5%，分歧来自需求和产能利用率。"
        elif "Value Trap" in system_prompt:
            title = "现金流型价值陷阱"
            detail = "自由现金流下降而分红增加，分红覆盖存在恶化风险。"
        else:
            title = "资本密集型商业模式"
            detail = "扩产依赖资本开支，需求不足会通过产能利用率压低资本回报。"
        return {
            "summary": detail,
            "findings": [
                {
                    "title": title,
                    "detail": detail,
                    "classification": "risk",
                    "evidence_ids": evidence_ids,
                    "confidence": "medium",
                }
            ],
            "missing_materials": [],
            "warnings": [],
            "confidence": "medium",
            "status": "pass",
        }


class FunctionalParityTest(unittest.TestCase):
    def setUp(self):
        self.old_db = os.environ.get("DATABASE_URL")
        self.temp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp.name) / 'parity.db'}"
        evidence = [
            EvidenceItem(
                category=EvidenceCategory.FINANCIAL_FACT,
                statement="2025年经营现金流下降",
                source_refs=[SourceRef(source_id="FIN")],
                verification_status=VerificationStatus.VERIFIED,
            ),
            EvidenceItem(
                category=EvidenceCategory.SELL_SIDE_OPINION,
                statement="卖方A预计需求增长20%",
                source_refs=[SourceRef(source_id="A")],
                verification_status=VerificationStatus.VERIFIED,
            ),
            EvidenceItem(
                category=EvidenceCategory.SELL_SIDE_OPINION,
                statement="卖方B预计需求增长5%",
                source_refs=[SourceRef(source_id="B")],
                verification_status=VerificationStatus.VERIFIED,
            ),
        ]
        self.state = WorkflowState(
            company_profile=CompanyProfile(company_name="测试制造", industry="制造业"),
            source_documents=[
                SourceDocument(title="卖方A", source_id="A", source_type=SourceType.SELL_SIDE_SUMMARY, content="预计需求增长20%"),
                SourceDocument(title="卖方B", source_id="B", source_type=SourceType.SELL_SIDE_SUMMARY, content="预计需求增长5%"),
            ],
            evidence_items=evidence,
        )

    def tearDown(self):
        if self.old_db is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.old_db
        self.temp.cleanup()

    def test_normal_workflow_routes_to_deep_skill_implementations(self):
        self.assertEqual(_runner("financial_quality_dividend").__name__, "run_financial_quality_dividend_llm")
        self.assertEqual(_runner("management_view_comparison").__name__, "run_management_view_comparison_llm")
        self.assertEqual(_runner("manufacturing_analysis").__name__, "run_manufacturing_analysis_skill")

    def test_deep_skills_return_company_specific_analysis_not_checklists(self):
        client = DeepSkillClient()
        outputs = [
            run_financial_quality_dividend_llm(self.state, client),
            run_business_model_moat_llm(self.state, client),
            run_management_view_comparison_llm(self.state, client),
            run_value_trap_contradiction_llm(self.state, client),
        ]
        expected = ["现金转化恶化", "资本密集型", "需求增长20%", "自由现金流下降"]
        for output, phrase in zip(outputs, expected):
            self.assertEqual(output.status.value, "pass")
            self.assertIn(phrase, output.findings[0].title + output.findings[0].detail)
            self.assertTrue(output.findings[0].evidence_ids)
            self.assertNotIn("当前骨架", output.findings[0].detail)

    def test_industry_skills_use_different_metrics_risks_and_outputs(self):
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="跨行业测试", industry="待选择"),
            evidence_items=[
                EvidenceItem(
                    category=EvidenceCategory.FACT,
                    statement="产能利用率下降且存货积压",
                    source_refs=[SourceRef(source_id="M")],
                    verification_status=VerificationStatus.VERIFIED,
                ),
                EvidenceItem(
                    category=EvidenceCategory.FACT,
                    statement="净息差收窄且不良率上升",
                    source_refs=[SourceRef(source_id="B")],
                    verification_status=VerificationStatus.VERIFIED,
                ),
                EvidenceItem(
                    category=EvidenceCategory.FACT,
                    statement="渠道库存上升且终端动销下降",
                    source_refs=[SourceRef(source_id="C")],
                    verification_status=VerificationStatus.VERIFIED,
                ),
                EvidenceItem(
                    category=EvidenceCategory.FACT,
                    statement="监管电价稳定但资本开支和负债上升",
                    source_refs=[SourceRef(source_id="U")],
                    verification_status=VerificationStatus.VERIFIED,
                ),
            ],
        )
        offline = type("Offline", (), {"available": False})()
        outputs = {
            skill_id: run_industry_analysis_skill(state, skill_id, offline)
            for skill_id in (
                "bank_analysis",
                "manufacturing_analysis",
                "consumer_analysis",
                "utility_analysis",
            )
        }
        text = {
            key: " ".join(item.detail for item in output.findings)
            for key, output in outputs.items()
        }
        self.assertIn("净息差", text["bank_analysis"])
        self.assertIn("产能利用率", text["manufacturing_analysis"])
        self.assertIn("渠道库存", text["consumer_analysis"])
        self.assertIn("监管电价", text["utility_analysis"])
        self.assertEqual(len(set(text.values())), 4)
        self.assertEqual(
            len({tuple(output.missing_materials) for output in outputs.values()}),
            4,
        )

    def test_multi_sell_side_comparison_produces_actual_consensus_and_divergence(self):
        output = run_management_view_comparison_llm(
            self.state, type("Offline", (), {"available": False})()
        )
        by_title = {item.title: item for item in output.findings}
        for title in (
            "卖方共同点",
            "卖方分歧点",
            "分歧来源",
            "核心假设差异",
            "买方需独立验证的问题",
        ):
            self.assertIn(title, by_title)
            self.assertTrue(by_title[title].evidence_ids)
        self.assertTrue(any(title.startswith("单份卖方观点｜卖方A") for title in by_title))
        self.assertTrue(any(title.startswith("单份卖方观点｜卖方B") for title in by_title))
        combined = " ".join(item.detail for item in output.findings)
        self.assertIn("20%", combined)
        self.assertIn("5%", combined)
        self.assertIn("增长率或估值倍数口径不同", by_title["分歧来源"].detail)

    def test_doctrine_is_in_planner_context_runtime_and_deterministic_judge(self):
        captured = {}

        class PlannerClient:
            available = True
            settings = type("Settings", (), {"openai_model": "test"})()

            def generate_json(self, system_prompt, **_kwargs):
                captured["prompt"] = system_prompt
                return {"required_skills": ["manufacturing_analysis"]}

        run_planner_agent(self.state, client=PlannerClient())
        self.assertIn("Owner Earnings", captured["prompt"])
        self.assertIn("安全边际", captured["prompt"])

        runtime = run_analysis_workflow(
            AnalyzeRequest(
                company_profile=CompanyProfile(company_name="准则测试", industry="制造业"),
                materials=parity_materials(),
            )
        )
        doctrine = runtime.skill_outputs["doctrine_context"]
        self.assertGreaterEqual(len(doctrine.findings), 12)
        self.assertIn("安全边际", {item.title for item in doctrine.findings})

        evidence = EvidenceItem(
            category=EvidenceCategory.FINANCIAL_FACT,
            statement="公司PE为6倍",
            source_refs=[SourceRef(source_id="FIN")],
            verification_status=VerificationStatus.VERIFIED,
        )
        judge_state = WorkflowState(
            company_profile=CompanyProfile(company_name="准则测试", industry="制造业"),
            evidence_items=[evidence],
            research_claims=[
                ResearchClaim(
                    topic="估值",
                    statement="公司低PE就是安全边际",
                    supporting_evidence_ids=[evidence.evidence_id],
                )
            ],
        )
        decisions, _ = run_judge_agent(
            judge_state, "pass", type("Offline", (), {"available": False})()
        )
        self.assertEqual(decisions[0].decision, "rejected")
        self.assertIn("价值投资准则", decisions[0].reason)

    def test_review_mode_runs_financial_pipeline_and_uses_detected_anomalies(self):
        state = run_review_workflow(
            ReviewRequest(
                company_profile=CompanyProfile(company_name="批改测试", industry="制造业"),
                memo_text="卖方一致看好，公司净利润增长，因此建议买入。",
                materials=parity_materials(),
            )
        )
        self.assertTrue(state.processing_records)
        self.assertTrue(state.financial_calculations)
        self.assertTrue(state.financial_anomalies)
        self.assertIsNotNone(state.valuation_analysis.method)
        metrics = {item.metric_name for item in state.evidence_items}
        self.assertTrue(
            {
                "dividend",
                "capital_expenditure",
                "short_term_interest_bearing_debt",
                "interest_expense",
            }.issubset(metrics)
        )
        self.assertTrue(state.evidence_graph.nodes)
        review = state.skill_outputs["research_coach_review"]
        anomaly_titles = [
            item.title for item in review.findings if item.title.startswith("财务异常未解释")
        ]
        self.assertTrue(anomaly_titles)
        self.assertTrue(
            any(item.classification == "value_trap_omission" for item in review.findings)
        )

    def test_memo_has_all_19_sections_and_only_judge_approved_research_text(self):
        evidence = EvidenceItem(
            category=EvidenceCategory.FINANCIAL_FACT,
            statement="2025年经营现金流下降",
            source_refs=[SourceRef(source_id="FIN")],
            verification_status=VerificationStatus.VERIFIED,
        )
        approved = ResearchClaim(
            topic="现金流质量",
            statement="这段原始表述不能直接进入报告",
            supporting_evidence_ids=[evidence.evidence_id],
            falsification_conditions=["核对现金流下降是否来自一次性营运资金变化。"],
        )
        rejected = ResearchClaim(
            topic="估值",
            statement="秘密未批准结论：公司一定被低估",
            supporting_evidence_ids=[evidence.evidence_id],
        )
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="报告测试", industry="制造业"),
            source_documents=[
                SourceDocument(
                    source_id="FIN",
                    title="财务表",
                    source_type=SourceType.FINANCIAL_TABLE,
                )
            ],
            evidence_items=[evidence],
            research_claims=[approved, rejected],
            judge_decisions=[
                JudgeDecision(
                    claim_id=approved.claim_id,
                    decision="approved",
                    reason="证据充分",
                    approved_statement="2025年经营现金流下降，利润现金转化需要进一步解释。",
                ),
                JudgeDecision(
                    claim_id=rejected.claim_id,
                    decision="rejected",
                    reason="缺少内在价值和安全边际证据",
                ),
            ],
            pre_memo_gate=ComplianceGateOutput(gate_name="pre", status="pass"),
            skill_outputs={
                "doctrine_context": SkillResult(
                    skill_id="doctrine_context",
                    status="pass",
                    findings=[
                        AgentFinding(
                            title="安全边际",
                            detail="低估值不等于安全边际",
                            classification="ai_reasoning",
                            confidence=Confidence.MEDIUM,
                        )
                    ],
                )
            },
        )
        memo = run_memo_writing_skill(state)
        expected_ids = [section_id for section_id, _ in STANDARD_SECTIONS]
        self.assertEqual([section.section_id for section in memo.sections], expected_ids)
        self.assertEqual(len(memo.sections), 19)
        self.assertIn("2025年经营现金流下降", memo.markdown)
        self.assertNotIn(approved.statement, memo.markdown)
        self.assertNotIn(rejected.statement, memo.markdown)
        self.assertIn("当前没有经 Red Team & Judge 批准", memo.markdown)
        self.assertIn("FIN：财务表", memo.markdown)

    def test_orchestrator_marks_model_degradation_and_blocks_failed_required_skill(self):
        state = run_analysis_workflow(
            AnalyzeRequest(
                company_profile=CompanyProfile(company_name="编排测试", industry="制造业"),
                materials=parity_materials(),
            )
        )
        for skill_id in state.research_plan.required_skills:
            result = state.skill_outputs[skill_id]
            self.assertTrue(result.inputs_fingerprint)
            self.assertGreaterEqual(result.attempt, 1)
            expected_mode = "deterministic" if skill_id == "valuation_margin" else "degraded"
            self.assertEqual(result.execution_mode, expected_mode)

        def broken(_state):
            raise RuntimeError("required skill unavailable")

        with patch("backend.workflow_runner._runner", return_value=broken):
            failed = run_analysis_workflow(
                AnalyzeRequest(
                    company_profile=CompanyProfile(company_name="失败测试", industry="制造业"),
                    materials=parity_materials(),
                )
            )
        self.assertEqual(failed.workflow_status, "needs_evidence")
        self.assertEqual(failed.pre_memo_gate.status, "fail")
        self.assertTrue(
            any("必要 Skills 未完成" in issue for issue in failed.pre_memo_gate.evidence_issues)
        )
        self.assertTrue(
            any(
                result.failure_code == "RuntimeError" and result.execution_mode == "not_run"
                for result in failed.skill_outputs.values()
            )
        )

    def test_compliance_gate_understands_safe_negative_statements(self):
        self.assertFalse(_is_blocking_warning("未发现收益承诺或交易指令。"))
        self.assertFalse(_is_blocking_warning("To C 模式未输出买入或卖出评级。"))
        self.assertFalse(_is_blocking_warning("未复述或重构未授权付费研报。"))
        self.assertTrue(_is_blocking_warning("Memo包含买入评级和收益承诺。"))

    def test_different_periods_of_same_metric_are_not_treated_as_conflicts(self):
        left = EvidenceGraphNode(
            node_id="EVIDENCE:A",
            node_type="financial_fact",
            label="2024年有息负债30亿元",
            metadata={"metric_name": "interest_bearing_debt", "period": "2024"},
        )
        right = EvidenceGraphNode(
            node_id="EVIDENCE:B",
            node_type="financial_fact",
            label="2025年有息负债65亿元",
            metadata={"metric_name": "interest_bearing_debt", "period": "2025"},
        )
        edge = EvidenceGraphEdge(
            from_node_id=left.node_id,
            to_node_id=right.node_id,
            relation=EvidenceRelation.CONTRADICTS,
            rationale="错误的跨期冲突",
        )
        self.assertTrue(
            _invalid_temporal_contradiction(
                edge, {left.node_id: left, right.node_id: right}
            )
        )


if __name__ == "__main__":
    unittest.main()
