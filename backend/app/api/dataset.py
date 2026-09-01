import asyncio
from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import dataset as dataset_service

router = APIRouter(prefix="/api/dataset", tags=["dataset"])

# Concurrent generate/reset requests would otherwise interleave (generation
# reseeds the shared random/Faker state, and both operations delete-then-write
# each store). A single-process asyncio.Lock is enough here -- this app never
# runs more than one backend process, so there's no need for a distributed lock.
_mutation_lock = asyncio.Lock()


class StoreCounts(BaseModel):
    customers: int
    products: int
    orders: int


class StoreResult(BaseModel):
    status: str
    counts: StoreCounts | None = None
    message: str | None = None


class DatasetStatus(BaseModel):
    postgres: StoreResult
    mongodb: StoreResult


def _to_status(results: dict[str, dataset_service.StoreResult]) -> DatasetStatus:
    def convert(result: dataset_service.StoreResult) -> StoreResult:
        return StoreResult(
            status=result.status,
            counts=StoreCounts(**asdict(result.counts)) if result.counts else None,
            message=result.message,
        )

    return DatasetStatus(postgres=convert(results["postgres"]), mongodb=convert(results["mongodb"]))


@router.get("/status", response_model=DatasetStatus)
async def get_dataset_status() -> DatasetStatus:
    results = await asyncio.to_thread(dataset_service.dataset_status)
    return _to_status(results)


@router.post("/generate", response_model=DatasetStatus)
async def generate_dataset() -> DatasetStatus:
    async with _mutation_lock:
        results = await asyncio.to_thread(dataset_service.generate_dataset)
    return _to_status(results)


@router.post("/reset", response_model=DatasetStatus)
async def reset_dataset() -> DatasetStatus:
    async with _mutation_lock:
        results = await asyncio.to_thread(dataset_service.reset_dataset)
    return _to_status(results)
