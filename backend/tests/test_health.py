from fastapi.testclient import TestClient

from app.api import health
from app.main import app

client = TestClient(app)


def test_root_describes_api() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/health"


def test_postgres_health_reports_healthy(monkeypatch) -> None:
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: "16.15")
    response = client.get("/api/health/postgres")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "PostgreSQL"
    assert body["version"] == "16.15"


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
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: "16.15")

    def fail(_settings) -> None:
        raise ConnectionError

    monkeypatch.setattr(health, "ping_mongodb", fail)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert set(response.json()["services"]) == {"postgres", "mongodb"}


def test_liveness_never_touches_the_databases(monkeypatch) -> None:
    def fail(_settings) -> None:
        raise ConnectionError

    monkeypatch.setattr(health, "ping_postgres", fail)
    monkeypatch.setattr(health, "ping_mongodb", fail)

    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_readiness_is_200_when_both_stores_are_healthy(monkeypatch) -> None:
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: "16.15")
    monkeypatch.setattr(health, "ping_mongodb", lambda _settings: "7.0.39")

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_is_503_when_a_store_is_down(monkeypatch) -> None:
    monkeypatch.setattr(health, "ping_postgres", lambda _settings: "16.15")

    def fail(_settings) -> None:
        raise ConnectionError

    monkeypatch.setattr(health, "ping_mongodb", fail)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["mongodb"]["status"] == "unavailable"
