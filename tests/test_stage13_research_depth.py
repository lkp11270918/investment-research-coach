import unittest
from backend.models import EvidenceCategory, EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode, EvidenceItem, EvidenceRelation, VerificationStatus
from backend.valuation import analyze_valuation
from backend.research_quality import assess_graph_quality, detect_financial_anomalies

def ev(metric,value,period="2025"):
    return EvidenceItem(category=EvidenceCategory.FINANCIAL_FACT,statement=metric,metric_name=metric,metric_value=value,period=period,verification_status=VerificationStatus.VERIFIED)

class ResearchDepthTest(unittest.TestCase):
    def test_structured_valuation_has_three_scenarios_and_margin(self):
        result=analyze_valuation([ev("share_price",10),ev("eps",1),ev("free_cash_flow",100),ev("shares_outstanding",10)])
        self.assertEqual(result.status,"completed")
        self.assertEqual(result.multiples["pe"],10)
        self.assertEqual({x.name for x in result.scenarios},{"bear","base","bull"})
        self.assertTrue(all(x.margin_of_safety_percent is not None for x in result.scenarios))

    def test_financial_anomalies_are_actionable(self):
        findings=detect_financial_anomalies([ev("net_profit",100),ev("operating_cash_flow",40),ev("revenue",100),ev("accounts_receivable",50)])
        self.assertEqual({x.anomaly_type for x in findings},{"cash_profit_divergence","receivable_pressure"})
        self.assertTrue(all(x.verification_question for x in findings))

    def test_graph_quality_penalizes_missing_traceability_and_relations(self):
        graph=EvidenceGraph(nodes=[EvidenceGraphNode(node_id="n1",node_type="fact",label="x",evidence_id="e1",verification_status=VerificationStatus.TO_BE_VERIFIED)])
        quality=assess_graph_quality(graph)
        self.assertLess(quality.score,50)
        self.assertGreaterEqual(len(quality.issues),2)

if __name__ == "__main__": unittest.main()
