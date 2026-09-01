"""Collection browsing and validated ad-hoc query execution against MongoDB --
the same approach and safety philosophy as app/services/sql_console.py, for
the document side.

Accepts a small, safe subset of real mongosh syntax: `db.<collection>.<op>(<args>)`
where <op> is one of a fixed allowlist (find/aggregate/countDocuments/
insertOne/insertMany/updateOne/updateMany/deleteOne/deleteMany) and <args>
are strict JSON values -- not a full JavaScript interpreter, so unquoted
keys, JS expressions, and functions aren't supported. That's a deliberate
constraint, not an oversight: it's a big enough subset for real practice
while keeping "what can actually run" fully enumerable, mirroring the SQL
console's "no DDL" boundary (nothing here can create/drop a collection,
build an index, or touch another database).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from pymongo.errors import PyMongoError

from app.config import get_settings
from app.db.mongodb import get_database
from app.services.bson_utils import to_jsonable

_COMMAND_PATTERN = re.compile(
    r"^\s*db\.(?P<collection>[A-Za-z_][A-Za-z0-9_]*)\.(?P<operation>[A-Za-z]+)\((?P<args>.*)\)\s*;?\s*$",
    re.DOTALL,
)

_ALLOWED_OPERATIONS = {
    "find",
    "aggregate",
    "countDocuments",
    "insertOne",
    "insertMany",
    "updateOne",
    "updateMany",
    "deleteOne",
    "deleteMany",
}


class MongoConsoleError(ValueError):
    """A user-facing validation error, distinct from a database driver error."""


@dataclass(frozen=True)
class CollectionInfo:
    name: str
    document_count: int
    sample_fields: list[str]


@dataclass(frozen=True)
class CollectionDocuments:
    documents: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class MongoQueryResult:
    documents: list[dict[str, Any]] | None
    row_count: int
    truncated: bool
    duration_ms: float
    operation: str


def _split_top_level_args(args: str) -> list[str]:
    """Splits "a, b, c" into ["a", "b", "c"], respecting nested {}/[]/"" so
    commas inside JSON values aren't mistaken for argument separators."""
    parts: list[str] = []
    depth = 0
    in_string: str | None = None
    escape = False
    current: list[str] = []
    for ch in args:
        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in "\"'":
            in_string = ch
            current.append(ch)
        elif ch in "{[":
            depth += 1
            current.append(ch)
        elif ch in "}]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [part.strip() for part in parts]


def parse_command(raw: str) -> tuple[str, str, list[Any]]:
    match = _COMMAND_PATTERN.match(raw)
    if not match:
        raise MongoConsoleError(
            "명령을 이해할 수 없습니다. db.<컬렉션>.<연산>(...) 형태로 입력하세요. "
            '예: db.customers.find({"status": "active"})'
        )
    collection = match.group("collection")
    operation = match.group("operation")
    if operation not in _ALLOWED_OPERATIONS:
        raise MongoConsoleError(
            f"'{operation}' 연산은 지원하지 않습니다. "
            f"{', '.join(sorted(_ALLOWED_OPERATIONS))}만 실행할 수 있습니다."
        )
    args_text = match.group("args").strip()
    args: list[Any] = []
    if args_text:
        for part in _split_top_level_args(args_text):
            try:
                args.append(json.loads(part))
            except json.JSONDecodeError as exc:
                raise MongoConsoleError(
                    f"인자를 JSON으로 해석할 수 없습니다: {part!r}. "
                    '키는 반드시 큰따옴표로 감싸야 합니다 (예: {"status": "active"}).'
                ) from exc
    return collection, operation, args


def list_collections() -> list[CollectionInfo]:
    db = get_database()
    infos = []
    for name in sorted(db.list_collection_names()):
        collection = db[name]
        count = collection.count_documents({})
        sample = collection.find_one()
        sample_fields = sorted(sample.keys()) if sample else []
        infos.append(CollectionInfo(name=name, document_count=count, sample_fields=sample_fields))
    return infos


def get_collection_documents(
    collection_name: str, page: int, page_size: int
) -> CollectionDocuments:
    db = get_database()
    if collection_name not in db.list_collection_names():
        raise MongoConsoleError(f"컬렉션 '{collection_name}'을(를) 찾을 수 없습니다.")

    page_size = max(1, min(page_size, get_settings().document_query_max_results))
    offset = max(page - 1, 0) * page_size

    collection = db[collection_name]
    total = collection.count_documents({})
    cursor = collection.find().skip(offset).limit(page_size)
    documents = [to_jsonable(doc) for doc in cursor]
    return CollectionDocuments(documents=documents, total=total, page=page, page_size=page_size)


def _require_args(operation: str, args: list[Any], shape: str) -> None:
    raise MongoConsoleError(f"{operation}은(는) {shape}를 인자로 받습니다.")


def run_query(raw: str) -> MongoQueryResult:
    collection_name, operation, args = parse_command(raw)
    settings = get_settings()
    max_results = settings.document_query_max_results
    timeout_ms = settings.query_timeout_seconds * 1000
    collection = get_database()[collection_name]

    started = time.perf_counter()
    try:
        if operation == "find":
            filter_ = args[0] if len(args) > 0 else {}
            projection = args[1] if len(args) > 1 else None
            cursor = (
                collection.find(filter_, projection).max_time_ms(timeout_ms).limit(max_results + 1)
            )
            documents = list(cursor)
            truncated = len(documents) > max_results
            documents = documents[:max_results]
            return MongoQueryResult(
                documents=[to_jsonable(doc) for doc in documents],
                row_count=len(documents),
                truncated=truncated,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation == "aggregate":
            pipeline = args[0] if len(args) > 0 else []
            if not isinstance(pipeline, list):
                raise MongoConsoleError("aggregate의 인자는 파이프라인 배열이어야 합니다.")
            documents = []
            for doc in collection.aggregate(pipeline, maxTimeMS=timeout_ms):
                documents.append(doc)
                if len(documents) > max_results:
                    break
            truncated = len(documents) > max_results
            documents = documents[:max_results]
            return MongoQueryResult(
                documents=[to_jsonable(doc) for doc in documents],
                row_count=len(documents),
                truncated=truncated,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation == "countDocuments":
            filter_ = args[0] if len(args) > 0 else {}
            count = collection.count_documents(filter_, maxTimeMS=timeout_ms)
            return MongoQueryResult(
                documents=None,
                row_count=count,
                truncated=False,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation == "insertOne":
            if len(args) != 1 or not isinstance(args[0], dict):
                _require_args(operation, args, "문서 하나(JSON 객체)")
            result = collection.insert_one(args[0])
            return MongoQueryResult(
                documents=None,
                row_count=1 if result.inserted_id else 0,
                truncated=False,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation == "insertMany":
            if len(args) != 1 or not isinstance(args[0], list):
                _require_args(operation, args, "문서 배열")
            result = collection.insert_many(args[0])
            return MongoQueryResult(
                documents=None,
                row_count=len(result.inserted_ids),
                truncated=False,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation in ("updateOne", "updateMany"):
            if len(args) != 2 or not isinstance(args[0], dict) or not isinstance(args[1], dict):
                _require_args(operation, args, "(필터, 업데이트) JSON 객체 두 개")
            method = collection.update_one if operation == "updateOne" else collection.update_many
            result = method(args[0], args[1])
            return MongoQueryResult(
                documents=None,
                row_count=result.modified_count,
                truncated=False,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )

        if operation in ("deleteOne", "deleteMany"):
            if len(args) != 1 or not isinstance(args[0], dict):
                _require_args(operation, args, "필터(JSON 객체) 하나")
            method = collection.delete_one if operation == "deleteOne" else collection.delete_many
            result = method(args[0])
            return MongoQueryResult(
                documents=None,
                row_count=result.deleted_count,
                truncated=False,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                operation=operation,
            )
    except PyMongoError as exc:
        raise MongoConsoleError(f"MongoDB 오류: {exc}") from exc

    # Unreachable: parse_command() already rejects anything outside
    # _ALLOWED_OPERATIONS, and every allowed operation is handled above.
    raise MongoConsoleError(f"'{operation}' 처리 로직이 구현되지 않았습니다.")
