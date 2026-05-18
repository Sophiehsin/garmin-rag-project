"""Database connection helpers."""

from app.core.config import settings


def get_connection_string() -> str:
    """Return a psycopg2-compatible PostgreSQL connection string from settings.

    For AWS deployment, set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME as env vars
    pointing at your RDS instance — no code changes required.
    """
    return (
        f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )
