import unittest
from unittest.mock import patch

from backend.evidence_graph import build_evidence_graph
from backend.llm_agents import run_business_model_moat_llm, run_material_organizer_llm
from backend.memo_writing import STANDARD_SECTIONS, run_memo_writing_skill
from backend.models import (
    AnalyzeRequest, CompanyProfile, ComplianceGateOutput, Confidence,
    EvidenceCategory, EvidenceRelation, EvidenceItem, JudgeDecision, RawMaterial,
    ResearchClaim, SourceDocument, SourceRef, SourceType, VerificationStatus,
    WorkflowOptions, WorkflowState, WorkflowStopAfter,
)
from backend.workflow_runner import run_analysis_workflow, run_review_workflow
from backend.models import ReviewRequest
from tests.functional_parity_fixtures import parity_materials


class StructuredBusinessClient:
    available=True

    def generate_json(self, system_prompt, user_payload, **_kwargs):
        evidence_ids=[item["evidence_id"] for item in user_payload["evidence_items"]]
        return {
            "summary":"公司通过工业设备销售和高毛利维保服务获利。",
            "findings":[
                {"title":"商业模式","detail":"向工业客户销售设备，并通过维保服务获得持续收入。","classification":"fact_based","evidence_ids":evidence_ids,"confidence":"medium"},
                {"title":"护城河证据","detail":"装机量形成维保网络效应，但低价竞争可能削弱优势。","classification":"ai_reasoning","evidence_ids":evidence_ids,"confidence":"medium"},
            ],
            "business_model":{
                "value_proposition":"为工业客户提供自动化设备和持续维保",
                "customers":["工业制造企业"],"revenue_sources":["设备销售","维保服务"],
                "profit_pools":["高毛利维保服务"],"cost_structure":["原材料","研发","售后网络"],
                "cash_flow_characteristics":["设备验收影响回款节奏"],"capital_intensity":"中等",
                "competitive_advantages":["装机基础形成服务网络"],
                "moat_types":["转换成本","服务网络"],
                "moat_evidence":["存量装机客户续签维保"],
                "moat_durability":"取决于续签率和服务质量",
                "moat_erosion_risks":["低价竞争","技术替代"],
                "circle_of_competence":{"status":"partial","reasoning":"收入来源可理解，但续签率资料不足","unknowns":["维保续签率"]},
                "evidence_ids":evidence_ids,"missing_information":["分产品毛利率"],
            },
            "missing_materials":["分产品毛利率"],"warnings":[],
            "confidence":"medium","status":"partial",
        }


class OrganizerClient:
    available=True

    def generate_json(self, **_kwargs):
        return {
            "summary":"识别为券商研究报告。",
            "documents":[{
                "input_index":0,"source_type":"announcement_excerpt",
                "detected_type":"announcement_excerpt","publisher":"中信证券研究部",
                "reporting_period":"2025年度","document_scope":"盈利预测与估值",
                "reliability_level":"secondary","reliability_note":"券商二手观点",
                "contains_financial_data":True,"contains_sell_side_views":True,
                "contains_forecasts":True,"contains_unverified_claims":True,
                "usable_sections":["view_comparison","valuation_margin"],"warnings":[],
            }],
            "findings":[],"missing_materials":[],"warnings":[],"confidence":"high",
        }


class SecondCapabilityRecoveryTest(unittest.TestCase):
    def test_business_model_semantics_are_populated(self):
        evidence=EvidenceItem(
            category=EvidenceCategory.FACT,
            statement="公司向工业客户销售自动化设备，并提供高毛利维保服务；存量客户续签维保。",
            source_refs=[SourceRef(source_id="AR")],
            verification_status=VerificationStatus.VERIFIED,
        )
        state=WorkflowState(
            company_profile=CompanyProfile(company_name="制造样例",industry="制造业"),
            evidence_items=[evidence],
        )
        output=run_business_model_moat_llm(state,StructuredBusinessClient())
        data=output.structured_output
        self.assertIn("维保服务",data["revenue_sources"])
        self.assertIn("高毛利维保服务",data["profit_pools"])
        self.assertIn("服务网络",data["moat_types"])
        self.assertTrue(data["moat_evidence"])
        self.assertEqual(data["circle_of_competence"]["status"],"partial")
        self.assertIn("低价竞争",data["moat_erosion_risks"])

    def test_material_organizer_corrects_declared_type(self):
        state=WorkflowState(
            company_profile=CompanyProfile(company_name="资料纠错",industry="制造业"),
            raw_materials=[RawMaterial(
                title="盈利预测报告",source_type=SourceType.ANNOUNCEMENT_EXCERPT,
                content="中信证券研究部 分析师预计公司2025年度利润增长，给出盈利预测。",
            )],
        )
        run_material_organizer_llm(state,OrganizerClient())
        doc=state.document_intelligence[0]
        self.assertEqual(doc.declared_type,"announcement_excerpt")
        self.assertEqual(doc.detected_type,"sell_side_summary")
        self.assertTrue(doc.type_conflict)
        self.assertEqual(doc.publisher,"中信证券研究部")
        self.assertEqual(doc.reporting_period,"2025年度")
        self.assertEqual(doc.reliability_level,"secondary")

    def test_stop_after_has_no_downstream_products(self):
        expected={
            WorkflowStopAfter.DOCTRINE:(False,False,False,False),
            WorkflowStopAfter.MATERIAL_ORGANIZER:(False,False,False,False),
            WorkflowStopAfter.EVIDENCE_EXTRACTOR:(False,False,False,False),
            WorkflowStopAfter.FINANCIAL_QUALITY:(False,False,False,False),
            WorkflowStopAfter.BUSINESS_MODEL:(False,False,False,False),
            WorkflowStopAfter.MANAGEMENT_VIEW:(False,False,False,False),
            WorkflowStopAfter.VALUE_TRAP:(False,False,False,False),
            WorkflowStopAfter.PRE_MEMO_GATE:(True,False,False,False),
            WorkflowStopAfter.MEMO:(True,True,True,False),
            WorkflowStopAfter.POST_MEMO_GATE:(True,True,True,True),
        }
        for stop,products in expected.items():
            with self.subTest(stop=stop.value):
                state=run_analysis_workflow(AnalyzeRequest(
                    company_profile=CompanyProfile(company_name="停止点",industry="制造业"),
                    materials=parity_materials(),options=WorkflowOptions(stop_after=stop),
                ))
                actual=(state.pre_memo_gate is not None,bool(state.judge_decisions),state.memo is not None,state.post_memo_gate is not None)
                self.assertEqual(state.current_stage,stop.value)
                self.assertEqual(actual,products)
        with patch("backend.workflow_runner.run_compliance_gate_llm",side_effect=AssertionError("不应调用 Pre-Gate")):
            run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="停止",industry="制造业"),materials=parity_materials(),options=WorkflowOptions(stop_after=WorkflowStopAfter.VALUE_TRAP)))
        with patch("backend.workflow_runner.run_judge_agent",side_effect=AssertionError("不应调用 Judge")):
            run_analysis_workflow(AnalyzeRequest(company_profile=CompanyProfile(company_name="停止",industry="制造业"),materials=parity_materials(),options=WorkflowOptions(stop_after=WorkflowStopAfter.PRE_MEMO_GATE)))

    def test_graph_covers_analysis_red_judge_review_and_memo(self):
        state=run_analysis_workflow(AnalyzeRequest(
            company_profile=CompanyProfile(company_name="图谱样例",industry="制造业"),
            materials=parity_materials(),
        ))
        types=[item.node_type for item in state.evidence_graph.nodes]
        self.assertGreater(types.count("analysis_claim"),0)
        self.assertGreater(types.count("red_team_challenge"),0)
        self.assertGreater(types.count("judge_finding"),0)
        self.assertEqual(types.count("memo_section"),19)
        challenge_edges=[item for item in state.evidence_graph.edges if item.relation==EvidenceRelation.CHALLENGES]
        self.assertTrue(challenge_edges)
        self.assertTrue(all(item.to_node_id.startswith("CLAIM:") for item in challenge_edges))
        supported={item.to_node_id for item in state.evidence_graph.edges if item.relation==EvidenceRelation.SUPPORTS}
        self.assertTrue(any(f"CLAIM:{item.claim_id}" in supported for item in state.research_claims))

        review=run_review_workflow(ReviewRequest(
            company_profile=CompanyProfile(company_name="批改图谱",industry="制造业"),
            memo_text="卖方一致看好，所以公司利润增长确定，建议买入。",
            materials=parity_materials(),
        ))
        review_types=[item.node_type for item in review.evidence_graph.nodes]
        self.assertGreater(review_types.count("review_finding"),0)
        self.assertTrue(any(item.relation==EvidenceRelation.RESPONDS_TO for item in review.evidence_graph.edges))

    def test_memo_routes_once_and_synthesizes_sections(self):
        evidence=EvidenceItem(
            category=EvidenceCategory.FACT,statement="设备销售和维保服务构成收入。",
            source_refs=[SourceRef(source_id="AR")],verification_status=VerificationStatus.VERIFIED,
        )
        claims=[
            ResearchClaim(topic="商业模式",statement="设备销售和维保服务构成收入。",supporting_evidence_ids=[evidence.evidence_id],source_skill_ids=["business_model_moat"],primary_section="business_model"),
            ResearchClaim(topic="护城河",statement="存量装机形成服务网络，但面临低价竞争。",supporting_evidence_ids=[evidence.evidence_id],source_skill_ids=["business_model_moat"],primary_section="moat"),
            ResearchClaim(topic="能力圈",statement="收入逻辑可理解，维保续签率仍未知。",supporting_evidence_ids=[evidence.evidence_id],source_skill_ids=["business_model_moat"],primary_section="circle_of_competence"),
            ResearchClaim(topic="管理层目标与现金流",statement="管理层预计增长，但经营现金流尚未验证。",supporting_evidence_ids=[evidence.evidence_id],source_skill_ids=["management_view_comparison"],primary_section="narrative_vs_financials"),
        ]
        state=WorkflowState(
            company_profile=CompanyProfile(company_name="Memo样例",industry="制造业"),
            source_documents=[SourceDocument(source_id="AR",title="年报",source_type=SourceType.ANNUAL_REPORT_SUMMARY)],
            evidence_items=[evidence],research_claims=claims,
            judge_decisions=[JudgeDecision(claim_id=item.claim_id,decision="approved",reason="证据充分",approved_statement=item.statement) for item in claims],
            pre_memo_gate=ComplianceGateOutput(gate_name="pre",status="pass"),
        )
        memo=run_memo_writing_skill(state)
        self.assertEqual([item.section_id for item in memo.sections],[item[0] for item in STANDARD_SECTIONS])
        self.assertEqual(len(memo.sections),19)
        by_id={item.section_id:item for item in memo.sections}
        for section in ("business_model","moat","circle_of_competence"):
            self.assertEqual(by_id[section].status,"complete")
            self.assertTrue(by_id[section].supporting_claim_ids)
            self.assertTrue(by_id[section].evidence_ids)
        all_claim_ids=[claim_id for section in memo.sections for claim_id in section.supporting_claim_ids]
        self.assertEqual(len(all_claim_ids),len(set(all_claim_ids)))
        self.assertIn("交叉审查后",by_id["narrative_vs_financials"].body)
        self.assertNotEqual(by_id["narrative_vs_financials"].body,claims[-1].statement)


if __name__=="__main__":
    unittest.main()
