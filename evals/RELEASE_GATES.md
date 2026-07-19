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

## 2026-07-20 Acceptance Record

- PRD traceability: TC-01 through TC-20 implemented and covered by product or
  regression acceptance.
- Automated regression: 25 tests passed.
- Evaluation suite: 10 metrics passed; 5 cases per metric; no provisional
  metrics.
- API contract: Python compilation passed and 22 OpenAPI routes generated.
- Lifecycle: account, project, materials, analysis, graph, map, Thesis, defense,
  task feedback, and capability profile passed in an isolated database.
- Frontend: TypeScript check and Next.js production build passed.
- Desktop journey: landing entry and all five research areas passed at a PC
  viewport; no visible overlap or text overflow was found.

Run before each release:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m backend.evals.run_eval
cd frontend && npx tsc --noEmit && npm run build
```
