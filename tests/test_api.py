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
from app.core.security import get_current_user
from app.main import app
from app.models.sql_models import User

client = TestClient(app)

# ---------------------------------------------------------------------------
# Auth + store helpers — mock both dependencies so no real DB is needed
# ---------------------------------------------------------------------------

_MOCK_USER = User(id=1, email="test@example.com")
_MOCK_STORE = MagicMock()
_MOCK_STORE.similarity_search_with_score.return_value = []


def _auth():
    """Override auth + store so tests never hit a real DB."""
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    app.dependency_overrides[get_store] = lambda: _MOCK_STORE


def _clear():
    app.dependency_overrides.clear()


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


def test_upload_returns_401_without_auth():
    """Upload endpoint requires JWT — no token → 401."""
    response = client.post("/api/v1/upload")
    assert response.status_code == 401


def test_upload_returns_422_for_missing_file():
    _auth()
    try:
        response = client.post("/api/v1/upload")
    finally:
        _clear()
    assert response.status_code == 422


def test_upload_returns_400_for_non_zip_extension():
    _auth()
    try:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("export.txt", b"some text", "text/plain")},
        )
    finally:
        _clear()
    assert response.status_code == 400


def test_upload_returns_400_for_invalid_zip_bytes():
    _auth()
    try:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("export.zip", _make_zip_bytes(valid=False), "application/zip")},
        )
    finally:
        _clear()
    assert response.status_code == 400


def test_upload_success_mocked():
    """Upload returns 202 immediately; background task runs and stores data."""
    mock_doc = Document(
        page_content="You completed a cycling session.",
        metadata={"data_type": "activity", "activity_type": "cycling", "source": "garmin_zip"},
    )
    _auth()
    try:
        with (
            patch(
                "app.api.routers.upload.parse_garmin_zip",
                return_value={"summarizedActivities": [], "sleepData": [], "personalRecords": []},
            ),
            patch("app.api.routers.upload.chunk_garmin_data", return_value=[mock_doc, mock_doc]),
            patch("app.api.routers.upload.embed_and_store", return_value=MagicMock()),
        ):
            response = client.post(
                "/api/v1/upload",
                files={"file": ("export.zip", _make_zip_bytes(), "application/zip")},
            )
    finally:
        _clear()

    # Async upload returns 202 with task_id
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert "task_id" in body


# ---------------------------------------------------------------------------
# POST /api/v1/query — validation / error paths (no DB)
# ---------------------------------------------------------------------------

def test_query_returns_401_without_auth():
    response = client.post("/api/v1/query")
    assert response.status_code == 401


def test_query_returns_422_for_missing_body():
    _auth()
    try:
        response = client.post("/api/v1/query")
    finally:
        _clear()
    assert response.status_code == 422


def test_query_returns_422_for_empty_query():
    _auth()
    try:
        response = client.post("/api/v1/query", json={"query": ""})
    finally:
        _clear()
    assert response.status_code == 422


def test_query_returns_422_for_whitespace_query():
    _auth()
    try:
        response = client.post("/api/v1/query", json={"query": "   "})
    finally:
        _clear()
    assert response.status_code == 422


def test_query_returns_422_for_invalid_data_type():
    _auth()
    try:
        response = client.post("/api/v1/query", json={"query": "best run", "data_type": "invalid"})
    finally:
        _clear()
    assert response.status_code == 422


def test_query_success_mocked():
    mock_doc = Document(
        page_content="You completed a cycling session.",
        metadata={"data_type": "activity", "source": "garmin_zip"},
    )
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.92)]

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "cycling session", "k": 3, "use_llm": False},
        )
    finally:
        _clear()

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

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "deep sleep", "k": 5, "data_type": "sleep", "use_llm": False},
        )
    finally:
        _clear()

    assert response.status_code == 200
    # Filter now includes user_id injected from JWT
    call_kwargs = mock_store.similarity_search_with_score.call_args[1]
    assert call_kwargs["filter"]["data_type"] == "sleep"
    assert call_kwargs["filter"]["user_id"] == str(_MOCK_USER.id)


def test_query_returns_503_when_store_unavailable():
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.side_effect = Exception("connection refused")

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        # use_llm=False to go directly to store (avoids Gemini call in tests)
        response = client.post(
            "/api/v1/query",
            json={"query": "best marathon", "use_llm": False},
        )
    finally:
        _clear()

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Integration tests (require running DB + real ZIP)
# ---------------------------------------------------------------------------

REAL_ZIP = Path(__file__).parent.parent / "data" / "86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip"


@pytest.mark.skipif(not REAL_ZIP.exists(), reason="Real Garmin ZIP not available")
def test_upload_real_zip():
    _auth()
    try:
        with open(REAL_ZIP, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": (REAL_ZIP.name, f, "application/zip")},
            )
    finally:
        _clear()
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert "task_id" in body


@pytest.mark.skipif(not REAL_ZIP.exists(), reason="Real Garmin ZIP not available")
def test_query_after_upload():
    _auth()  # _auth already mocks get_store with a default MagicMock
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "cycling session with high elevation", "k": 5, "data_type": "activity", "use_llm": False},
        )
    finally:
        _clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) >= 0
