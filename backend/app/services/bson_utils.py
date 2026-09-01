"""Shared helper for turning a MongoDB document (which may contain BSON types
FastAPI can't serialize natively) into plain JSON-safe Python values."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId


def to_jsonable(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_jsonable(val) for val in value]
    return value
