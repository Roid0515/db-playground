"""Phase 5: side-by-side comparison of the same order as PostgreSQL sees it
(normalized tables joined together) versus how MongoDB sees it (one order
document with its line items embedded).

Postgres uses an integer id and MongoDB an ObjectId, so the two stores have no
naturally shared key for "the same order" -- dataset.py seeds an identical
order_number (1..N) into both sides specifically so this module can look up
"order #7" in each store and know it's really the same order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.db.mongodb import get_database
from app.db.postgres import session_scope
from app.models import Order, OrderItem
from app.services.bson_utils import to_jsonable


class ComparisonError(ValueError):
    """Raised when the requested order isn't present in one or both stores."""


@dataclass(frozen=True)
class OrderSummary:
    order_number: int
    customer_name: str
    status: str
    item_count: int
    total_cents: int


@dataclass(frozen=True)
class RelationalOrderView:
    order: dict[str, Any]
    customer: dict[str, Any]
    items: list[dict[str, Any]]
    sql: str


@dataclass(frozen=True)
class DocumentOrderView:
    document: dict[str, Any]


@dataclass(frozen=True)
class OrderComparison:
    order_number: int
    relational: RelationalOrderView
    document: DocumentOrderView


def _display_sql(order_number: int) -> str:
    return (
        "SELECT c.full_name, c.email, p.name AS product_name, oi.quantity, oi.unit_price_cents\n"
        "FROM orders o\n"
        "JOIN customers c ON c.id = o.customer_id\n"
        "JOIN order_items oi ON oi.order_id = o.id\n"
        "JOIN products p ON p.id = oi.product_id\n"
        f"WHERE o.order_number = {order_number};"
    )


def list_order_summaries() -> list[OrderSummary]:
    with session_scope() as session:
        orders = session.scalars(
            select(Order)
            .where(Order.order_number.is_not(None))
            .order_by(Order.order_number)
            .options(selectinload(Order.items), joinedload(Order.customer))
        ).all()
        return [
            OrderSummary(
                order_number=order.order_number,
                customer_name=order.customer.full_name,
                status=order.status.value,
                item_count=len(order.items),
                total_cents=sum(item.quantity * item.unit_price_cents for item in order.items),
            )
            for order in orders
        ]


def get_order_comparison(order_number: int) -> OrderComparison:
    with session_scope() as session:
        order = session.scalar(
            select(Order)
            .where(Order.order_number == order_number)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                joinedload(Order.customer),
            )
        )
        if order is None:
            raise ComparisonError(
                f"주문 번호 {order_number}을(를) PostgreSQL에서 찾을 수 없습니다."
            )

        relational = RelationalOrderView(
            order={
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status.value,
                "created_at": order.created_at.isoformat(),
            },
            customer={
                "id": order.customer.id,
                "full_name": order.customer.full_name,
                "email": order.customer.email,
            },
            items=[
                {
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price_cents": item.unit_price_cents,
                }
                for item in order.items
            ],
            sql=_display_sql(order_number),
        )

    doc = get_database().orders.find_one({"order_number": order_number})
    if doc is None:
        raise ComparisonError(f"주문 번호 {order_number}을(를) MongoDB에서 찾을 수 없습니다.")

    return OrderComparison(
        order_number=order_number,
        relational=relational,
        document=DocumentOrderView(document=to_jsonable(doc)),
    )
