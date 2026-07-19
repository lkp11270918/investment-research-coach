from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


REQUIRED_FIELDS = {"participant_id", "case_id", "case_pair_id", "condition", "condition_order", "report_quality", "minutes", "unsupported_fact_count", "traceability_rate", "counter_evidence_score", "explanation_score", "return_intent", "completed", "blinded_review", "reviewer_ids"}
SCORE_FIELDS = ("report_quality", "minutes", "unsupported_fact_count", "traceability_rate", "counter_evidence_score", "explanation_score", "return_intent")


def evaluate_pilot(path: Path = Path("evals/pilot_results.json")) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results", [])
    errors: list[str] = []
    participants = {str(row.get("participant_id")) for row in rows if row.get("participant_id")}
    conditions: dict[str, list[dict]] = defaultdict(list)
    by_participant: dict[str, dict[str, dict]] = defaultdict(dict)
    for index, row in enumerate(rows):
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"result[{index}] missing: {', '.join(sorted(missing))}")
            continue
        conditions[str(row["condition"])].append(row)
        participant = str(row["participant_id"])
        condition = str(row["condition"])
        if condition in by_participant[participant]: errors.append(f"duplicate condition for participant: {participant}/{condition}")
        by_participant[participant][condition] = row
        if row.get("blinded_review") is not True: errors.append(f"review was not blinded: result[{index}]")
        if not isinstance(row.get("reviewer_ids"), list) or len(set(row["reviewer_ids"])) < 2: errors.append(f"two independent reviewers required: result[{index}]")
        if row.get("completed") is not True: errors.append(f"incomplete user task: result[{index}]")
    if len(participants) < 10:
        errors.append("at least ten real target users are required")
    for required in ("generic_agent", "research_coach"):
        if required not in conditions:
            errors.append(f"missing comparison condition: {required}")
    for participant in participants:
        if set(by_participant[participant]) != {"generic_agent", "research_coach"}:
            errors.append(f"participant lacks crossover pair: {participant}")
        elif by_participant[participant]["generic_agent"]["condition_order"] == by_participant[participant]["research_coach"]["condition_order"]:
            errors.append(f"condition order is not counterbalanced: {participant}")
    summaries = {}
    for condition, items in conditions.items():
        summaries[condition] = {field: round(sum(float(item[field]) for item in items) / len(items), 2) for field in SCORE_FIELDS}
    passed = not errors
    if passed:
        generic, coach = summaries["generic_agent"], summaries["research_coach"]
        if coach["report_quality"] - generic["report_quality"] < 5: errors.append("report quality improvement is below 5 points")
        if coach["traceability_rate"] - generic["traceability_rate"] < 10: errors.append("traceability improvement is below 10 points")
        if coach["counter_evidence_score"] - generic["counter_evidence_score"] < 10: errors.append("counter-evidence improvement is below 10 points")
        if coach["explanation_score"] - generic["explanation_score"] < 5: errors.append("user explanation improvement is below 5 points")
        if coach["unsupported_fact_count"] >= generic["unsupported_fact_count"]: errors.append("unsupported facts did not decrease")
        if coach["minutes"] > generic["minutes"] * 1.25: errors.append("completion time is more than 25% slower")
        positive_quality = sum(float(pair["research_coach"]["report_quality"]) > float(pair["generic_agent"]["report_quality"]) for pair in by_participant.values()) / len(by_participant)
        if positive_quality < 0.7: errors.append("fewer than 70% of paired users improved report quality")
        passed = not errors
    return {"suite": "target_user_comparative_pilot", "passed": passed, "release_eligible": passed, "participant_count": len(participants), "paired_design": True, "summaries": summaries, "errors": errors}


if __name__ == "__main__":
    report = evaluate_pilot()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 2)
