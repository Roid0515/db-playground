import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db.mongodb import ping_mongodb
from app.db.postgres import ping_postgres

router = APIRouter(prefix="/api/health", tags=["health"])


class ServiceHealth(BaseModel):
    service: str
    status: str
    latency_ms: float
    checked_at: datetime
    message: str


class SystemHealth(BaseModel):
    status: str
    services: dict[str, ServiceHealth]


async def check_service(service: str, check: Callable[[], None]) -> ServiceHealth:
    started_at = perf_counter()
    try:
        await asyncio.to_thread(check)
        status = "healthy"
        message = "Connection established"
    except Exception:
        status = "unavailable"
        message = "Connection could not be established"

    return ServiceHealth(
        service=service,
        status=status,
        latency_ms=round((perf_counter() - started_at) * 1000, 1),
        checked_at=datetime.now(UTC),
        message=message,
    )


async def postgres_health(settings: Settings | None = None) -> ServiceHealth:
    current = settings or get_settings()
    return await check_service("PostgreSQL", lambda: ping_postgres(current))


async def mongodb_health(settings: Settings | None = None) -> ServiceHealth:
    current = settings or get_settings()
    return await check_service("MongoDB", lambda: ping_mongodb(current))


@router.get("", response_model=SystemHealth)
async def system_health() -> SystemHealth:
    postgres, mongodb = await asyncio.gather(postgres_health(), mongodb_health())
    services = {"postgres": postgres, "mongodb": mongodb}
    all_healthy = all(item.status == "healthy" for item in services.values())
    overall = "healthy" if all_healthy else "degraded"
    return SystemHealth(status=overall, services=services)


@router.get("/postgres", response_model=ServiceHealth)
async def get_postgres_health() -> ServiceHealth:
    return await postgres_health()


@router.get("/mongodb", response_model=ServiceHealth)
async def get_mongodb_health() -> ServiceHealth:
    return await mongodb_health()
