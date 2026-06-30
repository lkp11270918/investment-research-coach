from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_ROOT / "data" / "runs"
BAD_CASES_DIR = PROJECT_ROOT / "data" / "bad_cases"


def save_model_json(model: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_run(model: BaseModel, run_id: str) -> Path:
    path = RUNS_DIR / f"{run_id}.json"
    save_model_json(model, path)
    return path
