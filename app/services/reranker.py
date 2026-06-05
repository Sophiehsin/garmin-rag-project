"""Reranking layer — cross-encoder rescoring of vector search hits (Task 9).

Uses cross-encoder/ms-marco-MiniLM-L-6-v2 (~67 MB).
CPU-bound scoring is offloaded to a thread via asyncio.to_thread so it never
blocks FastAPI's event loop under concurrent requests.
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

_reranker: "CrossEncoder | None" = None


def load_reranker() -> "CrossEncoder":
    """Lazy-load the cross-encoder on first call; return cached instance after."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder as _CE
        _reranker = _CE("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def _sigmoid(x: float) -> float:
    """Map a raw logit to (0.0, 1.0)."""
    return 1.0 / (1.0 + math.exp(-x))


def _rerank_sync(
    query: str,
    hits: list[tuple[Document, float]],
    top_n: int,
) -> list[tuple[Document, float]]:
    """Score each hit with the cross-encoder and return top_n by score.

    Scores are sigmoid-normalized to (0.0, 1.0) so they stay consistent with
    the cosine similarity scores from the initial vector search.
    """
    model = load_reranker()
    pairs = [(query, doc.page_content) for doc, _ in hits]
    raw_scores: list[float] = model.predict(pairs)  # type: ignore[arg-type]
    scored = [
        (doc, _sigmoid(float(raw)))
        for (doc, _), raw in zip(hits, raw_scores)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


async def rerank(
    query: str,
    hits: list[tuple[Document, float]],
    top_n: int = 5,
) -> list[tuple[Document, float]]:
    """Public async API. Wraps _rerank_sync in asyncio.to_thread so CPU work
    does not block the event loop."""
    if not hits:
        return []
    return await asyncio.to_thread(_rerank_sync, query, hits, top_n)
