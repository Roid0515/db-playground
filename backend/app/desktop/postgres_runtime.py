"""Starts and stops a local, unmanaged PostgreSQL server for the desktop app.

Binds to 127.0.0.1 only and uses trust authentication: this process is a
single-user local learning sandbox, not a multi-tenant server, so the usual
password-auth threat model doesn't apply as long as nothing else can reach the port.

Trust auth only decides who's allowed to *connect* -- it says nothing about
what they can do once connected. That's why the app never runs as the initdb
bootstrap role: it's a real Postgres superuser, so a bug (or a learner's SQL
console query) could otherwise reach past the db_playground database into
server-wide state. create_app_role/grant_database_privileges set up a
NOSUPERUSER role scoped to just that one database instead.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import psycopg
from psycopg import sql

from app.desktop.binaries import resolve_postgres_bin_dir

MAINTENANCE_DB = "postgres"


class PostgresRuntimeError(RuntimeError):
    pass


def is_initialized(data_dir: Path) -> bool:
    return (data_dir / "PG_VERSION").is_file()


def initdb(data_dir: Path, username: str) -> None:
    bin_dir = resolve_postgres_bin_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(bin_dir / "initdb"),
            "-D",
            str(data_dir),
            "-U",
            username,
            "-A",
            "trust",
            "--locale=C",
            "--encoding=UTF8",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def start(data_dir: Path, port: int, log_file: Path) -> subprocess.Popen:
    bin_dir = resolve_postgres_bin_dir()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    # Without a forced C locale, macOS can load Core Foundation frameworks that spin up
    # extra threads before postgres forks, tripping its "postmaster became multithreaded
    # during startup" safety check.
    env = {**os.environ, "LC_ALL": "C", "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES"}
    with log_file.open("ab") as log:
        return subprocess.Popen(
            [
                str(bin_dir / "postgres"),
                "-D",
                str(data_dir),
                "-p",
                str(port),
                "-c",
                "listen_addresses=127.0.0.1",
                "-c",
                f"unix_socket_directories={data_dir}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )


def wait_ready(host: str, port: int, user: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    dsn = f"host={host} port={port} dbname={MAINTENANCE_DB} user={user} connect_timeout=2"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(dsn) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.4)
    raise PostgresRuntimeError(f"PostgreSQL did not become ready in time: {last_error}")


def create_app_role(
    host: str, port: int, bootstrap_user: str, app_user: str, app_password: str
) -> None:
    """Create (or reset the password of) a NOSUPERUSER app role.

    The bootstrap role from initdb is a real Postgres superuser -- fine for our
    own setup steps, but the SQL console lets a learner run arbitrary SELECT/
    INSERT/UPDATE/DELETE, so the connection that actually serves the app must
    not be able to do things like CREATE ROLE, ALTER SYSTEM, or read arbitrary
    server-side files.
    """
    dsn = f"host={host} port={port} dbname={MAINTENANCE_DB} user={bootstrap_user}"
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,)).fetchone()
        privileges = "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
        if exists:
            conn.execute(
                sql.SQL("ALTER ROLE {} WITH " + privileges + " PASSWORD {}").format(
                    sql.Identifier(app_user), sql.Literal(app_password)
                )
            )
        else:
            conn.execute(
                sql.SQL("CREATE ROLE {} WITH " + privileges + " PASSWORD {}").format(
                    sql.Identifier(app_user), sql.Literal(app_password)
                )
            )


def ensure_database(host: str, port: int, bootstrap_user: str, dbname: str) -> None:
    dsn = f"host={host} port={port} dbname={MAINTENANCE_DB} user={bootstrap_user}"
    with psycopg.connect(dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))


def grant_database_privileges(
    host: str, port: int, bootstrap_user: str, dbname: str, app_user: str
) -> None:
    """Give the unprivileged app role full DML/DDL rights, but only inside
    `dbname` -- not database-creation or server-wide rights. Idempotent, so
    it's safe to call on every startup rather than tracking first-run state.
    """
    maintenance_dsn = f"host={host} port={port} dbname={MAINTENANCE_DB} user={bootstrap_user}"
    with psycopg.connect(maintenance_dsn, autocommit=True) as conn:
        conn.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(dbname), sql.Identifier(app_user)
            )
        )

    # Schema-level grants must run against the target database itself.
    db_dsn = f"host={host} port={port} dbname={dbname} user={bootstrap_user}"
    with psycopg.connect(db_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(sql.Identifier(app_user)))
        conn.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}").format(
                sql.Identifier(app_user)
            )
        )
        conn.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {}"
            ).format(sql.Identifier(app_user))
        )


def stop(data_dir: Path) -> None:
    bin_dir = resolve_postgres_bin_dir()
    subprocess.run(
        [str(bin_dir / "pg_ctl"), "-D", str(data_dir), "-m", "fast", "stop"],
        capture_output=True,
        text=True,
    )
