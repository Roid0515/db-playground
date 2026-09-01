# DB Playground agent guide

## Purpose and structure
DB Playground is a localhost-first learning environment for comparing PostgreSQL with MongoDB. The current implementation phase is **Phase 3: relational DB practice** (Phase 1's foundation, Phase 2's seeded e-commerce dataset, plus PostgreSQL table/row browsing and a SQL console). A security/reliability hardening pass followed Phase 3 -- see "Security and reliability" below -- without adding new learning features.

- `backend/`: FastAPI, database adapters, API routes, pytest tests.
  - `app/models/`: SQLAlchemy ORM models for the PostgreSQL schema (customers, products, orders, order_items).
  - `app/services/dataset.py`: generates the same seeded dataset into both stores; owns the reset/status logic too. Each store's generate/reset/status runs independently (`StoreResult` per store), so one store being down never 500s the other's result.
  - `app/services/sql_console.py`: table/row browsing and validated ad-hoc SQL execution against PostgreSQL. See `docs/phase-3.md` for the safety model before touching this.
  - `app/api/dataset.py`: `/api/dataset/{generate,reset,status}`. Generate/reset share a process-wide `asyncio.Lock` -- keep it that way; don't let concurrent requests interleave.
  - `app/api/postgres.py`: `/api/postgres/{tables,tables/{name}/rows,query}`.
  - `app/api/health.py`: `/api/health` (dashboard, always 200), `/api/health/live` (process up, no DB calls), `/api/health/ready` (503 unless both stores are healthy -- what Docker healthchecks and the desktop app actually poll).
  - `alembic/`: PostgreSQL schema migrations -- the only sanctioned way to change the schema. `env.py` builds its engine from `app.config.Settings`, not a separate URL in `alembic.ini`.
  - `app/desktop/`: standalone-app runtime (boots real local Postgres/MongoDB
    child processes with no Docker; see `docs/desktop-app.md`). Docker-mode
    code paths must keep working unchanged when this module isn't used.
    - `postgres_runtime.py` / `mongodb_runtime.py`: create a least-privilege app role/user, never the bootstrap superuser/root -- see "Security and reliability".
    - `migrations.py`: runs Alembic in-process (the frozen app can't shell out to an `alembic` CLI).
  - `docker/postgres-init/`, `docker/mongo-init/`: init scripts the official images run on first boot, creating the same kind of least-privilege app account the desktop path creates.
- `frontend/`: React + TypeScript + Vite dashboard and Vitest tests.
  - `src/components/Sidebar.tsx`: shared app-shell sidebar/nav, used by every page.
  - `src/features/relational/`: the "관계형 DB" table browser + SQL console page.
  - `src/api/client.ts`: shared fetch/error-handling client every `api/*.ts` module builds on -- add new endpoints here, don't hand-roll another `fetch()` wrapper.
  - `src/config/dbMeta.ts`, `src/config/phase.ts`: single source of truth for PostgreSQL/MongoDB display labels and the current-phase labels shown in the sidebar/footers -- edit these, not the per-component copies.
- `desktop/DBPlaygroundApp/`: SwiftUI macOS launcher app (Swift Package, no Xcode project).
- `scripts/build_dmg.sh`: builds the standalone `.app`/`.dmg`.
- `.github/workflows/ci.yml`: backend tests (with Postgres/Mongo service containers), frontend tests/lint/build, and a `docker compose up` smoke test that regression-checks the real init-script-based privilege separation.
- `docs/`: architecture notes.
- `docker-compose.yml`: all four services, bound to `127.0.0.1` only.

## Commands
- Backend dev: `cd backend && uvicorn app.main:app --reload`
- Frontend dev: `cd frontend && pnpm dev`
- Full stack: `docker compose up -d --build`
- Stop: `docker compose down`
- Reset volumes: `docker compose down -v` (destructive; confirm first)
- Backend checks: `cd backend && pytest && ruff check . && ruff format --check .` (the real-database tests in `tests/test_desktop_runtime_integration.py` skip automatically if postgres/mongod binaries aren't installed locally)
- Frontend checks: `cd frontend && pnpm test --run && pnpm lint && pnpm build`
- Desktop app build: `./scripts/build_dmg.sh` (needs Homebrew postgresql@16,
  mongodb-community@7.0, dylibbundler, and Xcode command line tools)
- Desktop runtime dev check: `cd backend && python -m app.desktop.runtime` (uses
  Homebrew-installed postgres/mongod as a fallback when not frozen)

## Rules
- Copy `.env.example` to `.env`; never commit `.env` or hardcode credentials. `docker-compose.yml` requires `POSTGRES_ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, `MONGODB_ADMIN_PASSWORD`, and `MONGODB_PASSWORD` to be set explicitly (Compose `${VAR:?...}`) -- an unconfigured `.env` fails the compose file to parse rather than silently running with a baked-in default.
- Keep connection code in `app/db`, routes in `app/api`, and business logic in `app/services`.
- Validate inputs with Pydantic and never expose connection strings or credentials in errors.
- Any PostgreSQL schema change needs a new Alembic revision (`alembic revision --autogenerate -m "..."`), reviewed and adjusted by hand -- don't rely on `Base.metadata.create_all()` for anything beyond what it already covers (it isn't called anywhere in `app/services/` anymore; schema lifecycle is Alembic's job end to end, applied automatically at startup in both the desktop runtime and the Docker backend's entrypoint).
- A `sqlalchemy.Enum` column must pass `values_callable` to store the Python enum's `.value`, not its member name -- this repo's MongoDB side stores `.value` directly, so the two stores must agree on casing (see `app/models/order.py`).
- Any raw, learner-submitted SQL must run via `Connection.exec_driver_sql()`, never `session.execute(text(raw_sql))` -- `text()` scans for `:name` bind-parameter syntax and misfires on legitimate SQL with literal colons. Keep it going through `app/services/sql_console.py`'s validation (single statement, no DDL) rather than adding a second raw-execution path.
- The app (health checks, dataset service, SQL console) must always connect as the least-privilege role/user -- never the Postgres bootstrap superuser or a MongoDB root user. If a feature seems to need more privilege than that, that's a signal to reconsider the feature, not to widen the grant.
- Before completion, run tests, lint, build, `docker compose config`, and update docs.

## Security and reliability
A hardening pass followed Phase 3, without adding new learning features. It's worth understanding before touching `app/desktop/`, `app/db/`, `app/api/health.py`, or `docker-compose.yml`:

- **Least-privilege DB accounts.** PostgreSQL's `initdb` bootstrap role is a real superuser by necessity, but the app never connects as it -- `postgres_runtime.create_app_role`/`grant_database_privileges` (desktop) and `docker/postgres-init/01-create-app-role.sh` (Docker) create a `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION` role scoped to just the `db_playground` database instead. MongoDB never gets a `root` user at all -- `mongodb_runtime.bootstrap_app_user` (desktop) and `docker/mongo-init/01-create-app-user.js` (Docker) create a user with `readWrite`+`dbAdmin` on `db_playground` only, so `Settings.mongodb_uri`'s `authSource` is the app database, not `admin`.
- **Query limits are enforced server-side**, not just hidden in the UI: `app/services/sql_console.py` sets `statement_timeout` and caps returned rows to `QUERY_MAX_ROWS`; `app/db/mongodb.py`'s pooled client sets `serverSelectionTimeoutMS`/`connectTimeoutMS` from `QUERY_TIMEOUT_SECONDS`.
- **`/api/health/ready` is what orchestration should poll**, not `/api/health` (which always returns 200, even degraded, since the dashboard needs a body either way).
- **Docker Compose binds every port to `127.0.0.1`** -- this is a localhost-first tool, not something meant to be reachable from other machines.
- **The desktop runtime puts itself in its own process group** (`os.setpgrp()`) specifically so the macOS launcher can clean up orphaned `postgres`/`mongod` children if the backend process is ever killed outright instead of shut down gracefully (see `BackendRuntime.swift`'s `killProcessGroup`).
- **Dataset and health endpoints report per-store outcomes independently** -- one database being down must never turn into an opaque 500 for the other.

## Scope
Current phase: Phase 3. Do not add MongoDB browsing/querying, schema diagrams, comparison-lesson content, transactions, indexes, authentication, cloud connections, or deployment features beyond the existing Docker/desktop paths.

The standalone macOS app (`desktop/`, `app/desktop/`, `scripts/build_dmg.sh`) is
a packaging/distribution path for whatever phase the Docker/dev path is on, not
its own product scope — it must not grow ahead of that phase.
