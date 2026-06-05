"""RAG evaluation utilities — Hit Rate@K, MRR, and Gemini-based faithfulness (Task 6).

Usage:
    from app.services.evaluator import evaluate_retrieval, evaluate_faithfulness
"""

from __future__ import annotations

import asyncio
from typing import Optional

from langchain_postgres.vectorstores import PGVector


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------

def compute_hit_rate(results: list[dict]) -> float:
    """Fraction of queries where at least one expected doc was found in top-K."""
    if not results:
        return 0.0
    hits = sum(1 for r in results if r.get("hit"))
    return hits / len(results)


def compute_mrr(results: list[dict]) -> float:
    """Mean Reciprocal Rank — mean(1 / rank_of_first_correct_doc)."""
    if not results:
        return 0.0
    total = 0.0
    for r in results:
        rank = r.get("first_hit_rank")
        if rank is not None:
            total += 1.0 / rank
    return total / len(results)


def evaluate_retrieval(
    store: PGVector,
    dataset: list[dict],
    k: int = 5,
    filter_dict: Optional[dict] = None,
) -> dict:
    """Compute Hit Rate@K and MRR over a golden dataset.

    Each dataset entry must have:
        "query": str
        "expected_doc_ids": list[str]  — SHA-256 IDs of relevant documents

    Returns:
        {"hit_rate": float, "mrr": float, "total": int, "hits": int}
    """
    per_query: list[dict] = []

    for entry in dataset:
        query = entry["query"]
        expected_ids: set[str] = set(entry.get("expected_doc_ids", []))

        hits = store.similarity_search_with_score(query, k=k, filter=filter_dict)
        retrieved_ids = [doc.metadata.get("record_id") for doc, _ in hits]

        hit = False
        first_hit_rank: Optional[int] = None
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid and str(rid) in expected_ids:
                hit = True
                first_hit_rank = rank
                break

        per_query.append({"hit": hit, "first_hit_rank": first_hit_rank})

    return {
        "hit_rate": compute_hit_rate(per_query),
        "mrr": compute_mrr(per_query),
        "total": len(per_query),
        "hits": sum(1 for r in per_query if r["hit"]),
    }


# ---------------------------------------------------------------------------
# Faithfulness (Gemini-based RAGAS-style judge)
# ---------------------------------------------------------------------------

async def evaluate_faithfulness(
    rag_results: list[dict],
    batch_size: int = 5,
    throttle_seconds: float = 1.5,
) -> dict:
    """Score faithfulness and answer relevance using Gemini as judge.

    Each rag_result must have:
        "question": str
        "answer":   str
        "contexts": list[str]

    Throttles between batches to respect Gemini rate limits.
    Returns:
        {"faithfulness": float, "answer_relevance": float}
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    from app.core.config import settings

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
        max_output_tokens=64,
    )

    faithfulness_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a faithfulness evaluator. Given a question, context passages, and an answer, "
            "rate whether the answer is fully supported by the context. "
            "Output a JSON object with a single key 'score' between 0.0 and 1.0. "
            "1.0 = fully supported, 0.0 = not supported at all.",
        ),
        (
            "human",
            "Question: {question}\nContexts:\n{contexts}\nAnswer: {answer}",
        ),
    ])

    relevance_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a relevance evaluator. Given a question and an answer, rate how well "
            "the answer addresses the question. "
            "Output a JSON object with a single key 'score' between 0.0 and 1.0.",
        ),
        ("human", "Question: {question}\nAnswer: {answer}"),
    ])

    import json as _json
    import re as _re

    def _parse_score(text: str) -> float:
        text = _re.sub(r"^```(?:json)?", "", text.strip()).rstrip("`").strip()
        try:
            return float(_json.loads(text).get("score", 0.5))
        except Exception:
            try:
                m = _re.search(r"[0-9]+(?:\.[0-9]+)?", text)
                return float(m.group()) if m else 0.5
            except Exception:
                return 0.5

    faithfulness_scores: list[float] = []
    relevance_scores: list[float] = []

    for i in range(0, len(rag_results), batch_size):
        batch = rag_results[i: i + batch_size]
        for item in batch:
            ctx_text = "\n\n".join(item.get("contexts", []))
            try:
                f_resp = await (faithfulness_prompt | llm).ainvoke({
                    "question": item["question"],
                    "contexts": ctx_text,
                    "answer": item["answer"],
                })
                faithfulness_scores.append(_parse_score(f_resp.content))

                r_resp = await (relevance_prompt | llm).ainvoke({
                    "question": item["question"],
                    "answer": item["answer"],
                })
                relevance_scores.append(_parse_score(r_resp.content))
            except Exception:
                faithfulness_scores.append(0.5)
                relevance_scores.append(0.5)

        if i + batch_size < len(rag_results):
            await asyncio.sleep(throttle_seconds)

    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    return {
        "faithfulness": _mean(faithfulness_scores),
        "answer_relevance": _mean(relevance_scores),
    }
