"""Locates the PostgreSQL and MongoDB server binaries the desktop runtime drives.

Bundled builds ship the binaries next to the frozen executable under `db-bin/`.
Local dev runs fall back to the Homebrew install used to build/test this runtime.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_POSTGRES_DIRS = [
    "/opt/homebrew/opt/postgresql@16/bin",
    "/usr/local/opt/postgresql@16/bin",
]
_MONGOD_DIRS = [
    "/opt/homebrew/opt/mongodb-community@7.0/bin",
    "/usr/local/opt/mongodb-community@7.0/bin",
]


def _bundled_bin_dir() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "db-bin"
    return None


def resolve_postgres_bin_dir() -> Path:
    bundled = _bundled_bin_dir()
    if bundled and (bundled / "postgres").is_file():
        return bundled
    for candidate in _POSTGRES_DIRS:
        path = Path(candidate)
        if (path / "postgres").is_file():
            return path
    found = shutil.which("postgres")
    if found:
        return Path(found).resolve().parent
    raise RuntimeError("Could not locate a PostgreSQL server binary (postgres).")


def resolve_mongod_binary() -> Path:
    bundled = _bundled_bin_dir()
    if bundled and (bundled / "mongod").is_file():
        return bundled / "mongod"
    for candidate in _MONGOD_DIRS:
        path = Path(candidate) / "mongod"
        if path.is_file():
            return path
    found = shutil.which("mongod")
    if found:
        return Path(found)
    raise RuntimeError("Could not locate a MongoDB server binary (mongod).")
