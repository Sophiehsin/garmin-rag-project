"""POST /api/v1/query — semantic search + optional Claude LLM answer."""

from fastapi import APIRouter, Depends, HTTPException
from langchain_postgres.vectorstores import PGVector

from app.api.dependencies import get_store
from app.api.schemas import ChunkResult, QueryRequest, QueryResponse
from app.services import rag_engine

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_garmin_data(
    request: QueryRequest,
    store: PGVector = Depends(get_store),
) -> QueryResponse:
    """Semantic search over stored Garmin embeddings, with optional LLM answer."""
    filter_dict: dict | None = None
    if request.data_type:
        filter_dict = {"data_type": request.data_type}

    if request.use_llm:
        try:
            answer, hits = await rag_engine.ask(
                request.query, store, request.k, filter_dict
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"RAG chain failed: {exc}") from exc
    else:
        try:
            hits = store.similarity_search_with_score(
                request.query, k=request.k, filter=filter_dict
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail=f"Vector store unavailable: {exc}"
            ) from exc
        answer = None

    results = [
        ChunkResult(content=doc.page_content, metadata=doc.metadata, score=float(score))
        for doc, score in hits
    ]
    return QueryResponse(query=request.query, results=results, answer=answer)
