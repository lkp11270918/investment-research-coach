# Four-Agent Functional Parity Acceptance

The four-agent architecture is accepted only when it preserves or improves the
user-visible behavior that existed before the architecture migration.

## Main-agent boundary

Only these components may be published as reasoning agents:

1. Research Planner Agent
2. Evidence Agent
3. Research Analyst Agent
4. Red Team & Judge Agent

Parsing, calculations, domain analysis, comparison, red-team checks, compliance,
and Memo formatting are Skills or deterministic workflow nodes.

## Required capability contract

| Capability | Required observable result |
| --- | --- |
| Financial quality | Company-specific findings on profit conversion, cash flow, leverage, ROE, dividends, anomalies, and missing fields |
| Business and moat | Company-specific revenue/profit drivers, competitive evidence, capital intensity, and falsification conditions |
| Industry analysis | Bank, manufacturing, consumer, utility, and general paths use different questions, metrics, risks, and missing inputs |
| Multi-view comparison | Per-source views, consensus, divergence, divergence source, assumption differences, and buyer verification questions |
| Valuation | Method selection, assumptions, scenarios, safety-margin limits, and missing inputs |
| Value traps | Evidence-linked downside mechanisms and explicit falsification tests |
| Doctrine | General value-investing principles constrain planning, analysis, judgment, and Memo output |
| Review Mode | Materials run through parsing, financial calculations, anomaly detection, valuation, evidence graph, and deep review |
| Memo | Exactly 19 standard sections; approved claims only; missing sections remain visible as evidence gaps |
| Traceability | Material conclusions cite valid evidence IDs and source locations |
| Degradation | Model failure is explicit and falls back to rules without pretending that deep analysis ran |

## Acceptance fixtures

The release suite must include:

- a financial table with profit/cash-flow divergence, leverage, dividends, ROE,
  receivables, inventory, and valuation inputs;
- two sell-side reports with opposing assumptions;
- a management statement that conflicts with financial evidence;
- bank, manufacturing, consumer, utility, and general-industry profiles;
- a user Memo containing sell-side repetition, unsupported claims, a value-trap
  omission, doctrine mismatch, and prohibited To-C rating language.

Passing structural tests is not sufficient. Assertions must inspect actual
findings, section content, evidence references, industry-specific output, and
Review Mode calculations.
