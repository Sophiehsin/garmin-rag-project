"""POST /api/v1/upload — async Garmin ZIP ingest with background processing (Task 5)."""

from __future__ import annotations

import shutil
import tempfile
import uuid
import zipfile
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from langchain_core.documents import Document

from app.api.schemas import (
    SportInfo,
    UploadAcceptedResponse,
    UploadStatusResponse,
)
from app.core.config import settings
from app.core.security import get_current_user
from app.models.sql_models import User
from app.services.chunker import chunk_garmin_data
from app.services.embedder import embed_and_store
from app.services.parser import parse_garmin_zip

router = APIRouter()

# In-memory task store — replace with Redis/DB for multi-process deployments
_task_store: dict[str, dict] = {}


@router.post("/upload", response_model=UploadAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_garmin_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadAcceptedResponse:
    """Stream ZIP to disk and dispatch parse+embed as a background task.

    Returns immediately with a task_id — poll /upload/status/{task_id} for results.
    """
    if file.filename and not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    task_id = str(uuid.uuid4())
    _task_store[task_id] = {"status": "processing"}

    # Stream to disk — avoids loading potentially large ZIP into RAM
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    if not zipfile.is_zipfile(tmp_path):
        Path(tmp_path).unlink(missing_ok=True)
        _task_store[task_id] = {"status": "failed", "error": "Not a valid ZIP archive"}
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive")

    background_tasks.add_task(
        _parse_and_embed, tmp_path, str(current_user.id), task_id
    )
    return UploadAcceptedResponse(status="processing", task_id=task_id)


async def _parse_and_embed(tmp_path: str, user_id: str, task_id: str) -> None:
    """Background task: parse ZIP → chunk → embed → update task_store → clean up."""
    try:
        parsed = parse_garmin_zip(tmp_path)
        docs = chunk_garmin_data(parsed, user_id)
        embed_and_store(docs)

        sports = _build_sport_summary(docs)
        sleep_count = sum(
            1 for d in docs if d.metadata.get("data_type") == "sleep"
        )
        _task_store[task_id] = {
            "status": "completed",
            "sports_found": sports,
            "sleep_records": sleep_count,
        }
    except Exception as exc:
        _task_store[task_id] = {"status": "failed", "error": str(exc)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _build_sport_summary(documents: list[Document]) -> dict[str, SportInfo]:
    """Count activity records per sport and set analysis_ready = count >= 10."""
    counts: Counter = Counter()
    for doc in documents:
        if doc.metadata.get("data_type") == "activity":
            sport = doc.metadata.get("activity_type") or "other"
            counts[sport] += 1

    result: dict[str, SportInfo] = {}
    for sport, count in counts.items():
        analysis_ready = count >= 10
        warning = f"Only {count} sessions — trends may be unreliable" if not analysis_ready else None
        result[sport] = SportInfo(count=count, analysis_ready=analysis_ready, warning=warning)
    return result


@router.get("/upload/status/{task_id}", response_model=UploadStatusResponse)
async def upload_status(task_id: str) -> UploadStatusResponse:
    """Return current processing status for a previously submitted upload."""
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return UploadStatusResponse(**task)
