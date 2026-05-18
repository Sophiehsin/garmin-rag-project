"""POST /api/v1/upload — accepts a Garmin ZIP and runs the full ingest pipeline."""

import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.api.schemas import UploadResponse
from app.core.config import settings
from app.services.chunker import chunk_garmin_data
from app.services.embedder import embed_and_store
from app.services.parser import parse_garmin_zip

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_garmin_zip(file: UploadFile) -> UploadResponse:
    """Accept a Garmin export ZIP, parse it, embed the data, and store in pgvector."""
    if file.filename and not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        if not zipfile.is_zipfile(tmp_path):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive")

        try:
            parsed = parse_garmin_zip(tmp_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse ZIP: {exc}") from exc

        docs = chunk_garmin_data(parsed)

        try:
            embed_and_store(docs)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to store embeddings: {exc}") from exc

        breakdown: dict[str, int] = {}
        for doc in docs:
            dt = doc.metadata.get("data_type", "unknown")
            breakdown[dt] = breakdown.get(dt, 0) + 1

        return UploadResponse(
            status="ok",
            documents_stored=len(docs),
            breakdown=breakdown,
            collection=settings.vector_collection,
        )

    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
