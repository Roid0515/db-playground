"""Entry point for the standalone desktop build.

Boots real PostgreSQL and MongoDB servers as local child processes (no Docker),
points the FastAPI app's settings at them via environment variables, then serves
the API and the bundled frontend build from a single in-process uvicorn server.
This module is the target the desktop build freezes with PyInstaller and the one
the macOS launcher app runs as a child process.
"""

from __future__ import annotations

import logging
import os

from app.desktop import mongodb_runtime, postgres_runtime
from app.desktop.paths import AppPaths, load_or_create_credentials

LOG = logging.getLogger("db_playground.desktop")

APP_HOST = "127.0.0.1"
APP_PORT = 8765
POSTGRES_PORT = 55432
MONGODB_PORT = 57017
DB_USER = "db_playground"
DB_NAME = "db_playground"


def _configure_environment(credentials: dict[str, str]) -> None:
    os.environ.update(
        {
            "APP_ENV": "desktop",
            "APP_HOST": APP_HOST,
            "APP_PORT": str(APP_PORT),
            "POSTGRES_HOST": APP_HOST,
            "POSTGRES_PORT": str(POSTGRES_PORT),
            "POSTGRES_DB": DB_NAME,
            "POSTGRES_USER": DB_USER,
            "POSTGRES_PASSWORD": credentials["postgres_password"],
            "MONGODB_HOST": APP_HOST,
            "MONGODB_PORT": str(MONGODB_PORT),
            "MONGODB_DATABASE": DB_NAME,
            "MONGODB_USERNAME": DB_USER,
            "MONGODB_PASSWORD": credentials["mongodb_password"],
            "FRONTEND_ORIGIN": f"http://{APP_HOST}:{APP_PORT}",
        }
    )


def _start_postgres(paths: AppPaths, credentials: dict[str, str]) -> None:
    first_run = not postgres_runtime.is_initialized(paths.postgres_data)
    if first_run:
        LOG.info("Initializing PostgreSQL data directory")
        postgres_runtime.initdb(paths.postgres_data, DB_USER)
    postgres_runtime.start(paths.postgres_data, POSTGRES_PORT, paths.logs / "postgres.log")
    postgres_runtime.wait_ready(APP_HOST, POSTGRES_PORT, DB_USER)
    if first_run:
        postgres_runtime.set_password(
            APP_HOST, POSTGRES_PORT, DB_USER, credentials["postgres_password"]
        )
    postgres_runtime.ensure_database(APP_HOST, POSTGRES_PORT, DB_USER, DB_NAME)


def _start_mongodb(paths: AppPaths, credentials: dict[str, str]):
    bootstrapped_marker = paths.mongo_data / ".bootstrapped"
    if not bootstrapped_marker.exists():
        LOG.info("Bootstrapping MongoDB root user")
        process = mongodb_runtime.start(
            paths.mongo_data, MONGODB_PORT, paths.logs / "mongod.log", auth=False
        )
        mongodb_runtime.wait_ready(APP_HOST, MONGODB_PORT)
        mongodb_runtime.bootstrap_root_user(
            APP_HOST, MONGODB_PORT, DB_USER, credentials["mongodb_password"]
        )
        mongodb_runtime.stop(process)
        bootstrapped_marker.write_text("ok")

    process = mongodb_runtime.start(
        paths.mongo_data, MONGODB_PORT, paths.logs / "mongod.log", auth=True
    )
    mongodb_runtime.wait_ready(
        APP_HOST, MONGODB_PORT, username=DB_USER, password=credentials["mongodb_password"]
    )
    return process


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    paths = AppPaths.default()
    credentials = load_or_create_credentials(paths.runtime)
    _configure_environment(credentials)

    # Everything from here on must be cleaned up on any failure, not just a clean
    # uvicorn exit -- otherwise a mid-startup crash leaks a running postgres/mongod.
    mongo_process = None
    try:
        LOG.info("Starting PostgreSQL on port %s", POSTGRES_PORT)
        _start_postgres(paths, credentials)

        LOG.info("Starting MongoDB on port %s", MONGODB_PORT)
        mongo_process = _start_mongodb(paths, credentials)

        import uvicorn

        from app.main import app

        LOG.info("Serving DB Playground at http://%s:%s", APP_HOST, APP_PORT)
        uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="info")
    finally:
        LOG.info("Shutting down database processes")
        if mongo_process is not None:
            mongodb_runtime.stop(mongo_process)
        postgres_runtime.stop(paths.postgres_data)


if __name__ == "__main__":
    main()
