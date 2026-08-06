# DB Playground agent guide

## Purpose and structure
DB Playground is a localhost-first learning environment for comparing PostgreSQL with MongoDB. The current implementation phase is **Phase 1: project foundation** only.

- `backend/`: FastAPI, database adapters, API routes, pytest tests.
- `frontend/`: React + TypeScript + Vite dashboard and Vitest tests.
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

## Rules
- Copy `.env.example` to `.env`; never commit `.env` or hardcode credentials.
- Keep connection code in `app/db`, routes in `app/api`, and later business logic in `app/services`.
- Validate inputs with Pydantic and never expose connection strings or credentials in errors.
- Make schema changes through Alembic once Phase 2 introduces migrations.
- Before completion, run tests, lint, build, `docker compose config`, and update docs.

## Scope
Current phase: Phase 1. Do not add CRUD, schema editing, sample data generation, query consoles, migrations, authentication, cloud connections, or deployment features.