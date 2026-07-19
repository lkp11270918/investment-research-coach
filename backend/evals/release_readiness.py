from __future__ import annotations

import json
from pathlib import Path

from .comparative_eval import evaluate_pilot
from .real_world import validate_manifest
from .run_sec_financial_eval import run as run_sec_financial
from .acceptance_matrix import validate_acceptance_matrix
from ..config import get_settings
from ..production import production_configuration_report


def run() -> dict:
    gates = {
        "sec_real_financial": run_sec_financial(),
        "real_world_corpus": validate_manifest(Path("evals/real_cases/manifest.json")),
        "target_user_pilot": evaluate_pilot(),
        "acceptance_matrix": validate_acceptance_matrix(Path("evals/final_acceptance_matrix.json")),
        "production_configuration": production_configuration_report(get_settings()),
    }
    return {"suite": "production_release_readiness", "passed": all(gate["passed"] for gate in gates.values()), "gates": gates}


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 2)
