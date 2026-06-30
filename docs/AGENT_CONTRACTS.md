# Agent Contracts

All agents must use the shared schemas in `schemas/`.

Each agent must:

- Accept a structured input object.
- Return a structured output object.
- Preserve source references.
- Explicitly state uncertainty.
- Avoid inventing missing data.
- Separate facts, opinions, assumptions, and AI reasoning.

## 1. Firm Doctrine & Case Retrieval Agent

Purpose:

Retrieve and adapt the applicable institution doctrine, historical cases, templates, and internal rating rules.

Required for:

- To B mode.

Optional for:

- To C mode, using default doctrine only.

Inputs:

- Company profile
- Industry
- User mode
- Institution doctrine documents
- Historical good memos
- Historical failed cases
- Rating rules
- Committee question bank

Outputs:

- Applicable doctrine rules
- Similar cases
- Common institutional penalty items
- Memo template requirements
- Internal rating rules
- Key questions to emphasize

## 2. Material Organizer Agent

Purpose:

Classify and organize uploaded or pasted materials.

Inputs:

- Company profile
- Raw material list

Outputs:

- Source document inventory
- Material type classification
- Source reliability notes
- Coverage map by value investing dimension
- Missing material list

## 3. Evidence Extractor Agent

Purpose:

Extract key facts, financial data, views, risks, assumptions, and verification questions.

Inputs:

- Organized source documents
- Text chunks
- Company profile

Outputs:

- Evidence items
- Financial fields
- Fact list
- Opinion list
- Assumption list
- Risk list
- Verification questions

Rules:

- Facts require sources.
- Financial numbers preserve original units and periods.
- Missing data returns null.
- No fabricated data.

## 4. Financial Quality & Dividend Agent

Purpose:

Analyze cash flow quality, dividend sustainability, and balance sheet safety.

Inputs:

- Extracted evidence
- Financial fields
- Applicable doctrine

Outputs:

- Cash flow quality judgment
- Free cash flow quality judgment
- Dividend sustainability judgment
- Balance sheet safety judgment
- Financial quality penalty items
- Missing verification data

## 5. Business Model & Moat Agent

Purpose:

Analyze how the company makes money and whether the business is understandable, stable, and durable.

Inputs:

- Extracted evidence
- Company profile
- Applicable doctrine

Outputs:

- Revenue and profit source analysis
- Core operating variables
- Business model stability judgment
- Competitive advantage or moat judgment
- Cycle and demand risk
- Circle-of-competence assessment

## 6. Management & View Comparison Agent

Purpose:

Compare management narrative, sell-side views, news or market views, user notes, and financial reality.

Inputs:

- Extracted evidence
- Financial analysis output
- Business model output

Outputs:

- Consensus
- Disagreements
- Minority views
- Key assumption differences
- Management credibility observations
- Questions to ask management or verify later

## 7. Value Trap & Contradiction Agent

Purpose:

Actively search for evidence that could weaken or overturn the current thesis.

Inputs:

- Extracted evidence
- Financial analysis output
- Business model output
- View comparison output
- Applicable doctrine

Outputs:

- Value trap signals
- Counter-evidence risks
- One-vote veto variables
- Required verification questions
- Reasons to downgrade confidence

## 8. Evidence & Compliance Gate Agent

Purpose:

Check evidence quality, unsupported claims, over-reasoning, compliance risk, and output mode restrictions.

Run positions:

- Pre-Memo Gate
- Post-Memo Gate

Inputs:

- Current workflow state
- User mode
- Draft memo, for Post-Memo Gate

Outputs:

- Pass or fail status
- Unsupported claims
- Evidence issues
- Downgraded claims
- Compliance warnings
- Rewrite suggestions

## 9. Research Memo Generator Agent

Purpose:

Generate a structured buy-side research memo from the workflow state.

Inputs:

- Company profile
- Doctrine output
- Organized materials
- Evidence output
- Analysis outputs
- Pre-Memo Gate result
- User mode

Outputs:

- Memo markdown
- Section-level source references
- Confidence statement
- Missing material section
- Disclaimer

## Independent Mode: Research Coach Review Mode

Purpose:

Critique a user-written memo against the doctrine, evidence discipline, and institution memo standard.

Inputs:

- User-written memo
- Company profile, when provided
- Supporting materials, when provided
- Applicable doctrine

Outputs:

- Missing evidence critique
- Sell-side repetition critique
- Fact/opinion/assumption confusion critique
- Value trap omission critique
- Compliance risk critique
- Suggested rewrite directions
- Training feedback scorecard
