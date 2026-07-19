# To C Backend Execution Roadmap

This file is a persistent execution constraint. It supplements, and never
overrides, `PROJECT_PRD_GUARDRAILS.md`.

## Scope Constraint

- Implement backend data models, storage, agents, APIs, and automated evaluation.
- Do not change the frontend during this roadmap.
- Preserve the existing nine-agent PRD workflow. Strengthen existing agents
  before considering any additional agent.
- A stage may start only after the previous stage passes its automated acceptance
  tests.

## Locked Stage Order

1. Research project data foundation
2. Multimodal material normalization
3. Evidence Graph
4. Research Map
5. Thesis Builder
6. Dynamic evidence gate and red team
7. AI investment committee defense
8. Personal research capability profile
9. Benchmark and release acceptance

## Stage Gates

Each stage must provide:

- persisted and user-isolated data where applicable;
- typed API contracts;
- backward compatibility for existing analysis and review endpoints;
- deterministic tests for rules and storage;
- model-independent fallback behavior;
- PRD compliance checks, including evidence traceability and no deterministic
  To C investment rating.

The implementation status and acceptance evidence for every stage must be
recorded in `docs/TO_C_STAGE_ACCEPTANCE.md`.
