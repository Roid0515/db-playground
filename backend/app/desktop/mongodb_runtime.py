"""Starts and stops a local, unmanaged MongoDB server for the desktop app.

MongoDB has no "trust" auth equivalent, so the root user is bootstrapped once
against a temporary no-auth instance (mirroring what the official Docker image's
entrypoint does), then every later launch starts mongod with --auth enforced.
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
    timeout: float = 30,
) -> None:
    if username and password:
        uri = f"mongodb://{username}:{password}@{host}:{port}/?authSource=admin"
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


def bootstrap_root_user(host: str, port: int, username: str, password: str) -> None:
    uri = f"mongodb://{host}:{port}/"
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client.admin.command(
            "createUser",
            username,
            pwd=password,
            roles=[{"role": "root", "db": "admin"}],
        )


def stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
