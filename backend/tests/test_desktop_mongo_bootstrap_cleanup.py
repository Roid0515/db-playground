"""Proves the no-auth bootstrap mongod is stopped even when bootstrapping the
app user fails partway through -- a mocked negative-path test, since the happy
path alone (exercised elsewhere) can't tell you the try/finally actually does
anything.
"""

from pathlib import Path

import pytest

from app.desktop import mongodb_runtime
from app.desktop.paths import AppPaths
from app.desktop.runtime import _bootstrap_mongodb_app_user


def _fake_paths(tmp_path: Path) -> AppPaths:
    return AppPaths(
        root=tmp_path,
        postgres_data=tmp_path / "postgres-data",
        mongo_data=tmp_path / "mongo-data",
        logs=tmp_path / "logs",
        runtime=tmp_path / "runtime",
    )


def test_stops_noauth_process_when_wait_ready_fails(monkeypatch, tmp_path) -> None:
    fake_process = object()
    stopped: list[object] = []

    monkeypatch.setattr(mongodb_runtime, "start", lambda *a, **k: fake_process)
    monkeypatch.setattr(
        mongodb_runtime,
        "wait_ready",
        lambda *a, **k: (_ for _ in ()).throw(mongodb_runtime.MongoRuntimeError("never came up")),
    )
    monkeypatch.setattr(mongodb_runtime, "stop", lambda process: stopped.append(process))

    with pytest.raises(mongodb_runtime.MongoRuntimeError):
        _bootstrap_mongodb_app_user(_fake_paths(tmp_path), {"mongodb_password": "x"})

    assert stopped == [fake_process]


def test_stops_noauth_process_when_bootstrap_app_user_fails(monkeypatch, tmp_path) -> None:
    fake_process = object()
    stopped: list[object] = []

    def fail_bootstrap(*_args, **_kwargs):
        raise RuntimeError("createUser failed")

    monkeypatch.setattr(mongodb_runtime, "start", lambda *a, **k: fake_process)
    monkeypatch.setattr(mongodb_runtime, "wait_ready", lambda *a, **k: None)
    monkeypatch.setattr(mongodb_runtime, "bootstrap_app_user", fail_bootstrap)
    monkeypatch.setattr(mongodb_runtime, "stop", lambda process: stopped.append(process))

    with pytest.raises(RuntimeError, match="createUser failed"):
        _bootstrap_mongodb_app_user(_fake_paths(tmp_path), {"mongodb_password": "x"})

    assert stopped == [fake_process]
