"""POST /api/v1/query — semantic search over stored Garmin embeddings."""

from fastapi import APIRouter, Depends, HTTPException
from langchain_postgres.vectorstores import PGVector

from app.api.dependencies import get_store
from app.api.schemas import ChunkResult, QueryRequest, QueryResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query_garmin_data(
    request: QueryRequest,
    store: PGVector = Depends(get_store),
) -> QueryResponse:
    """Run a semantic similarity search and return the top-k matching chunks."""
    filter_dict: dict | None = None
    if request.data_type:
        filter_dict = {"data_type": request.data_type}

    try:
        hits = store.similarity_search_with_score(
            request.query,
            k=request.k,
            filter=filter_dict,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Vector store unavailable: {exc}") from exc

    results = [
        ChunkResult(content=doc.page_content, metadata=doc.metadata, score=float(score))
        for doc, score in hits
    ]

    return QueryResponse(query=request.query, results=results)
