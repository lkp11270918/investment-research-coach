# Value Investing Research Coach PRD Guardrails

This document is the highest project rule for implementation.

All product, architecture, prompt, UI, backend, evaluation, and future roadmap decisions must preserve the intent of the PRD: build a value investing research training agent for junior buy-side research workflows, not a stock recommendation or market prediction tool.

## 1. Product Identity

The product is a Value Investing Research Coach.

It helps users analyze a company research material package through a buy-side value investing framework. It trains evidence awareness, assumption discipline, contradiction checking, value trap detection, and structured memo writing.

It is not:

- A stock recommendation tool.
- A short-term price prediction tool.
- A trading signal generator.
- A public investment advice product.
- A generic financial document summarizer.
- A sell-side report rewriter.

Any feature that pushes the product toward these rejected identities must be redesigned or removed.

## 2. Non-Negotiable Principles

The system must always:

- Distinguish fact, opinion, assumption, and AI reasoning.
- Bind key facts to sources whenever possible.
- Mark unsupported claims as unsupported or move them to "to be verified".
- Downgrade confidence when materials are insufficient.
- Check for value traps and contradictory evidence.
- Treat sell-side views as inputs, not conclusions.
- Include uncertainty, missing materials, and follow-up questions.
- Include a non-investment-advice statement in generated reports.

The system must never:

- Give deterministic buy or sell instructions to public users.
- Promise returns.
- Use language such as "must rise", "surely undervalued", or "guaranteed recovery".
- Treat high dividends as automatically safe.
- Treat low valuation as automatically a margin of safety.
- Force high-confidence conclusions when evidence is weak.
- Fabricate missing financial figures.
- Copy or reconstruct unauthorized paid research reports.

## 3. V1 Scope

V1 is a material-package-driven research workflow.

V1 supports:

- Company code, company name, and industry input.
- User-uploaded or pasted research materials.
- Financial tables, annual report summaries, announcement excerpts, management notes, sell-side summaries, news summaries, and user notes.
- Evidence extraction.
- Value investing analysis.
- Value trap and contradiction checks.
- Structured buy-side research memo generation.
- Missing material, counter-evidence, and verification question output.
- Research Coach Review Mode for user-written memo critique.

V1 does not support:

- Fully automatic public web research.
- Automatic crawling of all announcements or webpages.
- Commercial database integrations such as Wind, Bloomberg, or Choice.
- Unauthorized paid report ingestion.
- Automatic stock pools.
- Stock selection.
- Trading.
- Short-term price prediction.
- Public deterministic investment ratings.

## 4. Required Agent Workflow

The main workflow is a DAG, not a single summary prompt.

Required main agents:

1. Firm Doctrine & Case Retrieval Agent
2. Material Organizer Agent
3. Evidence Extractor Agent
4. Financial Quality & Dividend Agent
5. Business Model & Moat Agent
6. Management & View Comparison Agent
7. Value Trap & Contradiction Agent
8. Evidence & Compliance Gate Agent
9. Research Memo Generator Agent

Required independent mode:

- Research Coach Review Mode

The Evidence & Compliance Gate must run at least twice:

- Pre-Memo Gate before memo generation.
- Post-Memo Gate after memo generation.

## 5. Evidence Rules

Every key fact should carry:

- `source_id`
- source document name
- original excerpt when available
- page, paragraph, row, or location when available
- URL when provided by the user

Missing data must be represented as `null`, "not provided", or "to be verified". The system must not invent missing values.

Generated analysis must classify content into:

- Facts
- Management opinions
- Sell-side opinions
- User opinions
- Assumptions
- AI reasoning
- Verification questions

## 6. Value Investing Doctrine

The default doctrine prefers:

- Stable operating cash flow.
- High-quality free cash flow.
- Dividends supported by free cash flow.
- Safe balance sheets.
- Understandable and stable business models.
- Clear profit sources.
- Rational management capital allocation.
- Valuation with a real margin of safety.

The default doctrine penalizes:

- Net profit growth with worsening operating cash flow.
- High dividends not covered by free cash flow.
- ROE driven mainly by leverage.
- Profit reliance on non-recurring gains.
- Dividends funded by historical cash rather than current operations.
- Management narratives unsupported by execution or financial reality.
- Heavy capex that persistently consumes free cash flow.
- Long-term demand decline.
- Worsening receivables or inventory.
- Low valuation caused by business deterioration.

## 7. Output Requirements

The final memo must include:

- Material scope and conclusion confidence.
- Company basic information.
- Applicable research doctrine.
- Circle-of-competence assessment.
- How the company makes money.
- Cash flow quality.
- Dividend quality and sustainability.
- Balance sheet safety.
- Business model stability and moat.
- Management capital allocation.
- Management narrative versus financial reality.
- Sell-side consensus and disagreements.
- Valuation and margin of safety.
- Value trap and counter-evidence risks.
- Verification questions.
- Research view or internal research label where allowed.
- Uncertainty and missing materials.
- Source list.
- Non-investment-advice disclaimer.

For To C mode, default output must not include buy, sell, overweight, underweight, or equivalent public investment ratings.

For To B mode, internal ratings are allowed only when explicitly marked as internal research labels, not public investment advice or trading instructions.

## 8. UI Requirements

The default user view should prioritize:

- Final memo.
- Core view summary.
- Key evidence.
- Counter-evidence risks.
- Missing materials.
- Evidence quality warnings.
- Download action.

Expandable views should expose:

- Cash flow quality analysis.
- Dividend sustainability analysis.
- Business model analysis.
- Management capital allocation analysis.
- Sell-side consensus and disagreement.
- Value trap checks.
- Evidence verification results.

Enterprise/admin views may expose:

- Raw agent outputs.
- Retrieved institutional cases.
- Referenced doctrine.
- Downgraded claims.
- Bad cases.
- Common junior researcher errors.
- Usage records.
- Template usage.

## 9. Evaluation Targets

Implementation quality must be judged against PRD metrics, especially:

- Memo usability.
- Source annotation completeness.
- Unsupported key fact rate.
- Major financial field error rate.
- Opinion misreading rate.
- Over-reasoning rate.
- Value investing framework coverage.
- Fact/opinion/assumption/reasoning separation accuracy.
- Sell-side view repetition rate.
- Value trap check coverage.
- Compliance risk rate.

Bad cases must be recorded for:

- Missing financial fields.
- Conflicting financial fields.
- Missing sources.
- Opinion misreading.
- Sell-side view repetition.
- High-dividend safety misjudgment.
- Low-valuation margin-of-safety misjudgment.
- Missed value traps.
- Over-reasoning.
- Compliance expression risk.

## 10. Development Rule

Before adding or changing a feature, check it against this document.

If a decision conflicts with this document, follow the PRD guardrails unless the user explicitly updates the PRD.

If future implementation details are ambiguous, choose the option that best preserves:

- Evidence traceability.
- Value investing discipline.
- Buy-side research training.
- Compliance safety.
- Material-package-driven V1 scope.
- Separation between facts, opinions, assumptions, and reasoning.
