"""Tests for app/services/embedder.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_postgres.vectorstores import DistanceStrategy

from app.core.database import get_connection_string
from app.services.embedder import _detect_device, _make_doc_id, embed_and_store, get_vector_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_reachable() -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432,
            user="postgres", password="test123",
            dbname="vectordb", connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


def _sample_doc(data_type="activity", record_id=123, date="2024-03-16") -> Document:
    return Document(
        page_content="You completed a cycling session on March 16, 2024.",
        metadata={"data_type": data_type, "record_id": record_id, "date": date, "source": "garmin_zip"},
    )


# ---------------------------------------------------------------------------
# Connection string tests
# ---------------------------------------------------------------------------

def test_get_connection_string_format():
    conn_str = get_connection_string()
    assert conn_str.startswith("postgresql+psycopg2://")
    assert "localhost" in conn_str
    assert "vectordb" in conn_str


# ---------------------------------------------------------------------------
# Deterministic ID tests
# ---------------------------------------------------------------------------

def test_make_doc_id_is_deterministic():
    doc = _sample_doc()
    assert _make_doc_id(doc) == _make_doc_id(doc)


def test_make_doc_id_differs_for_different_records():
    doc_a = _sample_doc(record_id=100)
    doc_b = _sample_doc(record_id=999)
    assert _make_doc_id(doc_a) != _make_doc_id(doc_b)


def test_make_doc_id_differs_for_different_data_types():
    doc_a = _sample_doc(data_type="activity")
    doc_b = _sample_doc(data_type="sleep")
    assert _make_doc_id(doc_a) != _make_doc_id(doc_b)


def test_make_doc_id_is_64_char_hex():
    doc = _sample_doc()
    doc_id = _make_doc_id(doc)
    assert len(doc_id) == 64
    assert all(c in "0123456789abcdef" for c in doc_id)


# ---------------------------------------------------------------------------
# Hardware detection test
# ---------------------------------------------------------------------------

def test_detect_device_returns_valid_string():
    device = _detect_device()
    assert device in ("mps", "cuda", "cpu")


# ---------------------------------------------------------------------------
# embed_and_store unit tests (mocked — no DB, no model download)
# ---------------------------------------------------------------------------

@patch("app.services.embedder.PGVector.from_documents")
@patch("app.services.embedder.get_embeddings")
def test_embed_and_store_passes_ids(mock_get_embeddings, mock_from_docs):
    mock_get_embeddings.return_value = MagicMock()
    mock_from_docs.return_value = MagicMock()

    docs = [_sample_doc(record_id=1), _sample_doc(record_id=2)]
    embed_and_store(docs)

    call_kwargs = mock_from_docs.call_args.kwargs
    assert "ids" in call_kwargs
    assert len(call_kwargs["ids"]) == 2


@patch("app.services.embedder.PGVector.from_documents")
@patch("app.services.embedder.get_embeddings")
def test_embed_and_store_uses_cosine_distance(mock_get_embeddings, mock_from_docs):
    mock_get_embeddings.return_value = MagicMock()
    mock_from_docs.return_value = MagicMock()

    embed_and_store([_sample_doc()])

    call_kwargs = mock_from_docs.call_args.kwargs
    assert call_kwargs.get("distance_strategy") == DistanceStrategy.COSINE


@patch("app.services.embedder.PGVector.from_documents")
@patch("app.services.embedder.get_embeddings")
def test_embed_and_store_default_collection(mock_get_embeddings, mock_from_docs):
    mock_get_embeddings.return_value = MagicMock()
    mock_from_docs.return_value = MagicMock()

    from app.core.config import settings
    embed_and_store([_sample_doc()])

    call_kwargs = mock_from_docs.call_args.kwargs
    assert call_kwargs.get("collection_name") == settings.vector_collection


@patch("app.services.embedder.PGVector.from_documents")
@patch("app.services.embedder.get_embeddings")
def test_embed_and_store_custom_collection(mock_get_embeddings, mock_from_docs):
    mock_get_embeddings.return_value = MagicMock()
    mock_from_docs.return_value = MagicMock()

    embed_and_store([_sample_doc()], collection_name="test_col")

    call_kwargs = mock_from_docs.call_args.kwargs
    assert call_kwargs.get("collection_name") == "test_col"


# ---------------------------------------------------------------------------
# get_vector_store unit tests (mocked)
# ---------------------------------------------------------------------------

@patch("app.services.embedder.PGVector")
@patch("app.services.embedder.get_embeddings")
def test_get_vector_store_returns_pgvector(mock_get_embeddings, mock_pgvector_cls):
    mock_get_embeddings.return_value = MagicMock()
    mock_pgvector_cls.return_value = MagicMock()

    store = get_vector_store()
    assert store is mock_pgvector_cls.return_value


@patch("app.services.embedder.PGVector")
@patch("app.services.embedder.get_embeddings")
def test_get_vector_store_uses_cosine_distance(mock_get_embeddings, mock_pgvector_cls):
    mock_get_embeddings.return_value = MagicMock()
    mock_pgvector_cls.return_value = MagicMock()

    get_vector_store()

    call_kwargs = mock_pgvector_cls.call_args.kwargs
    assert call_kwargs.get("distance_strategy") == DistanceStrategy.COSINE


# ---------------------------------------------------------------------------
# Integration test — requires docker-compose up -d
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL not running (docker-compose up -d)")
def test_embed_and_store_roundtrip():
    """Full pipeline: embed → store → similarity_search → verify metadata survives."""
    docs = [
        Document(
            page_content="You completed a cycling session on March 16, 2024, covering 7.91 km.",
            metadata={"data_type": "activity", "record_id": 99991, "date": "2024-03-16", "source": "garmin_zip"},
        ),
        Document(
            page_content="On the night of May 14, 2024, you slept for 7 hours and 23 minutes.",
            metadata={"data_type": "sleep", "record_id": None, "date": "2024-05-14", "source": "garmin_zip"},
        ),
    ]

    store = embed_and_store(docs, collection_name="test_task8")
    results = store.similarity_search("long cycling session", k=1)

    assert len(results) == 1
    assert results[0].metadata["data_type"] == "activity"
    assert "cycling" in results[0].page_content


@pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL not running (docker-compose up -d)")
def test_embed_and_store_idempotent():
    """Re-storing the same documents must not create duplicate rows."""
    import psycopg2

    doc = Document(
        page_content="You completed a running session on April 1, 2024.",
        metadata={"data_type": "activity", "record_id": 99992, "date": "2024-04-01", "source": "garmin_zip"},
    )

    embed_and_store([doc], collection_name="test_task8_idem")
    embed_and_store([doc], collection_name="test_task8_idem")  # second upload — same data

    conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="test123", dbname="vectordb")
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM langchain_pg_embedding e "
        "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
        "WHERE c.name = %s",
        ("test_task8_idem",),
    )
    count = cur.fetchone()[0]
    conn.close()

    assert count == 1, f"Expected 1 row after two identical uploads, got {count}"
