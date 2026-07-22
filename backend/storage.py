from __future__ import annotations

import json
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pydantic import BaseModel

from .config import get_settings
from .models import (
    ResearchProjectCreate,
    ResearchProjectDetail,
    ResearchProjectStatus,
    ResearchProjectSummary,
    ResearchProjectUpdate,
    EvidenceGraph,
    EvidenceNodeReview,
    EvidenceEdgeReview,
    ResearchRunDetail,
    ResearchRunSummary,
    WorkflowState,
    ThesisVersion,
    DefenseSession,
    CapabilityProfile,
    ProjectMaterial,
    ResearchTask,
    Confidence,
    MaterialBlockReview,
    MemoVersion,
    MemoVersionCreate,
    MemoSuggestion,
    ResearchBehaviorEvent,
    ResearchTaskUpdate,
    VerificationStatus,
    ResearchMap,
    ValuationAssumptions,
)


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
            conn.execute("ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS project_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_user_created ON research_runs (user_id, created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_project_created ON research_runs (project_id, created_at DESC)")
            _init_postgres_projects(conn)
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
        columns = {row[1] for row in conn.execute("PRAGMA table_info(research_runs)").fetchall()}
        if "project_id" not in columns:
            conn.execute("ALTER TABLE research_runs ADD COLUMN project_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_research_runs_project_created ON research_runs (project_id, created_at DESC)")
        _init_sqlite_projects(conn)


def _init_postgres_projects(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_projects (
            project_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            company_profile JSONB NOT NULL,
            research_objective TEXT,
            investment_horizon TEXT,
            initial_view TEXT,
            key_question TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_projects_user_updated ON research_projects (user_id, updated_at DESC)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_evidence_graphs (project_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS evidence_graph_versions (project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(project_id,version))")
    conn.execute("CREATE TABLE IF NOT EXISTS thesis_versions (thesis_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, version))")
    conn.execute("CREATE TABLE IF NOT EXISTS defense_sessions (session_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS capability_profiles (profile_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_materials (material_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, run_id TEXT NOT NULL, logical_key TEXT NOT NULL, content_hash TEXT NOT NULL, version INTEGER NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, content_hash))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_materials_project_created ON project_materials (project_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_tasks (task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, source_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, source_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS memo_versions (memo_version_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, source_run_id TEXT, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, version), UNIQUE(project_id, source_run_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS research_behavior_events (event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, project_id TEXT, action TEXT NOT NULL, dimension TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_behavior_user_created ON research_behavior_events(user_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_map_versions (project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, fingerprint TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(project_id,version))")
    conn.execute("CREATE TABLE IF NOT EXISTS project_valuation_assumptions (project_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")


def _init_sqlite_projects(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_projects (
            project_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            company_profile TEXT NOT NULL,
            research_objective TEXT,
            investment_horizon TEXT,
            initial_view TEXT,
            key_question TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_projects_user_updated ON research_projects (user_id, updated_at DESC)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_evidence_graphs (project_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS evidence_graph_versions (project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(project_id,version))")
    conn.execute("CREATE TABLE IF NOT EXISTS thesis_versions (thesis_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, version))")
    conn.execute("CREATE TABLE IF NOT EXISTS defense_sessions (session_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS capability_profiles (profile_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_materials (material_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, run_id TEXT NOT NULL, logical_key TEXT NOT NULL, content_hash TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, content_hash))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_materials_project_created ON project_materials (project_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_tasks (task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, source_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, source_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS memo_versions (memo_version_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, source_run_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, version), UNIQUE(project_id, source_run_id))")
    conn.execute("CREATE TABLE IF NOT EXISTS research_behavior_events (event_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, project_id TEXT, action TEXT NOT NULL, dimension TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_behavior_user_created ON research_behavior_events(user_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_map_versions (project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(project_id,version))")
    conn.execute("CREATE TABLE IF NOT EXISTS project_valuation_assumptions (project_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")

def get_valuation_assumptions(user_id: str, project_id: str) -> ValuationAssumptions:
    database_url=get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: row=conn.execute("SELECT payload FROM project_valuation_assumptions WHERE user_id=%s AND project_id=%s",(user_id,project_id)).fetchone()
    else:
        with _sqlite_connection(database_url) as conn: row=conn.execute("SELECT payload FROM project_valuation_assumptions WHERE user_id=? AND project_id=?",(user_id,project_id)).fetchone()
    if not row: return ValuationAssumptions(project_id=project_id)
    return ValuationAssumptions.model_validate(json.loads(row[0]) if isinstance(row[0],str) else row[0])

def save_valuation_assumptions(user_id: str, project_id: str, assumptions: ValuationAssumptions) -> ValuationAssumptions:
    if not project_belongs_to_user(user_id, project_id):
        raise ValueError("project not found")
    assumptions.project_id=project_id; assumptions.updated_at=_now(); payload=json.dumps(assumptions.model_dump(mode="json"),ensure_ascii=False); database_url=get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("INSERT INTO project_valuation_assumptions(project_id,user_id,payload,updated_at) VALUES(%s,%s,%s::jsonb,%s) ON CONFLICT(project_id) DO UPDATE SET payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at",(project_id,user_id,payload,assumptions.updated_at))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("INSERT INTO project_valuation_assumptions(project_id,user_id,payload,updated_at) VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",(project_id,user_id,payload,assumptions.updated_at.isoformat()))
    return assumptions


def list_research_map_versions(user_id: str, project_id: str) -> list[ResearchMap]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM research_map_versions WHERE user_id=%s AND project_id=%s ORDER BY version", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM research_map_versions WHERE user_id=? AND project_id=? ORDER BY version", (user_id, project_id)).fetchall()
    return [ResearchMap.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def save_research_map_version(user_id: str, research_map: ResearchMap) -> ResearchMap:
    history = list_research_map_versions(user_id, research_map.project_id)
    if history and history[-1].context_fingerprint == research_map.context_fingerprint:
        return history[-1]
    database_url = get_settings().database_url
    payload = json.dumps(research_map.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("INSERT INTO research_map_versions(project_id,user_id,version,fingerprint,payload,created_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s)", (research_map.project_id, user_id, research_map.version, research_map.context_fingerprint or "", payload, research_map.updated_at))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("INSERT INTO research_map_versions(project_id,user_id,version,fingerprint,payload,created_at) VALUES(?,?,?,?,?,?)", (research_map.project_id, user_id, research_map.version, research_map.context_fingerprint or "", payload, research_map.updated_at.isoformat()))
    return research_map


def save_user_run(*, user_id: str | None, run_type: str, state: WorkflowState, project_id: str | None = None) -> None:
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
            if project_id:
                conn.execute(
                    "UPDATE research_runs SET project_id = %s WHERE run_id = %s AND user_id = %s",
                    (project_id, state.run_id, user_id),
                )
                _upsert_project_graph_postgres(conn, user_id, project_id, state.evidence_graph)
                _save_project_materials(conn, True, user_id, project_id, state)
                _save_generated_memo_version(conn, True, user_id, project_id, state)
                conn.execute(
                    "UPDATE research_projects SET updated_at = %s WHERE project_id = %s AND user_id = %s",
                    (_now(), project_id, user_id),
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
        if project_id:
            conn.execute(
                "UPDATE research_runs SET project_id = ? WHERE run_id = ? AND user_id = ?",
                (project_id, state.run_id, user_id),
            )
            _upsert_project_graph_sqlite(conn, user_id, project_id, state.evidence_graph)
            _save_project_materials(conn, False, user_id, project_id, state)
            _save_generated_memo_version(conn, False, user_id, project_id, state)
            conn.execute(
                "UPDATE research_projects SET updated_at = ? WHERE project_id = ? AND user_id = ?",
                (_now().isoformat(), project_id, user_id),
            )


def _save_project_materials(conn: Any, postgres: bool, user_id: str, project_id: str, state: WorkflowState) -> None:
    placeholder = "%s" if postgres else "?"
    for raw in state.raw_materials:
        digest = hashlib.sha256((raw.content + "\0" + (raw.file_name or "") + "\0" + raw.source_type.value).encode("utf-8")).hexdigest()
        exists = conn.execute(f"SELECT material_id FROM project_materials WHERE project_id={placeholder} AND content_hash={placeholder}", (project_id, digest)).fetchone()
        if exists:
            continue
        logical_key = (raw.file_name or raw.title).strip().lower()
        row = conn.execute(f"SELECT COALESCE(MAX(version),0) FROM project_materials WHERE project_id={placeholder} AND logical_key={placeholder}", (project_id, logical_key)).fetchone()
        material = ProjectMaterial(
            project_id=project_id, run_id=state.run_id, version=int(row[0]) + 1,
            title=raw.title, source_type=raw.source_type, modality=raw.modality,
            file_name=raw.file_name, url=raw.url, period_covered=raw.period_covered,
            publisher=raw.publisher, published_at=raw.published_at, content_hash=digest,
            content=raw.content, blocks=raw.blocks, parse_warnings=raw.parse_warnings,
        )
        payload = json.dumps(material.model_dump(mode="json"), ensure_ascii=False)
        values = (material.material_id, project_id, user_id, state.run_id, logical_key, digest, material.version, payload, material.created_at if postgres else material.created_at.isoformat())
        sql = "INSERT INTO project_materials(material_id,project_id,user_id,run_id,logical_key,content_hash,version,payload,created_at) VALUES(" + ",".join([placeholder] * 9) + ")"
        if postgres:
            sql = sql.replace(f"{placeholder},{placeholder})", f"{placeholder}::jsonb,{placeholder})")
        conn.execute(sql, values)


def _save_generated_memo_version(conn: Any, postgres: bool, user_id: str, project_id: str, state: WorkflowState) -> None:
    if not state.memo:
        return
    placeholder = "%s" if postgres else "?"
    exists = conn.execute(f"SELECT memo_version_id FROM memo_versions WHERE project_id={placeholder} AND source_run_id={placeholder}", (project_id, state.run_id)).fetchone()
    if exists:
        return
    row = conn.execute(f"SELECT COALESCE(MAX(version),0) FROM memo_versions WHERE project_id={placeholder}", (project_id,)).fetchone()
    gate_issues = []
    if state.pre_memo_gate and state.pre_memo_gate.status == "fail": gate_issues.extend(state.pre_memo_gate.evidence_issues)
    if state.post_memo_gate and state.post_memo_gate.status == "fail": gate_issues.extend(state.post_memo_gate.evidence_issues)
    version = MemoVersion(project_id=project_id, version=int(row[0]) + 1, sections=state.memo.sections, source_run_id=state.run_id, created_by="ai", change_summary="AI分析生成初稿", gate_status="needs_evidence" if gate_issues else "draft", gate_issues=list(dict.fromkeys(gate_issues)), evidence_graph_version=state.evidence_graph.version)
    payload = json.dumps(version.model_dump(mode="json"), ensure_ascii=False)
    values = (version.memo_version_id, project_id, user_id, version.version, state.run_id, payload, version.created_at if postgres else version.created_at.isoformat())
    sql = "INSERT INTO memo_versions(memo_version_id,project_id,user_id,version,source_run_id,payload,created_at) VALUES(" + ",".join([placeholder] * 7) + ")"
    if postgres: sql = sql.replace(f"{placeholder},{placeholder})", f"{placeholder}::jsonb,{placeholder})")
    conn.execute(sql, values)


def list_project_materials(user_id: str, project_id: str) -> list[ProjectMaterial]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            rows = conn.execute("SELECT payload FROM project_materials WHERE user_id=%s AND project_id=%s ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn:
            rows = conn.execute("SELECT payload FROM project_materials WHERE user_id=? AND project_id=? ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    return [ProjectMaterial.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def review_project_material_block(user_id: str, project_id: str, material_id: str, block_id: str, review: MaterialBlockReview) -> ProjectMaterial | None:
    database_url = get_settings().database_url
    postgres = _is_postgres_url(database_url)
    if postgres:
        import psycopg
        with psycopg.connect(database_url) as conn:
            row = conn.execute("SELECT payload FROM project_materials WHERE user_id=%s AND project_id=%s AND material_id=%s", (user_id, project_id, material_id)).fetchone()
            if not row: return None
            material = ProjectMaterial.model_validate(row[0])
            block = next((item for item in material.blocks if item.block_id == block_id), None)
            if not block: return None
            block.review_status = "confirmed" if review.confirmed else "rejected"
            block.review_note = review.note
            block.requires_confirmation = False
            conn.execute("UPDATE project_materials SET payload=%s::jsonb WHERE material_id=%s AND user_id=%s", (json.dumps(material.model_dump(mode="json"), ensure_ascii=False), material_id, user_id))
            return material
    with _sqlite_connection(database_url) as conn:
        row = conn.execute("SELECT payload FROM project_materials WHERE user_id=? AND project_id=? AND material_id=?", (user_id, project_id, material_id)).fetchone()
        if not row: return None
        material = ProjectMaterial.model_validate(json.loads(row[0]))
        block = next((item for item in material.blocks if item.block_id == block_id), None)
        if not block: return None
        block.review_status = "confirmed" if review.confirmed else "rejected"
        block.review_note = review.note
        block.requires_confirmation = False
        conn.execute("UPDATE project_materials SET payload=? WHERE material_id=? AND user_id=?", (json.dumps(material.model_dump(mode="json"), ensure_ascii=False), material_id, user_id))
    return material


def review_evidence_for_material_block(user_id: str, project_id: str, block_id: str, confirmed: bool, note: str | None = None) -> EvidenceGraph | None:
    graph = get_project_evidence_graph(user_id, project_id)
    if graph is None:
        return None
    changed = False
    for node in graph.nodes:
        refs = node.metadata.get("source_refs", [])
        if any(ref.get("block_id") == block_id for ref in refs if isinstance(ref, dict)):
            node.verification_status = VerificationStatus.VERIFIED if confirmed else VerificationStatus.UNSUPPORTED
            node.metadata["multimodal_review_note"] = note
            changed = True
    if not changed:
        return graph
    database_url = get_settings().database_url
    payload = json.dumps(graph.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("UPDATE project_evidence_graphs SET payload=%s::jsonb,updated_at=%s WHERE project_id=%s AND user_id=%s", (payload, _now(), project_id, user_id))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("UPDATE project_evidence_graphs SET payload=?,updated_at=? WHERE project_id=? AND user_id=?", (payload, _now().isoformat(), project_id, user_id))
    return graph


def sync_defense_tasks(user_id: str, session: DefenseSession) -> list[ResearchTask]:
    tasks = [ResearchTask(project_id=session.project_id, title=f"补强{turn.role.value}答辩", detail=turn.feedback or "补充证据并重答", source_type="defense", source_id=turn.turn_id, evidence_ids=turn.answer_evidence_ids) for turn in session.turns if turn.passed is False]
    return upsert_research_tasks(user_id, tasks, session.project_id)


def upsert_research_tasks(user_id: str, tasks: list[ResearchTask], project_id: str) -> list[ResearchTask]:
    existing = {task.source_id: task for task in list_research_tasks(user_id, project_id)}
    tasks = [task for task in tasks if existing.get(task.source_id, task).status != "completed"]
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            for task in tasks:
                payload = json.dumps(task.model_dump(mode="json"), ensure_ascii=False)
                conn.execute("INSERT INTO research_tasks(task_id,project_id,user_id,source_id,payload,created_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(project_id,source_id) DO UPDATE SET payload=EXCLUDED.payload", (task.task_id, task.project_id, user_id, task.source_id, payload, task.created_at))
    else:
        with _sqlite_connection(database_url) as conn:
            for task in tasks:
                payload = json.dumps(task.model_dump(mode="json"), ensure_ascii=False)
                conn.execute("INSERT INTO research_tasks(task_id,project_id,user_id,source_id,payload,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(project_id,source_id) DO UPDATE SET payload=excluded.payload", (task.task_id, task.project_id, user_id, task.source_id, payload, task.created_at.isoformat()))
    return list_research_tasks(user_id, project_id)


def list_research_tasks(user_id: str, project_id: str) -> list[ResearchTask]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM research_tasks WHERE user_id=%s AND project_id=%s ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM research_tasks WHERE user_id=? AND project_id=? ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    return [ResearchTask.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def update_research_task(user_id: str, project_id: str, task_id: str, request: ResearchTaskUpdate) -> ResearchTask | None:
    task = next((item for item in list_research_tasks(user_id, project_id) if item.task_id == task_id), None)
    if not task or request.status not in {"open", "completed"}:
        return None
    if request.status == "completed":
        graph = get_project_evidence_graph(user_id, project_id) or EvidenceGraph()
        verified = {node.evidence_id for node in graph.nodes if node.evidence_id and node.verification_status == VerificationStatus.VERIFIED}
        if not request.evidence_ids or not set(request.evidence_ids).issubset(verified):
            raise ValueError("完成研究任务必须引用至少一条已确认的证据")
        task.completion_evidence_ids = request.evidence_ids
        task.completed_at = _now()
    else:
        task.completion_evidence_ids = []
        task.completed_at = None
    task.status = request.status
    task.updated_at = _now()
    database_url = get_settings().database_url
    payload = json.dumps(task.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("UPDATE research_tasks SET payload=%s::jsonb WHERE task_id=%s AND user_id=%s AND project_id=%s", (payload, task_id, user_id, project_id))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("UPDATE research_tasks SET payload=? WHERE task_id=? AND user_id=? AND project_id=?", (payload, task_id, user_id, project_id))
    return task


def record_behavior_event(event: ResearchBehaviorEvent) -> ResearchBehaviorEvent:
    database_url = get_settings().database_url
    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("INSERT INTO research_behavior_events(event_id,user_id,project_id,action,dimension,payload,created_at) VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s)", (event.event_id, event.user_id, event.project_id, event.action, event.dimension, payload, event.created_at))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("INSERT INTO research_behavior_events(event_id,user_id,project_id,action,dimension,payload,created_at) VALUES(?,?,?,?,?,?,?)", (event.event_id, event.user_id, event.project_id, event.action, event.dimension, payload, event.created_at.isoformat()))
    return event


def list_behavior_events(user_id: str, limit: int = 1000) -> list[ResearchBehaviorEvent]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM research_behavior_events WHERE user_id=%s ORDER BY created_at ASC LIMIT %s", (user_id, limit)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM research_behavior_events WHERE user_id=? ORDER BY created_at ASC LIMIT ?", (user_id, limit)).fetchall()
    return [ResearchBehaviorEvent.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def _upsert_project_graph_postgres(conn: Any, user_id: str, project_id: str, incoming: EvidenceGraph) -> None:
    from .evidence_graph import merge_evidence_graphs
    row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=%s AND user_id=%s", (project_id, user_id)).fetchone()
    existing = EvidenceGraph.model_validate(row[0]) if row else None
    graph = merge_evidence_graphs(existing, incoming)
    conn.execute("INSERT INTO evidence_graph_versions(project_id,user_id,version,payload,created_at) VALUES(%s,%s,%s,%s::jsonb,%s) ON CONFLICT(project_id,version) DO NOTHING", (project_id, user_id, graph.version, json.dumps(graph.model_dump(mode="json"), ensure_ascii=False), _now()))
    conn.execute("""INSERT INTO project_evidence_graphs(project_id,user_id,payload,updated_at) VALUES(%s,%s,%s::jsonb,%s)
        ON CONFLICT(project_id) DO UPDATE SET payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at""", (project_id, user_id, json.dumps(graph.model_dump(mode="json"), ensure_ascii=False), _now()))


def _upsert_project_graph_sqlite(conn: sqlite3.Connection, user_id: str, project_id: str, incoming: EvidenceGraph) -> None:
    from .evidence_graph import merge_evidence_graphs
    row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=? AND user_id=?", (project_id, user_id)).fetchone()
    existing = EvidenceGraph.model_validate(json.loads(row[0])) if row else None
    graph = merge_evidence_graphs(existing, incoming)
    conn.execute("INSERT OR IGNORE INTO evidence_graph_versions(project_id,user_id,version,payload,created_at) VALUES(?,?,?,?,?)", (project_id, user_id, graph.version, json.dumps(graph.model_dump(mode="json"), ensure_ascii=False), _now().isoformat()))
    conn.execute("INSERT OR REPLACE INTO project_evidence_graphs(project_id,user_id,payload,updated_at) VALUES(?,?,?,?)", (project_id, user_id, json.dumps(graph.model_dump(mode="json"), ensure_ascii=False), _now().isoformat()))


def get_project_evidence_graph(user_id: str, project_id: str) -> EvidenceGraph | None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=%s AND user_id=%s", (project_id, user_id)).fetchone()
    else:
        with _sqlite_connection(database_url) as conn:
            row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=? AND user_id=?", (project_id, user_id)).fetchone()
    if not row:
        return None
    payload = row[0]
    return EvidenceGraph.model_validate(json.loads(payload) if isinstance(payload, str) else payload)


def list_evidence_graph_versions(user_id: str, project_id: str) -> list[EvidenceGraph]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM evidence_graph_versions WHERE user_id=%s AND project_id=%s ORDER BY version", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM evidence_graph_versions WHERE user_id=? AND project_id=? ORDER BY version", (user_id, project_id)).fetchall()
    return [EvidenceGraph.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def review_project_evidence_node(user_id: str, project_id: str, node_id: str, review: EvidenceNodeReview) -> EvidenceGraph | None:
    graph = get_project_evidence_graph(user_id, project_id)
    if graph is None:
        return None
    matched = False
    for node in graph.nodes:
        if node.node_id == node_id:
            node.verification_status = review.verification_status
            node.metadata["user_review_note"] = review.note
            matched = True
            break
    if not matched:
        return None
    return _persist_reviewed_graph(user_id, project_id, graph, f"用户复核证据节点 {node_id}")


def review_project_evidence_edge(user_id: str, project_id: str, edge_id: str, review: EvidenceEdgeReview) -> EvidenceGraph | None:
    graph = get_project_evidence_graph(user_id, project_id)
    if graph is None:
        return None
    edge = next((item for item in graph.edges if item.edge_id == edge_id), None)
    if edge is None:
        return None
    edge.relation = review.relation
    edge.confidence = Confidence.HIGH
    edge.relation_source = "user_review"
    edge.reviewed_by_user = True
    edge.user_review_note = review.note
    return _persist_reviewed_graph(user_id, project_id, graph, f"用户修正证据关系 {edge_id}")


def _persist_reviewed_graph(user_id: str, project_id: str, graph: EvidenceGraph, summary: str) -> EvidenceGraph:
    graph.parent_version = graph.version
    graph.version += 1
    graph.change_summary = summary
    graph.updated_at = _now()
    database_url = get_settings().database_url
    payload = json.dumps(graph.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            conn.execute("UPDATE project_evidence_graphs SET payload=%s::jsonb,updated_at=%s WHERE project_id=%s AND user_id=%s", (payload, _now(), project_id, user_id))
            conn.execute("INSERT INTO evidence_graph_versions(project_id,user_id,version,payload,created_at) VALUES(%s,%s,%s,%s::jsonb,%s) ON CONFLICT(project_id,version) DO UPDATE SET payload=EXCLUDED.payload", (project_id, user_id, graph.version, payload, _now()))
    else:
        with _sqlite_connection(database_url) as conn:
            conn.execute("UPDATE project_evidence_graphs SET payload=?,updated_at=? WHERE project_id=? AND user_id=?", (payload, _now().isoformat(), project_id, user_id))
            conn.execute("INSERT OR REPLACE INTO evidence_graph_versions(project_id,user_id,version,payload,created_at) VALUES(?,?,?,?,?)", (project_id, user_id, graph.version, payload, _now().isoformat()))
    return graph


def _project_from_row(row: Any, run_count: int = 0) -> ResearchProjectSummary:
    def value(name: str, index: int) -> Any:
        return row[name] if isinstance(row, sqlite3.Row) else row[index]

    profile = value("company_profile", 1)
    return ResearchProjectSummary(
        project_id=value("project_id", 0),
        company_profile=json.loads(profile) if isinstance(profile, str) else profile,
        research_objective=value("research_objective", 2),
        investment_horizon=value("investment_horizon", 3),
        initial_view=value("initial_view", 4),
        key_question=value("key_question", 5),
        status=value("status", 6),
        run_count=run_count,
        created_at=_parse_dt(value("created_at", 7)),
        updated_at=_parse_dt(value("updated_at", 8)),
    )


def create_research_project(user_id: str, request: ResearchProjectCreate) -> ResearchProjectSummary:
    database_url = get_settings().database_url
    project_id = f"PRJ-{uuid4().hex[:10]}"
    now = _now()
    profile = json.dumps(request.company_profile.model_dump(mode="json"), ensure_ascii=False)
    values = (
        project_id, user_id, profile, request.research_objective, request.investment_horizon,
        request.initial_view, request.key_question, ResearchProjectStatus.ACTIVE.value, now, now,
    )
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            conn.execute(
                """
                INSERT INTO research_projects (
                    project_id, user_id, company_profile, research_objective, investment_horizon,
                    initial_view, key_question, status, created_at, updated_at
                ) VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
                """,
                values,
            )
    else:
        with _sqlite_connection(database_url) as conn:
            conn.execute(
                """
                INSERT INTO research_projects (
                    project_id, user_id, company_profile, research_objective, investment_horizon,
                    initial_view, key_question, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*values[:-2], now.isoformat(), now.isoformat()),
            )
    return ResearchProjectSummary(project_id=project_id, company_profile=request.company_profile,
        research_objective=request.research_objective, investment_horizon=request.investment_horizon,
        initial_view=request.initial_view, key_question=request.key_question, created_at=now, updated_at=now)


def list_research_projects(user_id: str, include_archived: bool = False) -> list[ResearchProjectSummary]:
    database_url = get_settings().database_url
    where_status_pg = "" if include_archived else " AND p.status <> %s"
    where_status_sqlite = "" if include_archived else " AND p.status <> ?"
    select = """
        SELECT p.project_id, p.company_profile, p.research_objective, p.investment_horizon,
               p.initial_view, p.key_question, p.status, p.created_at, p.updated_at,
               COUNT(r.run_id) AS run_count
        FROM research_projects p LEFT JOIN research_runs r ON r.project_id = p.project_id
    """
    if _is_postgres_url(database_url):
        import psycopg

        params = (user_id,) if include_archived else (user_id, ResearchProjectStatus.ARCHIVED.value)
        with psycopg.connect(database_url) as conn:
            rows = conn.execute(select + " WHERE p.user_id = %s" + where_status_pg +
                " GROUP BY p.project_id ORDER BY p.updated_at DESC", params).fetchall()
    else:
        params = (user_id,) if include_archived else (user_id, ResearchProjectStatus.ARCHIVED.value)
        with _sqlite_connection(database_url) as conn:
            rows = conn.execute(select + " WHERE p.user_id = ?" + where_status_sqlite +
                " GROUP BY p.project_id ORDER BY p.updated_at DESC", params).fetchall()
    return [_project_from_row(row, int(row[9])) for row in rows]


def get_research_project(user_id: str, project_id: str) -> ResearchProjectDetail | None:
    database_url = get_settings().database_url
    select_project = """
        SELECT project_id, company_profile, research_objective, investment_horizon,
               initial_view, key_question, status, created_at, updated_at
        FROM research_projects WHERE user_id = {user} AND project_id = {project}
    """
    select_runs = """
        SELECT run_id, run_type, company_name, ticker, industry, memo_confidence,
               material_count, evidence_count, created_at FROM research_runs
        WHERE user_id = {user} AND project_id = {project} ORDER BY created_at ASC
    """
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            row = conn.execute(select_project.format(user="%s", project="%s"), (user_id, project_id)).fetchone()
            runs = conn.execute(select_runs.format(user="%s", project="%s"), (user_id, project_id)).fetchall() if row else []
    else:
        with _sqlite_connection(database_url) as conn:
            row = conn.execute(select_project.format(user="?", project="?"), (user_id, project_id)).fetchone()
            runs = conn.execute(select_runs.format(user="?", project="?"), (user_id, project_id)).fetchall() if row else []
    if not row:
        return None
    timeline = [_summary_from_row(run) for run in runs]
    return ResearchProjectDetail(project=_project_from_row(row, len(timeline)), timeline=timeline, materials=list_project_materials(user_id, project_id))


def update_research_project(user_id: str, project_id: str, request: ResearchProjectUpdate) -> ResearchProjectDetail | None:
    existing = get_research_project(user_id, project_id)
    if not existing:
        return None
    current = existing.project
    profile = request.company_profile or current.company_profile
    values = {
        "company_profile": json.dumps(profile.model_dump(mode="json"), ensure_ascii=False),
        "research_objective": request.research_objective if request.research_objective is not None else current.research_objective,
        "investment_horizon": request.investment_horizon if request.investment_horizon is not None else current.investment_horizon,
        "initial_view": request.initial_view if request.initial_view is not None else current.initial_view,
        "key_question": request.key_question if request.key_question is not None else current.key_question,
        "status": (request.status or current.status).value,
        "updated_at": _now(),
    }
    database_url = get_settings().database_url
    ordered = tuple(values.values()) + (project_id, user_id)
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            conn.execute("""UPDATE research_projects SET company_profile=%s::jsonb, research_objective=%s,
                investment_horizon=%s, initial_view=%s, key_question=%s, status=%s, updated_at=%s
                WHERE project_id=%s AND user_id=%s""", ordered)
    else:
        sqlite_values = ordered[:6] + (values["updated_at"].isoformat(), project_id, user_id)
        with _sqlite_connection(database_url) as conn:
            conn.execute("""UPDATE research_projects SET company_profile=?, research_objective=?,
                investment_horizon=?, initial_view=?, key_question=?, status=?, updated_at=?
                WHERE project_id=? AND user_id=?""", sqlite_values)
    return get_research_project(user_id, project_id)


def project_belongs_to_user(user_id: str, project_id: str) -> bool:
    return get_research_project(user_id, project_id) is not None


def save_thesis_version(user_id: str, thesis: ThesisVersion) -> ThesisVersion:
    if not project_belongs_to_user(user_id, thesis.project_id):
        raise ValueError("project not found")
    database_url = get_settings().database_url
    payload = json.dumps(thesis.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            conn.execute("INSERT INTO thesis_versions(thesis_id,project_id,user_id,version,payload,created_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s)", (thesis.thesis_id, thesis.project_id, user_id, thesis.version, payload, thesis.created_at))
    else:
        with _sqlite_connection(database_url) as conn:
            conn.execute("INSERT INTO thesis_versions(thesis_id,project_id,user_id,version,payload,created_at) VALUES(?,?,?,?,?,?)", (thesis.thesis_id, thesis.project_id, user_id, thesis.version, payload, thesis.created_at.isoformat()))
    return thesis


def list_thesis_versions(user_id: str, project_id: str) -> list[ThesisVersion]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            rows = conn.execute("SELECT payload FROM thesis_versions WHERE user_id=%s AND project_id=%s ORDER BY version ASC", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn:
            rows = conn.execute("SELECT payload FROM thesis_versions WHERE user_id=? AND project_id=? ORDER BY version ASC", (user_id, project_id)).fetchall()
    return [ThesisVersion.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def list_memo_versions(user_id: str, project_id: str) -> list[MemoVersion]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM memo_versions WHERE user_id=%s AND project_id=%s ORDER BY version ASC", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM memo_versions WHERE user_id=? AND project_id=? ORDER BY version ASC", (user_id, project_id)).fetchall()
    return [MemoVersion.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def save_memo_version(user_id: str, project_id: str, request: MemoVersionCreate) -> MemoVersion:
    from .memo_coauthor import assess_memo_sections
    from .valuation import analyze_valuation
    if not project_belongs_to_user(user_id, project_id):
        raise ValueError("project not found")
    graph = get_project_evidence_graph(user_id, project_id) or EvidenceGraph()
    gate_status, issues = assess_memo_sections(request.sections, graph, request.request_formal)
    if request.request_formal and any(section.section_id == "valuation_margin" for section in request.sections):
        project=get_research_project(user_id,project_id); assumptions=get_valuation_assumptions(user_id,project_id)
        latest=get_user_run(user_id,project.timeline[-1].run_id) if project and project.timeline else None
        valuation=analyze_valuation(latest.state.evidence_items,project.project.company_profile.industry,assumptions) if latest and project else None
        if not valuation or not valuation.formal_conclusion_allowed:
            issues.append("估值与安全边际：现金流口径、股权价值桥接或用户估值假设尚未完成确认")
            gate_status="needs_evidence"
    history = list_memo_versions(user_id, project_id)
    version = MemoVersion(project_id=project_id, version=len(history) + 1, sections=request.sections, created_by="user", change_summary=request.change_summary, gate_status=gate_status, gate_issues=issues, evidence_graph_version=graph.version)
    _persist_memo_version(user_id, version)
    return version


def update_memo_suggestions(user_id: str, version: MemoVersion, suggestions: list[MemoSuggestion]) -> MemoVersion:
    version.suggestions = suggestions
    database_url = get_settings().database_url
    payload = json.dumps(version.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("UPDATE memo_versions SET payload=%s::jsonb WHERE memo_version_id=%s AND user_id=%s", (payload, version.memo_version_id, user_id))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("UPDATE memo_versions SET payload=? WHERE memo_version_id=? AND user_id=?", (payload, version.memo_version_id, user_id))
    return version


def decide_memo_suggestion(user_id: str, project_id: str, memo_version_id: str, suggestion_id: str, status: str) -> MemoVersion | None:
    if status not in {"accepted", "rejected"}: return None
    version = next((item for item in list_memo_versions(user_id, project_id) if item.memo_version_id == memo_version_id), None)
    if not version: return None
    suggestion = next((item for item in version.suggestions if item.suggestion_id == suggestion_id), None)
    if not suggestion: return None
    suggestion.status = status
    return update_memo_suggestions(user_id, version, version.suggestions)


def _persist_memo_version(user_id: str, version: MemoVersion) -> None:
    database_url = get_settings().database_url
    payload = json.dumps(version.model_dump(mode="json"), ensure_ascii=False)
    values = (version.memo_version_id, version.project_id, user_id, version.version, version.source_run_id, payload, version.created_at)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("INSERT INTO memo_versions(memo_version_id,project_id,user_id,version,source_run_id,payload,created_at) VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s)", values)
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("INSERT INTO memo_versions(memo_version_id,project_id,user_id,version,source_run_id,payload,created_at) VALUES(?,?,?,?,?,?,?)", (*values[:-1], version.created_at.isoformat()))


def save_defense_session(user_id: str, session: DefenseSession) -> DefenseSession:
    if not project_belongs_to_user(user_id, session.project_id):
        raise ValueError("project not found")
    database_url = get_settings().database_url
    payload = json.dumps(session.model_dump(mode="json"), ensure_ascii=False)
    values = (session.session_id, session.project_id, user_id, payload, session.created_at, session.updated_at)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            conn.execute("""INSERT INTO defense_sessions(session_id,project_id,user_id,payload,created_at,updated_at) VALUES(%s,%s,%s,%s::jsonb,%s,%s)
                ON CONFLICT(session_id) DO UPDATE SET payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at""", values)
    else:
        with _sqlite_connection(database_url) as conn:
            conn.execute("INSERT OR REPLACE INTO defense_sessions(session_id,project_id,user_id,payload,created_at,updated_at) VALUES(?,?,?,?,?,?)", (*values[:-2], session.created_at.isoformat(), session.updated_at.isoformat()))
    return session


def get_defense_session(user_id: str, session_id: str) -> DefenseSession | None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            row = conn.execute("SELECT payload FROM defense_sessions WHERE user_id=%s AND session_id=%s", (user_id, session_id)).fetchone()
    else:
        with _sqlite_connection(database_url) as conn:
            row = conn.execute("SELECT payload FROM defense_sessions WHERE user_id=? AND session_id=?", (user_id, session_id)).fetchone()
    if not row: return None
    return DefenseSession.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0])


def list_defense_sessions(user_id: str, project_id: str | None = None) -> list[DefenseSession]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        query = "SELECT payload FROM defense_sessions WHERE user_id=%s" + (" AND project_id=%s" if project_id else "") + " ORDER BY created_at ASC"
        params = (user_id, project_id) if project_id else (user_id,)
        with psycopg.connect(database_url) as conn: rows = conn.execute(query, params).fetchall()
    else:
        query = "SELECT payload FROM defense_sessions WHERE user_id=?" + (" AND project_id=?" if project_id else "") + " ORDER BY created_at ASC"
        params = (user_id, project_id) if project_id else (user_id,)
        with _sqlite_connection(database_url) as conn: rows = conn.execute(query, params).fetchall()
    return [DefenseSession.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def save_capability_profile(profile: CapabilityProfile) -> CapabilityProfile:
    database_url = get_settings().database_url
    payload = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: conn.execute("INSERT INTO capability_profiles(profile_id,user_id,payload,created_at) VALUES(%s,%s,%s::jsonb,%s)", (profile.profile_id, profile.user_id, payload, profile.created_at))
    else:
        with _sqlite_connection(database_url) as conn: conn.execute("INSERT INTO capability_profiles(profile_id,user_id,payload,created_at) VALUES(?,?,?,?)", (profile.profile_id, profile.user_id, payload, profile.created_at.isoformat()))
    return profile


def list_capability_profiles(user_id: str, limit: int = 30) -> list[CapabilityProfile]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM capability_profiles WHERE user_id=%s ORDER BY created_at DESC LIMIT %s", (user_id, limit)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM capability_profiles WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
    return [CapabilityProfile.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


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
