"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.api.routers.query import router as query_router
from app.api.routers.upload import router as upload_router
from app.core.database import get_db
from app.core.security import google_oauth_callback, google_oauth_login
from app.services.embedder import get_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embeddings()  # pre-load embedding model so first request isn't slow
    yield


app = FastAPI(
    title="Garmin Insight RAG",
    description="RAG system for Garmin fitness data — upload a ZIP, ask health questions.",
    version="0.2.0",
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


# Google OAuth routes (Task 4)
@app.get("/auth/google")
async def auth_google():
    return await google_oauth_login()


@app.get("/auth/callback")
async def auth_callback(code: str = Query(...), db: Session = Depends(get_db)):
    return await google_oauth_callback(code=code, db=db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
