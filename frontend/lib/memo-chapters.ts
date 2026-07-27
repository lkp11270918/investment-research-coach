export const MEMO_CHAPTERS = [
  ['company_info', '公司基本信息'],
  ['scope_doctrine_confidence', '资料范围、研究准则适用性与结论置信度'],
  ['circle_of_competence', '能力圈判断'],
  ['business_model', '商业模式：公司靠什么赚钱'],
  ['key_variables', '核心经营变量'],
  ['financial_earnings_quality', '财务质量与盈利质量'],
  ['cash_flow', '现金流质量'],
  ['dividend', '分红质量与可持续性'],
  ['balance_sheet', '资产负债表安全性'],
  ['business_stability_moat', '商业模式稳定性、护城河与竞争优势'],
  ['industry_competition', '行业与竞争格局'],
  ['management_capital_allocation', '管理层资本配置'],
  ['narrative_vs_financials', '管理层叙事与财务现实'],
  ['sell_side_consensus_divergence', '卖方共识、核心分歧与分歧来源'],
  ['valuation_margin', '估值与安全边际'],
  ['value_trap', '价值陷阱与反证风险'],
  ['verification_questions', '待验证问题'],
  ['research_view_uncertainty', '研究观点、内部研究标签、不确定性与资料缺口'],
  ['sources_disclaimer', '来源列表与不构成投资建议声明'],
] as const

export type MemoChapterId = typeof MEMO_CHAPTERS[number][0]
export const MEMO_CHAPTER_TITLES = Object.fromEntries(MEMO_CHAPTERS) as Record<MemoChapterId, string>
