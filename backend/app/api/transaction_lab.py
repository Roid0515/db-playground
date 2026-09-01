import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import transaction_lab

router = APIRouter(prefix="/api/transaction-lab", tags=["transaction-lab"])


class BeginResponse(BaseModel):
    session_id: str


class ExecuteRequest(BaseModel):
    session_id: str
    sql: str


class SessionRequest(BaseModel):
    session_id: str


class ExecuteResultSchema(BaseModel):
    columns: list[str] | None
    rows: list[list[Any]] | None
    row_count: int


class StatusSchema(BaseModel):
    status: str


@router.post("/begin", response_model=BeginResponse)
async def begin() -> BeginResponse:
    session_id = await asyncio.to_thread(transaction_lab.begin)
    return BeginResponse(session_id=session_id)


@router.post("/execute", response_model=ExecuteResultSchema)
async def execute(payload: ExecuteRequest) -> ExecuteResultSchema:
    try:
        result = await asyncio.to_thread(transaction_lab.execute, payload.session_id, payload.sql)
    except transaction_lab.TransactionLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecuteResultSchema(**asdict(result))


@router.post("/peek", response_model=ExecuteResultSchema)
async def peek(payload: SessionRequest) -> ExecuteResultSchema:
    try:
        result = await asyncio.to_thread(transaction_lab.peek_within_session, payload.session_id)
    except transaction_lab.TransactionLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecuteResultSchema(**asdict(result))


@router.get("/peek-committed", response_model=ExecuteResultSchema)
async def peek_committed() -> ExecuteResultSchema:
    result = await asyncio.to_thread(transaction_lab.peek_committed_state)
    return ExecuteResultSchema(**asdict(result))


@router.post("/commit", response_model=StatusSchema)
async def commit(payload: SessionRequest) -> StatusSchema:
    try:
        await asyncio.to_thread(transaction_lab.commit, payload.session_id)
    except transaction_lab.TransactionLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StatusSchema(status="committed")


@router.post("/rollback", response_model=StatusSchema)
async def rollback(payload: SessionRequest) -> StatusSchema:
    try:
        await asyncio.to_thread(transaction_lab.rollback, payload.session_id)
    except transaction_lab.TransactionLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StatusSchema(status="rolled_back")
