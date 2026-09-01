from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from app.config import Settings, get_settings


def ping_mongodb(settings: Settings) -> str:
    """Open a short-lived client, verify the server responds, and report its
    real version (buildInfo), same rationale as ping_postgres.
    """
    timeout_ms = min(settings.query_timeout_seconds, 10) * 1000
    with MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
    ) as client:
        return str(client.admin.command("buildInfo")["version"])


@lru_cache
def get_client() -> MongoClient:
    """A single pooled client shared by longer-lived callers (e.g. dataset generation).

    Unlike ping_mongodb's short-lived client, this one used to have no timeouts
    at all -- a Mongo instance that's up but not responding (network partition,
    stuck lock, etc.) could hang a request indefinitely. serverSelectionTimeoutMS
    and connectTimeoutMS bound how long we'll wait to find/connect to a server;
    per-operation limits (maxTimeMS, cursor caps) belong on individual queries
    once there's a Mongo query console to apply them to.
    """
    settings = get_settings()
    timeout_ms = settings.query_timeout_seconds * 1000
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
    )


def get_database() -> Database:
    return get_client()[get_settings().mongodb_database]
