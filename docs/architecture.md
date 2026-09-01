# Architecture

```text
Browser :5173
  └─ React dashboard
       ├─ GET  /api/health           → FastAPI :8000  (dashboard status, always 200)
       │                                 ├─ SELECT 1  → PostgreSQL :5432 (as the app's own least-privilege role)
       │                                 └─ ping      → MongoDB :27017   (as the app's own least-privilege user)
       ├─ GET  /api/health/live      → FastAPI :8000  (process is up; touches neither database)
       ├─ GET  /api/health/ready     → FastAPI :8000  (200 only if both stores are healthy, else 503)
       ├─ GET  /api/dataset/status   → FastAPI :8000
       ├─ POST /api/dataset/generate → FastAPI :8000  (serialized by a process-wide asyncio.Lock)
       │                                 ├─ SQLAlchemy session → PostgreSQL (customers, products, orders, order_items)
       │                                 └─ pymongo            → MongoDB (customers, products, orders with embedded items)
       ├─ POST /api/dataset/reset    → FastAPI :8000  (same lock)
       ├─ GET  /api/postgres/tables            → FastAPI :8000 → inspect(engine) + COUNT(*) → PostgreSQL
       ├─ GET  /api/postgres/tables/{t}/rows   → FastAPI :8000 → SELECT ... LIMIT/OFFSET     → PostgreSQL
       ├─ POST /api/postgres/query             → FastAPI :8000 → exec_driver_sql(sql), statement_timeout set → PostgreSQL
       ├─ GET  /api/mongodb/collections            → FastAPI :8000 → list_collection_names() + count_documents → MongoDB
       ├─ GET  /api/mongodb/collections/{c}/documents → FastAPI :8000 → find().skip().limit() → MongoDB
       ├─ POST /api/mongodb/query              → FastAPI :8000 → constrained mongosh-syntax parser → MongoDB
       ├─ GET  /api/comparison/orders           → FastAPI :8000 → PostgreSQL (order summaries)
       ├─ GET  /api/comparison/orders/{n}       → FastAPI :8000 → PostgreSQL join + MongoDB find_one, matched by order_number
       ├─ GET  /api/index-lab/status            → FastAPI :8000 → pg_indexes lookup → PostgreSQL
       ├─ POST /api/index-lab/explain           → FastAPI :8000 → EXPLAIN (ANALYZE, FORMAT JSON) → PostgreSQL
       ├─ POST /api/index-lab/{create,drop}-index → FastAPI :8000 → CREATE/DROP INDEX (one hardcoded index) → PostgreSQL
       └─ POST /api/transaction-lab/{begin,execute,peek,commit,rollback} → FastAPI :8000
                                        → a held-open psycopg connection per session_id → PostgreSQL
```

## Decisions (Phase 1)

- **Localhost-first:** only the configured frontend origin is accepted; there's no arbitrary database connection form.
- **Short-lived health connections:** health checks create and close their own connections so the foundation stays simple.
- **Parallel checks:** PostgreSQL and MongoDB pings run concurrently in worker threads, keeping FastAPI's event loop responsive.
- **Safe degradation:** a database outage returns a `degraded` aggregate status and a generic message rather than an HTTP 500 or raw driver error.
- **Browser API address:** `VITE_API_URL` is compiled into the frontend because the browser cannot resolve Docker service names.

## Decisions (Phase 2)

- **Pooled connections for dataset work:** unlike the short-lived health-check connections, `app.db.postgres.get_engine()` and `app.db.mongodb.get_client()` are process-wide singletons (SQLAlchemy's own pool; pymongo's built-in pool), since dataset generation does many more round trips than a single ping.
- **Same seed, two shapes:** `app/services/dataset.py` generates one seeded, deterministic set of customers/products/orders and writes it into both stores using the model each store encourages -- see `docs/phase-2.md` for why the orders are modeled differently (normalized + joined in PostgreSQL vs. embedded in MongoDB).
- **Schema lifecycle is Alembic's job, end to end:** both the desktop runtime (`app/desktop/migrations.py`) and the Docker backend's entrypoint run `alembic upgrade head` on startup, before serving anything. `app/services/dataset.py` no longer calls `Base.metadata.create_all()` at all -- see "Decisions (Hardening)" below for why that changed after Phase 2.
- **Status/generate/reset return the same shape:** all three dataset endpoints return per-store row/document counts, so the frontend (and curl) can treat "just generated" and "just checked" identically.
- **Phase boundary:** query consoles, row/document browsing or editing, schema diagrams, comparison lessons, transactions, and indexes are deferred until the phase that uses them.

## Decisions (Phase 3)

- **Live schema introspection, not a hardcoded table list:** `app/services/sql_console.py` uses SQLAlchemy's `inspect(engine)` for table/column metadata, so the console reflects whatever's actually in the database (including tables a learner creates through other means), not just the four models this app ships with.
- **DML allowed, DDL is not:** the console accepts SELECT/INSERT/UPDATE/DELETE so learners can practice real writes, but rejects anything that would change the schema -- see `docs/phase-3.md` for the full safety model and why raw SQL execution uses `exec_driver_sql` instead of `text()`.
- **Writes invalidate broadly:** a successful query invalidates the table list, row browser, and dashboard dataset-status React Query caches together, so effects of a learner's own INSERT/UPDATE/DELETE show up everywhere immediately.
- **Phase boundary:** MongoDB browsing/querying, schema diagrams, comparison lessons, transactions, and indexes are deferred until the phase that uses them.

## Decisions (Phase 4)

- **An operation allowlist instead of trying to parse JavaScript:** `app/services/mongo_console.py` accepts only `db.<collection>.<op>(<args>)` with `<op>` in a fixed set (find/aggregate/countDocuments/insert*/update*/delete*) and `<args>` as strict JSON -- see `docs/phase-4.md` for why a real mongosh grammar wasn't worth building.
- **Documents render as JSON, not table rows:** unlike Phase 3's `ResultsTable`, MongoDB's schema-flexible documents are shown as formatted JSON cards, since a fixed set of table columns would misrepresent the whole point of a document store.
- **BSON serialization is shared, not duplicated:** `app/services/bson_utils.to_jsonable` converts `ObjectId`/`datetime` to JSON-safe values; both the Mongo console and Phase 5's comparison view use it.
- **Phase boundary:** structure comparison, transactions, and indexes are deferred until the phase that uses them.

## Decisions (Phase 5)

- **A shared `order_number`, not positional matching:** PostgreSQL's `orders.id` and MongoDB's `orders._id` have no natural correspondence, so `dataset.py` seeds an explicit, identical `order_number` (1..N) into both stores at generation time. `app/services/comparison.py` looks each side up independently by that number -- see `docs/phase-5.md` for the real bug this avoids.
- **The relational pane shows its own SQL**, not just the joined result, since the join itself (not just its output) is what Phase 3 already taught and this phase is reinforcing by contrast.
- **Phase boundary:** transactions and indexes are deferred until Phase 6.

## Decisions (Phase 6)

- **The index lab runs against a dedicated 100k-row table, not the shopping-mall dataset.** Verified directly: creating an index on the 40-row `orders` table never changed PostgreSQL's query plan -- a sequential scan over 40 rows is genuinely cheaper than an index lookup, so the demo would be a no-op. `index_lab_events` (`app/models/index_lab_event.py`) is lazily bulk-seeded (a single server-side `INSERT ... SELECT ... generate_series(...)`, not a Python loop) the first time the lab loads, and is excluded from Phase 3's Table Explorer since it isn't part of the narrative dataset.
- **Only one specific, hardcoded index is ever created or dropped** by the index lab -- a curated teaching action, not a general DDL passthrough; the SQL console still blocks all DDL everywhere else.
- **The transaction lab holds a real connection open per session**, keyed by an opaque `session_id` the frontend carries between requests, because an open SQL transaction is fundamentally tied to one physical connection and there's no way around that for a genuine `BEGIN`/`COMMIT`/`ROLLBACK` demo. An in-process dict is sufficient (single-learner local app, no multi-process deployment).
- **Dataset generate/reset force-closes every open transaction-lab session first**, rolling each back, so an abandoned open transaction can't block or deadlock the reset's deletes.
- **Phase boundary:** none remaining in this work order -- see Phase 7 for the closing reference notes.

## Decisions (Phase 7)

- **No backend at all.** The learning notes are static content that doesn't depend on the current dataset; adding an endpoint just to serve hardcoded strings the frontend could hold directly would be pure overhead.

## Decisions (Hardening)

A security/reliability pass followed Phase 3, deliberately without adding new learning features (existing UI and both run modes were preserved). See `AGENTS.md`'s "Security and reliability" section for the day-to-day rules this leaves behind; the reasoning:

- **Neither database account the app uses is privileged.** PostgreSQL's `initdb` bootstrap role is inherently a superuser, and MongoDB's Docker image bootstraps a `root` admin -- but the app itself (health checks, dataset generation, the SQL console) always connects as a separate role/user scoped to just the `db_playground` database (`NOSUPERUSER` on the Postgres side, `readWrite`+`dbAdmin` with no `root` role on the Mongo side). The SQL console already blocked DDL at the application layer since Phase 3; this adds a second, independent layer at the database privilege level, so a bug in that validation can't reach past the app's own database either.
- **`/api/health/ready` exists because `/api/health` can't safely mean "ready."** The dashboard endpoint always returns 200 (with a `degraded` body) so the frontend has something to render either way; that's indistinguishable from "fully up" to anything that only checks the HTTP status code, which is exactly what Docker healthchecks and the desktop app's startup poll do. `/ready` returns 503 when either store isn't healthy; `/live` never touches either database, so a slow/unavailable database can't make the process itself look unhealthy.
- **A crashed backend gets cleaned up, not just detected.** `app/desktop/runtime.py` puts itself and every child it spawns (postgres, mongod) in one process group (`os.setpgrp()`). The Swift launcher's normal `stop()` still just sends `SIGTERM` to the one process it tracks, relying on that process's own `finally` block to shut its children down gracefully -- but if the backend is ever killed outright (crash, `SIGKILL`) and that `finally` never runs, the launcher's termination handler falls back to signaling the whole process group instead of leaving `postgres`/`mongod` orphaned.
- **Dataset endpoints report each store's outcome independently.** `app/services/dataset.py`'s `_run_independently` runs the PostgreSQL and MongoDB halves of generate/reset/status separately, catching each one's exceptions on its own, so one store being down never turns into an opaque 500 that also hides whether the *other* store worked.
- **Generate/reset share one lock.** Both mutate global random/Faker state and do delete-then-write against both stores; a process-wide `asyncio.Lock` in `app/api/dataset.py` serializes them so concurrent requests can't interleave (single backend process, so this doesn't need to be a distributed lock).
- **Docker Compose binds every port to `127.0.0.1`**, and requires `POSTGRES_ADMIN_PASSWORD`/`POSTGRES_PASSWORD`/`MONGODB_ADMIN_PASSWORD`/`MONGODB_PASSWORD` to be set explicitly rather than falling back to a baked-in default -- both match the desktop app's already-local-only, always-real-credentials posture.

## Health contract

`GET /api/health` returns aggregate status and keyed service results, for the dashboard -- always 200, even when a service is down, since the frontend needs a body to render either way. Individual endpoints are available at `/api/health/postgres` and `/api/health/mongodb`. A service result contains a display name, `healthy` or `unavailable`, latency, UTC check time, a non-sensitive message, and the store's real reported version (`null` when unavailable).

`GET /api/health/live` returns `{"status": "live"}` whenever the FastAPI process is running, without touching either database. `GET /api/health/ready` returns the same shape as `GET /api/health`, but with an actual HTTP 503 (not 200) when either store isn't healthy -- this is what `docker-compose.yml`'s healthchecks and the desktop app's Swift launcher poll, not `GET /api/health`.

## Dataset contract

`GET /api/dataset/status`, `POST /api/dataset/generate`, and `POST /api/dataset/reset` all return the same shape: per-store (`postgres`, `mongodb`) results of `{status: "success" | "failed", counts: {customers, products, orders} | null, message: string | null}`. The two stores' results are independent -- one can be `"success"` while the other is `"failed"` in the same response, and the request is still a 200. Generation is seeded, so re-running it always reproduces the same 24 customers / 18 products / 40 orders rather than accumulating more rows on each call.

## Postgres console contract

`GET /api/postgres/tables` returns each table's name, row count, and columns (name + type). `GET /api/postgres/tables/{table}/rows` returns a page of rows as `{columns, rows, total, page, page_size}`, capped by `QUERY_MAX_ROWS`. `POST /api/postgres/query` takes `{"sql": "..."}`, applies a `statement_timeout` of `QUERY_TIMEOUT_SECONDS`, and returns `{columns, rows, row_count, truncated, duration_ms, statement_type}` -- `columns`/`rows` are `null` for INSERT/UPDATE/DELETE, where `row_count` is rows affected rather than rows returned. A rejected statement (wrong type, multiple statements, a timeout, or a real SQL error) comes back as an HTTP 400 with a `detail` message meant to be shown directly to the learner.

## Mongo console contract

`GET /api/mongodb/collections` returns each collection's name, document count, and `sample_fields` (one sample document's top-level keys). `GET /api/mongodb/collections/{name}/documents` returns `{documents, total, page, page_size}`, capped by `DOCUMENT_QUERY_MAX_RESULTS`. `POST /api/mongodb/query` takes `{"command": "db.<collection>.<op>(<args>)"}` and returns `{documents, row_count, truncated, duration_ms, operation}` -- `documents` is `null` for insert/update/delete operations, where `row_count` is the affected/inserted count. A rejected command (unrecognized syntax, an operation outside the allowlist, invalid JSON, or a real MongoDB error) comes back as an HTTP 400 with a `detail` message.

## Comparison contract

`GET /api/comparison/orders` returns every order as `{order_number, customer_name, status, item_count, total_cents}`, ordered by `order_number`. `GET /api/comparison/orders/{order_number}` returns `{order_number, relational, document}`, where `relational` is `{order, customer, items, sql}` (the actual SQL that produced it) and `document` is `{document}` (the raw MongoDB order document, BSON-serialized). A 404 names which store the order is missing from.

## Index lab contract

`GET /api/index-lab/status` returns `{table, column, index_name, index_exists, row_count}` for the fixed demo table/index, lazily seeding the practice table on first call if it's empty. `POST /api/index-lab/explain` runs the demo query and returns `{node_type, used_index, execution_time_ms, planning_time_ms, row_count, plan_text}` -- `used_index` is derived by walking the JSON plan tree for any node whose type contains "Index". `POST /api/index-lab/create-index` / `drop-index` return the same status shape after creating or dropping the one hardcoded demo index.

## Transaction lab contract

`POST /api/transaction-lab/begin` opens a new sandboxed connection and returns `{session_id}`. `POST /api/transaction-lab/execute` takes `{session_id, sql}` (one SELECT/INSERT/UPDATE/DELETE statement, same validation as the Postgres console) and returns `{columns, rows, row_count}`. `POST /api/transaction-lab/peek` (same session) and `GET /api/transaction-lab/peek-committed` (a fresh, separate connection) both run the same fixed representative query and return the same shape, so the frontend can show them side by side. `POST /api/transaction-lab/commit` / `rollback` take `{session_id}`, close that session, and return `{status}`. An unknown or expired `session_id` on any of these comes back as an HTTP 400.