# Architecture

```text
Browser :5173
  └─ React dashboard
       ├─ GET  /api/health           → FastAPI :8000
       │                                 ├─ SELECT 1 → PostgreSQL :5432
       │                                 └─ ping     → MongoDB :27017
       ├─ GET  /api/dataset/status   → FastAPI :8000
       ├─ POST /api/dataset/generate → FastAPI :8000
       │                                 ├─ SQLAlchemy session → PostgreSQL (customers, products, orders, order_items)
       │                                 └─ pymongo            → MongoDB (customers, products, orders with embedded items)
       └─ POST /api/dataset/reset    → FastAPI :8000
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
- **Fresh installs don't need a manual migration:** `Base.metadata.create_all()` runs at the start of every dataset endpoint, so a brand-new Docker volume or desktop-app data directory bootstraps itself. Alembic (`backend/alembic/`) is still the required path for changing the schema of a database that already has data.
- **Status/generate/reset return the same shape:** all three dataset endpoints return per-store row/document counts, so the frontend (and curl) can treat "just generated" and "just checked" identically.
- **Phase boundary:** query consoles, row/document browsing or editing, schema diagrams, comparison lessons, transactions, and indexes are deferred until the phase that uses them.

## Health contract

`GET /api/health` returns aggregate status and keyed service results. Individual endpoints are available at `/api/health/postgres` and `/api/health/mongodb`. A service result contains a display name, `healthy` or `unavailable`, latency, UTC check time, and a non-sensitive message.

## Dataset contract

`GET /api/dataset/status`, `POST /api/dataset/generate`, and `POST /api/dataset/reset` all return the same shape: per-store (`postgres`, `mongodb`) counts of `customers`, `products`, and `orders`. Generation is seeded, so re-running it always reproduces the same 24 customers / 18 products / 40 orders rather than accumulating more rows on each call.