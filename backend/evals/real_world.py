from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_METADATA = {
    "case_id",
    "split",
    "metric",
    "industry",
    "company",
    "modality",
    "source",
    "publisher",
    "published_at",
    "usage_rights",
    "content_sha256",
    "gold_label_path",
}

REQUIRED_REAL_METRICS = {
    "financial_fact_accuracy",
    "source_coordinate_completeness",
    "evidence_relation_judgement",
    "research_question_grounding",
    "image_visible_data_accuracy",
    "audio_speaker_claim_accuracy",
    "unsupported_conclusion_block",
    "defense_scoring_agreement",
    "research_question_expert_relevance",
    "lightweight_classification_macro_f1",
    "retrieval_ndcg_at_10",
    "view_comparison_expert_score",
    "red_team_critical_recall",
    "thesis_evidence_relevance",
    "memo_traceability",
    "valuation_scenario_accuracy",
    "financial_anomaly_recall",
    "multimodal_crosscheck_accuracy",
    "capability_profile_expert_agreement",
}

MINIMUM_BY_METRIC = {"research_question_expert_relevance": 60, "defense_scoring_agreement": 100, "evidence_relation_judgement": 200}


def validate_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    minimum = int(payload.get("minimum_cases_per_metric", 20))
    cases = payload.get("cases", [])
    errors: list[str] = []
    counts: Counter[str] = Counter()
    ids: set[str] = set()
    sources_by_split: dict[str, set[str]] = {}
    for index, case in enumerate(cases):
        missing = sorted(REQUIRED_METADATA - set(case))
        if missing:
            errors.append(f"case[{index}] missing: {', '.join(missing)}")
            continue
        case_id = str(case["case_id"])
        if case_id in ids:
            errors.append(f"duplicate case_id: {case_id}")
        ids.add(case_id)
        digest = str(case["content_sha256"])
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
            errors.append(f"invalid sha256: {case_id}")
        metric = str(case["metric"])
        counts[metric] += 1
        split = str(case["split"])
        source_key = hashlib.sha256(str(case["source"]).encode()).hexdigest()
        for other_split, source_keys in sources_by_split.items():
            if other_split != split and source_key in source_keys:
                errors.append(f"source leakage across splits: {case_id}")
        sources_by_split.setdefault(split, set()).add(source_key)
    undersized = sorted(metric for metric, count in counts.items() if count < MINIMUM_BY_METRIC.get(metric, minimum))
    missing_metrics = sorted(REQUIRED_REAL_METRICS - set(counts))
    if not cases:
        errors.append("real-world corpus is empty")
    if undersized:
        errors.append("undersized metrics: " + ", ".join(undersized))
    if missing_metrics:
        errors.append("missing required metrics: " + ", ".join(missing_metrics))
    passed = bool(cases) and not errors
    return {
        "suite": "real_world_corpus_readiness",
        "passed": passed,
        "release_eligible": passed,
        "case_count": len(cases),
        "metric_counts": dict(counts),
        "minimum_cases_per_metric": minimum,
        "minimum_by_metric": MINIMUM_BY_METRIC,
        "required_metrics": sorted(REQUIRED_REAL_METRICS),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("evals/real_cases/manifest.json"))
    args = parser.parse_args()
    report = validate_manifest(args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
