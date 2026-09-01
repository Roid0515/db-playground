from fastapi.testclient import TestClient

from app.api import comparison as comparison_api
from app.main import app
from app.services.comparison import (
    ComparisonError,
    DocumentOrderView,
    OrderComparison,
    OrderSummary,
    RelationalOrderView,
)

client = TestClient(app)


def test_get_order_summaries_returns_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        comparison_api.comparison,
        "list_order_summaries",
        lambda: [
            OrderSummary(
                order_number=1,
                customer_name="Jane Doe",
                status="paid",
                item_count=2,
                total_cents=5000,
            )
        ],
    )
    response = client.get("/api/comparison/orders")
    assert response.status_code == 200
    assert response.json() == [
        {
            "order_number": 1,
            "customer_name": "Jane Doe",
            "status": "paid",
            "item_count": 2,
            "total_cents": 5000,
        }
    ]


def test_get_order_comparison_returns_404_for_unknown_order(monkeypatch) -> None:
    def fail(_order_number):
        raise ComparisonError("주문 번호 999을(를) PostgreSQL에서 찾을 수 없습니다.")

    monkeypatch.setattr(comparison_api.comparison, "get_order_comparison", fail)
    response = client.get("/api/comparison/orders/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]


def test_get_order_comparison_returns_both_views(monkeypatch) -> None:
    monkeypatch.setattr(
        comparison_api.comparison,
        "get_order_comparison",
        lambda order_number: OrderComparison(
            order_number=order_number,
            relational=RelationalOrderView(
                order={"id": 1, "order_number": order_number, "status": "paid", "created_at": "x"},
                customer={"id": 1, "full_name": "Jane Doe", "email": "jane@example.com"},
                items=[
                    {
                        "product_id": 1,
                        "product_name": "Widget",
                        "quantity": 2,
                        "unit_price_cents": 1000,
                    }
                ],
                sql="SELECT ...",
            ),
            document=DocumentOrderView(
                document={
                    "_id": "abc",
                    "order_number": order_number,
                    "items": [{"product_name": "Widget", "quantity": 2}],
                }
            ),
        ),
    )
    response = client.get("/api/comparison/orders/7")
    assert response.status_code == 200
    body = response.json()
    assert body["order_number"] == 7
    assert body["relational"]["customer"]["full_name"] == "Jane Doe"
    assert body["document"]["document"]["_id"] == "abc"
