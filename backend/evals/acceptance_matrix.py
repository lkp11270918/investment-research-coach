from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {"id", "outcome", "implementation", "tests", "real_metric", "release_gate", "status"}
VALID_STATUS = {"planned", "engineering_complete", "real_validated"}


def validate_acceptance_matrix(path: Path = Path("evals/final_acceptance_matrix.json")) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    requirements = payload.get("requirements", [])
    errors: list[str] = []
    ids: set[str] = set()
    for index, item in enumerate(requirements):
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"requirement[{index}] missing: {', '.join(sorted(missing))}")
            continue
        if item["id"] in ids:
            errors.append(f"duplicate requirement id: {item['id']}")
        ids.add(item["id"])
        if item["status"] not in VALID_STATUS:
            errors.append(f"invalid status: {item['id']}")
        for field in ("implementation", "tests"):
            if not item[field]:
                errors.append(f"{item['id']} has no {field}")
            for filename in item[field]:
                if not Path(filename).exists():
                    errors.append(f"{item['id']} missing file: {filename}")
        if not item["real_metric"] or not item["release_gate"]:
            errors.append(f"{item['id']} has no real-world release gate")
    expected = {f"FP-{index:02d}" for index in range(1, 21)}
    missing_ids = expected - ids
    if missing_ids:
        errors.append("missing final-product requirements: " + ", ".join(sorted(missing_ids)))
    return {"suite": "final_product_acceptance_governance", "passed": not errors, "requirement_count": len(requirements), "errors": errors}


if __name__ == "__main__":
    report = validate_acceptance_matrix()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 2)
