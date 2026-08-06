from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title="DB Playground API",
    description="Local learning API for PostgreSQL and MongoDB",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(health_router)


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


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "DB Playground API", "docs": "/docs", "health": "/api/health"}