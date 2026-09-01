import asyncio
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import index_lab

router = APIRouter(prefix="/api/index-lab", tags=["index-lab"])


class IndexStatusSchema(BaseModel):
    table: str
    column: str
    index_name: str
    index_exists: bool
    row_count: int


class ExplainResultSchema(BaseModel):
    node_type: str
    used_index: bool
    execution_time_ms: float
    planning_time_ms: float
    row_count: int
    plan_text: str


@router.get("/status", response_model=IndexStatusSchema)
async def get_status() -> IndexStatusSchema:
    status = await asyncio.to_thread(index_lab.index_status)
    return IndexStatusSchema(**asdict(status))


@router.post("/explain", response_model=ExplainResultSchema)
async def post_explain() -> ExplainResultSchema:
    try:
        result = await asyncio.to_thread(index_lab.explain_query)
    except Exception as exc:  # noqa: BLE001 - surface the DB's own error (e.g. empty dataset)
        raise HTTPException(
            status_code=400, detail=f"실행 계획을 가져오지 못했습니다: {exc}"
        ) from exc
    return ExplainResultSchema(**asdict(result))


@router.post("/create-index", response_model=IndexStatusSchema)
async def post_create_index() -> IndexStatusSchema:
    status = await asyncio.to_thread(index_lab.create_index)
    return IndexStatusSchema(**asdict(status))


@router.post("/drop-index", response_model=IndexStatusSchema)
async def post_drop_index() -> IndexStatusSchema:
    status = await asyncio.to_thread(index_lab.drop_index)
    return IndexStatusSchema(**asdict(status))
