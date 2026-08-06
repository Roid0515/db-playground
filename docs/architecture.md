# Phase 1 architecture

```text
Browser :5173
  └─ React dashboard
       └─ GET /api/health → FastAPI :8000
                              ├─ SELECT 1 → PostgreSQL :5432
                              └─ ping     → MongoDB :27017
```

## Decisions

- **Localhost-first:** Phase 1 only accepts the configured frontend origin and exposes no arbitrary database connection form.
- **Short-lived health connections:** Health checks create and close their own connections so the foundation remains simple. Later query services can introduce pools with explicit limits.
- **Parallel checks:** PostgreSQL and MongoDB pings run concurrently in worker threads, keeping FastAPI's event loop responsive.
- **Safe degradation:** A database outage returns a `degraded` aggregate status and a generic message rather than an HTTP 500 or raw driver error.
- **Browser API address:** `VITE_API_URL` is compiled into the frontend because the browser cannot resolve Docker service names.
- **Phase boundary:** Alembic scaffolding, models, CRUD, datasets, query execution, Monaco, forms, and React Flow are deferred until the phase that uses them.

## Health contract

`GET /api/health` returns aggregate status and keyed service results. Individual endpoints are available at `/api/health/postgres` and `/api/health/mongodb`. A service result contains a display name, `healthy` or `unavailable`, latency, UTC check time, and a non-sensitive message.