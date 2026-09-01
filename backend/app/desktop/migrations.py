"""Applies Alembic migrations before the app starts serving requests.

Both the Docker and desktop-app runtimes treat Alembic as the single source of
truth for the PostgreSQL schema (see docs/phase-2.md and AGENTS.md) -- neither
runtime relies on Base.metadata.create_all() anymore. The desktop app can't
shell out to an `alembic` CLI (nothing installs it on the learner's machine),
so this runs the upgrade in-process via Alembic's own Python API, pointed at
the alembic.ini/alembic/ directory scripts/build_dmg.sh bundles alongside the
frozen executable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config

from alembic import command


def _resolve_backend_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "migrations"
    # Running from source: this file is backend/app/desktop/migrations.py.
    return Path(__file__).resolve().parent.parent.parent


def run_migrations() -> None:
    backend_root = _resolve_backend_root()
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(cfg, "head")
