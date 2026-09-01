"""Table browsing and ad-hoc SQL execution against the practice PostgreSQL database.

This is a local, single-user learning sandbox: the point of the SQL console is
letting the learner run their own SELECT/INSERT/UPDATE/DELETE against their own
practice data. What's enforced here is narrower than "safe SQL" in general --
one statement at a time, no DDL (so the schema stays whatever Alembic put
there), a query timeout, and a cap on how many rows come back.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Row

from app.config import get_settings
from app.db.postgres import get_engine, session_scope

_ALLOWED_LEADING_KEYWORDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "WITH"}
# alembic_version is Alembic's own bookkeeping table; index_lab_events is a
# 100k-row bulk table that exists only for Phase 6's index lab (see
# app/services/index_lab.py) -- neither is part of the shopping-mall dataset
# this Table Explorer is meant to showcase, so both would just be confusing
# noise here.
_EXCLUDED_TABLES = {"alembic_version", "index_lab_events"}


class SqlConsoleError(ValueError):
    """A user-facing validation error, distinct from a database driver error."""


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    row_count: int
    columns: list[ColumnInfo]


@dataclass(frozen=True)
class TableRows:
    columns: list[str]
    rows: list[list[Any]]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class QueryResult:
    columns: list[str] | None
    rows: list[list[Any]] | None
    row_count: int
    truncated: bool
    duration_ms: float
    statement_type: str


def _strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--[^\n]*", "", sql)
    return re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.DOTALL)


def _leading_keyword(sql: str) -> str:
    match = re.match(r"\s*([A-Za-z]+)", sql)
    return match.group(1).upper() if match else ""


def validate_single_statement(raw_sql: str) -> str:
    """Returns the statement's leading keyword, or raises SqlConsoleError."""
    stripped = _strip_sql_comments(raw_sql).strip()
    if not stripped:
        raise SqlConsoleError("실행할 SQL을 입력하세요.")

    body = stripped[:-1] if stripped.endswith(";") else stripped
    if ";" in body:
        raise SqlConsoleError("한 번에 하나의 SQL 문만 실행할 수 있습니다.")

    keyword = _leading_keyword(body)
    if keyword not in _ALLOWED_LEADING_KEYWORDS:
        raise SqlConsoleError(
            f"'{keyword or '(빈 문장)'}' 문은 지원하지 않습니다. "
            "SELECT, INSERT, UPDATE, DELETE만 실행할 수 있습니다. "
            "스키마를 바꾸려면 Alembic 마이그레이션을 사용하세요."
        )
    return keyword


def _jsonable(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def _row_to_list(row: Row) -> list[Any]:
    return [_jsonable(value) for value in row]


def list_tables() -> list[TableInfo]:
    engine = get_engine()
    inspector = inspect(engine)
    names = [name for name in inspector.get_table_names() if name not in _EXCLUDED_TABLES]

    tables = []
    with session_scope() as session:
        for name in sorted(names):
            columns = [
                ColumnInfo(name=col["name"], type=str(col["type"]))
                for col in inspector.get_columns(name)
            ]
            count = session.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar_one()
            tables.append(TableInfo(name=name, row_count=count, columns=columns))
    return tables


def get_table_rows(table_name: str, page: int, page_size: int) -> TableRows:
    engine = get_engine()
    inspector = inspect(engine)
    valid_names = set(inspector.get_table_names()) - _EXCLUDED_TABLES
    if table_name not in valid_names:
        raise SqlConsoleError(f"테이블 '{table_name}'을(를) 찾을 수 없습니다.")

    page_size = max(1, min(page_size, get_settings().query_max_rows))
    offset = max(page - 1, 0) * page_size

    pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    order_clause = ""
    if pk_columns:
        quoted = ", ".join(f'"{col}"' for col in pk_columns)
        order_clause = f" ORDER BY {quoted}"

    with session_scope() as session:
        total = session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
        result = session.execute(
            text(f'SELECT * FROM "{table_name}"{order_clause} LIMIT :limit OFFSET :offset'),
            {"limit": page_size, "offset": offset},
        )
        columns = list(result.keys())
        rows = [_row_to_list(row) for row in result.fetchall()]

    return TableRows(columns=columns, rows=rows, total=total, page=page, page_size=page_size)


def run_query(raw_sql: str) -> QueryResult:
    statement_type = validate_single_statement(raw_sql)
    settings = get_settings()
    max_rows = settings.query_max_rows
    timeout_ms = settings.query_timeout_seconds * 1000

    started = time.perf_counter()
    with session_scope() as session:
        session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
        # exec_driver_sql sends the learner's SQL to the driver verbatim. Unlike
        # session.execute(text(...)), it does not scan the string for ":name"
        # bind-parameter syntax, which would otherwise misfire on legitimate SQL
        # containing literal colons (time literals, JSON paths, casts, etc).
        result = session.connection().exec_driver_sql(raw_sql)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        if result.returns_rows:
            columns = list(result.keys())
            fetched = result.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            rows = [_row_to_list(row) for row in fetched[:max_rows]]
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                duration_ms=duration_ms,
                statement_type=statement_type,
            )

        affected = result.rowcount if result.rowcount and result.rowcount >= 0 else 0
        return QueryResult(
            columns=None,
            rows=None,
            row_count=affected,
            truncated=False,
            duration_ms=duration_ms,
            statement_type=statement_type,
        )
