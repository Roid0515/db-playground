"""Generates the same e-commerce dataset into PostgreSQL and MongoDB, modeled
the way each database naturally encourages: normalized tables with a join
(orders -> order_items -> products) in PostgreSQL, versus an order document
with its line items embedded directly in MongoDB.

Generation is seeded, so re-running "generate" always reproduces the same
dataset rather than piling up random rows across repeated calls.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from faker import Faker
from sqlalchemy import delete, func, select

from app.db.mongodb import get_database
from app.db.postgres import get_engine, session_scope
from app.models import Base, Customer, Order, OrderItem, OrderStatus, Product

SEED = 20260101
CUSTOMER_COUNT = 24
PRODUCT_COUNT = 18
ORDER_COUNT = 40


@dataclass(frozen=True)
class StoreCounts:
    customers: int
    products: int
    orders: int


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


def generate_dataset() -> StoreCounts:
    Base.metadata.create_all(get_engine())

    Faker.seed(SEED)
    random.seed(SEED)
    fake = Faker()

    customer_rows = _build_customer_rows(fake)
    product_rows = _build_product_rows(fake)
    order_specs = _build_order_specs(product_rows)

    _seed_postgres(customer_rows, product_rows, order_specs)
    _seed_mongodb(customer_rows, product_rows, order_specs)

    return StoreCounts(customers=CUSTOMER_COUNT, products=PRODUCT_COUNT, orders=ORDER_COUNT)


def reset_dataset() -> None:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        _clear_postgres(session)

    db = get_database()
    db.customers.delete_many({})
    db.products.delete_many({})
    db.orders.delete_many({})


def dataset_status() -> dict[str, StoreCounts]:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        postgres_counts = StoreCounts(
            customers=session.scalar(select(func.count()).select_from(Customer)) or 0,
            products=session.scalar(select(func.count()).select_from(Product)) or 0,
            orders=session.scalar(select(func.count()).select_from(Order)) or 0,
        )

    db = get_database()
    mongodb_counts = StoreCounts(
        customers=db.customers.count_documents({}),
        products=db.products.count_documents({}),
        orders=db.orders.count_documents({}),
    )
    return {"postgres": postgres_counts, "mongodb": mongodb_counts}
