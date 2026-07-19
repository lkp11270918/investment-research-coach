# Release Gates

The evaluation suite uses three levels of evidence:

- deterministic unit cases for parsing, normalization, gates, and persistence;
- curated product cases for semantic relationships, planning, Thesis, defense,
  and capability scoring;
- end-to-end desktop journeys for the complete research lifecycle.

Every metric reports a numerator, denominator, score, and threshold. A metric
with fewer than five cases is marked `insufficient_sample` and cannot be used as
final release evidence. Synthetic cases are useful regression tests but cannot
be presented as real-world model quality.

The final release gate requires:

- financial field accuracy >= 95%;
- number/unit/period accuracy >= 98%;
- key-fact source coverage = 100%;
- critical contradiction recall >= 90%;
- semantic evidence relation accuracy >= 85%;
- unsupported conclusion block rate = 100%;
- prohibited To C system rating rate = 0%;
- all project, Thesis, defense, and capability history remains user-isolated;
- desktop production build and browser journey pass.
- structured valuation scenarios match independently calculated values >= 95%;
- critical financial anomaly recall >= 90%;
- multimodal metric-period-unit cross-check accuracy >= 95%;
- capability-profile dimension agreement with expert reviewers >= 85%.

## 2026-07-20 Engineering Acceptance Record

- PRD traceability: TC-01 through TC-20 have an engineering implementation or
  interface. This does not prove real-world model quality.
- Automated regression: 55 tests passed.
- Synthetic regression suite: 10 metrics passed; 5 cases per metric; no
  provisional metrics. These cases are not release-quality evidence.
- API contract: Python compilation passed and 39 application routes generated.
- Lifecycle: account, project, materials, analysis, graph, map, Thesis, defense,
  task feedback, and capability profile passed in an isolated database.
- Frontend: TypeScript check and Next.js production build passed.
- Desktop journey: landing entry and all five research areas passed at a PC
  viewport; no visible overlap or text overflow was found.

The product remains an enhanced MVP until the real-world corpus gate passes.
Synthetic scores must never be reported as production accuracy.

## Current Real-World Results

- Official filing financial extraction: 24 independently sourced facts across
  technology, banking, pharmaceuticals, retail, and energy; 100% passed against
  SEC filing values. This result applies only to the tested financial fields.
- The release-readiness command intentionally returns blocked because fifteen
  product-quality metrics still lack their required manually labelled real cases.
- The target-user comparison is also blocked until at least ten real interns or
  junior researchers complete both the generic-agent and Research Coach tasks.
- The empty pilot file is a collection template, not evidence of user value.

## Real-World Corpus Gate

Each quality metric requires at least 20 independently labelled examples from
real public or user-authorized research materials. Every case must record its
source, publication date, industry, modality, annotator decision, and usage
rights. Model output must be scored without changing the gold label.

Release is blocked when any of the following is true:

- fewer than 20 real examples exist for a claimed metric;
- only synthetic or prompt-authored examples support the score;
- source provenance or usage rights are missing;
- an evaluator uses the same model output as its gold answer;
- image, audio, or semantic-relation quality has not been manually reviewed.

Run before each release:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m backend.evals.run_eval
.venv/bin/python -m backend.evals.run_sec_financial_eval
.venv/bin/python -m backend.evals.release_readiness
cd frontend && npx tsc --noEmit && npm run build
```

Only `backend.evals.release_readiness` determines production readiness. A
successful synthetic regression run does not override a failed real-world gate.
