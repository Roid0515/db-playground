# Phase 5 scope

## Included

- `GET /api/comparison/orders`: lists every order with a shared, human-facing `order_number`
- `GET /api/comparison/orders/{order_number}`: the same order rendered both ways -- PostgreSQL's joined tables and MongoDB's embedded document
- A "구조 비교" page: an order picker plus two panes side by side, each with a short explanation of what that structure trades off
- Backend and frontend tests, including a real-database check that the same `order_number` really does refer to the same order in both stores

## Deliberately deferred

Transactions and indexes remain in Phase 6; this phase is presentation over the existing Phase 2 dataset, not a new one.

## The order_number problem

PostgreSQL's `orders.id` is an auto-incrementing integer; MongoDB's `orders._id` is an `ObjectId`. The two stores are seeded from the same source data (`app/services/dataset.py`) but have no naturally shared key for "this is the same order" -- comparing "Postgres order #12" to "the 12th Mongo document" by insertion position would be fragile and would break the moment either store's ordering assumptions changed.

The fix: `dataset.py` now assigns an explicit `order_number` (1..`ORDER_COUNT`) to every order spec, and writes it into both the PostgreSQL `orders` row (`orders.order_number`, added via an Alembic migration, unique) and the MongoDB order document (`order_number` field). `app/services/comparison.py` looks up an order by this shared number in each store independently -- if either store is missing it (not yet generated, or the two stores have drifted), that's a distinct, correctly-reported 404, not a silent mismatch.

## Learning-flow decisions

- The relational pane shows the actual SQL (`JOIN customers ... JOIN order_items ... JOIN products ...`) that produced the rows, not just the rows themselves -- the join is the point being taught, not just the result.
- The document pane reuses `app/services/bson_utils.to_jsonable`, the same BSON-to-JSON serializer Phase 4's Mongo console uses, so `ObjectId`/`datetime` fields render the same way in both places.
- Documents/rows are read-only here; editing either representation belongs to Phase 3 (SQL console) or Phase 4 (Mongo console), not this comparison view.
