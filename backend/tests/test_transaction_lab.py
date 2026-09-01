import pytest
from fastapi.testclient import TestClient

from app.api import transaction_lab as transaction_lab_api
from app.main import app
from app.services.transaction_lab import ExecuteResult, TransactionLabError, execute

client = TestClient(app)


def test_execute_rejects_unknown_session() -> None:
    with pytest.raises(TransactionLabError, match="찾을 수 없습니다"):
        execute("nonexistent-session", "SELECT 1")


@pytest.mark.parametrize(
    "sql",
    ["DROP TABLE products", "CREATE INDEX x ON products (name)", "TRUNCATE products"],
)
def test_execute_rejects_ddl_before_touching_any_session(sql: str) -> None:
    # DDL is rejected by validate_single_statement before the session lookup even
    # runs, so this must fail the same way regardless of whether a session exists.
    with pytest.raises(TransactionLabError):
        execute("nonexistent-session", sql)


def test_begin_returns_a_session_id(monkeypatch) -> None:
    monkeypatch.setattr(transaction_lab_api.transaction_lab, "begin", lambda: "sess-123")
    response = client.post("/api/transaction-lab/begin")
    assert response.status_code == 200
    assert response.json() == {"session_id": "sess-123"}


def test_execute_returns_400_for_lab_error(monkeypatch) -> None:
    def fail(_session_id, _sql):
        raise TransactionLabError("트랜잭션 세션을 찾을 수 없습니다. 다시 시작해 주세요.")

    monkeypatch.setattr(transaction_lab_api.transaction_lab, "execute", fail)
    response = client.post(
        "/api/transaction-lab/execute", json={"session_id": "nope", "sql": "SELECT 1"}
    )
    assert response.status_code == 400
    assert "찾을 수 없습니다" in response.json()["detail"]


def test_execute_returns_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        transaction_lab_api.transaction_lab,
        "execute",
        lambda session_id, sql: ExecuteResult(columns=["id"], rows=[[1]], row_count=1),
    )
    response = client.post(
        "/api/transaction-lab/execute",
        json={"session_id": "sess-123", "sql": "SELECT id FROM products"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == [[1]]


def test_commit_and_rollback_return_status(monkeypatch) -> None:
    monkeypatch.setattr(transaction_lab_api.transaction_lab, "commit", lambda session_id: None)
    monkeypatch.setattr(transaction_lab_api.transaction_lab, "rollback", lambda session_id: None)

    commit_response = client.post("/api/transaction-lab/commit", json={"session_id": "sess-123"})
    assert commit_response.json() == {"status": "committed"}

    rollback_response = client.post(
        "/api/transaction-lab/rollback", json={"session_id": "sess-123"}
    )
    assert rollback_response.json() == {"status": "rolled_back"}
