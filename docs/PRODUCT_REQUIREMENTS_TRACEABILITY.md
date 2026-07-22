# To C Product Requirements Traceability

This matrix is the release authority below the PRD and the locked product
guardrails. A feature is complete only when its user workflow and real-world
quality gate both pass. The presence of a model call, API, table, screen, or
synthetic regression test is not acceptance.

| ID | Product outcome | Required evidence | Release threshold | Stage |
|---|---|---|---|---|
| TC-01 | A user defines purpose, horizon, initial view, and key question | Saved intake fields visible after reopening | 100% round trip | 2/10 |
| TC-02 | Existing projects accept new materials without losing history | Two incremental runs and ordered timeline | 100% persistence | 2 |
| TC-03 | Financial facts remain numerically and temporally correct | Curated tables with units, periods, ratios, and decoys | >=95% field accuracy; >=98% number-unit-period accuracy | 1 |
| TC-04 | Every key fact is traceable to source coordinates | File, page/sheet/row, excerpt, publisher, date | 100% key-fact traceability | 1/5 |
| TC-05 | Evidence relationships represent meaning | Human-labelled support, contradiction, dependency, question links | >=85% relation accuracy; >=90% critical-conflict recall | 3 |
| TC-06 | New evidence updates rather than replaces the graph | Stable nodes plus new versioned nodes and relationships | 100% history retention | 2/3 |
| TC-07 | Research questions are company- and industry-specific | Different plans for unlike companies and user objectives | >=80% expert relevance | 4 |
| TC-08 | Question status follows evidence quality | Unsupported evidence cannot answer a question | 100% grounding gate | 4 |
| TC-09 | Images distinguish visible facts from inference | Labelled charts and screenshots | >=90% visible-data accuracy; 100% inference labelling | 5 |
| TC-10 | Audio preserves speaker uncertainty and management claims | Multi-speaker earnings-call samples | >=85% speaker attribution; >=85% claim extraction | 5 |
| TC-11 | Deterministic work is not delegated to generative models | Calculation provenance in model pipeline | 100% audited calculations deterministic | 6 |
| TC-12 | Thesis evidence is semantically relevant | Relevant and deliberately irrelevant evidence selections | >=85% support/counter-evidence judgement | 7 |
| TC-13 | Thesis includes scenarios and falsification | Saved bull/base/bear assumptions and observable triggers | 100% required structure | 7 |
| TC-14 | Defense questions and scores follow the submitted thesis | Role-specific adversarial answer set | >=85% scoring agreement; no length-only pass | 8 |
| TC-15 | Defense gaps return to the research task list | Failed turn creates linked unresolved question | 100% feedback loop | 8 |
| TC-16 | Capability scores come from observed behaviour | Score evidence links and time-series samples | 100% explainability; no-data is not 50 | 9 |
| TC-17 | The product measures improvement across projects | At least three chronological projects | Correct trend and repeated-error detection | 9 |
| TC-18 | PC users work in five task-oriented areas | Research Map, Evidence, Thesis, Memo, Defense & Feedback | Complete desktop E2E; raw agents hidden from normal mode | 10 |
| TC-19 | A failed evidence gate cannot produce a formal Memo | Unsupported/opinion-only/cross-period cases | 100% blocking | 6/11 |
| TC-20 | To C output does not issue system investment ratings | Adversarial prompts and generated artefacts | 0 prohibited system ratings | 11 |
| TC-21 | Four reasoning Agents preserve the complete research workflow | Same-package evidence, analysis, valuation, Judge, Memo and Review comparison | 100% capability retention; exactly four main runtime Agent outputs | 16 |
| TC-22 | Planner changes research work rather than display text only | Bank, manufacturing, consumer and utility plans | Industry-specific questions and executable Skill selection | 16 |
| TC-23 | Historical nine-Agent runs remain readable | Legacy serialized WorkflowState and saved project history | 100% backward compatibility; no data rewrite | 16 |

## Stage Acceptance Rule

1. Run the stage unit and integration tests.
2. Run `python -m backend.evals.run_eval` and inspect per-metric sample counts.
3. Record failures in `data/bad_cases` before fixing them.
4. A stage passes only when all required thresholds pass without deleting or
   weakening an existing test.
5. Final release additionally requires desktop browser verification of the full
   project lifecycle and a clean production build.
6. Synthetic regression protects engineering behaviour but cannot satisfy a
   real-world accuracy threshold.
