from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "db_playground"
    postgres_user: str = "db_playground"
    postgres_password: str = Field(repr=False)
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_database: str = "db_playground"
    mongodb_username: str = "db_playground"
    mongodb_password: str = Field(repr=False)
    query_timeout_seconds: int = 10
    query_max_rows: int = 500
    document_query_max_results: int = 500
    frontend_origin: str = "http://localhost:5173"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"host={self.postgres_host} port={self.postgres_port} dbname={self.postgres_db} "
            f"user={self.postgres_user} password={self.postgres_password}"
        )

    @property
    def mongodb_uri(self) -> str:
        return (
            f"mongodb://{self.mongodb_username}:{self.mongodb_password}@"
            f"{self.mongodb_host}:{self.mongodb_port}/?authSource=admin"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
