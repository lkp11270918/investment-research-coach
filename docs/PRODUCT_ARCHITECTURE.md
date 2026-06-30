# Product Architecture

## Product Definition

Value Investing Research Coach is a material-package-driven buy-side research training agent.

It helps junior researchers convert company materials into evidence-backed value investing analysis, counter-evidence checks, and structured research memos.

It is not a stock recommendation, trading, or short-term price prediction product.

## User Modes

### To C / Student Mode

Default public-facing mode.

Allowed outputs:

- Verified facts
- Management views
- Sell-side views
- AI reasoning
- Core variables
- Counter-evidence risks
- Verification questions
- Missing materials
- Research view summary

Disallowed outputs:

- Buy, sell, overweight, underweight, increase, reduce, or equivalent deterministic investment ratings
- Trading instructions
- Return promises

### To B / Enterprise Internal Mode

Institutional internal research mode.

Allowed outputs:

- Internal research labels
- Institution-specific rating labels
- Institution-specific memo templates
- Institution-specific doctrine and case retrieval

Required disclaimer:

Internal labels are internal research views only. They are not public investment advice, trading instructions, or return guarantees.

## System Layers

### 1. Input Layer

Accepts:

- Company code
- Company name
- Industry
- Output mode
- Financial tables
- Annual report summaries
- Announcement excerpts
- Management meeting notes
- Sell-side summary notes
- News and industry summaries
- User research notes
- Institution doctrine and historical cases, for To B

### 2. Material Layer

Normalizes user materials into source documents and text chunks.

Each source and chunk must be traceable.

### 3. Evidence Layer

Extracts and classifies information into:

- Facts
- Management opinions
- Sell-side opinions
- News or market opinions
- User opinions
- Assumptions
- AI reasoning
- Risks
- Verification questions

### 4. Analysis Layer

Runs value investing analysis across:

- Financial quality and dividend sustainability
- Business model and moat
- Management and view comparison
- Value trap and contradiction checks

### 5. Gate Layer

Runs evidence and compliance checks:

- Pre-Memo Gate
- Post-Memo Gate

### 6. Output Layer

Generates:

- Final research memo
- Evidence table
- Counter-evidence risk list
- Missing material list
- Compliance warnings
- Markdown download

## Main Workflow Agents

1. Firm Doctrine & Case Retrieval Agent
2. Material Organizer Agent
3. Evidence Extractor Agent
4. Financial Quality & Dividend Agent
5. Business Model & Moat Agent
6. Management & View Comparison Agent
7. Value Trap & Contradiction Agent
8. Evidence & Compliance Gate Agent
9. Research Memo Generator Agent

Independent mode:

- Research Coach Review Mode

## Implementation Bias

When in doubt, prefer:

- Lower confidence over unsupported confidence.
- Structured evidence over fluent prose.
- Missing data disclosure over fabricated completion.
- Buy-side reasoning over sell-side repetition.
- Training feedback over final-answer authority.
