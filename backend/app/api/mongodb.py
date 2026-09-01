import asyncio
import re
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import mongo_console

router = APIRouter(prefix="/api/mongodb", tags=["mongodb"])

_PASSWORD_PATTERN = re.compile(r"password=\S+", re.IGNORECASE)


def _safe_error_message(exc: Exception) -> str:
    return _PASSWORD_PATTERN.sub("password=***", str(exc))[:2000]


class CollectionSchema(BaseModel):
    name: str
    document_count: int
    sample_fields: list[str]


class CollectionDocumentsSchema(BaseModel):
    documents: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class QueryRequest(BaseModel):
    command: str


class QueryResultSchema(BaseModel):
    documents: list[dict[str, Any]] | None
    row_count: int
    truncated: bool
    duration_ms: float
    operation: str


@router.get("/collections", response_model=list[CollectionSchema])
async def get_collections() -> list[CollectionSchema]:
    collections = await asyncio.to_thread(mongo_console.list_collections)
    return [CollectionSchema(**asdict(collection)) for collection in collections]


@router.get("/collections/{collection_name}/documents", response_model=CollectionDocumentsSchema)
async def get_collection_documents(
    collection_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> CollectionDocumentsSchema:
    try:
        result = await asyncio.to_thread(
            mongo_console.get_collection_documents, collection_name, page, page_size
        )
    except mongo_console.MongoConsoleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CollectionDocumentsSchema(**asdict(result))


@router.post("/query", response_model=QueryResultSchema)
async def execute_query(payload: QueryRequest) -> QueryResultSchema:
    try:
        result = await asyncio.to_thread(mongo_console.run_query, payload.command)
    except mongo_console.MongoConsoleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface the DB's own error to the learner
        raise HTTPException(status_code=400, detail=_safe_error_message(exc)) from exc
    return QueryResultSchema(**asdict(result))
