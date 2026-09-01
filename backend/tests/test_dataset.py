import random

from faker import Faker
from fastapi.testclient import TestClient

from app.api import dataset
from app.main import app
from app.services.dataset import (
    CUSTOMER_COUNT,
    ORDER_COUNT,
    PRODUCT_COUNT,
    OrderStatus,
    StoreCounts,
    _build_customer_rows,
    _build_order_specs,
    _build_product_rows,
)

client = TestClient(app)

_SAMPLE_COUNTS = {
    "postgres": StoreCounts(customers=24, products=18, orders=40),
    "mongodb": StoreCounts(customers=24, products=18, orders=40),
}


def test_generation_helpers_are_deterministic_and_consistent() -> None:
    Faker.seed(20260101)
    random.seed(20260101)
    fake = Faker()

    customers = _build_customer_rows(fake)
    products = _build_product_rows(fake)
    orders = _build_order_specs(products)

    assert len(customers) == CUSTOMER_COUNT
    assert len(products) == PRODUCT_COUNT
    assert len(orders) == ORDER_COUNT
    assert len({c["email"] for c in customers}) == CUSTOMER_COUNT
    assert len({p["sku"] for p in products}) == PRODUCT_COUNT

    for spec in orders:
        assert 0 <= spec["customer_index"] < CUSTOMER_COUNT
        assert isinstance(spec["status"], OrderStatus)
        assert 1 <= len(spec["items"]) <= 4
        for item in spec["items"]:
            assert 0 <= item["product_index"] < PRODUCT_COUNT
            assert item["unit_price_cents"] == products[item["product_index"]]["price_cents"]


def test_dataset_status_reports_counts(monkeypatch) -> None:
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: _SAMPLE_COUNTS)

    response = client.get("/api/dataset/status")

    assert response.status_code == 200
    body = response.json()
    assert body["postgres"] == {"customers": 24, "products": 18, "orders": 40}
    assert body["mongodb"] == {"customers": 24, "products": 18, "orders": 40}


def test_generate_calls_service_then_returns_status(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        dataset.dataset_service, "generate_dataset", lambda: calls.append("generate")
    )
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: _SAMPLE_COUNTS)

    response = client.post("/api/dataset/generate")

    assert response.status_code == 200
    assert calls == ["generate"]
    assert response.json()["postgres"]["orders"] == 40


def test_reset_calls_service_then_returns_status(monkeypatch) -> None:
    calls: list[str] = []
    empty = {
        "postgres": StoreCounts(customers=0, products=0, orders=0),
        "mongodb": StoreCounts(customers=0, products=0, orders=0),
    }
    monkeypatch.setattr(dataset.dataset_service, "reset_dataset", lambda: calls.append("reset"))
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: empty)

    response = client.post("/api/dataset/reset")

    assert response.status_code == 200
    assert calls == ["reset"]
    assert response.json()["postgres"] == {"customers": 0, "products": 0, "orders": 0}
