# Public Benchmark Adapters

The product benchmark is split into two layers.

## Runnable PRD Regression Suite

Run:

```bash
python -m backend.evals.run_eval
```

This is the release gate for product-specific requirements such as evidence
traceability, opinion separation, sell-side repetition, contradiction detection,
value-trap coverage, and To C compliance.

## External Dataset Mapping

- FinanceBench: financial document question answering and source-grounded answers.
- FinQA: numerical reasoning over financial reports.
- TAT-QA: hybrid table and text reasoning.
- ConvFinQA: multi-turn financial numerical reasoning.
- FinEval: Chinese financial knowledge and reasoning.

External datasets are not bundled into this repository. Their licenses and source
versions must be recorded before importing them. Imported examples must be adapted
to the local evaluation contract without weakening source traceability or To C
compliance requirements. Public benchmark scores supplement the PRD suite; they do
not replace it.
