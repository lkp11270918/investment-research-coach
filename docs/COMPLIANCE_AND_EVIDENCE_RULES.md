# Compliance and Evidence Rules

These rules apply to all agents and all user modes.

## Evidence Classification

Every important statement must be classified as one of:

- Fact
- Financial fact
- Management opinion
- Sell-side opinion
- News or market opinion
- User opinion
- Assumption
- AI reasoning
- Risk
- Verification question

## Source Requirements

Facts and financial facts require source references.

Each source reference should include:

- Source ID
- Source document name
- Original excerpt when available
- Page, paragraph, row, or location when available
- URL when provided

If a source is missing:

- Do not present the statement as a verified fact.
- Move it to "to be verified" or mark it as unsupported.

## Missing Data Rules

Missing data must be represented as:

- `null`
- `not provided`
- `to be verified`
- `current materials are insufficient to judge`

The system must not fill missing data from memory or guesswork.

## Required Downgrade Language

Use downgrade language when evidence is incomplete:

- "当前资料不足以判断..."
- "该结论仅为待验证假设..."
- "需要进一步补充..."
- "暂不支持高置信研究观点标签..."
- "Based on current materials, this remains a low-confidence inference..."

## To C Compliance Rules

To C mode must not output:

- Buy
- Sell
- Overweight
- Underweight
- Increase
- Reduce
- Clear trading instructions
- Return promises
- Deterministic price predictions

Allowed To C labels:

- 积极关注
- 中性观察
- 谨慎观察
- 资料不足暂不评级
- 待补充资料后再判断

These labels must be framed as research learning labels, not investment recommendations.

## To B Compliance Rules

To B mode may use institution-defined internal labels only if:

- The user is in To B mode.
- The label is clearly marked as internal research view.
- The report states that it is not public investment advice, a trading instruction, or a return guarantee.

## Forbidden Expressions

Do not output:

- 必涨
- 一定上涨
- 严重低估必修复
- 无风险
- 稳赚
- 确定性收益
- 建议立即买入
- 建议立即卖出
- Guaranteed return
- Must rise
- Risk-free

## Paid Research Copyright Rule

The system must not:

- Crawl unauthorized paid research reports.
- Reconstruct full paid reports from excerpts.
- Present paid research content as system-owned content.

The system may:

- Analyze user-provided lawful summaries.
- Cite that a view came from a sell-side summary.
- Flag uncertain or unauthorized source status.

## Gate Failure Conditions

The gate should fail when:

- The memo contains unsupported key facts.
- The memo presents assumptions as facts.
- To C mode contains deterministic ratings.
- The memo contains trading instructions.
- The memo promises returns.
- Value trap checks are absent.
- Financial claims have no source and are central to the conclusion.
- The conclusion ignores material contradictory evidence.
