"""RAG chain — retrieval from pgvector + generation via Claude.

Production-grade enhancements:
  1. Metadata-enriched context: each excerpt includes Date and Type tags so
     Claude can distinguish a 2018 session from a 2026 one without guessing.
  2. Chronological sorting: chunks are sorted by date before context assembly
     (lost-in-the-middle mitigation — most recent data at the end of the prompt).
  3. Async invocation: ainvoke() keeps the FastAPI thread pool unblocked during
     the 2-5s Anthropic network round-trip.
  4. Token budgeting: character-length gate + explicit max_tokens + timeout
     prevent runaway billing and stalled requests.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
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


def _build_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.llm_model,
        api_key=settings.anthropic_api_key,
        max_tokens=1024,
        timeout=30.0,
    )


def _build_context(hits: list[tuple[Document, float]]) -> str:
    context = "\n\n".join(
        f"[Excerpt {i + 1}] (Date: {doc.metadata.get('date')}, Type: {doc.metadata.get('data_type')})\n"
        f"Content: {doc.page_content}"
        for i, (doc, _) in enumerate(hits)
    )
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated]"
    return context


async def ask(
    query: str,
    store: PGVector,
    k: int = 5,
    filter_dict: dict | None = None,
) -> tuple[str, list[tuple[Document, float]]]:
    """Retrieve top-k chunks from pgvector and generate an answer via Claude.

    Returns:
        (answer, hits) — the LLM-generated answer string and the raw retrieved
        chunks (passed back so the API can include them in the response).
    """
    hits: list[tuple[Document, float]] = store.similarity_search_with_score(
        query, k=k, filter=filter_dict
    )

    # Sort chronologically so Claude reads data oldest-to-newest; most recent
    # data sits at the end of the prompt (strongest LLM recall position).
    hits.sort(key=lambda x: x[0].metadata.get("date") or "")

    context = _build_context(hits)

    response = await (_PROMPT | _build_llm()).ainvoke(
        {"context": context, "question": query}
    )
    return response.content, hits
