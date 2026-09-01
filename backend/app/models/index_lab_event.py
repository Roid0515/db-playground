from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IndexLabEvent(Base):
    """Bulk synthetic rows that exist only for Phase 6's index lab.

    The shopping-mall dataset (customers/products/orders) tops out at 40
    orders -- far too small for PostgreSQL's cost-based optimizer to ever
    prefer an index scan over a sequential one, so creating a demo index on
    orders.customer_id would never visibly change the query plan. This table
    is seeded with enough rows (see index_lab.py) that the crossover actually
    happens, so the plan change a learner sees is the planner's real decision,
    not a forced one.
    """

    __tablename__ = "index_lab_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deliberately left unindexed -- this is exactly the column index_lab.py
    # creates/drops its demo index on.
    customer_id: Mapped[int] = mapped_column(Integer)
