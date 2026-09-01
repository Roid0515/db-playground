"""On-disk layout for the desktop app's data, logs, and generated local credentials."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    postgres_data: Path
    mongo_data: Path
    logs: Path
    runtime: Path

    @classmethod
    def default(cls) -> AppPaths:
        root = Path.home() / "Library" / "Application Support" / "DBPlayground"
        paths = cls(
            root=root,
            postgres_data=root / "postgres-data",
            mongo_data=root / "mongo-data",
            logs=root / "logs",
            runtime=root / "runtime",
        )
        for path in (paths.postgres_data, paths.mongo_data, paths.logs, paths.runtime):
            path.mkdir(parents=True, exist_ok=True)
        return paths


def load_or_create_credentials(runtime_dir: Path) -> dict[str, str]:
    """Generate local-only DB credentials once and reuse them on every later launch.

    Postgres runs with trust auth on 127.0.0.1, so the password is cosmetic there;
    MongoDB enforces it for real, so it must stay stable across restarts.
    """
    credentials_file = runtime_dir / "credentials.json"
    if credentials_file.is_file():
        return json.loads(credentials_file.read_text())
    credentials = {
        "postgres_password": secrets.token_urlsafe(24),
        "mongodb_password": secrets.token_urlsafe(24),
    }
    credentials_file.write_text(json.dumps(credentials))
    credentials_file.chmod(0o600)
    return credentials
