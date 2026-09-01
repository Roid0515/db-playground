"""Phase 6: a real PostgreSQL transaction sandbox -- BEGIN, run statements,
then COMMIT or ROLLBACK, with a live "what does a separate connection see
right now" panel so the isolation between an open, uncommitted transaction
and the rest of the world is something a learner can watch happen, not just
read about.

Each open transaction holds a real psycopg connection in memory, keyed by an
opaque session_id the frontend carries between requests -- HTTP is
stateless, but an open SQL transaction is fundamentally tied to one physical
connection, so there's no way around holding one open server-side for as
long as the learner's transaction stays open. This is a single-learner local
app, so an in-process dict is sufficient; there's no multi-worker deployment
to share it across.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

import psycopg

from app.config import get_settings
from app.services.sql_console import SqlConsoleError, validate_single_statement

_IDLE_TIMEOUT_SECONDS = 5 * 60
_PEEK_SQL = "SELECT id, name, stock_quantity FROM products ORDER BY id LIMIT 5"


class TransactionLabError(ValueError):
    """User-facing validation error for the transaction sandbox."""


@dataclass
class _Session:
    connection: psycopg.Connection
    created_at: float
    last_used_at: float


_sessions: dict[str, _Session] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class ExecuteResult:
    columns: list[str] | None
    rows: list[list[Any]] | None
    row_count: int


def _connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().postgres_dsn, autocommit=False)


def _close(session: _Session, *, rollback: bool) -> None:
    try:
        if rollback:
            session.connection.rollback()
    finally:
        session.connection.close()


def _sweep_idle_locked() -> None:
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.last_used_at > _IDLE_TIMEOUT_SECONDS]
    for sid in expired:
        _close(_sessions.pop(sid), rollback=True)


def _pop_session(session_id: str) -> _Session:
    with _lock:
        session = _sessions.pop(session_id, None)
    if session is None:
        raise TransactionLabError("트랜잭션 세션을 찾을 수 없습니다. 다시 시작해 주세요.")
    return session


def close_all_sessions() -> int:
    """Force-closes every open sandbox session, rolling each back.

    Called before dataset generate/reset: an open, uncommitted transaction
    holding row locks on these same tables would otherwise block -- or even
    deadlock -- the reset's DELETEs indefinitely.
    """
    with _lock:
        session_ids = list(_sessions.keys())
        for session_id in session_ids:
            _close(_sessions.pop(session_id), rollback=True)
        return len(session_ids)


def begin() -> str:
    with _lock:
        _sweep_idle_locked()
        session_id = secrets.token_urlsafe(16)
        now = time.time()
        _sessions[session_id] = _Session(connection=_connect(), created_at=now, last_used_at=now)
        return session_id


def _run(conn: psycopg.Connection, sql: str) -> ExecuteResult:
    with conn.cursor() as cursor:
        cursor.execute(sql)
        if cursor.description:
            columns = [col.name for col in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]
            return ExecuteResult(columns=columns, rows=rows, row_count=len(rows))
        return ExecuteResult(columns=None, rows=None, row_count=cursor.rowcount)


def execute(session_id: str, sql: str) -> ExecuteResult:
    try:
        validate_single_statement(sql)
    except SqlConsoleError as exc:
        raise TransactionLabError(str(exc)) from exc

    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise TransactionLabError("트랜잭션 세션을 찾을 수 없습니다. 다시 시작해 주세요.")
        session.last_used_at = time.time()
        conn = session.connection

    try:
        return _run(conn, sql)
    except psycopg.Error as exc:
        conn.rollback()
        raise TransactionLabError(f"실행 오류: {exc}") from exc


def peek_within_session(session_id: str) -> ExecuteResult:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise TransactionLabError("트랜잭션 세션을 찾을 수 없습니다. 다시 시작해 주세요.")
        session.last_used_at = time.time()
        conn = session.connection
    return _run(conn, _PEEK_SQL)


def peek_committed_state() -> ExecuteResult:
    with psycopg.connect(get_settings().postgres_dsn, autocommit=True) as conn:
        return _run(conn, _PEEK_SQL)


def commit(session_id: str) -> None:
    session = _pop_session(session_id)
    try:
        session.connection.commit()
    finally:
        session.connection.close()


def rollback(session_id: str) -> None:
    session = _pop_session(session_id)
    _close(session, rollback=True)
