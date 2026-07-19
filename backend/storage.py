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
    ResearchRunDetail,
    ResearchRunSummary,
    WorkflowState,
    ThesisVersion,
    DefenseSession,
    CapabilityProfile,
    ProjectMaterial,
    ResearchTask,
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
    conn.execute("CREATE TABLE IF NOT EXISTS thesis_versions (thesis_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, version))")
    conn.execute("CREATE TABLE IF NOT EXISTS defense_sessions (session_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS capability_profiles (profile_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_materials (material_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, run_id TEXT NOT NULL, logical_key TEXT NOT NULL, content_hash TEXT NOT NULL, version INTEGER NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, content_hash))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_materials_project_created ON project_materials (project_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_tasks (task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, source_id TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL, UNIQUE(project_id, source_id))")


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
    conn.execute("CREATE TABLE IF NOT EXISTS thesis_versions (thesis_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, version))")
    conn.execute("CREATE TABLE IF NOT EXISTS defense_sessions (session_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS capability_profiles (profile_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_materials (material_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, run_id TEXT NOT NULL, logical_key TEXT NOT NULL, content_hash TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, content_hash))")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_materials_project_created ON project_materials (project_id, created_at ASC)")
    conn.execute("CREATE TABLE IF NOT EXISTS research_tasks (task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, user_id TEXT NOT NULL, source_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id, source_id))")


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


def sync_defense_tasks(user_id: str, session: DefenseSession) -> list[ResearchTask]:
    tasks = [ResearchTask(project_id=session.project_id, title=f"补强{turn.role.value}答辩", detail=turn.feedback or "补充证据并重答", source_type="defense", source_id=turn.turn_id, evidence_ids=turn.answer_evidence_ids) for turn in session.turns if turn.passed is False]
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
    return list_research_tasks(user_id, session.project_id)


def list_research_tasks(user_id: str, project_id: str) -> list[ResearchTask]:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn: rows = conn.execute("SELECT payload FROM research_tasks WHERE user_id=%s AND project_id=%s ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    else:
        with _sqlite_connection(database_url) as conn: rows = conn.execute("SELECT payload FROM research_tasks WHERE user_id=? AND project_id=? ORDER BY created_at ASC", (user_id, project_id)).fetchall()
    return [ResearchTask.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0]) for row in rows]


def _upsert_project_graph_postgres(conn: Any, user_id: str, project_id: str, incoming: EvidenceGraph) -> None:
    from .evidence_graph import merge_evidence_graphs
    row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=%s AND user_id=%s", (project_id, user_id)).fetchone()
    existing = EvidenceGraph.model_validate(row[0]) if row else None
    graph = merge_evidence_graphs(existing, incoming)
    conn.execute("""INSERT INTO project_evidence_graphs(project_id,user_id,payload,updated_at) VALUES(%s,%s,%s::jsonb,%s)
        ON CONFLICT(project_id) DO UPDATE SET payload=EXCLUDED.payload,updated_at=EXCLUDED.updated_at""", (project_id, user_id, json.dumps(graph.model_dump(mode="json"), ensure_ascii=False), _now()))


def _upsert_project_graph_sqlite(conn: sqlite3.Connection, user_id: str, project_id: str, incoming: EvidenceGraph) -> None:
    from .evidence_graph import merge_evidence_graphs
    row = conn.execute("SELECT payload FROM project_evidence_graphs WHERE project_id=? AND user_id=?", (project_id, user_id)).fetchone()
    existing = EvidenceGraph.model_validate(json.loads(row[0])) if row else None
    graph = merge_evidence_graphs(existing, incoming)
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
    database_url = get_settings().database_url
    payload = json.dumps(graph.model_dump(mode="json"), ensure_ascii=False)
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            conn.execute("UPDATE project_evidence_graphs SET payload=%s::jsonb,updated_at=%s WHERE project_id=%s AND user_id=%s", (payload, _now(), project_id, user_id))
    else:
        with _sqlite_connection(database_url) as conn:
            conn.execute("UPDATE project_evidence_graphs SET payload=?,updated_at=? WHERE project_id=? AND user_id=?", (payload, _now().isoformat(), project_id, user_id))
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
