import asyncio
import random
import time

import httpx
import pytest
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
    StoreResult,
    _build_customer_rows,
    _build_order_specs,
    _build_product_rows,
    _run_independently,
)

client = TestClient(app)

_SAMPLE_COUNTS = StoreCounts(customers=24, products=18, orders=40)
_SUCCESSFUL_RESULTS = {
    "postgres": StoreResult(status="success", counts=_SAMPLE_COUNTS),
    "mongodb": StoreResult(status="success", counts=_SAMPLE_COUNTS),
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


def test_run_independently_isolates_store_failures() -> None:
    def ok() -> StoreCounts:
        return StoreCounts(customers=1, products=1, orders=1)

    def fail() -> StoreCounts:
        raise RuntimeError("boom")

    results = _run_independently({"postgres": ok, "mongodb": fail})

    assert results["postgres"].status == "success"
    assert results["postgres"].counts == StoreCounts(customers=1, products=1, orders=1)
    assert results["mongodb"].status == "failed"
    assert results["mongodb"].message == "MongoDB unavailable"


def test_dataset_status_reports_counts(monkeypatch) -> None:
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: _SUCCESSFUL_RESULTS)

    response = client.get("/api/dataset/status")

    assert response.status_code == 200
    body = response.json()
    assert body["postgres"] == {
        "status": "success",
        "counts": {"customers": 24, "products": 18, "orders": 40},
        "message": None,
    }
    assert body["mongodb"]["status"] == "success"


def test_generate_returns_service_result(monkeypatch) -> None:
    monkeypatch.setattr(dataset.dataset_service, "generate_dataset", lambda: _SUCCESSFUL_RESULTS)

    response = client.post("/api/dataset/generate")

    assert response.status_code == 200
    assert response.json()["postgres"]["counts"]["orders"] == 40


def test_reset_returns_service_result(monkeypatch) -> None:
    empty = StoreCounts(customers=0, products=0, orders=0)
    results = {
        "postgres": StoreResult(status="success", counts=empty),
        "mongodb": StoreResult(status="success", counts=empty),
    }
    monkeypatch.setattr(dataset.dataset_service, "reset_dataset", lambda: results)

    response = client.post("/api/dataset/reset")

    assert response.status_code == 200
    assert response.json()["postgres"]["counts"] == {"customers": 0, "products": 0, "orders": 0}


def test_one_store_failing_does_not_500_the_request(monkeypatch) -> None:
    partial = {
        "postgres": StoreResult(status="success", counts=_SAMPLE_COUNTS),
        "mongodb": StoreResult(status="failed", message="MongoDB unavailable"),
    }
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: partial)

    response = client.get("/api/dataset/status")

    assert response.status_code == 200
    body = response.json()
    assert body["postgres"]["status"] == "success"
    assert body["mongodb"] == {"status": "failed", "counts": None, "message": "MongoDB unavailable"}


def test_both_stores_failing_does_not_500_the_request(monkeypatch) -> None:
    both_down = {
        "postgres": StoreResult(status="failed", message="PostgreSQL unavailable"),
        "mongodb": StoreResult(status="failed", message="MongoDB unavailable"),
    }
    monkeypatch.setattr(dataset.dataset_service, "dataset_status", lambda: both_down)

    response = client.get("/api/dataset/status")

    assert response.status_code == 200
    body = response.json()
    assert body["postgres"]["status"] == "failed"
    assert body["mongodb"]["status"] == "failed"


def test_generate_dataset_reports_independent_store_failures(monkeypatch) -> None:
    def fake_generate() -> dict[str, StoreResult]:
        return {
            "postgres": StoreResult(status="failed", message="PostgreSQL unavailable"),
            "mongodb": StoreResult(status="success", counts=_SAMPLE_COUNTS),
        }

    monkeypatch.setattr(dataset.dataset_service, "generate_dataset", fake_generate)

    response = client.post("/api/dataset/generate")

    assert response.status_code == 200
    body = response.json()
    assert body["postgres"]["status"] == "failed"
    assert body["mongodb"]["status"] == "success"


@pytest.mark.asyncio
async def test_concurrent_generate_requests_are_serialized(monkeypatch) -> None:
    active = 0
    max_concurrent = 0

    def slow_generate() -> dict[str, StoreResult]:
        nonlocal active, max_concurrent
        active += 1
        max_concurrent = max(max_concurrent, active)
        time.sleep(0.2)
        active -= 1
        return _SUCCESSFUL_RESULTS

    monkeypatch.setattr(dataset.dataset_service, "generate_dataset", slow_generate)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        responses = await asyncio.gather(
            async_client.post("/api/dataset/generate"),
            async_client.post("/api/dataset/generate"),
            async_client.post("/api/dataset/generate"),
        )

    assert all(response.status_code == 200 for response in responses)
    assert max_concurrent == 1
