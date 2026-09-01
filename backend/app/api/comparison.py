import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import comparison

router = APIRouter(prefix="/api/comparison", tags=["comparison"])


class OrderSummarySchema(BaseModel):
    order_number: int
    customer_name: str
    status: str
    item_count: int
    total_cents: int


class RelationalOrderViewSchema(BaseModel):
    order: dict[str, Any]
    customer: dict[str, Any]
    items: list[dict[str, Any]]
    sql: str


class DocumentOrderViewSchema(BaseModel):
    document: dict[str, Any]


class OrderComparisonSchema(BaseModel):
    order_number: int
    relational: RelationalOrderViewSchema
    document: DocumentOrderViewSchema


@router.get("/orders", response_model=list[OrderSummarySchema])
async def get_order_summaries() -> list[OrderSummarySchema]:
    summaries = await asyncio.to_thread(comparison.list_order_summaries)
    return [OrderSummarySchema(**asdict(summary)) for summary in summaries]


@router.get("/orders/{order_number}", response_model=OrderComparisonSchema)
async def get_order_comparison(order_number: int) -> OrderComparisonSchema:
    try:
        result = await asyncio.to_thread(comparison.get_order_comparison, order_number)
    except comparison.ComparisonError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OrderComparisonSchema(
        order_number=result.order_number,
        relational=RelationalOrderViewSchema(**asdict(result.relational)),
        document=DocumentOrderViewSchema(**asdict(result.document)),
    )
