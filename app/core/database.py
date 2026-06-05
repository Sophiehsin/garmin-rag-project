"""Database connection helpers."""

from typing import Generator

from sqlmodel import Session, create_engine

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


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_connection_string())
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a SQLModel session, closes on exit."""
    with Session(get_engine()) as session:
        yield session
