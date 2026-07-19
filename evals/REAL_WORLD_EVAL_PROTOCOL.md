# Real-World Evaluation Protocol

## Purpose

This protocol prevents engineering regressions from being mistaken for product
quality. Real-world scores use public or user-authorized investment research
materials and independently prepared gold labels.

## Corpus Requirements

- At least five industries and five companies.
- At least 20 labelled examples for every claimed metric.
- Annual reports, announcements, financial workbooks, sell-side summaries,
  charts or screenshots, and earnings-call audio must be represented.
- Every item records source URL or file identity, publisher, publication date,
  usage rights, modality, and SHA-256 digest.
- Gold labels are written before inspecting the system output.

## Evaluation Splits

- `development`: visible during implementation.
- `validation`: used for stage acceptance.
- `holdout`: never used to tune prompts, rules, or thresholds.

No source document may appear in more than one split.

## Required Metrics

1. Financial field, value, unit, and period accuracy.
2. Key-fact source-coordinate completeness.
3. Evidence support, contradiction, dependency, and irrelevance judgement.
4. Research-question relevance and evidence grounding.
5. Image-visible data accuracy and inference labelling.
6. Audio speaker attribution and management-claim extraction.
7. Unsupported conclusion blocking and prohibited-rating rate.
8. Defense scoring agreement with human reviewers.

## Release Decision

The real-world gate fails when the corpus is undersized, provenance is missing,
or any required metric misses its threshold. Synthetic regression results are
reported separately and never fill a missing real-world denominator.
