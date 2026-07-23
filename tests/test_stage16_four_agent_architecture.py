import os
import tempfile
import unittest
from pathlib import Path

from backend.agent_architecture import MAIN_AGENT_KEYS, build_research_plan
from backend.models import AgentOutput, AnalyzeRequest, CompanyProfile, RawMaterial, ReviewRequest, SourceType, WorkflowState
from backend.workflow_runner import run_analysis_workflow, run_review_workflow


class FourAgentArchitectureTest(unittest.TestCase):
    def setUp(self):
        self.old_llm = os.environ.get("USE_LLM_AGENTS")
        self.old_db = os.environ.get("DATABASE_URL")
        self.temp = tempfile.TemporaryDirectory()
        os.environ["USE_LLM_AGENTS"] = "false"
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(self.temp.name) / 'architecture.db'}"

    def tearDown(self):
        if self.old_llm is None: os.environ.pop("USE_LLM_AGENTS", None)
        else: os.environ["USE_LLM_AGENTS"] = self.old_llm
        if self.old_db is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = self.old_db
        self.temp.cleanup()

    def materials(self):
        return [
            RawMaterial(title="财务表", source_type=SourceType.FINANCIAL_TABLE, content="指标 | 2024年 | 2025年\n营业收入 | 90亿元 | 100亿元\n净利润 | 9亿元 | 10亿元\n经营现金流 | 7亿元 | 8亿元\n企业自由现釔1 | 4亿元 | 5亿元\n总股本 | 10亿股 | 10亿股\n股价 | 10元 | 10元\n每股收益 | 0.9元 | 1元\n可比公司PE | 8倍 | 10倍\n可比公司PE | 10倍 | 12倍\n有息负债 | 20亿元 | 20亿元\n货币资金 | 5亿元 | 5亿元"),
            RawMaterial(title="管理层交流", source_type=SourceType.MANAGEMENT_NOTE, content="管理层计划扩张产能，目标是未来收入继续增长。"),
            RawMaterial(title="卖方A", source_type=SourceType.SELL_SIDE_SUMMARY, content="分析师预测需求增长，给出乐观利润预测。"),
            RawMaterial(title="卖方B", source_type=SourceType.SELL_SIDE_SUMMARY, content="分析师认为产能过剩可能压制利润率。"),
        ]

    def test_planner_changes_real_research_questions_by_industry(self):
        bank = build_research_plan(WorkflowState(company_profile=CompanyProfile(company_name="B", industry="商业银行"), raw_materials=self.materials()))
        factory = build_research_plan(WorkflowState(company_profile=CompanyProfile(company_name="M", industry="制造业"), raw_materials=self.materials()))
        self.assertEqual(bank.company_type, "bank")
        self.assertEqual(factory.company_type, "manufacturing")
        self.assertNotEqual(bank.priority_questions, factory.priority_questions)
        self.assertTrue(any("资产质量" in item for item in bank.priority_questions))
        self.assertTrue(any("产能" in item for item in factory.priority_questions))

    def test_four_agents_preserve_all_user_facing_research_capabilities(self):
        result = run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="测试制造", industry="制造业"), materials=self.materials()))
        self.assertEqual(tuple(result.agent_outputs), MAIN_AGENT_KEYS)
        self.assertEqual(set(result.research_plan.required_skills), {"financial_quality_dividend", "business_model_moat", "manufacturing_analysis", "management_view_comparison", "valuation_margin"})
        required_outputs = {"material_organization", "evidence_extraction", "financial_quality_dividend", "business_model_moat", "manufacturing_analysis", "management_view_comparison", "valuation_margin", "value_trap_contradiction"}
        self.assertTrue(required_outputs.issubset(result.skill_outputs))
        self.assertTrue(result.source_documents)
        self.assertTrue(result.evidence_items)
        self.assertTrue(result.evidence_graph.nodes)
        metrics = {item.metric_name for item in result.evidence_items}
        self.assertTrue({"revenue", "net_profit", "operating_cash_flow", "eps", "peer_pe"}.issubset(metrics))
        self.assertEqual(len(result.valuation_analysis.scenarios), 3)
        self.assertTrue(result.research_judgment)
        self.assertIsNotNone(result.pre_memo_gate)
        self.assertIsNotNone(result.memo)
        self.assertTrue(result.workflow_events)
        self.assertNotIn("research_memo_generator", result.agent_outputs)

    def test_missing_materials_skip_analysis_without_fake_outputs(self):
        result = run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="空项目", industry="制造业"), materials=[]))
        self.assertEqual(result.research_plan.required_skills, [])
        self.assertEqual(result.agent_outputs["research_analyst"].findings, [])
        self.assertEqual(result.workflow_status, "needs_evidence")

    def test_review_mode_reuses_judge_and_keeps_deep_review_skill(self):
        result = run_review_workflow(ReviewRequest(company_profile=CompanyProfile(company_name="测试", industry="制造业"), memo_text="卖方预测公司必然高增长，因此建议买入。", materials=self.materials()))
        self.assertEqual(tuple(result.agent_outputs), MAIN_AGENT_KEYS)
        self.assertIn("research_coach_review", result.skill_outputs)
        review = result.skill_outputs["research_coach_review"]
        self.assertTrue(review.findings)
        titles = {item.title for item in review.findings}
        self.assertIn("缺少证据来源", titles)
        self.assertIn("缺少反证风险", titles)

    def test_historical_nine_agent_payload_remains_readable(self):
        historical = WorkflowState.model_validate({"company_profile":{"company_name":"旧项目","industry":"制造业"},"agent_outputs":{"financial_quality_dividend":AgentOutput(agent_name="Financial Agent",summary="旧财务结论").model_dump(mode="json")}})
        self.assertEqual(historical.output_for("financial_quality_dividend").summary, "旧财务结论")
        self.assertEqual(historical.skill_outputs, {})


if __name__ == "__main__": unittest.main()
