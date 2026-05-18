"""Dependency injection for API endpoints."""

from langchain_postgres.vectorstores import PGVector

from app.services.embedder import get_vector_store


def get_store() -> PGVector:
    """Return a connected PGVector store for similarity search."""
    return get_vector_store()
