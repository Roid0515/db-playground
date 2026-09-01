from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from app.config import Settings, get_settings


def ping_mongodb(settings: Settings) -> None:
    """Open a short-lived client and verify the server responds."""
    timeout_ms = min(settings.query_timeout_seconds, 10) * 1000
    with MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
    ) as client:
        client.admin.command("ping")


@lru_cache
def get_client() -> MongoClient:
    """A single pooled client shared by longer-lived callers (e.g. dataset generation)."""
    return MongoClient(get_settings().mongodb_uri)


def get_database() -> Database:
    return get_client()[get_settings().mongodb_database]
