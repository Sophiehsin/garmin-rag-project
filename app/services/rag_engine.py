"""RAG chain — retrieval from pgvector + generation via Gemini (Tasks 7 + 8).

Enhancements over the original:
  1. LLMConfig params: temperature, max_output_tokens, k, top_n, use_rerank
  2. Self-querying filter (_build_filter): async Gemini pre-pass translates
     colloquial terms to activity_type values and detects multi-type queries
  3. Multi-filter parallel search: asyncio.gather across filter dicts
  4. Reranking: cross-encoder rescoring before context assembly
  5. Chronological sort before context assembly (lost-in-the-middle mitigation)
  6. Token budgeting via character gate + max_output_tokens cap
"""

from __future__ import annotations

import asyncio
import json
import re

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_postgres.vectorstores import PGVector

from app.core.config import settings

MAX_CONTEXT_CHARS = 12_000  # ~3,000 tokens at avg 4 chars/token

SYSTEM_PROMPT = (
    "You are a personal health assistant with access to the user's Garmin fitness data. "
    "Answer the user's question using ONLY the data excerpts provided below. "
    "Be specific, cite numbers and dates when available, and speak directly to "
    'the user ("you", "your"). If the data doesn\'t contain enough information '
    "to answer, say so clearly."
)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Data excerpts:\n{context}\n\nQuestion: {question}"),
])

# Sports vocabulary for the self-querying pre-pass
_SPORTS_VOCAB = (
    "Known activity_type values: running, treadmill_running, cycling, indoor_cycling, "
    "swimming, open_water_swimming, triathlon, strength_training, hiking, mountaineering, other. "
    "Synonyms: bike/biking/ride/riding → cycling; jog/jogging → running; "
    "gym/weights/lift → strength_training; tri → triathlon; swim → swimming; "
    "hike/trail → hiking; climb/summit → mountaineering."
)

_FILTER_SYSTEM_PROMPT = (
    "You are a query router for a fitness RAG system. "
    "Given a user query, output a JSON array of filter dicts. "
    f"{_SPORTS_VOCAB} "
    "Rules: "
    "(1) Always include user_id in every filter dict. "
    "(2) Map colloquial sport terms to their canonical activity_type values. "
    "(3) For fatigue/recovery/sleep questions, include both the activity filter and a sleep filter. "
    "(4) For personal record / PR / best time questions, use data_type: personal_record. "
    "(5) Output ONLY valid JSON, no prose. "
    "Examples: "
    'Query: "my long bike rides" → [{"user_id": "U", "data_type": "activity", "activity_type": "cycling"}] '
    'Query: "why am I tired" → [{"user_id": "U", "data_type": "activity"}, {"user_id": "U", "data_type": "sleep"}] '
    'Query: "my running PR" → [{"user_id": "U", "data_type": "personal_record"}]'
)


# ---------------------------------------------------------------------------
# LLM factory (Task 7)
# ---------------------------------------------------------------------------

def _build_llm(temperature: float = 0.2, max_output_tokens: int = 1024) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _build_context(hits: list[tuple[Document, float]]) -> str:
    context = "\n\n".join(
        f"[Excerpt {i + 1}] (Date: {doc.metadata.get('date')}, "
        f"Type: {doc.metadata.get('data_type')}, "
        f"Sport: {doc.metadata.get('activity_type') or 'N/A'})\n"
        f"Content: {doc.page_content}"
        for i, (doc, _) in enumerate(hits)
    )
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated]"
    return context


# ---------------------------------------------------------------------------
# Self-querying filter (Task 8)
# ---------------------------------------------------------------------------

async def _build_filter(
    query: str,
    user_id: str,
    base_filter: dict | None = None,
) -> list[dict]:
    """Async Gemini pre-pass: translate query → list of pgvector filter dicts.

    Always injects user_id into every returned filter.
    Falls back to a single base_filter (with user_id) on any parse error.
    """
    if base_filter:
        # Caller already specified a filter — just ensure user_id is present
        merged = {**base_filter, "user_id": user_id}
        return [merged]

    llm = _build_llm(temperature=0.0, max_output_tokens=256)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _FILTER_SYSTEM_PROMPT.replace('"U"', f'"{user_id}"')),
        ("human", "{query}"),
    ])
    try:
        response = await (prompt | llm).ainvoke({"query": query})
        raw = response.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
        filters: list[dict] = json.loads(raw)
        # Guarantee user_id in every filter
        for f in filters:
            f["user_id"] = user_id
        return filters if filters else [{"user_id": user_id}]
    except Exception:
        return [{"user_id": user_id}]


# ---------------------------------------------------------------------------
# Main ask function (Tasks 7 + 8)
# ---------------------------------------------------------------------------

async def ask(
    query: str,
    store: PGVector,
    k: int = 15,
    top_n: int = 5,
    filter_dict: dict | None = None,
    use_rerank: bool = True,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
    user_id: str | None = None,
) -> tuple[str, list[tuple[Document, float]]]:
    """Retrieve relevant chunks and generate an answer via Gemini.

    Flow:
      1. _build_filter(query, user_id) → list of filter dicts
      2. similarity_search_with_score() for each filter (parallel)
      3. Merge + deduplicate hits by doc ID
      4. Cross-encoder rerank if use_rerank=True
      5. Chronological sort → context assembly
      6. LLM generation

    Returns:
        (answer, hits) — answer string and the final ranked hits list.
    """
    # Build filters
    if user_id:
        filter_dicts = await _build_filter(query, user_id, filter_dict)
    else:
        filter_dicts = [filter_dict] if filter_dict else [None]

    # Parallel vector searches
    async def _search(f: dict | None) -> list[tuple[Document, float]]:
        return await asyncio.to_thread(
            store.similarity_search_with_score, query, k=k, filter=f
        )

    search_results = await asyncio.gather(*[_search(f) for f in filter_dicts])

    # Merge and deduplicate by page_content hash
    seen: set[str] = set()
    merged: list[tuple[Document, float]] = []
    for batch in search_results:
        for doc, score in batch:
            key = doc.page_content[:120]
            if key not in seen:
                seen.add(key)
                merged.append((doc, score))

    # Rerank
    if use_rerank and merged:
        from app.services.reranker import rerank
        hits = await rerank(query, merged, top_n=top_n)
    else:
        hits = sorted(merged, key=lambda x: x[1], reverse=True)[:top_n]

    # Sort chronologically for context assembly
    hits.sort(key=lambda x: x[0].metadata.get("date") or "")

    context = _build_context(hits)
    llm = _build_llm(temperature=temperature, max_output_tokens=max_output_tokens)
    response = await (_PROMPT | llm).ainvoke({"context": context, "question": query})
    return response.content, hits
