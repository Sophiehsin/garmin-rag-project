"""POST /api/v1/query — hybrid semantic/SQL search with JWT auth (Tasks 4, 10)."""

from fastapi import APIRouter, Depends, HTTPException
from langchain_postgres.vectorstores import PGVector

from app.api.dependencies import get_store
from app.api.schemas import ChunkResult, LLMConfig, QueryRequest, QueryResponse
from app.core.security import get_current_user
from app.models.sql_models import User
from app.services import sql_retriever

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_garmin_data(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    store: PGVector = Depends(get_store),
) -> QueryResponse:
    """Hybrid semantic/SQL search over the authenticated user's Garmin data.

    user_id from the JWT is hard-injected into every filter — the vector store
    physically cannot return another user's records.
    """
    user_id = str(current_user.id)
    llm_config = request.llm_config or LLMConfig(k=request.k)

    # Honour explicit data_type filter from the request
    base_filter: dict | None = None
    if request.data_type:
        base_filter = {"data_type": request.data_type}

    if request.use_llm:
        try:
            from app.services.rag_engine import ask

            answer, hits = await ask(
                query=request.query,
                store=store,
                k=llm_config.k,
                top_n=llm_config.top_n,
                filter_dict=base_filter,
                use_rerank=llm_config.use_rerank,
                temperature=llm_config.temperature,
                max_output_tokens=llm_config.max_output_tokens,
                user_id=user_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"RAG chain failed: {exc}") from exc
    else:
        try:
            filter_dict = {**(base_filter or {}), "user_id": user_id}
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
