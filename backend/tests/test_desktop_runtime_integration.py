"""Integration tests against REAL, disposable PostgreSQL and MongoDB instances
-- boots them the same way app.desktop.runtime does, but without the FastAPI
server on top. Skipped automatically when postgres/mongod binaries aren't
available locally (see app/desktop/binaries.py), so this stays a no-op on a
machine/CI runner without Homebrew's postgresql@16 and mongodb-community@7.0.

This is what actually proves the things a mock can't: that the app's
PostgreSQL role really isn't a superuser, that the MongoDB user really has no
root role, and that the SQL console's query timeout and row cap hold up
against a real server.
"""

from __future__ import annotations

import os
import shutil
import socket
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from pymongo import MongoClient

from app.desktop import mongodb_runtime, postgres_runtime
from app.desktop.binaries import resolve_mongod_binary, resolve_postgres_bin_dir


def _binaries_available() -> bool:
    try:
        resolve_postgres_bin_dir()
        resolve_mongod_binary()
    except RuntimeError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _binaries_available(),
    reason="postgres/mongod binaries not found locally (see app/desktop/binaries.py)",
)

POSTGRES_APP_USER = "db_playground_test"
POSTGRES_APP_PASSWORD = "test-password"
DB_NAME = "db_playground_test"
MONGO_APP_USER = "db_playground_test"
MONGO_APP_PASSWORD = "test-password"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def live_databases() -> Iterator[dict[str, int]]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="db-playground-test-"))
    pg_data = tmp_dir / "pg"
    mongo_data = tmp_dir / "mongo"
    mongo_data.mkdir(parents=True)
    logs = tmp_dir / "logs"
    logs.mkdir(parents=True)

    pg_port = _free_port()
    mongo_port = _free_port()

    postgres_runtime.initdb(pg_data, "postgres")
    postgres_runtime.start(pg_data, pg_port, logs / "postgres.log")
    postgres_runtime.wait_ready("127.0.0.1", pg_port, "postgres")
    postgres_runtime.create_app_role(
        "127.0.0.1", pg_port, "postgres", POSTGRES_APP_USER, POSTGRES_APP_PASSWORD
    )
    postgres_runtime.ensure_database("127.0.0.1", pg_port, "postgres", DB_NAME)
    postgres_runtime.grant_database_privileges(
        "127.0.0.1", pg_port, "postgres", DB_NAME, POSTGRES_APP_USER
    )

    bootstrap_process = mongodb_runtime.start(
        mongo_data, mongo_port, logs / "mongod.log", auth=False
    )
    mongodb_runtime.wait_ready("127.0.0.1", mongo_port)
    mongodb_runtime.bootstrap_app_user(
        "127.0.0.1", mongo_port, DB_NAME, MONGO_APP_USER, MONGO_APP_PASSWORD
    )
    mongodb_runtime.stop(bootstrap_process)
    mongo_process = mongodb_runtime.start(mongo_data, mongo_port, logs / "mongod.log", auth=True)
    mongodb_runtime.wait_ready(
        "127.0.0.1",
        mongo_port,
        username=MONGO_APP_USER,
        password=MONGO_APP_PASSWORD,
        auth_source=DB_NAME,
    )

    env_overrides = {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": str(pg_port),
        "POSTGRES_DB": DB_NAME,
        "POSTGRES_USER": POSTGRES_APP_USER,
        "POSTGRES_PASSWORD": POSTGRES_APP_PASSWORD,
        "MONGODB_HOST": "127.0.0.1",
        "MONGODB_PORT": str(mongo_port),
        "MONGODB_DATABASE": DB_NAME,
        "MONGODB_USERNAME": MONGO_APP_USER,
        "MONGODB_PASSWORD": MONGO_APP_PASSWORD,
        "QUERY_TIMEOUT_SECONDS": "2",
        "QUERY_MAX_ROWS": "3",
        "FRONTEND_ORIGIN": "http://localhost:5173",
    }
    original_env = {key: os.environ.get(key) for key in env_overrides}
    os.environ.update(env_overrides)

    from app import config as config_module
    from app.db import mongodb as mongodb_module
    from app.db import postgres as postgres_module

    config_module.get_settings.cache_clear()
    postgres_module.get_engine.cache_clear()
    postgres_module._session_factory.cache_clear()
    mongodb_module.get_client.cache_clear()

    from app.desktop import migrations

    migrations.run_migrations()

    try:
        yield {"postgres_port": pg_port, "mongo_port": mongo_port}
    finally:
        postgres_runtime.stop(pg_data)
        mongodb_runtime.stop(mongo_process)
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        config_module.get_settings.cache_clear()
        postgres_module.get_engine.cache_clear()
        postgres_module._session_factory.cache_clear()
        mongodb_module.get_client.cache_clear()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_postgres_app_role_is_not_superuser(live_databases) -> None:
    with psycopg.connect(
        f"host=127.0.0.1 port={live_databases['postgres_port']} "
        f"dbname={DB_NAME} user={POSTGRES_APP_USER}"
    ) as conn:
        (is_super,) = conn.execute(
            "SELECT usesuper FROM pg_user WHERE usename = current_user"
        ).fetchone()
    assert is_super is False


def test_postgres_app_role_cannot_create_roles(live_databases) -> None:
    with psycopg.connect(
        f"host=127.0.0.1 port={live_databases['postgres_port']} "
        f"dbname={DB_NAME} user={POSTGRES_APP_USER}",
        autocommit=True,
    ) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE ROLE sneaky_role")


def test_mongo_app_user_has_no_root_role(live_databases) -> None:
    uri = (
        f"mongodb://{MONGO_APP_USER}:{MONGO_APP_PASSWORD}@127.0.0.1:"
        f"{live_databases['mongo_port']}/{DB_NAME}?authSource={DB_NAME}"
    )
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        roles = client[DB_NAME].command("connectionStatus")["authInfo"]["authenticatedUserRoles"]
    role_names = {r["role"] for r in roles}
    assert "root" not in role_names
    assert {"readWrite", "dbAdmin"}.issubset(role_names)


def test_dataset_generate_and_reset_against_real_databases(live_databases) -> None:
    from app.services import dataset as dataset_service

    results = dataset_service.generate_dataset()
    assert results["postgres"].status == "success"
    assert results["postgres"].counts.customers == dataset_service.CUSTOMER_COUNT
    assert results["mongodb"].status == "success"
    assert results["mongodb"].counts.customers == dataset_service.CUSTOMER_COUNT

    reset_results = dataset_service.reset_dataset()
    assert reset_results["postgres"].counts.customers == 0
    assert reset_results["mongodb"].counts.customers == 0

    # Leave data behind for the sql_console tests below.
    dataset_service.generate_dataset()


def test_sql_console_enforces_max_rows(live_databases) -> None:
    from app.services import sql_console

    result = sql_console.run_query("SELECT * FROM customers")

    assert result.truncated is True
    assert result.row_count == 3  # QUERY_MAX_ROWS=3 from the fixture's env


def test_sql_console_enforces_statement_timeout(live_databases) -> None:
    from app.services import sql_console

    started = time.monotonic()
    with pytest.raises(Exception):  # noqa: B017 -- SQLAlchemy wraps psycopg's QueryCanceled
        sql_console.run_query("SELECT pg_sleep(5)")
    elapsed = time.monotonic() - started

    assert elapsed < 4  # QUERY_TIMEOUT_SECONDS=2 from the fixture's env, well under the 5s sleep


def test_migrations_are_idempotent_on_an_existing_schema(live_databases) -> None:
    from app.desktop import migrations

    migrations.run_migrations()  # already at head; must be a safe no-op
