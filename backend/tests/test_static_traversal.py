"""Verifies the SPA static-file handler can't be tricked into serving files
outside backend/static/, including via percent-encoded ".." segments.

Starlette/uvicorn percent-decode the request path before routing, so by the
time our handler sees `full_path` it's already a plain string -- an encoded
`..%2f` and a literal `../` look identical to it. Testing the handler directly
with decoded traversal strings exercises exactly the code path a real
(encoded or not) attack would reach, without depending on how any particular
HTTP client happens to normalize URLs before sending the request.
"""

import asyncio
import importlib
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SECRET_DIR = STATIC_DIR.parent / "secret_outside_static_test"


@pytest.fixture
def static_main():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "index.html").write_text("<html>spa-index</html>")
    (STATIC_DIR / "assets").mkdir(exist_ok=True)
    SECRET_DIR.mkdir(parents=True, exist_ok=True)
    (SECRET_DIR / "secret.txt").write_text("do not serve this")

    import app.main as main_module

    importlib.reload(main_module)
    try:
        yield main_module
    finally:
        shutil.rmtree(STATIC_DIR, ignore_errors=True)
        shutil.rmtree(SECRET_DIR, ignore_errors=True)
        importlib.reload(main_module)


def test_serves_index_for_unknown_client_routes(static_main) -> None:
    response = asyncio.run(static_main.serve_spa("some/client/route"))
    assert Path(response.path) == STATIC_DIR / "index.html"


@pytest.mark.parametrize(
    "traversal_path",
    [
        "../secret_outside_static_test/secret.txt",
        "../../secret_outside_static_test/secret.txt",
        "assets/../../secret_outside_static_test/secret.txt",
    ],
)
def test_blocks_path_traversal_outside_static_dir(static_main, traversal_path: str) -> None:
    response = asyncio.run(static_main.serve_spa(traversal_path))
    assert Path(response.path) == STATIC_DIR / "index.html"
    assert "secret_outside_static_test" not in str(response.path)


def test_http_level_encoded_traversal_is_blocked(static_main) -> None:
    client = TestClient(static_main.app)
    # %2e%2e%2f decodes to "../" -- sent as raw encoded bytes so no HTTP client
    # -side URL normalization collapses it before it reaches the server.
    response = client.get("/assets/%2e%2e%2f%2e%2e%2fsecret_outside_static_test/secret.txt")
    assert "do not serve this" not in response.text
