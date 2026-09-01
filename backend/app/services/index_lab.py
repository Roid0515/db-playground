"""Phase 6: lets a learner watch PostgreSQL's own query planner change its
mind when an index appears -- run EXPLAIN ANALYZE, add a demo index, run it
again, and see the plan switch from a sequential scan to an index scan.

Runs against a dedicated bulk practice table (index_lab_events), not the
shopping-mall dataset: that dataset tops out at 40 orders, and Postgres's
cost-based optimizer correctly keeps preferring a sequential scan over an
index scan at that size no matter what -- scanning 40 rows really is cheaper
than an index lookup. Verified directly: creating the demo index on
orders.customer_id never changed the plan. index_lab_events is seeded with
enough rows that the crossover actually happens, so the plan change a
learner sees is the planner's genuine decision, not a forced one.

Only this one specific, hardcoded index is ever created or dropped here --
this is a curated teaching action, not a general DDL passthrough (the SQL
console still blocks all DDL). The app's own database role can safely do
this because it already owns every table it created via migrations (see
app/desktop/postgres_runtime.py) -- full freedom inside its own database, no
server-admin privilege involved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.postgres import session_scope

TABLE_NAME = "index_lab_events"
COLUMN_NAME = "customer_id"
INDEX_NAME = "ix_index_lab_events_customer_id_demo"

# 100k rows spread over 500 customer ids (~200 rows/id, ~0.2% selectivity) is
# comfortably past the point where Postgres's planner switches to an index
# scan once one exists, while staying fast to seed (a single server-side
# INSERT ... SELECT, no Python round-trip per row).
SEED_ROW_COUNT = 100_000
SEED_CUSTOMER_ID_RANGE = 500

_COUNT_SQL = text(f"SELECT count(*) FROM {TABLE_NAME}")
_SEED_SQL = text(
    f"INSERT INTO {TABLE_NAME} (customer_id) "
    f"SELECT (random() * {SEED_CUSTOMER_ID_RANGE - 1} + 1)::int "
    f"FROM generate_series(1, {SEED_ROW_COUNT})"
)
_PICK_CUSTOMER_ID_SQL = text(f"SELECT {COLUMN_NAME} FROM {TABLE_NAME} ORDER BY id LIMIT 1")
# customer_id is bound as a real parameter (not inlined as a correlated
# subquery) specifically so the plan this produces is exactly one node -- a
# subquery to pick a representative id would add its own InitPlan, which
# (being a lookup by primary key) always uses an index of its own and would
# corrupt used_index below into reporting "yes" regardless of whether the
# *demo* index exists.
_EXPLAIN_SQL = text(
    f"EXPLAIN (ANALYZE, FORMAT JSON) SELECT * FROM {TABLE_NAME} WHERE {COLUMN_NAME} = :customer_id"
)
_INDEX_EXISTS_SQL = text("SELECT 1 FROM pg_indexes WHERE indexname = :name")
_CREATE_INDEX_SQL = text(f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE_NAME} ({COLUMN_NAME})")
_DROP_INDEX_SQL = text(f"DROP INDEX IF EXISTS {INDEX_NAME}")


@dataclass(frozen=True)
class IndexStatus:
    table: str
    column: str
    index_name: str
    index_exists: bool
    row_count: int


@dataclass(frozen=True)
class ExplainResult:
    node_type: str
    used_index: bool
    execution_time_ms: float
    planning_time_ms: float
    row_count: int
    plan_text: str


def _ensure_seed_data(session: Session) -> None:
    if (session.execute(_COUNT_SQL).scalar() or 0) == 0:
        session.execute(_SEED_SQL)


def _index_exists(session: Session) -> bool:
    return session.execute(_INDEX_EXISTS_SQL, {"name": INDEX_NAME}).first() is not None


def index_status() -> IndexStatus:
    with session_scope() as session:
        _ensure_seed_data(session)
        return IndexStatus(
            table=TABLE_NAME,
            column=COLUMN_NAME,
            index_name=INDEX_NAME,
            index_exists=_index_exists(session),
            row_count=session.execute(_COUNT_SQL).scalar() or 0,
        )


def _uses_index(node: dict[str, Any]) -> bool:
    if "Index" in node.get("Node Type", ""):
        return True
    return any(_uses_index(child) for child in node.get("Plans", []))


def explain_query() -> ExplainResult:
    with session_scope() as session:
        _ensure_seed_data(session)
        customer_id = session.execute(_PICK_CUSTOMER_ID_SQL).scalar()
        if customer_id is None:
            raise ValueError("실습용 데이터가 없습니다. 잠시 후 다시 시도해 주세요.")
        raw = session.execute(_EXPLAIN_SQL, {"customer_id": customer_id}).scalar()
    plan_rows = raw if isinstance(raw, list) else json.loads(raw)
    top = plan_rows[0]
    plan = top["Plan"]
    return ExplainResult(
        node_type=plan.get("Node Type", "Unknown"),
        used_index=_uses_index(plan),
        execution_time_ms=top.get("Execution Time", 0.0),
        planning_time_ms=top.get("Planning Time", 0.0),
        row_count=plan.get("Actual Rows", 0),
        plan_text=json.dumps(top, ensure_ascii=False, indent=2),
    )


def create_index() -> IndexStatus:
    with session_scope() as session:
        session.execute(_CREATE_INDEX_SQL)
    return index_status()


def drop_index() -> IndexStatus:
    with session_scope() as session:
        session.execute(_DROP_INDEX_SQL)
    return index_status()
