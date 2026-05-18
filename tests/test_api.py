"""Tests for the FastAPI endpoints."""

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.api.dependencies import get_store
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/upload — validation / error paths (no DB)
# ---------------------------------------------------------------------------

def _make_zip_bytes(valid: bool = True) -> bytes:
    """Return bytes that look like (or not like) a valid ZIP."""
    if not valid:
        return b"not a zip file at all"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("summarizedActivities.json", json.dumps([]))
        zf.writestr("sleepData.json", json.dumps([]))
        zf.writestr("personalRecord.json", json.dumps([]))
    return buf.getvalue()


def test_upload_returns_422_for_missing_file():
    response = client.post("/api/v1/upload")
    assert response.status_code == 422


def test_upload_returns_400_for_non_zip_extension():
    response = client.post(
        "/api/v1/upload",
        files={"file": ("export.txt", b"some text", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_returns_400_for_invalid_zip_bytes():
    response = client.post(
        "/api/v1/upload",
        files={"file": ("export.zip", _make_zip_bytes(valid=False), "application/zip")},
    )
    assert response.status_code == 400


def test_upload_success_mocked():
    mock_doc = Document(
        page_content="You completed a cycling session.",
        metadata={"data_type": "activity", "source": "garmin_zip"},
    )
    with (
        patch("app.api.routers.upload.parse_garmin_zip", return_value={"summarizedActivities": [], "sleepData": [], "personalRecords": []}),
        patch("app.api.routers.upload.chunk_garmin_data", return_value=[mock_doc, mock_doc]),
        patch("app.api.routers.upload.embed_and_store", return_value=MagicMock()),
    ):
        response = client.post(
            "/api/v1/upload",
            files={"file": ("export.zip", _make_zip_bytes(), "application/zip")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["documents_stored"] == 2
    assert body["breakdown"] == {"activity": 2}
    assert "collection" in body


# ---------------------------------------------------------------------------
# POST /api/v1/query — validation / error paths (no DB)
# ---------------------------------------------------------------------------

def test_query_returns_422_for_missing_body():
    response = client.post("/api/v1/query")
    assert response.status_code == 422


def test_query_returns_422_for_empty_query():
    response = client.post("/api/v1/query", json={"query": ""})
    assert response.status_code == 422


def test_query_returns_422_for_whitespace_query():
    response = client.post("/api/v1/query", json={"query": "   "})
    assert response.status_code == 422


def test_query_returns_422_for_invalid_data_type():
    response = client.post("/api/v1/query", json={"query": "best run", "data_type": "invalid"})
    assert response.status_code == 422


def test_query_success_mocked():
    mock_doc = Document(
        page_content="You completed a cycling session.",
        metadata={"data_type": "activity", "source": "garmin_zip"},
    )
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.92)]

    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post("/api/v1/query", json={"query": "cycling session", "k": 3})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "cycling session"
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["content"] == "You completed a cycling session."
    assert result["metadata"]["data_type"] == "activity"
    assert isinstance(result["score"], float)


def test_query_with_data_type_filter_mocked():
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = []

    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "deep sleep", "k": 5, "data_type": "sleep"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_store.similarity_search_with_score.assert_called_once_with(
        "deep sleep", k=5, filter={"data_type": "sleep"}
    )


def test_query_returns_503_when_store_unavailable():
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.side_effect = Exception("connection refused")

    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post("/api/v1/query", json={"query": "best marathon"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Integration tests (require running DB + real ZIP)
# ---------------------------------------------------------------------------

REAL_ZIP = Path(__file__).parent.parent / "data" / "86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip"


@pytest.mark.skipif(not REAL_ZIP.exists(), reason="Real Garmin ZIP not available")
def test_upload_real_zip():
    with open(REAL_ZIP, "rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": (REAL_ZIP.name, f, "application/zip")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["documents_stored"] > 0
    assert "activity" in body["breakdown"]


@pytest.mark.skipif(not REAL_ZIP.exists(), reason="Real Garmin ZIP not available")
def test_query_after_upload():
    response = client.post(
        "/api/v1/query",
        json={"query": "cycling session with high elevation", "k": 5, "data_type": "activity"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) > 0
    for result in body["results"]:
        assert result["metadata"]["data_type"] == "activity"
        assert result["score"] >= 0.0
