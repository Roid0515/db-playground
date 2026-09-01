# Phase 6 scope

## Included

- **Index lab**: `GET /api/index-lab/status`, `POST /api/index-lab/explain` (runs `EXPLAIN (ANALYZE, FORMAT JSON)`), `POST /api/index-lab/create-index` / `drop-index` -- lets a learner watch PostgreSQL's query planner switch from a sequential scan to an index scan
- **Transaction lab**: `POST /api/transaction-lab/{begin,execute,peek,commit,rollback}` and `GET /api/transaction-lab/peek-committed` -- a real, session-backed `BEGIN`/`COMMIT`/`ROLLBACK` sandbox with a side-by-side "what does my open transaction see vs. what does everyone else see" view
- A "트랜잭션 · 인덱스" page with one tab per lab
- Backend tests (mocked, plus real-database verification) and frontend tests for both

## Deliberately deferred

Nothing further was in this work order's scope; this closes out the phase-by-phase build. See Phase 7 for the reference notes that summarize everything above.

## Why the index lab needed its own bulk table

The index lab was originally built against `orders.customer_id` (an unindexed foreign key) in the existing 40-row shopping-mall dataset. Verified directly against a real PostgreSQL instance: creating that index changed *nothing* -- the planner kept choosing `Seq Scan` even with the index present, because scanning 40 rows really is cheaper than an index lookup at that size. That's correct planner behavior, not a bug, but it means the demo would never show a plan change, which defeats the entire point of the exercise.

The fix (`app/services/index_lab.py`, `app/models/index_lab_event.py`): a dedicated `index_lab_events` table, lazily bulk-seeded with 100,000 rows spread over 500 `customer_id` values (`INSERT ... SELECT ... FROM generate_series(...)`, done server-side in a single statement rather than round-tripping rows through Python) the first time the lab is opened. At that size the crossover is real: verified `Seq Scan` (~5 ms) becoming `Bitmap Heap Scan` (~0.06 ms) once the demo index exists, and reverting cleanly on drop. This table is excluded from Phase 3's Table Explorer (`sql_console._EXCLUDED_TABLES`) since it's implementation detail for this lab, not part of the shopping-mall narrative.

Only one specific, hardcoded index (`ix_index_lab_events_customer_id_demo`) is ever created or dropped -- this is a curated teaching action, not a general DDL passthrough; the SQL console still blocks all DDL. The app's database role can do this safely because it already owns every table it created via Alembic migrations (see `docs/architecture.md`'s "Decisions (Hardening)") -- full freedom inside its own database, no server-admin privilege involved.

## Why the transaction lab needs server-side session state

An open SQL transaction is fundamentally tied to one physical database connection -- there's no way to `BEGIN`, let a learner run a few statements over several HTTP requests, and `COMMIT` later without holding that connection open somewhere between requests. `app/services/transaction_lab.py` holds a small in-process `dict[session_id, psycopg.Connection]`, protected by a lock, with an opaque token handed to the frontend. This is a single-learner local app with no multi-process deployment, so an in-memory dict (rather than something like Redis) is the appropriate amount of infrastructure.

Two correctness details worth calling out:

- **DDL is still blocked inside the sandbox.** `execute()` reuses Phase 3's `sql_console.validate_single_statement` before touching any session, so the sandbox can't be used to sneak in a `DROP TABLE` any more than the regular SQL console can.
- **Dataset generate/reset force-closes every open sandbox session first** (`transaction_lab.close_all_sessions()`, called from `app/services/dataset.py`). An abandoned, uncommitted transaction holding row locks on `products`/`orders` would otherwise block -- or deadlock -- the reset's `DELETE`s indefinitely. Idle sessions (no activity for 5 minutes) are also swept opportunistically whenever a new one begins.

## Learning-flow decisions

- The index lab keeps the last two `EXPLAIN` results side by side, so the before/after plan change is visible without the learner needing to remember what the previous run said.
- The transaction lab's "other connection" panel queries a fixed, realistic representative statement (`products.stock_quantity`) rather than an arbitrary one, so the isolation being demonstrated is concrete and repeatable.
- A page refresh silently orphans any open transaction-lab session (the frontend doesn't persist the session id) -- it will sit idle until the 5-minute sweep or the next dataset reset closes it. Acceptable for a local teaching tool; not something a production transaction API could get away with.
