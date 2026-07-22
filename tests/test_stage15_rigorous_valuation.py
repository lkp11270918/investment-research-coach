import os,tempfile,unittest
from pathlib import Path
from backend.models import CompanyProfile,EvidenceCategory,EvidenceItem,ResearchProjectCreate,ValuationAssumptions,VerificationStatus
from backend.storage import create_research_project,get_valuation_assumptions,init_research_runs_db,save_valuation_assumptions
from backend.valuation import analyze_valuation

def ev(name,value,unit="元",period="2025"):
    return EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT,statement=name,metric_name=name,metric_value=value,unit=unit,period=period,verification_status=VerificationStatus.VERIFIED)

class RigorousValuationTest(unittest.TestCase):
    def test_ambiguous_fcf_is_never_used_as_fcff_or_fcfe(self):
        result=analyze_valuation([ev("share_price",10,"元/股"),ev("free_cash_flow",100,"亿元"),ev("shares_outstanding",10,"亿股")],"制造业")
        self.assertFalse(result.scenarios)
        self.assertTrue(any("未标明FCFF或FCFE" in warning for warning in result.warnings))

    def test_fcff_enterprise_to_equity_bridge_and_confirmation_gate(self):
        items=[ev("share_price",10,"元/股"),ev("free_cash_flow_to_firm",100,"亿元"),ev("shares_outstanding",10,"亿股"),ev("interest_bearing_debt",20,"亿元"),ev("cash_and_equivalents",5,"亿元"),ev("minority_interest",2,"亿元"),ev("non_operating_assets",3,"亿元")]
        draft=analyze_valuation(items,"制造业",ValuationAssumptions())
        self.assertEqual(draft.status,"draft"); self.assertFalse(draft.formal_conclusion_allowed)
        formal=analyze_valuation(items,"制造业",ValuationAssumptions(confirmed=True))
        self.assertEqual(formal.status,"formal"); self.assertTrue(formal.formal_conclusion_allowed)
        base=next(item for item in formal.scenarios if item.name=="base")
        self.assertAlmostEqual((base.enterprise_value-15e8-2e8+3e8),base.equity_value,places=0)
        self.assertEqual(base.meets_required_margin,base.margin_of_safety_percent>=25)

    def test_unverified_or_conflicting_core_data_blocks_formal_conclusion(self):
        items=[ev("share_price",10,"元/股"),ev("free_cash_flow_to_firm",100,"亿元"),ev("free_cash_flow_to_firm",120,"亿元"),ev("shares_outstanding",10,"亿股"),ev("interest_bearing_debt",20,"亿元"),ev("cash_and_equivalents",5,"亿元")]
        items[0].verification_status=VerificationStatus.TO_BE_VERIFIED
        result=analyze_valuation(items,"制造业",ValuationAssumptions(confirmed=True))
        self.assertFalse(result.formal_conclusion_allowed)
        self.assertTrue(any("尚未核验" in warning for warning in result.warnings))
        self.assertTrue(any("冲突值" in warning for warning in result.warnings))

    def test_bank_uses_ddm_instead_of_industrial_net_debt(self):
        result=analyze_valuation([ev("share_price",10,"元/股"),ev("dividend_per_share",.6,"元/股")],"商业银行",ValuationAssumptions(confirmed=True))
        self.assertEqual(result.method,"ddm"); self.assertEqual(result.status,"formal")

    def test_relative_valuation_uses_peer_range(self):
        items=[ev("share_price",10,"元/股"),ev("eps",1,"元/股"),ev("peer_pe",8,"倍","A"),ev("peer_pe",10,"倍","B"),ev("peer_pe",12,"倍","C")]
        result=analyze_valuation(items,"制造业",ValuationAssumptions(method="relative",confirmed=True))
        self.assertEqual([item.estimated_value_per_share for item in result.scenarios],[8,10,12])

    def test_user_assumptions_persist_per_project(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=os.environ.get("DATABASE_URL");os.environ["DATABASE_URL"]=f"sqlite:///{Path(directory)/'valuation.db'}"
            try:
                init_research_runs_db();project=create_research_project("U1",ResearchProjectCreate(company_profile=CompanyProfile(company_name="公司",industry="制造业")))
                save_valuation_assumptions("U1",project.project_id,ValuationAssumptions(wacc=.09,confirmed=True))
                saved=get_valuation_assumptions("U1",project.project_id)
                self.assertEqual(saved.wacc,.09);self.assertTrue(saved.confirmed)
            finally:
                if previous is None:os.environ.pop("DATABASE_URL",None)
                else:os.environ["DATABASE_URL"]=previous

if __name__=="__main__":unittest.main()
