from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def validate_annotations(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("annotations", [])
    errors: list[str] = []
    by_case: dict[str, list[dict]] = defaultdict(list)
    for index, row in enumerate(rows):
        required = {"case_id", "metric", "annotator_id", "label", "source_coordinate", "annotated_at"}
        missing = required - set(row)
        if missing: errors.append(f"annotation[{index}] missing: {', '.join(sorted(missing))}")
        else: by_case[str(row["case_id"])].append(row)
    for case_id, items in by_case.items():
        if len({item["annotator_id"] for item in items}) < 2: errors.append(f"case requires two annotators: {case_id}")
    agreement_cases = [items for items in by_case.values() if len(items) >= 2]
    agreement = sum(len({json.dumps(item["label"], sort_keys=True, ensure_ascii=False) for item in items}) == 1 for items in agreement_cases) / max(len(agreement_cases), 1)
    if rows and agreement < 0.8: errors.append("raw inter-annotator agreement is below 80%; adjudication required")
    return {"suite":"annotation_quality", "passed": bool(rows) and not errors, "case_count":len(by_case), "agreement":round(agreement * 100, 2), "errors":errors}
