import pytest
from fastapi.testclient import TestClient

from app.api import mongodb as mongodb_api
from app.main import app
from app.services.mongo_console import (
    CollectionDocuments,
    CollectionInfo,
    MongoConsoleError,
    MongoQueryResult,
    parse_command,
)

client = TestClient(app)


@pytest.mark.parametrize(
    ("raw", "collection", "operation"),
    [
        ('db.customers.find({"status": "active"})', "customers", "find"),
        ("db.customers.find()", "customers", "find"),
        ('db.orders.aggregate([{"$match": {}}])', "orders", "aggregate"),
        ('db.customers.countDocuments({"status": "active"})', "customers", "countDocuments"),
        ('db.customers.insertOne({"email": "a@b.com"})', "customers", "insertOne"),
        ('db.customers.updateOne({"_id": "1"}, {"$set": {"x": 1}})', "customers", "updateOne"),
        ('db.customers.deleteOne({"_id": "1"})', "customers", "deleteOne"),
    ],
)
def test_parse_command_accepts_allowed_operations(
    raw: str, collection: str, operation: str
) -> None:
    parsed_collection, parsed_operation, _args = parse_command(raw)
    assert parsed_collection == collection
    assert parsed_operation == operation


def test_parse_command_rejects_unknown_syntax() -> None:
    with pytest.raises(MongoConsoleError):
        parse_command("show collections")


def test_parse_command_rejects_disallowed_operation() -> None:
    with pytest.raises(MongoConsoleError):
        parse_command("db.customers.drop()")


def test_parse_command_rejects_invalid_json_args() -> None:
    with pytest.raises(MongoConsoleError):
        parse_command("db.customers.find({status: 'active'})")


def test_parse_command_splits_nested_args_correctly() -> None:
    collection, operation, args = parse_command(
        'db.customers.updateOne({"status": "active", "tags": ["a,b", "c"]}, {"$set": {"x": 1}})'
    )
    assert collection == "customers"
    assert operation == "updateOne"
    assert args == [
        {"status": "active", "tags": ["a,b", "c"]},
        {"$set": {"x": 1}},
    ]


def test_get_collections_returns_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        mongodb_api.mongo_console,
        "list_collections",
        lambda: [
            CollectionInfo(name="customers", document_count=24, sample_fields=["_id", "email"])
        ],
    )
    response = client.get("/api/mongodb/collections")
    assert response.status_code == 200
    assert response.json() == [
        {"name": "customers", "document_count": 24, "sample_fields": ["_id", "email"]}
    ]


def test_get_collection_documents_returns_404_for_unknown_collection(monkeypatch) -> None:
    def fail(_collection_name, _page, _page_size):
        raise MongoConsoleError("컬렉션 'nope'을(를) 찾을 수 없습니다.")

    monkeypatch.setattr(mongodb_api.mongo_console, "get_collection_documents", fail)
    response = client.get("/api/mongodb/collections/nope/documents")
    assert response.status_code == 404


def test_get_collection_documents_returns_data(monkeypatch) -> None:
    monkeypatch.setattr(
        mongodb_api.mongo_console,
        "get_collection_documents",
        lambda collection_name, page, page_size: CollectionDocuments(
            documents=[{"_id": "1", "email": "a@b.com"}], total=1, page=1, page_size=50
        ),
    )
    response = client.get("/api/mongodb/collections/customers/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["documents"] == [{"_id": "1", "email": "a@b.com"}]


def test_execute_query_rejects_invalid_command(monkeypatch) -> None:
    def fail(_command):
        raise MongoConsoleError("명령을 이해할 수 없습니다.")

    monkeypatch.setattr(mongodb_api.mongo_console, "run_query", fail)
    response = client.post("/api/mongodb/query", json={"command": "show collections"})
    assert response.status_code == 400
    assert "명령" in response.json()["detail"]


def test_execute_query_returns_results(monkeypatch) -> None:
    monkeypatch.setattr(
        mongodb_api.mongo_console,
        "run_query",
        lambda command: MongoQueryResult(
            documents=[{"_id": "1"}, {"_id": "2"}],
            row_count=2,
            truncated=False,
            duration_ms=1.2,
            operation="find",
        ),
    )
    response = client.post("/api/mongodb/query", json={"command": "db.customers.find()"})
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["documents"] == [{"_id": "1"}, {"_id": "2"}]


def test_execute_query_sanitizes_driver_errors(monkeypatch) -> None:
    def fail(_command):
        raise RuntimeError("connection failed (password=super-secret should never appear)")

    monkeypatch.setattr(mongodb_api.mongo_console, "run_query", fail)
    response = client.post("/api/mongodb/query", json={"command": "db.customers.find()"})
    assert response.status_code == 400
    assert "super-secret" not in response.json()["detail"]
