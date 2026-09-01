import pytest
from fastapi.testclient import TestClient

from app.api import postgres as postgres_api
from app.main import app
from app.services.sql_console import (
    ColumnInfo,
    QueryResult,
    SqlConsoleError,
    TableInfo,
    TableRows,
    validate_single_statement,
)

client = TestClient(app)


@pytest.mark.parametrize(
    "sql", ["SELECT 1", "  select * from customers", "WITH x AS (SELECT 1) SELECT * FROM x"]
)
def test_validate_single_statement_accepts_allowed_keywords(sql: str) -> None:
    assert validate_single_statement(sql) in {"SELECT", "WITH"}


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers (email) VALUES ('a@b.com')",
        "UPDATE customers SET full_name = 'x'",
        "DELETE FROM customers",
    ],
)
def test_validate_single_statement_accepts_dml(sql: str) -> None:
    assert validate_single_statement(sql) in {"INSERT", "UPDATE", "DELETE"}


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN x int",
        "TRUNCATE customers",
        "CREATE TABLE x (id int)",
    ],
)
def test_validate_single_statement_rejects_ddl(sql: str) -> None:
    with pytest.raises(SqlConsoleError):
        validate_single_statement(sql)


def test_validate_single_statement_rejects_multiple_statements() -> None:
    with pytest.raises(SqlConsoleError):
        validate_single_statement("SELECT 1; DROP TABLE customers")


def test_validate_single_statement_rejects_empty() -> None:
    with pytest.raises(SqlConsoleError):
        validate_single_statement("   -- just a comment\n")


def test_validate_single_statement_ignores_comments() -> None:
    assert validate_single_statement("-- note\nSELECT 1 -- trailing") == "SELECT"


def test_get_tables_returns_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        postgres_api.sql_console,
        "list_tables",
        lambda: [
            TableInfo(
                name="customers",
                row_count=24,
                columns=[ColumnInfo(name="id", type="INTEGER")],
            )
        ],
    )
    response = client.get("/api/postgres/tables")
    assert response.status_code == 200
    assert response.json() == [
        {"name": "customers", "row_count": 24, "columns": [{"name": "id", "type": "INTEGER"}]}
    ]


def test_get_table_rows_returns_404_for_unknown_table(monkeypatch) -> None:
    def fail(_table_name, _page, _page_size):
        raise SqlConsoleError("테이블 'nope'을(를) 찾을 수 없습니다.")

    monkeypatch.setattr(postgres_api.sql_console, "get_table_rows", fail)
    response = client.get("/api/postgres/tables/nope/rows")
    assert response.status_code == 404


def test_get_table_rows_returns_data(monkeypatch) -> None:
    monkeypatch.setattr(
        postgres_api.sql_console,
        "get_table_rows",
        lambda table_name, page, page_size: TableRows(
            columns=["id", "email"], rows=[[1, "a@b.com"]], total=1, page=1, page_size=50
        ),
    )
    response = client.get("/api/postgres/tables/customers/rows")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["rows"] == [[1, "a@b.com"]]


def test_execute_query_rejects_invalid_sql(monkeypatch) -> None:
    def fail(_sql):
        raise SqlConsoleError("한 번에 하나의 SQL 문만 실행할 수 있습니다.")

    monkeypatch.setattr(postgres_api.sql_console, "run_query", fail)
    response = client.post("/api/postgres/query", json={"sql": "SELECT 1; DROP TABLE x"})
    assert response.status_code == 400
    assert "SQL" in response.json()["detail"]


def test_execute_query_returns_results(monkeypatch) -> None:
    monkeypatch.setattr(
        postgres_api.sql_console,
        "run_query",
        lambda sql: QueryResult(
            columns=["id"],
            rows=[[1], [2]],
            row_count=2,
            truncated=False,
            duration_ms=1.2,
            statement_type="SELECT",
        ),
    )
    response = client.post("/api/postgres/query", json={"sql": "SELECT id FROM customers"})
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["rows"] == [[1], [2]]


def test_execute_query_sanitizes_driver_errors(monkeypatch) -> None:
    def fail(_sql):
        raise RuntimeError('syntax error near "FORM" (password=super-secret should never appear)')

    monkeypatch.setattr(postgres_api.sql_console, "run_query", fail)
    response = client.post("/api/postgres/query", json={"sql": "SELECT 1 FORM x"})
    assert response.status_code == 400
    assert "super-secret" not in response.json()["detail"]
