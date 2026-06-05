"""Hybrid RAG — routes aggregation/trend queries to SQL; semantic queries to vector (Task 10).

Route logic (via Gemini):
  "aggregation" → LangChain SQLDatabaseChain on read-only engine
  "trend"       → direct parameterised SQL on personal_records
  "semantic"    → vector search + rerank (default)

The read-only engine uses settings.readonly_db_url if set; otherwise falls back
to the main connection string. In production, point this at a PostgreSQL role
granted SELECT-only to prevent any chance of mutation via SQL injection.
"""

from __future__ import annotations

import asyncio
import json
import re

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_postgres.vectorstores import PGVector
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.api.schemas import LLMConfig
from app.core.config import settings
from app.core.database import get_connection_string

_readonly_engine: Engine | None = None

_ROUTE_SYSTEM_PROMPT = (
    "You are a query classifier. Classify the user's fitness question into exactly one of: "
    '"aggregation" (needs totals/counts/averages across many records), '
    '"trend" (compares personal records over time to show improvement), '
    '"semantic" (needs specific session narratives or health context). '
    "Output ONLY the single word: aggregation, trend, or semantic."
)

_SQL_SYSTEM_PROMPT = (
    "You are a PostgreSQL expert. Generate a single SELECT query for the fitness database. "
    "Available tables: summarized_activities(user_id, activity_type, distance, duration, calories, start_time_in_seconds), "
    "sleep_data(user_id, calendar_date, deep_sleep_seconds, light_sleep_seconds, rem_sleep_seconds, awake_sleep_seconds, overall_sleep_score), "
    "personal_records(user_id, personal_record_type, value, record_unit, record_date). "
    "ALWAYS include WHERE user_id = :uid. Output ONLY the SQL query, no prose."
)


def get_readonly_engine() -> Engine:
    """Return a SQLAlchemy engine for read-only queries.

    Uses settings.readonly_db_url if configured; falls back to the main DB URL.
    In production set readonly_db_url to a Postgres role with GRANT SELECT only.
    """
    global _readonly_engine
    if _readonly_engine is None:
        url = settings.readonly_db_url or get_connection_string()
        _readonly_engine = create_engine(url)
    return _readonly_engine


def _make_llm(temperature: float = 0.0, max_tokens: int = 512) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )


async def route_query(query: str) -> str:
    """Classify query intent: 'aggregation' | 'trend' | 'semantic'."""
    llm = _make_llm(temperature=0.0, max_tokens=10)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _ROUTE_SYSTEM_PROMPT),
        ("human", "{query}"),
    ])
    try:
        resp = await (prompt | llm).ainvoke({"query": query})
        route = resp.content.strip().lower()
        if route in ("aggregation", "trend", "semantic"):
            return route
    except Exception:
        pass
    return "semantic"


async def sql_aggregation(query: str, user_id: str) -> str:
    """Generate and run a SELECT query; return prose answer from Gemini."""
    sql_llm = _make_llm(temperature=0.0, max_tokens=256)
    sql_prompt = ChatPromptTemplate.from_messages([
        ("system", _SQL_SYSTEM_PROMPT),
        ("human", "user_id value: {uid}\nQuestion: {query}"),
    ])
    try:
        sql_resp = await (sql_prompt | sql_llm).ainvoke({"uid": user_id, "query": query})
        raw_sql = sql_resp.content.strip()
        raw_sql = re.sub(r"^```(?:sql)?", "", raw_sql).rstrip("`").strip()

        # Safety: reject any non-SELECT statement
        if not raw_sql.upper().startswith("SELECT"):
            return "Could not generate a safe query for this question."

        def _run_query() -> list[dict]:
            engine = get_readonly_engine()
            with engine.connect() as conn:
                result = conn.execute(text(raw_sql), {"uid": user_id})
                cols = list(result.keys())
                return [dict(zip(cols, row)) for row in result.fetchall()]

        rows = await asyncio.to_thread(_run_query)

        # Ask Gemini to summarise the results
        summary_llm = _make_llm(temperature=0.2, max_tokens=512)
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarise the following SQL result data in plain English for the user. Be concise."),
            ("human", "Question: {query}\nData: {data}"),
        ])
        summary = await (summary_prompt | summary_llm).ainvoke({
            "query": query,
            "data": json.dumps(rows[:50]),  # cap at 50 rows
        })
        return summary.content
    except Exception as exc:
        return f"Aggregation query failed: {exc}"


async def sql_trend(record_type: str, user_id: str) -> list[dict]:
    """Fetch personal record time-series for a given record_type, oldest first."""
    def _fetch() -> list[dict]:
        engine = get_readonly_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT personal_record_type, value, record_unit, record_date "
                    "FROM personal_records "
                    "WHERE user_id = :uid AND personal_record_type = :rt "
                    "ORDER BY record_date ASC"
                ),
                {"uid": user_id, "rt": record_type},
            )
            cols = list(result.keys())
            return [dict(zip(cols, row)) for row in result.fetchall()]

    return await asyncio.to_thread(_fetch)


async def hybrid_ask(
    query: str,
    store: PGVector,
    user_id: str,
    llm_config: LLMConfig | None = None,
) -> str:
    """Top-level dispatcher used by the query endpoint.

    Routes to sql_aggregation, sql_trend, or rag_engine.ask based on query intent.
    """
    from app.services import rag_engine

    cfg = llm_config or LLMConfig()
    route = await route_query(query)

    if route == "aggregation":
        return await sql_aggregation(query, user_id)

    if route == "trend":
        # Extract record type from query via Gemini, fall back to semantic if unclear
        type_llm = _make_llm(temperature=0.0, max_tokens=20)
        type_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract the personal record type from the query as a short string "
                       "(e.g. 'fastest_5k', 'longest_run'). Output ONLY the type string."),
            ("human", "{query}"),
        ])
        try:
            type_resp = await (type_prompt | type_llm).ainvoke({"query": query})
            record_type = type_resp.content.strip()
            rows = await sql_trend(record_type, user_id)
            if rows:
                summary_llm = _make_llm(temperature=cfg.temperature, max_tokens=cfg.max_output_tokens)
                summary_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a personal fitness coach. Explain the trend in the "
                               "user's personal records over time. Speak directly to the user."),
                    ("human", "Question: {query}\nRecords (oldest first): {data}"),
                ])
                resp = await (summary_prompt | summary_llm).ainvoke({
                    "query": query,
                    "data": json.dumps(rows),
                })
                return resp.content
        except Exception:
            pass
        # Fall through to semantic if trend extraction failed

    answer, _ = await rag_engine.ask(
        query=query,
        store=store,
        k=cfg.k,
        top_n=cfg.top_n,
        use_rerank=cfg.use_rerank,
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
        user_id=user_id,
    )
    return answer
