from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import psycopg
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def ping_postgres(settings: Settings) -> None:
    """Open a short-lived connection and verify the server responds."""
    with psycopg.connect(
        settings.postgres_dsn,
        connect_timeout=min(settings.query_timeout_seconds, 10),
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()


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
