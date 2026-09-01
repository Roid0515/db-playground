import asyncio
from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import dataset as dataset_service

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


class StoreCounts(BaseModel):
    customers: int
    products: int
    orders: int


class DatasetStatus(BaseModel):
    postgres: StoreCounts
    mongodb: StoreCounts


def _to_status(counts: dict[str, dataset_service.StoreCounts]) -> DatasetStatus:
    return DatasetStatus(
        postgres=StoreCounts(**asdict(counts["postgres"])),
        mongodb=StoreCounts(**asdict(counts["mongodb"])),
    )


@router.get("/status", response_model=DatasetStatus)
async def get_dataset_status() -> DatasetStatus:
    counts = await asyncio.to_thread(dataset_service.dataset_status)
    return _to_status(counts)


@router.post("/generate", response_model=DatasetStatus)
async def generate_dataset() -> DatasetStatus:
    await asyncio.to_thread(dataset_service.generate_dataset)
    counts = await asyncio.to_thread(dataset_service.dataset_status)
    return _to_status(counts)


@router.post("/reset", response_model=DatasetStatus)
async def reset_dataset() -> DatasetStatus:
    await asyncio.to_thread(dataset_service.reset_dataset)
    counts = await asyncio.to_thread(dataset_service.dataset_status)
    return _to_status(counts)
