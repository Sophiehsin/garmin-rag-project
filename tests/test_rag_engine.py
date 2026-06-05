"""Tests for app/services/rag_engine.py"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.api.dependencies import get_store
from app.core.security import get_current_user
from app.main import app
from app.models.sql_models import User
from app.services.rag_engine import MAX_CONTEXT_CHARS, _build_context, ask

client = TestClient(app)

_MOCK_USER = User(id=1, email="test@example.com")
_MOCK_STORE_DEFAULT = MagicMock()
_MOCK_STORE_DEFAULT.similarity_search_with_score.return_value = []


def _auth():
    """Override auth + store so tests never hit a real DB."""
    app.dependency_overrides[get_current_user] = lambda: _MOCK_USER
    app.dependency_overrides[get_store] = lambda: _MOCK_STORE_DEFAULT


def _clear():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(content: str, date: str = "2024-01-01", data_type: str = "activity") -> Document:
    return Document(
        page_content=content,
        metadata={"data_type": data_type, "date": date, "source": "garmin_zip"},
    )


def _make_store(hits: list) -> MagicMock:
    store = MagicMock()
    store.similarity_search_with_score.return_value = hits
    return store


# ---------------------------------------------------------------------------
# _build_context unit tests (synchronous, no mock needed)
# ---------------------------------------------------------------------------

def test_build_context_injects_metadata():
    doc = _make_doc("You ran 5 km.", date="2024-03-15", data_type="activity")
    context = _build_context([(doc, 0.9)])
    assert "Date: 2024-03-15" in context
    assert "Type: activity" in context
    assert "You ran 5 km." in context


def test_build_context_truncates_long_input():
    big_content = "x" * (MAX_CONTEXT_CHARS + 500)
    doc = _make_doc(big_content)
    context = _build_context([(doc, 0.9)])
    assert "[Context truncated]" in context
    assert len(context) <= MAX_CONTEXT_CHARS + len("\n\n[Context truncated]")


def test_build_context_multiple_excerpts_numbered():
    docs = [(_make_doc(f"Content {i}"), 0.9) for i in range(3)]
    context = _build_context(docs)
    assert "[Excerpt 1]" in context
    assert "[Excerpt 2]" in context
    assert "[Excerpt 3]" in context


# ---------------------------------------------------------------------------
# ask() async unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ask_returns_answer_and_hits():
    doc = _make_doc("You cycled 20 km.")
    store = _make_store([(doc, 0.95)])

    mock_response = MagicMock()
    mock_response.content = "Your best cycling session was 20 km."

    with patch("app.services.rag_engine._build_llm") as mock_llm_factory:
        chain_mock = AsyncMock()
        chain_mock.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        with patch("app.services.rag_engine._PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=chain_mock)
            # use_rerank=False avoids loading the cross-encoder in unit tests
            answer, hits = await ask("best cycling", store, k=3, use_rerank=False)

    assert isinstance(answer, str)
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_ask_sorts_hits_chronologically():
    docs = [
        (_make_doc("Recent session", date="2024-06-01"), 0.9),
        (_make_doc("Oldest session", date="2022-01-15"), 0.85),
        (_make_doc("Middle session", date="2023-03-10"), 0.88),
    ]
    store = _make_store(docs)

    captured_context: list[str] = []

    async def fake_ainvoke(inputs: dict):
        captured_context.append(inputs["context"])
        resp = MagicMock()
        resp.content = "answer"
        return resp

    with patch("app.services.rag_engine._build_llm") as mock_llm_factory:
        chain_mock = MagicMock()
        chain_mock.ainvoke = fake_ainvoke
        mock_llm = MagicMock()
        mock_llm_factory.return_value = mock_llm

        with patch("app.services.rag_engine._PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=chain_mock)
            await ask("any query", store, use_rerank=False)

    ctx = captured_context[0]
    oldest_pos = ctx.find("2022-01-15")
    middle_pos = ctx.find("2023-03-10")
    recent_pos = ctx.find("2024-06-01")
    assert oldest_pos < middle_pos < recent_pos


@pytest.mark.asyncio
async def test_ask_passes_filter_to_store():
    store = _make_store([])
    with patch("app.services.rag_engine._build_llm") as mock_llm_factory:
        chain_mock = MagicMock()
        resp = MagicMock()
        resp.content = "no data"
        chain_mock.ainvoke = AsyncMock(return_value=resp)
        mock_llm_factory.return_value = MagicMock()

        with patch("app.services.rag_engine._PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=chain_mock)
            # user_id=None so _build_filter is skipped; filter_dict passed directly
            await ask("sleep quality", store, k=5, filter_dict={"data_type": "sleep"}, use_rerank=False)

    store.similarity_search_with_score.assert_called_once_with(
        "sleep quality", k=5, filter={"data_type": "sleep"}
    )


# ---------------------------------------------------------------------------
# Query endpoint tests (use FastAPI TestClient + dependency overrides)
# ---------------------------------------------------------------------------

def test_query_endpoint_with_llm_mocked():
    doc = _make_doc("You cycled 20 km.")
    mock_store = MagicMock()

    async def fake_ask(**kwargs):
        return "Great cycling session!", [(doc, 0.95)]

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        # Patch the canonical location; query.py does a local import of ask
        with patch("app.services.rag_engine.ask", side_effect=fake_ask):
            response = client.post(
                "/api/v1/query",
                json={"query": "cycling performance", "k": 3, "use_llm": True},
            )
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Great cycling session!"
    assert len(body["results"]) == 1


def test_query_endpoint_use_llm_false():
    doc = _make_doc("You slept 7 hours.", data_type="sleep")
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = [(doc, 0.88)]

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "sleep last week", "use_llm": False},
        )
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None
    assert len(body["results"]) == 1


def test_query_endpoint_llm_503_on_failure():
    mock_store = MagicMock()

    async def failing_ask(**kwargs):
        raise RuntimeError("Gemini timeout")

    _auth()
    app.dependency_overrides[get_store] = lambda: mock_store
    try:
        with patch("app.services.rag_engine.ask", side_effect=failing_ask):
            response = client.post(
                "/api/v1/query",
                json={"query": "best run", "use_llm": True},
            )
    finally:
        _clear()

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Integration test (requires running DB + GOOGLE_API_KEY in .env)
# ---------------------------------------------------------------------------

REAL_ZIP = Path(__file__).parent.parent / "data" / "86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip"


@pytest.mark.skipif(
    not REAL_ZIP.exists() or not os.getenv("GOOGLE_API_KEY"),
    reason="Real Garmin ZIP or GOOGLE_API_KEY not available",
)
def test_rag_end_to_end():
    _auth()
    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "What was my best cycling session?", "k": 5, "use_llm": True},
        )
    finally:
        _clear()
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is not None
    assert len(body["answer"]) > 20
    assert len(body["results"]) > 0
