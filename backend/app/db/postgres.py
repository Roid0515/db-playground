from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import psycopg
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def ping_postgres(settings: Settings) -> str:
    """Open a short-lived connection, verify the server responds, and report
    its real version -- this app runs against a Homebrew-built binary in the
    desktop app and an Alpine Docker image in the Compose path, so a
    hardcoded "16 · Alpine" label would be accurate for exactly one of them.
    """
    with psycopg.connect(
        settings.postgres_dsn,
        connect_timeout=min(settings.query_timeout_seconds, 10),
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            (version,) = cursor.fetchone()
            return version


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = URL.create(
        "postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )
    return create_engine(url)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
