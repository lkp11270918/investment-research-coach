# Four-Agent Research Architecture

## Design rule

A component is an Agent only when it owns an independent objective, context,
tool policy, evaluation target, and failure decision. Stable parsing,
calculation, analysis rubrics, graph writes, and formatting are Skills or
deterministic functions.

## Runtime agents

1. `research_planner`: selects company-specific questions and required Skills.
2. `evidence`: organizes multimodal material and builds traceable evidence.
3. `research_analyst`: runs approved analysis Skills and reconciles their output.
4. `red_team_judge`: tests counter-evidence and controls the semantic quality gate.

The deterministic orchestrator owns ordering, parallel execution, stop states,
retries, validation, persistence, and hard compliance gates. Memo generation is
the `memo_writing` Skill and cannot run before Judge approval.

## Skill migration

| Historical Agent | New owner |
|---|---|
| Firm Doctrine & Case Retrieval | Planner context Skill |
| Material Organizer | Evidence material-organization Skill |
| Evidence Extractor | Evidence extraction capability |
| Financial Quality & Dividend | Analyst Skill |
| Business Model & Moat | Analyst Skill |
| Management & View Comparison | Analyst Skill |
| Value Trap & Contradiction | Red Team Skill |
| Evidence & Compliance Gate | Judge plus deterministic hard gate |
| Research Memo Generator | Memo Writing Skill |

Historical runs retain their original `agent_outputs`. New runs publish only
the four runtime Agent keys and store specialist results in `skill_outputs`.
`WorkflowState.output_for()` reads both formats, so no account, project, Memo,
evidence, Thesis, defense, or capability history is rewritten.

## Behavioral release gate

The migration passes only when the same research package still produces:

- source documents, structured evidence, and an Evidence Graph;
- financial fields and deterministic calculations;
- financial, business-model, management/view, and valuation analysis;
- counter-evidence, value-trap review, and pre/post Memo gates;
- a gate-blocked or approved Memo with the same compliance behavior;
- Review Mode findings, project history, and historical-run readability.

Agent-key count alone is not acceptance. Industry-specific plans, missing-data
skip behavior, the complete research lifecycle, TypeScript validation, and the
production build must also pass.
