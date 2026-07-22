import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.memo_writing import run_memo_writing_skill
from backend.models import AgentOutput, AgentStatus, AnalyzeRequest, CompanyProfile, Confidence, EvidenceCategory, EvidenceItem, JudgeDecision, RawMaterial, ResearchClaim, SkillResult, SourceRef, SourceType, VerificationStatus, WorkflowState
from backend.research_agents import run_judge_agent, run_planner_agent
from backend.workflow_runner import _execute_skill, run_analysis_workflow


def material_set():
    return [RawMaterial(title="财务",source_type=SourceType.FINANCIAL_TABLE,content="指标 | 2025年\n营业收入 | 100亿元\n净利润 | 10亿元\n经营现金流 | 8亿元\n每股收益 | 1元\n可比公司PE | 10倍\n股价 | 8元"),RawMaterial(title="卖方",source_type=SourceType.SELL_SIDE_SUMMARY,content="分析师预测未来收入高增长。")]


class TrueFourAgentRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.old_llm=os.environ.get("USE_LLM_AGENTS"); self.old_db=os.environ.get("DATABASE_URL"); self.tmp=tempfile.TemporaryDirectory()
        os.environ["USE_LLM_AGENTS"]="false"; os.environ["DATABASE_URL"]=f"sqlite:///{Path(self.tmp.name)/'runtime.db'}"
    def tearDown(self):
        if self.old_llm is None: os.environ.pop("USE_LLM_AGENTS",None)
        else: os.environ["USE_LLM_AGENTS"]=self.old_llm
        if self.old_db is None: os.environ.pop("DATABASE_URL",None)
        else: os.environ["DATABASE_URL"]=self.old_db
        self.tmp.cleanup()

    def test_industry_and_objective_change_actual_skill_execution(self):
        bank=run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="B",industry="银行"),materials=material_set(),research_objective="检查财务质量"))
        factory=run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="M",industry="制造业"),materials=material_set(),research_objective="检查估值与安全边际"))
        self.assertIn("bank_analysis",bank.skill_outputs); self.assertNotIn("manufacturing_analysis",bank.skill_outputs)
        self.assertIn("manufacturing_analysis",factory.skill_outputs); self.assertIn("valuation_margin",factory.skill_outputs)
        self.assertNotEqual(set(bank.research_plan.required_skills),set(factory.research_plan.required_skills))

    def test_planner_cannot_select_cross_industry_skill(self):
        class Client:
            available=True
            settings=type("Settings",(),{"openai_model":"test-planner"})()
            def generate_json(self,**_kwargs): return {"required_skills":["bank_analysis","manufacturing_analysis","valuation_margin"],"research_questions":["产能利用率？"]}
        state=WorkflowState(company_profile=CompanyProfile(company_name="M",industry="制造业"),raw_materials=material_set())
        plan,_=run_planner_agent(state,client=Client())
        self.assertIn("manufacturing_analysis",plan.required_skills); self.assertNotIn("bank_analysis",plan.required_skills)

    def test_specialists_are_skill_results_and_analyst_creates_claims(self):
        state=run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="M",industry="制造业"),materials=material_set()))
        self.assertTrue(all(isinstance(value,SkillResult) for value in state.skill_outputs.values()))
        self.assertTrue(state.research_claims)
        self.assertTrue(all(claim.source_skill_ids for claim in state.research_claims))
        self.assertEqual(set(state.agent_outputs),{"research_planner","evidence","research_analyst","red_team_judge"})

    def test_judge_downgrades_opinion_and_rejects_toc_rating(self):
        opinion=EvidenceItem(category=EvidenceCategory.SELL_SIDE_OPINION,statement="卖方预测增长",source_refs=[SourceRef(source_id="S")],verification_status=VerificationStatus.VERIFIED)
        state=WorkflowState(company_profile=CompanyProfile(company_name="X",industry="制造业"),evidence_items=[opinion])
        state.research_claims=[ResearchClaim(topic="增长",statement="公司将高增长",supporting_evidence_ids=[opinion.evidence_id]),ResearchClaim(topic="评级",statement="建议买入",supporting_evidence_ids=[opinion.evidence_id])]
        decisions,_=run_judge_agent(state,"pass")
        self.assertEqual(decisions[0].decision,"downgraded"); self.assertEqual(decisions[1].decision,"rejected")

    def test_writing_uses_only_approved_statement(self):
        evidence=EvidenceItem(category=EvidenceCategory.FACT,statement="收入为100",source_refs=[SourceRef(source_id="S")],verification_status=VerificationStatus.VERIFIED)
        state=WorkflowState(company_profile=CompanyProfile(company_name="X",industry="制造业"),evidence_items=[evidence])
        claim=ResearchClaim(topic="现金流",statement="原始长结论",supporting_evidence_ids=[evidence.evidence_id]); state.research_claims=[claim]
        from backend.models import ComplianceGateOutput
        state.pre_memo_gate=ComplianceGateOutput(gate_name="pre",status="pass"); state.judge_decisions=[JudgeDecision(claim_id=claim.claim_id,decision="approved",reason="ok",approved_statement="唯一允许写入的结论")]
        memo=run_memo_writing_skill(state)
        self.assertIn("唯一允许写入的结论",memo.markdown); self.assertNotIn("原始长结论",memo.markdown)

    def test_skill_failure_retries_and_records_attempts(self):
        state=WorkflowState(company_profile=CompanyProfile(company_name="X",industry="制造业")); calls={"n":0}
        def flaky(_state):
            calls["n"]+=1
            if calls["n"]==1: raise RuntimeError("temporary")
            return AgentOutput(agent_name="Financial Skill",status=AgentStatus.PASS,summary="ok",confidence=Confidence.MEDIUM)
        with patch("backend.workflow_runner._runner",return_value=flaky): result=_execute_skill(state,"financial_quality_dividend")
        self.assertEqual(result.attempt,2); self.assertEqual(calls["n"],2)
        self.assertEqual([event.status for event in state.workflow_events],["running","retry","running","pass"])

    def test_failed_dependency_blocks_downstream_skill(self):
        class Client:
            available=True
            settings=type("Settings",(),{"openai_model":"test"})()
            def generate_json(self,**_kwargs): return {"required_skills":["manufacturing_analysis","valuation_margin"],"dependencies":{"valuation_margin":["manufacturing_analysis"]},"parallel_groups":[["manufacturing_analysis"],["valuation_margin"]]}
        with patch("backend.research_agents.OpenAIClient",return_value=Client()), patch("backend.workflow_runner._runner",return_value=lambda _state: (_ for _ in ()).throw(RuntimeError("broken"))):
            state=run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="M",industry="制造业"),materials=material_set()))
        self.assertEqual(state.skill_outputs["manufacturing_analysis"].status,"fail")
        self.assertEqual(state.skill_outputs["valuation_margin"].failure_code,"dependency_failed")

if __name__=="__main__": unittest.main()
