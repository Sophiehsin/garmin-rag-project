"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.query import router as query_router
from app.api.routers.upload import router as upload_router
from app.services.embedder import get_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embeddings()  # pre-load model so first request isn't slow
    yield


app = FastAPI(
    title="Garmin Insight RAG",
    description="RAG system for Garmin fitness data — upload a ZIP, ask health questions.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
