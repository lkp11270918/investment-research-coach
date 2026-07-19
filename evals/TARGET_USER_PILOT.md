# Target User Comparative Pilot

## Design

Recruit at least ten investment-research interns or junior analysts. Each user
completes matched company cases under both conditions in counterbalanced order:

1. a general-purpose agent with file access;
2. Research Coach with the evidence-driven training workflow.

Use difficulty-matched case pairs and the same time limit. Counterbalance which
condition is used first. Do not tell reviewers which condition produced a
report.

## Independent Review

Two experienced reviewers score report quality, factual support, source
traceability, counter-evidence quality, reasoning boundaries, and prohibited
ratings. Resolve reviewer disagreement before recording the gold score.

## Product Measures

- completion time;
- unsupported key facts;
- traceability rate;
- counter-evidence score;
- report quality;
- intention to return for a second company;
- ability to explain the final thesis without reading the generated report;
- whether the user resumed an existing workspace rather than starting over.

Record anonymized results in `evals/pilot_results.json`. Do not enter simulated
participants or model-generated reviewer scores.

Every row additionally records `case_pair_id`, condition order, completion,
blinding confirmation, and two independent reviewer IDs. Release requires at
least five-point report and explanation gains, ten-point traceability and
counter-evidence gains, fewer unsupported facts, no more than 25% additional
time, and report-quality improvement for at least 70% of paired users.
