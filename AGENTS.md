# DB Playground agent guide

## Purpose and structure
DB Playground is a localhost-first learning environment for comparing PostgreSQL with MongoDB. The current implementation phase is **Phase 2: sample data model** (Phase 1's foundation plus a seeded e-commerce dataset in both stores).

- `backend/`: FastAPI, database adapters, API routes, pytest tests.
  - `app/models/`: SQLAlchemy ORM models for the PostgreSQL schema (customers, products, orders, order_items).
  - `app/services/dataset.py`: generates the same seeded dataset into both stores; owns the reset/status logic too.
  - `app/api/dataset.py`: `/api/dataset/{generate,reset,status}`.
  - `alembic/`: PostgreSQL schema migrations. `env.py` builds its engine from `app.config.Settings`, not a separate URL in `alembic.ini`.
  - `app/desktop/`: standalone-app runtime (boots real local Postgres/MongoDB
    child processes with no Docker; see `docs/desktop-app.md`). Docker-mode
    code paths must keep working unchanged when this module isn't used.
- `frontend/`: React + TypeScript + Vite dashboard and Vitest tests.
- `desktop/DBPlaygroundApp/`: SwiftUI macOS launcher app (Swift Package, no Xcode project).
- `scripts/build_dmg.sh`: builds the standalone `.app`/`.dmg`.
- `docs/`: architecture notes.
- `docker-compose.yml`: all four services.

## Commands
- Backend dev: `cd backend && uvicorn app.main:app --reload`
- Frontend dev: `cd frontend && pnpm dev`
- Full stack: `docker compose up -d --build`
- Stop: `docker compose down`
- Reset volumes: `docker compose down -v` (destructive; confirm first)
- Backend checks: `cd backend && pytest && ruff check . && ruff format --check .`
- Frontend checks: `cd frontend && pnpm test --run && pnpm lint && pnpm build`
- Desktop app build: `./scripts/build_dmg.sh` (needs Homebrew postgresql@16,
  mongodb-community@7.0, dylibbundler, and Xcode command line tools)
- Desktop runtime dev check: `cd backend && python -m app.desktop.runtime` (uses
  Homebrew-installed postgres/mongod as a fallback when not frozen)

## Rules
- Copy `.env.example` to `.env`; never commit `.env` or hardcode credentials.
- Keep connection code in `app/db`, routes in `app/api`, and business logic in `app/services`.
- Validate inputs with Pydantic and never expose connection strings or credentials in errors.
- Any PostgreSQL schema change needs a new Alembic revision (`alembic revision --autogenerate -m "..."`), reviewed and adjusted by hand -- don't rely on `Base.metadata.create_all()` alone for anything beyond bootstrapping a brand-new empty database.
- A `sqlalchemy.Enum` column must pass `values_callable` to store the Python enum's `.value`, not its member name -- this repo's MongoDB side stores `.value` directly, so the two stores must agree on casing (see `app/models/order.py`).
- Before completion, run tests, lint, build, `docker compose config`, and update docs.

## Scope
Current phase: Phase 2. Do not add query consoles, row/document browsing or editing UI, schema diagrams, comparison-lesson content, transactions, indexes, authentication, cloud connections, or deployment features beyond the existing Docker/desktop paths.

The standalone macOS app (`desktop/`, `app/desktop/`, `scripts/build_dmg.sh`) is
a packaging/distribution path for whatever phase the Docker/dev path is on, not
its own product scope — it must not grow ahead of that phase.