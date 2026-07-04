from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel

from .config import get_settings
from .models import ResearchRunDetail, ResearchRunSummary, WorkflowState


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


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith("postgres://") or database_url.startswith("postgresql://")


@contextmanager
def _sqlite_connection(database_url: str) -> Iterator[sqlite3.Connection]:
    path = database_url.removeprefix("sqlite:///")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def init_research_runs_db() -> None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    ticker TEXT,
                    industry TEXT,
                    memo_confidence TEXT,
                    material_count INTEGER NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_user_created ON research_runs (user_id, created_at DESC)")
        return

    with _sqlite_connection(database_url) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_runs (
                run_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                run_type TEXT NOT NULL,
                company_name TEXT NOT NULL,
                ticker TEXT,
                industry TEXT,
                memo_confidence TEXT,
                material_count INTEGER NOT NULL,
                evidence_count INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_user_created ON research_runs (user_id, created_at DESC)")


def save_user_run(*, user_id: str | None, run_type: str, state: WorkflowState) -> None:
    if not user_id:
        return
    database_url = get_settings().database_url
    payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
    created_at = state.created_at if state.created_at else _now()
    memo_confidence = state.memo.confidence.value if state.memo else None
    values = (
        state.run_id,
        user_id,
        run_type,
        state.company_profile.company_name,
        state.company_profile.ticker,
        state.company_profile.industry,
        memo_confidence,
        len(state.raw_materials),
        len(state.evidence_items),
        payload,
        created_at,
    )

    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            conn.execute(
                """
                INSERT INTO research_runs (
                    run_id, user_id, run_type, company_name, ticker, industry, memo_confidence,
                    material_count, evidence_count, payload, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (run_id) DO UPDATE SET
                    payload = EXCLUDED.payload,
                    memo_confidence = EXCLUDED.memo_confidence,
                    material_count = EXCLUDED.material_count,
                    evidence_count = EXCLUDED.evidence_count
                """,
                values,
            )
        return

    with _sqlite_connection(database_url) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO research_runs (
                run_id, user_id, run_type, company_name, ticker, industry, memo_confidence,
                material_count, evidence_count, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*values[:-1], created_at.isoformat()),
        )


def _summary_from_row(row: Any) -> ResearchRunSummary:
    if isinstance(row, sqlite3.Row):
        return ResearchRunSummary(
            run_id=row["run_id"],
            run_type=row["run_type"],
            company_name=row["company_name"],
            ticker=row["ticker"],
            industry=row["industry"],
            memo_confidence=row["memo_confidence"],
            material_count=row["material_count"],
            evidence_count=row["evidence_count"],
            created_at=_parse_dt(row["created_at"]),
        )
    return ResearchRunSummary(
        run_id=row[0],
        run_type=row[1],
        company_name=row[2],
        ticker=row[3],
        industry=row[4],
        memo_confidence=row[5],
        material_count=row[6],
        evidence_count=row[7],
        created_at=_parse_dt(row[8]),
    )


def list_user_runs(user_id: str, limit: int = 30) -> list[ResearchRunSummary]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            rows = conn.execute(
                """
                SELECT run_id, run_type, company_name, ticker, industry, memo_confidence,
                       material_count, evidence_count, created_at
                FROM research_runs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()
        return [_summary_from_row(row) for row in rows]

    with _sqlite_connection(database_url) as conn:
        rows = conn.execute(
            """
            SELECT run_id, run_type, company_name, ticker, industry, memo_confidence,
                   material_count, evidence_count, created_at
            FROM research_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [_summary_from_row(row) for row in rows]


def get_user_run(user_id: str, run_id: str) -> ResearchRunDetail | None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            row = conn.execute(
                """
                SELECT run_id, run_type, company_name, ticker, industry, memo_confidence,
                       material_count, evidence_count, created_at, payload
                FROM research_runs
                WHERE user_id = %s AND run_id = %s
                """,
                (user_id, run_id),
            ).fetchone()
    else:
        with _sqlite_connection(database_url) as conn:
            row = conn.execute(
                """
                SELECT run_id, run_type, company_name, ticker, industry, memo_confidence,
                       material_count, evidence_count, created_at, payload
                FROM research_runs
                WHERE user_id = ? AND run_id = ?
                """,
                (user_id, run_id),
            ).fetchone()

    if not row:
        return None
    summary = _summary_from_row(row)
    payload = row["payload"] if isinstance(row, sqlite3.Row) else row[9]
    state = WorkflowState.model_validate(json.loads(payload) if isinstance(payload, str) else payload)
    return ResearchRunDetail(summary=summary, state=state)
