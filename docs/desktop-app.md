# Standalone macOS app

`DB Playground.app` packages the app (currently through Phase 3) as a
self-contained macOS app: no Docker, no Homebrew, and no separately installed
PostgreSQL/MongoDB needed on the learner's machine. Double-click, and both
real database servers run locally.

## Architecture

```text
DB Playground.app (SwiftUI, WKWebView)
  └─ spawns Contents/Resources/backend/db-playground-backend
       (PyInstaller-frozen app.desktop.runtime)
       ├─ starts Contents/Resources/backend/db-bin/postgres  (real PostgreSQL 16)
       ├─ starts Contents/Resources/backend/db-bin/mongod    (real MongoDB 7)
       └─ serves FastAPI + the built React SPA on http://127.0.0.1:8765
```

- The Swift launcher (`desktop/DBPlaygroundApp`) starts the backend as a child
  process, polls `/api/health/ready` until it's up, then loads the dashboard
  directly in an in-app `WKWebView`. Quitting the app sends `SIGTERM` to the
  backend, which stops postgres/mongod before exiting (see
  [`app/desktop/runtime.py`](../backend/app/desktop/runtime.py)). If the
  backend is ever killed outright instead (a crash, not a normal quit), the
  launcher detects that its child died unexpectedly and falls back to
  signaling the whole process group -- `runtime.main()` calls `os.setpgrp()`
  specifically so postgres/mongod are still reachable that way even after
  their own parent is gone. See [`BackendRuntime.swift`](../desktop/DBPlaygroundApp/Sources/DBPlaygroundApp/BackendRuntime.swift).
- PostgreSQL and MongoDB binaries are copied from Homebrew at build time and
  re-linked with [`dylibbundler`](https://github.com/auburnsounds/dylibbundler)
  so they carry their own dependency dylibs instead of pointing at
  `/opt/homebrew/...`. This is what makes the app installable on a Mac that
  has never touched Homebrew.
- PostgreSQL binds to `127.0.0.1:55432` with trust authentication (this is a
  single-user local sandbox, not a multi-tenant server) -- but the app
  connects as a separate, generated `NOSUPERUSER` role scoped to the
  `db_playground` database, not as the `initdb` bootstrap superuser. MongoDB
  binds to `127.0.0.1:57017` with a generated user scoped to `readWrite`+
  `dbAdmin` on `db_playground` only -- never a `root` role -- bootstrapped
  once against a temporary no-auth instance the same way the official Docker
  image's entrypoint bootstraps its own root user. See
  `app/desktop/postgres_runtime.py` / `mongodb_runtime.py` and AGENTS.md's
  "Security and reliability" section for the reasoning.
- App data lives in `~/Library/Application Support/DBPlayground/` (`postgres-data/`,
  `mongo-data/`, `logs/`, `runtime/credentials.json`). Deleting that folder
  resets everything.
- Alembic migrations run in-process on every launch
  (`app/desktop/migrations.py`, using the `alembic.ini`/`alembic/` directory
  `scripts/build_dmg.sh` bundles next to the frozen executable) before the
  server starts accepting requests -- the same schema-lifecycle path the
  Docker backend uses, not a separate one.
- The frontend is built once with `VITE_API_URL=""` so it calls the API with
  relative paths — the same port serves both the API and the SPA, so no
  separate nginx/frontend process is needed in this mode (unlike the Docker
  Compose path in the main [README](../README.md), which still runs `nginx`).

## Building the .dmg

Run on an Apple Silicon Mac with Xcode command line tools installed:

```bash
brew install postgresql@16 dylibbundler
brew tap mongodb/brew
brew install mongodb-community@7.0
./scripts/build_dmg.sh
```

Output: `dist/DB Playground.dmg`. The script builds the frontend, copies it
into `backend/static`, freezes the backend with PyInstaller, bundles the
postgres/mongod binaries with their dylibs, copies `alembic.ini`/`alembic/`
next to the frozen executable, builds the Swift launcher, and assembles +
signs (ad hoc) the `.app` before creating the `.dmg`.

## Known limitations

- **Apple Silicon only.** The bundled Postgres/MongoDB binaries come from
  this machine's Homebrew install (arm64). An Intel build would need the
  x86_64 Homebrew binaries built/bundled separately.
- **Ad-hoc signed, not notarized.** Gatekeeper will warn on first launch for
  anyone who downloads the `.dmg` rather than building it locally; right-click
  → Open bypasses this. Proper distribution outside this machine would need
  an Apple Developer ID and notarization.
- **Fixed ports** (8765 / 55432 / 57017, no negotiation). If something else
  on the machine already holds one of these, the app will fail to start;
  there's no conflict UI yet.
- **Crash cleanup has a short blind spot.** The process-group fallback described
  above sends `SIGTERM` first and only escalates to `SIGKILL` after a 2-second
  grace period, so if postgres/mongod are themselves wedged (not just the
  backend), there's a brief window after a crash where they're still exiting.
  In every case tested so far they've stopped well within that window.
