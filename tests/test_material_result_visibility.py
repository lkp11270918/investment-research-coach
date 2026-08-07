import unittest

from backend.models import CompanyProfile, RawMaterial, WorkflowState
from backend.research_judgment import build_research_judgment


class MaterialResultVisibilityTest(unittest.TestCase):
    def test_each_uploaded_material_has_a_visible_view_without_evidence(self) -> None:
        state = WorkflowState(
            company_profile=CompanyProfile(company_name="测试公司", industry=""),
            raw_materials=[
                RawMaterial(title="报告甲", content="我们认为新业务商业化将成为未来增长的核心驱动力，但其成立取决于客户付费率持续提升。"),
                RawMaterial(title="报告乙", content="核心观点是现有业务现金流依然稳定，预计费用投入会在短期压制利润率。"),
            ],
        )

        judgment = build_research_judgment(state)

        self.assertEqual([view.title for view in judgment.document_views], ["报告甲", "报告乙"])
        self.assertTrue(all(view.main_view for view in judgment.document_views))
        self.assertGreaterEqual(len(judgment.core_assumptions), 2)
        self.assertEqual(judgment.view_points, [])


if __name__ == "__main__":
    unittest.main()
