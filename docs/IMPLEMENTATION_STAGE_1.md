# Stage 1 Implementation Foundation

This stage establishes the shared protocol for the multi-agent system.

The goal is not to optimize any single agent yet. The goal is to make every future agent obey the same project meaning, data structures, evidence rules, compliance boundaries, and memo output standard.

## Stage 1 Deliverables

1. Shared data schemas
2. Agent input/output contracts
3. Workflow DAG definition
4. Value investing doctrine
5. Evidence and compliance rules
6. Memo output template
7. Evaluation and bad case taxonomy

## Why This Stage Comes First

The PRD defines a multi-agent architecture, but the product will fail if the agents use inconsistent language or incompatible structures.

The shared protocol prevents:

- A financial analysis agent inventing numbers.
- A memo generator turning assumptions into facts.
- A view comparison agent treating sell-side views as conclusions.
- A value trap agent being skipped because earlier modules sound confident.
- A To C output accidentally becoming investment advice.
- Each agent producing a different memo style.

## Non-Negotiable Shared Concepts

All implementation must preserve these concepts:

- Material package driven input.
- Source traceability.
- Fact, opinion, assumption, and AI reasoning separation.
- Value investing doctrine.
- Counter-evidence and value trap checks.
- Confidence downgrading when evidence is insufficient.
- Compliance review before and after memo generation.
- To C and To B output mode separation.

## Directory Map

- `docs/`
  Product, architecture, doctrine, workflow, and implementation documents.

- `schemas/`
  JSON Schemas for shared objects and agent outputs.

- `prompts/`
  Prompt contracts and later agent-specific prompts.

- `workflow/`
  DAG and orchestration definitions.

- `evals/`
  Evaluation criteria, bad case taxonomy, and test cases.

- `data/uploads/`
  Local uploaded materials during development.

- `data/runs/`
  Local run outputs during development.

- `data/bad_cases/`
  Bad case records produced by tests and user feedback.

## Stage 1 Exit Criteria

Stage 1 is complete when:

- Every agent has a named role and input/output contract.
- Evidence objects have a canonical structure.
- Source references have a canonical structure.
- The memo has a canonical section order.
- Compliance gates have explicit pass/fail criteria.
- To C and To B output restrictions are explicit.
- Future contributors can implement an agent without reinterpreting the PRD.
