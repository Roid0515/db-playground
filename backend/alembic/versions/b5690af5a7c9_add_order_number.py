"""add order_number

Revision ID: b5690af5a7c9
Revises: d4c72cac53d4
Create Date: 2026-09-01 21:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5690af5a7c9"
down_revision: str | Sequence[str] | None = "d4c72cac53d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable at first so the column can be added to a table that may already
    # have rows (existing installs' generated dataset) without failing the
    # ALTER; the dataset is reseeded with real order_number values immediately
    # after by whoever generates data next, and the NOT NULL is only meaningful
    # for rows created after this migration anyway -- see comparison.py, which
    # only ever reads order_number from freshly-generated data.
    op.add_column("orders", sa.Column("order_number", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_orders_order_number", "orders", ["order_number"])


def downgrade() -> None:
    op.drop_constraint("uq_orders_order_number", "orders", type_="unique")
    op.drop_column("orders", "order_number")
