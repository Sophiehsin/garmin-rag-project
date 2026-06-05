"""Embedder service — generates vector embeddings and stores them in pgvector.

Design notes:
  - Uses langchain-postgres (not deprecated langchain-community) for PGVector.
  - Embedding model: all-MiniLM-L6-v2 (384-dim, cosine similarity).
  - Device auto-detected: MPS (Apple Silicon) > CUDA > CPU.
  - Deterministic document IDs prevent duplicate rows on re-upload.
  - batch_size=32 prevents OOM when ingesting 2000+ activity records.
"""

from __future__ import annotations

import hashlib
from typing import Optional

import torch
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import DistanceStrategy, PGVector

from app.core.config import settings
from app.core.database import get_connection_string


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

def _detect_device() -> str:
    """Return the best available torch device: mps > cuda > cpu."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# ---------------------------------------------------------------------------
# Embedding model (module-level cache — loaded once, reused across calls)
# ---------------------------------------------------------------------------

_embeddings: Optional[HuggingFaceEmbeddings] = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached HuggingFaceEmbeddings instance.

    First call downloads all-MiniLM-L6-v2 (~90 MB) and moves it to the
    best available device. Subsequent calls return the cached instance.
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": _detect_device()},
            encode_kwargs={"batch_size": 32, "normalize_embeddings": True},
        )
    return _embeddings


# ---------------------------------------------------------------------------
# Deterministic document ID
# ---------------------------------------------------------------------------

def _make_doc_id(doc: Document) -> str:
    """Generate a stable SHA-256 ID from a document's unique identity fields.

    Key format: "{user_id}:{data_type}:{record_id}:{date}"
    Including user_id prevents cross-user collisions when two users happen to
    have the same activity_id (Garmin IDs are not globally unique).
    Falls back to hashing page_content for corrupt records missing all fields.
    """
    meta = doc.metadata
    user_id = meta.get("user_id") or ""
    data_type = meta.get("data_type") or ""
    record_id = meta.get("record_id")
    date = meta.get("date") or ""

    if data_type and (record_id is not None or date):
        key = f"{user_id}:{data_type}:{record_id}:{date}"
    else:
        key = f"content:{doc.page_content}"

    return hashlib.sha256(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_and_store(
    documents: list[Document],
    collection_name: Optional[str] = None,
) -> PGVector:
    """Embed documents and store them in pgvector.

    Generates deterministic IDs so re-uploading the same data upserts rather
    than duplicating. Uses cosine similarity — required for all-MiniLM-L6-v2.

    Args:
        documents: List of LangChain Documents from chunk_garmin_data().
        collection_name: pgvector collection name. Defaults to settings value.

    Returns:
        Connected PGVector store instance (can be used immediately for search).
    """
    ids = [_make_doc_id(doc) for doc in documents]
    collection = collection_name or settings.vector_collection

    return PGVector.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        connection=get_connection_string(),
        collection_name=collection,
        distance_strategy=DistanceStrategy.COSINE,
        ids=ids,
        pre_delete_collection=False,
        use_jsonb=True,
    )


def get_vector_store(collection_name: Optional[str] = None) -> PGVector:
    """Return a PGVector instance connected to an existing collection.

    Does NOT re-embed anything. Used by the RAG chain (Task 10) to run
    similarity searches against already-stored embeddings.

    Args:
        collection_name: pgvector collection name. Defaults to settings value.

    Returns:
        PGVector store instance ready for similarity_search().
    """
    return PGVector(
        embeddings=get_embeddings(),
        connection=get_connection_string(),
        collection_name=collection_name or settings.vector_collection,
        distance_strategy=DistanceStrategy.COSINE,
        use_jsonb=True,
    )
