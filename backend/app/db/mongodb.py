from pymongo import MongoClient

from app.config import Settings


def ping_mongodb(settings: Settings) -> None:
    """Open a short-lived client and verify the server responds."""
    timeout_ms = min(settings.query_timeout_seconds, 10) * 1000
    with MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
    ) as client:
        client.admin.command("ping")