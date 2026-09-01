import psycopg

from app.config import Settings


def ping_postgres(settings: Settings) -> None:
    """Open a short-lived connection and verify the server responds."""
    with psycopg.connect(
        settings.postgres_dsn,
        connect_timeout=min(settings.query_timeout_seconds, 10),
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
