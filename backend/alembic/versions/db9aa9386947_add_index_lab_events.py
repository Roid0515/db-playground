"""add index_lab_events

Revision ID: db9aa9386947
Revises: b5690af5a7c9
Create Date: 2026-09-01 22:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db9aa9386947"
down_revision: str | Sequence[str] | None = "b5690af5a7c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "index_lab_events",
        sa.Column("id", sa.Integer(), nullable=False),
        # Deliberately left unindexed -- app/services/index_lab.py creates/drops
        # its demo index on this column to show the query plan change.
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("index_lab_events")
