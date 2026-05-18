# PLAN.md — Garmin RAG Project: Remaining Tasks

## Task 7: Chunking ✅ DONE

Convert parsed Garmin JSON into LangChain `Document` objects for embedding and retrieval.

**New file:** `app/services/chunker.py`

Each record → one `Document` with:
- `page_content`: natural-language prose sentences (not pipe-delimited metrics)
- `metadata`: structured dict for retrieval filtering

Key implementation decisions:
- Running activities → pace in `min/km` (e.g. `4:15/km`), not `km/h`
- All other activities → speed in `km/h`
- Sleep: guard against `total_sleep_seconds == 0 or None` (ZeroDivisionError)
- Personal records: include `is_current_pr: bool` in metadata to filter out stale PRs

Main entry point: `chunk_garmin_data(parsed: dict) -> list[Document]`
- input: output of `parse_garmin_zip()`
- output: combined list of Documents for all 3 data types

Tests: `tests/test_chunker.py` (10 tests covering all edge cases)

---

## Task 8: Embeddings + PGVector Storage ✅ DONE

**New file:** `app/services/embedder.py`

- Generate embeddings for each `Document.page_content`
- Embedding model: TBD — `sentence-transformers` (local) or Anthropic API
- Store to pgvector via LangChain `PGVector` integration
- Enable `langchain`, `langchain-community`, `pgvector` in `requirements.txt`
- Wire up `app/core/database.py` (currently stub) for connection string

---

## Task 9: FastAPI Endpoints ✅ DONE

**Files:** `app/api/routers/upload.py`, `app/api/routers/query.py`, `app/main.py`, `app/api/schemas.py`, `app/api/dependencies.py`

- `POST /api/v1/upload` — accepts ZIP, runs: parse → chunk → embed → store; returns `{status, documents_stored, breakdown, collection}`
- `POST /api/v1/query` — query text → pgvector similarity search → ranked `ChunkResult` list; supports `data_type` filter
- `GET /health` — liveness check
- `lifespan` pre-loads embedding model on startup so first request isn't slow
- Uses `app.dependency_overrides` pattern for testable DI
- Tests: 14 tests in `tests/test_api.py` (mocked + real-ZIP integration)

---

## Task 10: RAG Chain

**File:** `app/services/rag_engine.py` (currently stub)

- LangChain retrieval chain: PGVector similarity search → Claude LLM
- Metadata filters: date range, activity type, data_type, `is_current_pr`
- Prompt template framing retrieved chunks as health context for Claude
