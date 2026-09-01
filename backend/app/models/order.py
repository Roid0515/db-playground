from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.customer import Customer
from app.models.order_item import OrderItem


class OrderStatus(enum.StrEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Postgres uses an integer id and MongoDB an ObjectId, so the two stores have
    # no naturally shared key for "the same order" -- this is a stable, seeded
    # 1..N number assigned identically to both sides at generation time
    # specifically so Phase 5's comparison view can look up "order #7" in each
    # store and know it's really the same order.
    order_number: Mapped[int] = mapped_column(Integer, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    # values_callable: store the enum *value* ("pending") as the Postgres label,
    # not the member name ("PENDING") that SQLAlchemy uses by default -- otherwise
    # this disagrees with the MongoDB side, which stores OrderStatus.value directly.
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            values_callable=lambda cls: [item.value for item in cls],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
