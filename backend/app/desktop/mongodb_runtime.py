"""Starts and stops a local, unmanaged MongoDB server for the desktop app.

MongoDB has no "trust" auth equivalent, so the app user is bootstrapped once
against a temporary no-auth instance (mirroring what the official Docker image's
entrypoint does), then every later launch starts mongod with --auth enforced.

The bootstrapped user is scoped to readWrite+dbAdmin on the app's own database
only -- never `root`. The SQL/query consoles this app offers are meant to let a
learner experiment freely with their own practice data, not with server-wide
MongoDB administration (other databases, user management, replication, ...).
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.desktop.binaries import resolve_mongod_binary


class MongoRuntimeError(RuntimeError):
    pass


def start(data_dir: Path, port: int, log_file: Path, *, auth: bool) -> subprocess.Popen:
    data_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(resolve_mongod_binary()),
        "--dbpath",
        str(data_dir),
        "--port",
        str(port),
        "--bind_ip",
        "127.0.0.1",
        "--logpath",
        str(log_file),
        "--logappend",
    ]
    if auth:
        command.append("--auth")
    return subprocess.Popen(command)


def wait_ready(
    host: str,
    port: int,
    *,
    username: str | None = None,
    password: str | None = None,
    auth_source: str | None = None,
    timeout: float = 30,
) -> None:
    if username and password:
        uri = f"mongodb://{username}:{password}@{host}:{port}/?authSource={auth_source}"
    else:
        uri = f"mongodb://{host}:{port}/"
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with MongoClient(uri, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500) as client:
                client.admin.command("ping")
            return
        except PyMongoError as exc:
            last_error = exc
            time.sleep(0.4)
    raise MongoRuntimeError(f"MongoDB did not become ready in time: {last_error}")


def bootstrap_app_user(host: str, port: int, dbname: str, username: str, password: str) -> None:
    """Create the app's MongoDB user, scoped to `dbname` only.

    createUser is issued against `dbname` (not `admin`), so the resulting user
    lives in `dbname`'s own user collection with no admin-database presence at
    all -- there's no root/admin account for this app to ever misuse.
    """
    uri = f"mongodb://{host}:{port}/"
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client[dbname].command(
            "createUser",
            username,
            pwd=password,
            roles=[
                {"role": "readWrite", "db": dbname},
                {"role": "dbAdmin", "db": dbname},
            ],
        )


def stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
