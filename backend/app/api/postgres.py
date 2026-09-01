import asyncio
import re
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import sql_console

router = APIRouter(prefix="/api/postgres", tags=["postgres"])

_PASSWORD_PATTERN = re.compile(r"password=\S+", re.IGNORECASE)


def _safe_error_message(exc: Exception) -> str:
    # Defensive only: exec_driver_sql errors are plain DBAPI messages and don't
    # normally include the DSN, but strip anything password-shaped just in case.
    return _PASSWORD_PATTERN.sub("password=***", str(exc))[:2000]


class ColumnSchema(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnSchema]


class TableRowsSchema(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total: int
    page: int
    page_size: int


class QueryRequest(BaseModel):
    sql: str


class QueryResultSchema(BaseModel):
    columns: list[str] | None
    rows: list[list[Any]] | None
    row_count: int
    truncated: bool
    duration_ms: float
    statement_type: str


@router.get("/tables", response_model=list[TableSchema])
async def get_tables() -> list[TableSchema]:
    tables = await asyncio.to_thread(sql_console.list_tables)
    return [TableSchema(**asdict(table)) for table in tables]


@router.get("/tables/{table_name}/rows", response_model=TableRowsSchema)
async def get_table_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> TableRowsSchema:
    try:
        result = await asyncio.to_thread(sql_console.get_table_rows, table_name, page, page_size)
    except sql_console.SqlConsoleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TableRowsSchema(**asdict(result))


@router.post("/query", response_model=QueryResultSchema)
async def execute_query(payload: QueryRequest) -> QueryResultSchema:
    try:
        result = await asyncio.to_thread(sql_console.run_query, payload.sql)
    except sql_console.SqlConsoleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface the DB's own error to the learner
        raise HTTPException(status_code=400, detail=_safe_error_message(exc)) from exc
    return QueryResultSchema(**asdict(result))
