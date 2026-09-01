# DB Playground agent guide

## Purpose and structure
DB Playground is a localhost-first learning environment for comparing PostgreSQL with MongoDB. All seven planned phases are implemented: Phase 1's foundation, Phase 2's seeded e-commerce dataset, Phase 3's PostgreSQL table/row browsing and SQL console, Phase 4's MongoDB collection/document browsing and mongosh-style console, Phase 5's side-by-side structure comparison, Phase 6's index lab and transaction sandbox, and Phase 7's static learning notes. A security/reliability hardening pass followed Phase 3 -- see "Security and reliability" below -- without adding new learning features at the time.

- `backend/`: FastAPI, database adapters, API routes, pytest tests.
  - `app/models/`: SQLAlchemy ORM models for the PostgreSQL schema (customers, products, orders, order_items, index_lab_events).
  - `app/services/dataset.py`: generates the same seeded dataset into both stores; owns the reset/status logic too. Each store's generate/reset/status runs independently (`StoreResult` per store), so one store being down never 500s the other's result. Also force-closes any open transaction-lab session before mutating (see `transaction_lab.py` below).
  - `app/services/sql_console.py`: table/row browsing and validated ad-hoc SQL execution against PostgreSQL. See `docs/phase-3.md` for the safety model before touching this. `_EXCLUDED_TABLES` hides Alembic's bookkeeping table and `index_lab_events` from the Table Explorer -- neither is part of the shopping-mall dataset this page showcases.
  - `app/services/mongo_console.py`: collection/document browsing and a constrained mongosh-syntax console against MongoDB. See `docs/phase-4.md` for the safety model (operation allowlist, strict-JSON args, no real JS parsing).
  - `app/services/bson_utils.py`: shared `to_jsonable()` for turning `ObjectId`/`datetime` into JSON-safe values -- used by both the Mongo console and the comparison view.
  - `app/services/comparison.py`: looks up one order in both stores by the shared `order_number` seeded into both by `dataset.py`, returning PostgreSQL's joined view and MongoDB's raw document side by side. See `docs/phase-5.md`.
  - `app/services/index_lab.py`: EXPLAIN ANALYZE against a dedicated, lazily-seeded 100k-row practice table (`index_lab_events`), plus create/drop of exactly one hardcoded demo index. See `docs/phase-6.md` for why the shopping-mall dataset couldn't be reused for this.
  - `app/services/transaction_lab.py`: a real, session-backed BEGIN/COMMIT/ROLLBACK sandbox holding one psycopg connection per `session_id` in an in-process dict. Reuses `sql_console.validate_single_statement` so DDL is blocked here too.
  - `app/api/dataset.py`: `/api/dataset/{generate,reset,status}`. Generate/reset share a process-wide `asyncio.Lock` -- keep it that way; don't let concurrent requests interleave.
  - `app/api/postgres.py`: `/api/postgres/{tables,tables/{name}/rows,query}`.
  - `app/api/mongodb.py`: `/api/mongodb/{collections,collections/{name}/documents,query}`.
  - `app/api/comparison.py`: `/api/comparison/{orders,orders/{order_number}}`.
  - `app/api/index_lab.py`: `/api/index-lab/{status,explain,create-index,drop-index}`.
  - `app/api/transaction_lab.py`: `/api/transaction-lab/{begin,execute,peek,peek-committed,commit,rollback}`.
  - `app/api/health.py`: `/api/health` (dashboard, always 200), `/api/health/live` (process up, no DB calls), `/api/health/ready` (503 unless both stores are healthy -- what Docker healthchecks and the desktop app actually poll).
  - `alembic/`: PostgreSQL schema migrations -- the only sanctioned way to change the schema. `env.py` builds its engine from `app.config.Settings`, not a separate URL in `alembic.ini`.
  - `app/desktop/`: standalone-app runtime (boots real local Postgres/MongoDB
    child processes with no Docker; see `docs/desktop-app.md`). Docker-mode
    code paths must keep working unchanged when this module isn't used.
    - `postgres_runtime.py` / `mongodb_runtime.py`: create a least-privilege app role/user, never the bootstrap superuser/root -- see "Security and reliability".
    - `migrations.py`: runs Alembic in-process (the frozen app can't shell out to an `alembic` CLI).
  - `docker/postgres-init/`, `docker/mongo-init/`: init scripts the official images run on first boot, creating the same kind of least-privilege app account the desktop path creates.
- `frontend/`: React + TypeScript + Vite dashboard and Vitest tests.
  - `src/components/Sidebar.tsx`: shared app-shell sidebar/nav, used by every page. Every phase now has a nav entry; there are no locked items left.
  - `src/features/relational/`: the "관계형 DB" table browser + SQL console page (Phase 3).
  - `src/features/mongo/`: the "MongoDB" collection browser + mongosh-style console page (Phase 4).
  - `src/features/comparison/`: the "구조 비교" side-by-side order comparison page (Phase 5).
  - `src/features/performance/`: the "트랜잭션 · 인덱스" page -- index lab and transaction sandbox tabs (Phase 6).
  - `src/features/notes/`: the "학습 노트" static reference page (Phase 7, no backend).
  - `src/api/client.ts`: shared fetch/error-handling client every `api/*.ts` module builds on -- add new endpoints here, don't hand-roll another `fetch()` wrapper.
  - `src/config/dbMeta.ts`, `src/config/phase.ts`: single source of truth for PostgreSQL/MongoDB display labels and the current-phase labels shown in the sidebar/footers -- edit these, not the per-component copies. `CURRENT_PHASE_NUMBER === TOTAL_PHASES` now (7/7); the dashboard's roadmap section shows a completion state, not locked "coming next" cards.
- `desktop/DBPlaygroundApp/`: SwiftUI macOS launcher app (Swift Package, no Xcode project). `BackendRuntime.swift`'s `stop()` signals the whole process group, not just the backend process -- see "Security and reliability" for why a plain `SIGTERM` to the backend alone isn't reliable here.
- `scripts/build_dmg.sh`: builds the standalone `.app`/`.dmg`.
- `.github/workflows/ci.yml`: backend tests (with Postgres/Mongo service containers), frontend tests/lint/build, and a `docker compose up` smoke test that regression-checks the real init-script-based privilege separation.
- `docs/`: architecture notes, one `phase-N.md` per phase.
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
- Any raw, learner-submitted SQL must run via `Connection.exec_driver_sql()`/a plain psycopg cursor, never `session.execute(text(raw_sql))` -- `text()` scans for `:name` bind-parameter syntax and misfires on legitimate SQL with literal colons. Keep it going through `app/services/sql_console.py`'s `validate_single_statement` (single statement, no DDL) rather than adding a second raw-execution path; `transaction_lab.py` already reuses it for exactly this reason.
- Any learner-submitted MongoDB command must go through `app/services/mongo_console.py`'s `parse_command` (operation allowlist, strict-JSON args) -- don't add a second entry point that accepts raw JS.
- The app (health checks, dataset service, SQL/Mongo consoles, index lab, transaction lab) must always connect as the least-privilege role/user -- never the Postgres bootstrap superuser or a MongoDB root user. If a feature seems to need more privilege than that, that's a signal to reconsider the feature, not to widen the grant. The index lab's `CREATE INDEX`/`DROP INDEX` is safe under this rule only because it targets one specific, hardcoded index name/table -- don't generalize it into an arbitrary-DDL endpoint.
- Before completion, run tests, lint, build, `docker compose config`, and update docs.

## Security and reliability
A hardening pass followed Phase 3, without adding new learning features at the time. It's worth understanding before touching `app/desktop/`, `app/db/`, `app/api/health.py`, or `docker-compose.yml`:

- **Least-privilege DB accounts.** PostgreSQL's `initdb` bootstrap role is a real superuser by necessity, but the app never connects as it -- `postgres_runtime.create_app_role`/`grant_database_privileges` (desktop) and `docker/postgres-init/01-create-app-role.sh` (Docker) create a `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION` role scoped to just the `db_playground` database instead. MongoDB never gets a `root` user at all -- `mongodb_runtime.bootstrap_app_user` (desktop) and `docker/mongo-init/01-create-app-user.js` (Docker) create a user with `readWrite`+`dbAdmin` on `db_playground` only, so `Settings.mongodb_uri`'s `authSource` is the app database, not `admin`. The Phase 6 index lab's `CREATE INDEX`/`DROP INDEX` works within this same boundary: the app role can do DDL on tables it owns (created via its own migrations), which is not the same as server-admin privilege.
- **Query limits are enforced server-side**, not just hidden in the UI: `app/services/sql_console.py` sets `statement_timeout` and caps returned rows to `QUERY_MAX_ROWS`; `app/db/mongodb.py`'s pooled client sets `serverSelectionTimeoutMS`/`connectTimeoutMS` from `QUERY_TIMEOUT_SECONDS`; the Mongo console applies the same via `maxTimeMS`/cursor limits.
- **`/api/health/ready` is what orchestration should poll**, not `/api/health` (which always returns 200, even degraded, since the dashboard needs a body either way).
- **Docker Compose binds every port to `127.0.0.1`** -- this is a localhost-first tool, not something meant to be reachable from other machines.
- **The desktop runtime puts itself in its own process group** (`os.setpgrp()`), and the macOS launcher's `stop()` signals that whole group (`SIGTERM`, then `SIGKILL` after a grace period) for *both* a normal quit and a crash -- not just the crash path. This was originally crash-only, relying on the backend's own `finally` block to stop postgres/mongod gracefully on a plain quit; verified directly that this doesn't work; see `BackendRuntime.swift`'s `killProcessGroup` and its comment on `stop()` for why. Postgres and MongoDB both treat a direct `SIGTERM` as their own clean shutdown signal, so signaling the whole group is no less graceful.
- **Dataset and health endpoints report per-store outcomes independently** -- one database being down must never turn into an opaque 500 for the other. Dataset generate/reset also force-close any open transaction-lab session first, so an abandoned open transaction can't block or deadlock the reset.

## Scope
All seven originally-scoped phases are implemented. Further work here means either a genuinely new phase (scope it with the user first, the way Phases 4-7 were scoped via a short Q&A rather than invented unilaterally) or refinements within an existing phase's boundaries.

The standalone macOS app (`desktop/`, `app/desktop/`, `scripts/build_dmg.sh`) is
a packaging/distribution path for whatever the Docker/dev path supports, not
its own product scope — it must not grow ahead of that.
