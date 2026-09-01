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
       └─ POST /api/postgres/query             → FastAPI :8000 → exec_driver_sql(sql), statement_timeout set → PostgreSQL
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