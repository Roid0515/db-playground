import sys
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.comparison import router as comparison_router
from app.api.dataset import router as dataset_router
from app.api.health import router as health_router
from app.api.index_lab import router as index_lab_router
from app.api.mongodb import router as mongodb_router
from app.api.postgres import router as postgres_router
from app.api.transaction_lab import router as transaction_lab_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="DB Playground API",
    description="Local learning API for PostgreSQL and MongoDB",
    version="1.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(dataset_router)
app.include_router(postgres_router)
app.include_router(mongodb_router)
app.include_router(comparison_router)
app.include_router(index_lab_router)
app.include_router(transaction_lab_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request",
                "details": exc.errors(),
            }
        },
    )


# Populated by the desktop build (frontend build copied next to the backend) so the
# packaged app can serve the dashboard and the API from a single process and port.
# A PyInstaller-frozen build has no real source tree, so `static/` is resolved next
# to the frozen executable instead of relative to this module's file.
if getattr(sys, "frozen", False):
    STATIC_DIR = (Path(sys.executable).resolve().parent / "static").resolve()
else:
    STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()
_has_static = STATIC_DIR.is_dir()

if _has_static:
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")


@app.get("/")
async def root() -> Response:
    if _has_static:
        return FileResponse(STATIC_DIR / "index.html")
    return JSONResponse({"name": "DB Playground API", "docs": "/docs", "health": "/api/health"})


if _has_static:

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        # full_path comes straight from the URL and may contain literal ".."
        # segments (encoded or not) that Starlette's routing doesn't strip.
        # resolve() collapses them, then is_relative_to() confirms the result
        # is still inside STATIC_DIR before it's ever handed to FileResponse --
        # otherwise a request for e.g. /../../../../etc/passwd would happily
        # serve any file readable by the process.
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_relative_to(STATIC_DIR) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
