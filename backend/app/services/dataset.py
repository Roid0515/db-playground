"""Generates the same e-commerce dataset into PostgreSQL and MongoDB, modeled
the way each database naturally encourages: normalized tables with a join
(orders -> order_items -> products) in PostgreSQL, versus an order document
with its line items embedded directly in MongoDB.

Generation is seeded, so re-running "generate" always reproduces the same
dataset rather than piling up random rows across repeated calls.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from faker import Faker
from sqlalchemy import delete, func, select

from app.db.mongodb import get_database
from app.db.postgres import session_scope
from app.models import Customer, Order, OrderItem, OrderStatus, Product

LOG = logging.getLogger("db_playground.dataset")

SEED = 20260101
CUSTOMER_COUNT = 24
PRODUCT_COUNT = 18
ORDER_COUNT = 40

_STORE_LABELS = {"postgres": "PostgreSQL", "mongodb": "MongoDB"}


@dataclass(frozen=True)
class StoreCounts:
    customers: int
    products: int
    orders: int


@dataclass(frozen=True)
class StoreResult:
    """Outcome of one store's half of a generate/reset/status operation.

    PostgreSQL and MongoDB fail independently in this app (unrelated
    processes, unrelated failure modes), so a request touching both must
    report each one's outcome separately rather than collapsing into a single
    500 the moment either store has a bad day -- a learner practicing against
    Postgres shouldn't be blocked by Mongo being down, and vice versa.
    """

    status: str  # "success" | "failed"
    counts: StoreCounts | None = None
    message: str | None = None


def _run_independently(
    operations: dict[str, Callable[[], StoreCounts]],
) -> dict[str, StoreResult]:
    results: dict[str, StoreResult] = {}
    for name, operation in operations.items():
        try:
            results[name] = StoreResult(status="success", counts=operation())
        except Exception:
            LOG.exception("%s operation failed", _STORE_LABELS[name])
            results[name] = StoreResult(
                status="failed", message=f"{_STORE_LABELS[name]} unavailable"
            )
    return results


def _build_customer_rows(fake: Faker) -> list[dict[str, Any]]:
    return [{"email": fake.unique.email(), "full_name": fake.name()} for _ in range(CUSTOMER_COUNT)]


def _build_product_rows(fake: Faker) -> list[dict[str, Any]]:
    return [
        {
            "sku": fake.unique.bothify("SKU-####??").upper(),
            "name": fake.unique.catch_phrase(),
            "description": fake.sentence(nb_words=12),
            "price_cents": random.randint(500, 50000),
            "stock_quantity": random.randint(0, 200),
        }
        for _ in range(PRODUCT_COUNT)
    ]


def _build_order_specs(product_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = []
    for _ in range(ORDER_COUNT):
        item_count = random.randint(1, min(4, PRODUCT_COUNT))
        product_indexes = random.sample(range(PRODUCT_COUNT), k=item_count)
        items = [
            {
                "product_index": index,
                "quantity": random.randint(1, 5),
                "unit_price_cents": product_rows[index]["price_cents"],
            }
            for index in product_indexes
        ]
        specs.append(
            {
                "customer_index": random.randrange(CUSTOMER_COUNT),
                "status": random.choice(list(OrderStatus)),
                "items": items,
            }
        )
    return specs


def _clear_postgres(session) -> None:
    session.execute(delete(OrderItem))
    session.execute(delete(Order))
    session.execute(delete(Product))
    session.execute(delete(Customer))


def _seed_postgres(
    customer_rows: list[dict[str, Any]],
    product_rows: list[dict[str, Any]],
    order_specs: list[dict[str, Any]],
) -> None:
    with session_scope() as session:
        _clear_postgres(session)

        customers = [Customer(**row) for row in customer_rows]
        products = [Product(**row) for row in product_rows]
        session.add_all(customers)
        session.add_all(products)
        session.flush()  # assign primary keys before orders reference them

        for spec in order_specs:
            order = Order(customer_id=customers[spec["customer_index"]].id, status=spec["status"])
            for item in spec["items"]:
                order.items.append(
                    OrderItem(
                        product_id=products[item["product_index"]].id,
                        quantity=item["quantity"],
                        unit_price_cents=item["unit_price_cents"],
                    )
                )
            session.add(order)


def _seed_mongodb(
    customer_rows: list[dict[str, Any]],
    product_rows: list[dict[str, Any]],
    order_specs: list[dict[str, Any]],
) -> None:
    db = get_database()
    db.customers.delete_many({})
    db.products.delete_many({})
    db.orders.delete_many({})

    now = datetime.now(UTC)
    customer_ids = db.customers.insert_many(
        [{**row, "created_at": now} for row in customer_rows]
    ).inserted_ids
    product_ids = db.products.insert_many(
        [{**row, "created_at": now} for row in product_rows]
    ).inserted_ids

    order_docs = [
        {
            "customer_id": customer_ids[spec["customer_index"]],
            "status": spec["status"].value,
            "created_at": now,
            "items": [
                {
                    "product_id": product_ids[item["product_index"]],
                    "product_name": product_rows[item["product_index"]]["name"],
                    "quantity": item["quantity"],
                    "unit_price_cents": item["unit_price_cents"],
                }
                for item in spec["items"]
            ],
        }
        for spec in order_specs
    ]
    db.orders.insert_many(order_docs)


def _generated_counts() -> StoreCounts:
    return StoreCounts(customers=CUSTOMER_COUNT, products=PRODUCT_COUNT, orders=ORDER_COUNT)


def _empty_counts() -> StoreCounts:
    return StoreCounts(customers=0, products=0, orders=0)


def _postgres_status() -> StoreCounts:
    with session_scope() as session:
        return StoreCounts(
            customers=session.scalar(select(func.count()).select_from(Customer)) or 0,
            products=session.scalar(select(func.count()).select_from(Product)) or 0,
            orders=session.scalar(select(func.count()).select_from(Order)) or 0,
        )


def _mongodb_status() -> StoreCounts:
    db = get_database()
    return StoreCounts(
        customers=db.customers.count_documents({}),
        products=db.products.count_documents({}),
        orders=db.orders.count_documents({}),
    )


def generate_dataset() -> dict[str, StoreResult]:
    Faker.seed(SEED)
    random.seed(SEED)
    fake = Faker()

    customer_rows = _build_customer_rows(fake)
    product_rows = _build_product_rows(fake)
    order_specs = _build_order_specs(product_rows)

    def generate_postgres() -> StoreCounts:
        _seed_postgres(customer_rows, product_rows, order_specs)
        return _generated_counts()

    def generate_mongodb() -> StoreCounts:
        _seed_mongodb(customer_rows, product_rows, order_specs)
        return _generated_counts()

    return _run_independently({"postgres": generate_postgres, "mongodb": generate_mongodb})


def reset_dataset() -> dict[str, StoreResult]:
    def reset_postgres() -> StoreCounts:
        with session_scope() as session:
            _clear_postgres(session)
        return _empty_counts()

    def reset_mongodb() -> StoreCounts:
        db = get_database()
        db.customers.delete_many({})
        db.products.delete_many({})
        db.orders.delete_many({})
        return _empty_counts()

    return _run_independently({"postgres": reset_postgres, "mongodb": reset_mongodb})


def dataset_status() -> dict[str, StoreResult]:
    return _run_independently({"postgres": _postgres_status, "mongodb": _mongodb_status})
