from fastapi.testclient import TestClient

from app.api import index_lab as index_lab_api
from app.main import app
from app.services.index_lab import ExplainResult, IndexStatus

client = TestClient(app)


def test_get_status_returns_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        index_lab_api.index_lab,
        "index_status",
        lambda: IndexStatus(
            table="index_lab_events",
            column="customer_id",
            index_name="ix_index_lab_events_customer_id_demo",
            index_exists=False,
            row_count=100_000,
        ),
    )
    response = client.get("/api/index-lab/status")
    assert response.status_code == 200
    assert response.json() == {
        "table": "index_lab_events",
        "column": "customer_id",
        "index_name": "ix_index_lab_events_customer_id_demo",
        "index_exists": False,
        "row_count": 100_000,
    }


def test_explain_reports_whether_index_was_used(monkeypatch) -> None:
    monkeypatch.setattr(
        index_lab_api.index_lab,
        "explain_query",
        lambda: ExplainResult(
            node_type="Seq Scan",
            used_index=False,
            execution_time_ms=1.2,
            planning_time_ms=0.3,
            row_count=1,
            plan_text="{}",
        ),
    )
    response = client.post("/api/index-lab/explain")
    assert response.status_code == 200
    body = response.json()
    assert body["node_type"] == "Seq Scan"
    assert body["used_index"] is False


def test_create_index_returns_updated_status(monkeypatch) -> None:
    monkeypatch.setattr(
        index_lab_api.index_lab,
        "create_index",
        lambda: IndexStatus(
            table="index_lab_events",
            column="customer_id",
            index_name="ix_index_lab_events_customer_id_demo",
            index_exists=True,
            row_count=100_000,
        ),
    )
    response = client.post("/api/index-lab/create-index")
    assert response.status_code == 200
    assert response.json()["index_exists"] is True


def test_drop_index_returns_updated_status(monkeypatch) -> None:
    monkeypatch.setattr(
        index_lab_api.index_lab,
        "drop_index",
        lambda: IndexStatus(
            table="index_lab_events",
            column="customer_id",
            index_name="ix_index_lab_events_customer_id_demo",
            index_exists=False,
            row_count=100_000,
        ),
    )
    response = client.post("/api/index-lab/drop-index")
    assert response.status_code == 200
    assert response.json()["index_exists"] is False
