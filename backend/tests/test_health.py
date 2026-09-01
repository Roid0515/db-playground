from fastapi.testclient import TestClient

from app.api import health
from app.main import app

client = TestClient(app)


def test_root_describes_api() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/health"


def test_postgres_health_reports_healthy(monkeypatch) -> None:
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: None)
    response = client.get("/api/health/postgres")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "PostgreSQL"


def test_mongodb_health_hides_connection_error(monkeypatch) -> None:
    def fail(_settings) -> None:
        raise RuntimeError("mongodb://user:secret@internal-host")

    monkeypatch.setattr(health, "ping_mongodb", fail)
    response = client.get("/api/health/mongodb")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "unavailable"
    assert "secret" not in body["message"]


def test_combined_health_is_degraded_when_one_service_fails(monkeypatch) -> None:
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: None)

    def fail(_settings) -> None:
        raise ConnectionError

    monkeypatch.setattr(health, "ping_mongodb", fail)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert set(response.json()["services"]) == {"postgres", "mongodb"}
