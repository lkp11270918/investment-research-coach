from backend.models import RawMaterial, SourceType


def parity_materials() -> list[RawMaterial]:
    return [
        RawMaterial(
            title="2024-2025财务表",
            source_type=SourceType.FINANCIAL_TABLE,
            content=(
                "指标 | 2024年 | 2025年\n"
                "营业收入 | 100亿元 | 110亿元\n"
                "净利润 | 10亿元 | 12亿元\n"
                "经营现金流 | 9亿元 | 5亿元\n"
                "自由现金流 | 6亿元 | 2亿元\n"
                "分红 | 3亿元 | 4亿元\n"
                "资本开支 | 3亿元 | 6亿元\n"
                "资产负债率 | 45% | 62%\n"
                "有息负债 | 30亿元 | 65亿元\n"
                "短期有息负债 | 8亿元 | 28亿元\n"
                "利息费用 | 1亿元 | 3亿元\n"
                "总资产 | 120亿元 | 130亿元\n"
                "股东权益 | 60亿元 | 52亿元\n"
                "ROE | 16.7% | 23.1%\n"
                "非经常性损益 | 0.5亿元 | 4亿元\n"
                "应收账款 | 20亿元 | 42亿元\n"
                "存货 | 25亿元 | 48亿元\n"
                "每股收益 | 1元 | 1.2元\n"
                "股价 | 10元 | 10元\n"
                "可比公司PE | 9倍 | 12倍"
            ),
        ),
        RawMaterial(
            title="管理层交流",
            source_type=SourceType.MANAGEMENT_NOTE,
            content="管理层目标是新增产能后收入增长20%，并称现金流压力只是暂时现象。",
        ),
        RawMaterial(
            title="卖方乐观报告",
            source_type=SourceType.SELL_SIDE_SUMMARY,
            content="预计需求增长20%，产能利用率提升，净利率上升，给予12倍PE。",
        ),
        RawMaterial(
            title="卖方谨慎报告",
            source_type=SourceType.SELL_SIDE_SUMMARY,
            content="预计需求仅增长5%，产能过剩压低利用率和利润率，资本开支拖累自由现金流，采用8倍PE。",
        ),
        RawMaterial(
            title="行业材料",
            source_type=SourceType.INDUSTRY_MATERIAL,
            content="行业新增产能集中投放，价格竞争加剧，原材料价格波动扩大。",
        ),
    ]
