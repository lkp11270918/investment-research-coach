import unittest
from types import SimpleNamespace
from backend.evidence_relations import infer_semantic_edges_nli
from backend.file_parsers import cross_check_multimodal_materials
from backend.financial_parser import extract_structured_financial_evidence
from backend.models import ContentBlock, EvidenceGraphNode, MaterialModality, RawMaterial, SourceDocument, SourceType
from backend.valuation import analyze_valuation

class PipelineClient:
    available=True
    settings=SimpleNamespace(openai_embedding_model="embed",openai_small_model="reranker",openai_nli_model="nli")
    def __init__(self): self.prompts=[]
    def embed(self,texts,**kwargs): return [[1.0,index/100] for index,_ in enumerate(texts)],1
    def generate_json(self,**kwargs):
        prompt=kwargs.get("system_prompt",""); self.prompts.append(prompt)
        if "重排器" in prompt: return {"ranking":[{"index":0,"score":99}]}
        return {"relations":[{"index":0,"relation":"supports","confidence":"high","rationale":"直接支持"}]}

class ProductionWiringTest(unittest.TestCase):
    def test_embedding_candidates_really_pass_through_reranker_before_nli(self):
        client=PipelineClient(); nodes=[EvidenceGraphNode(node_id="a",node_type="fact",label="经营现金流稳定"),EvidenceGraphNode(node_id="b",node_type="fact",label="现金流覆盖分红")]
        edges=infer_semantic_edges_nli(nodes,client)
        self.assertTrue(any("重排器" in prompt for prompt in client.prompts))
        self.assertTrue(any("NLI" in prompt for prompt in client.prompts))
        self.assertEqual(edges[0].relation_source,"nli_model")

    def test_real_parser_inputs_can_reach_three_scenario_valuation(self):
        doc=SourceDocument(title="估值表",source_type=SourceType.FINANCIAL_TABLE,content="指标 | 2025年\n股价 | 10\n每股收益 | 1\n企业自由现金流 | 100亿元\n总股本 | 10亿股\n有息负债 | 20亿元\n货币资金 | 5亿元")
        evidence=extract_structured_financial_evidence([doc])
        result=analyze_valuation(evidence)
        self.assertEqual(result.status,"draft")
        self.assertEqual(len(result.scenarios),3)

    def test_multimodal_check_matches_metric_period_unit_not_number_only(self):
        table=RawMaterial(title="表",content="2025年 营业收入 100亿元",modality=MaterialModality.TABLE)
        block=ContentBlock(modality=MaterialModality.IMAGE,content="2025年 营业收入 100亿元",extraction_method="vision_visible_data")
        image=RawMaterial(title="图",content="图",modality=MaterialModality.IMAGE,blocks=[block])
        cross_check_multimodal_materials([table,image])
        self.assertEqual(block.cross_check_status,"matched")
        self.assertTrue(block.cross_check_matches)

if __name__=="__main__": unittest.main()
