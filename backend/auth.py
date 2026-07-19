from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .models import AuthUser


TOKEN_TTL_DAYS = 30
PASSWORD_ITERATIONS = 210_000
security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    email: str
    name: str | None
    password_hash: str
    created_at: datetime


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


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64url_encode(expected), digest)
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(days=TOKEN_TTL_DAYS)).timestamp()),
    }
    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def verify_access_token(token: str) -> str:
    settings = get_settings()
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected), signature_b64):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload["exp"]) < int(_now().timestamp()):
            raise ValueError("expired")
        return str(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录") from exc


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


def init_auth_db() -> None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
        return

    with _sqlite_connection(database_url) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                name TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def delete_user_account(user_id: str) -> None:
    database_url = get_settings().database_url
    tables = ("research_behavior_events", "capability_profiles", "defense_sessions", "memo_versions", "research_tasks", "thesis_versions", "research_map_versions", "evidence_graph_versions", "project_materials", "project_evidence_graphs", "research_runs", "research_projects", "users")
    if _is_postgres_url(database_url):
        import psycopg
        with psycopg.connect(database_url) as conn:
            for table in tables: conn.execute(f"DELETE FROM {table} WHERE user_id=%s", (user_id,))
    else:
        with _sqlite_connection(database_url) as conn:
            for table in tables:
                conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        return


def _row_to_user_record(row: Any) -> UserRecord | None:
    if not row:
        return None
    if isinstance(row, sqlite3.Row):
        return UserRecord(
            user_id=row["user_id"],
            email=row["email"],
            name=row["name"],
            password_hash=row["password_hash"],
            created_at=_parse_dt(row["created_at"]),
        )
    return UserRecord(
        user_id=row[0],
        email=row[1],
        name=row[2],
        password_hash=row[3],
        created_at=_parse_dt(row[4]),
    )


def create_user(email: str, password: str, name: str | None = None) -> UserRecord:
    normalized_email = email.strip().lower()
    if "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码至少需要 8 位")

    user = UserRecord(
        user_id=f"USER-{uuid4().hex[:12]}",
        email=normalized_email,
        name=name.strip() if name and name.strip() else None,
        password_hash=hash_password(password),
        created_at=_now(),
    )
    database_url = get_settings().database_url

    try:
        if _is_postgres_url(database_url):
            import psycopg

            with psycopg.connect(database_url) as conn:
                conn.execute(
                    "INSERT INTO users (user_id, email, name, password_hash, created_at) VALUES (%s, %s, %s, %s, %s)",
                    (user.user_id, user.email, user.name, user.password_hash, user.created_at),
                )
            return user

        with _sqlite_connection(database_url) as conn:
            conn.execute(
                "INSERT INTO users (user_id, email, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user.user_id, user.email, user.name, user.password_hash, user.created_at.isoformat()),
            )
        return user
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="该邮箱已注册") from exc
        raise


def get_user_by_email(email: str) -> UserRecord | None:
    database_url = get_settings().database_url
    normalized_email = email.strip().lower()
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            row = conn.execute(
                "SELECT user_id, email, name, password_hash, created_at FROM users WHERE email = %s",
                (normalized_email,),
            ).fetchone()
        return _row_to_user_record(row)

    with _sqlite_connection(database_url) as conn:
        row = conn.execute(
            "SELECT user_id, email, name, password_hash, created_at FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    return _row_to_user_record(row)


def get_user_by_id(user_id: str) -> UserRecord | None:
    database_url = get_settings().database_url
    if _is_postgres_url(database_url):
        import psycopg

        with psycopg.connect(database_url) as conn:
            row = conn.execute(
                "SELECT user_id, email, name, password_hash, created_at FROM users WHERE user_id = %s",
                (user_id,),
            ).fetchone()
        return _row_to_user_record(row)

    with _sqlite_connection(database_url) as conn:
        row = conn.execute(
            "SELECT user_id, email, name, password_hash, created_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return _row_to_user_record(row)


def to_auth_user(user: UserRecord) -> AuthUser:
    return AuthUser(user_id=user.user_id, email=user.email, name=user.name, created_at=user.created_at)


def authenticate_user(email: str, password: str) -> UserRecord:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return user


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> AuthUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="请先登录")
    user_id = verify_access_token(credentials.credentials)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在，请重新登录")
    return to_auth_user(user)


def get_optional_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> AuthUser | None:
    if not credentials:
        return None
    try:
        user_id = verify_access_token(credentials.credentials)
        user = get_user_by_id(user_id)
        return to_auth_user(user) if user else None
    except HTTPException:
        return None
