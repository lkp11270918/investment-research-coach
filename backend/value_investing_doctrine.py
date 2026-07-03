from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctrinePrinciple:
    name: str
    requirement: str
    failure_pattern: str


GENERAL_VALUE_INVESTING_DOCTRINE: tuple[DoctrinePrinciple, ...] = (
    DoctrinePrinciple(
        "安全边际",
        "必须先讨论内在价值、估值假设和价格中隐含的预期；低估值本身不是安全边际。",
        "把低 PE、低 PB 或股价下跌直接当成便宜。",
    ),
    DoctrinePrinciple(
        "能力圈",
        "必须说明研究者是否真正理解公司如何赚钱、核心经营变量和行业约束；看不懂时应降级结论。",
        "只因为行业热门、公司知名或卖方覆盖充分就提高置信度。",
    ),
    DoctrinePrinciple(
        "现金流质量",
        "必须检查利润是否能转化为经营现金流，并关注自由现金流和维持性资本开支。",
        "只看净利润增长，不看现金流和资本开支。",
    ),
    DoctrinePrinciple(
        "Owner Earnings",
        "必须关注扣除维持竞争地位所需投入后的股东真实可得现金创造能力。",
        "把会计利润、 EBITDA 或未扣资本开支的现金流当成股东真实收益。",
    ),
    DoctrinePrinciple(
        "分红可持续性",
        "必须验证分红是否由自由现金流覆盖，是否依赖借债、一次性收益或消耗历史现金。",
        "把高股息率直接等同于安全或低风险。",
    ),
    DoctrinePrinciple(
        "资产负债表安全",
        "必须检查资产负债率、有息负债、短债压力、利息覆盖和再融资风险。",
        "只看盈利，不看杠杆、期限错配和偿债压力。",
    ),
    DoctrinePrinciple(
        "ROE 质量",
        "必须区分 ROE 来自经营效率、利润率、周转率还是高杠杆，并检查非经常性损益影响。",
        "把高 ROE 直接当成优秀公司，而不拆来源。",
    ),
    DoctrinePrinciple(
        "护城河",
        "必须用证据验证品牌、成本优势、网络效应、转换成本、规模经济、牌照或渠道优势。",
        "把龙头、市占率高、管理层愿景或行业空间直接当作护城河。",
    ),
    DoctrinePrinciple(
        "管理层资本配置",
        "必须检查管理层在分红、回购、并购、扩产、举债和再投资上的长期理性。",
        "只引用管理层表态，不检查资本配置结果。",
    ),
    DoctrinePrinciple(
        "价值陷阱与反证",
        "必须主动寻找低估值背后的基本面恶化、周期下行、现金流背离、应收存货恶化和治理风险。",
        "只寻找支持买入/乐观的证据，不写反方问题。",
    ),
    DoctrinePrinciple(
        "市场预期与二阶思维",
        "必须说明市场已经反映了什么、研究者和市场的分歧在哪里，以及分歧如何被验证。",
        "只说公司好，不讨论当前价格是否已经反映这些好处。",
    ),
    DoctrinePrinciple(
        "本金保护与机会成本",
        "必须优先避免永久性资本损失，并比较风险收益与其他机会的吸引力。",
        "只讨论上涨空间，不讨论下行风险、等待成本和替代机会。",
    ),
)


def doctrine_text() -> str:
    lines = ["通用价值投资 Doctrine："]
    for index, principle in enumerate(GENERAL_VALUE_INVESTING_DOCTRINE, start=1):
        lines.append(
            f"{index}. {principle.name}：{principle.requirement} 常见错误：{principle.failure_pattern}"
        )
    return "\n".join(lines)


def doctrine_findings() -> list[tuple[str, str]]:
    return [(principle.name, principle.requirement) for principle in GENERAL_VALUE_INVESTING_DOCTRINE]


def doctrine_missing_materials() -> list[str]:
    return [
        "内在价值与估值假设材料",
        "能力圈与核心经营变量说明",
        "自由现金流与资本开支数据",
        "分红覆盖能力数据",
        "资产负债表与有息负债明细",
        "ROE 拆解与非经常性损益",
        "护城河证据",
        "管理层资本配置记录",
        "反方材料与价值陷阱检查",
        "市场预期与估值敏感性分析",
    ]
