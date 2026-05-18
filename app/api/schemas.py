"""API request/response Pydantic schemas."""

from typing import Any, Optional

from pydantic import BaseModel, field_validator


class UploadResponse(BaseModel):
    status: str
    documents_stored: int
    breakdown: dict[str, int]
    collection: str


class QueryRequest(BaseModel):
    query: str
    k: int = 5
    data_type: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

    @field_validator("data_type")
    @classmethod
    def data_type_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"activity", "sleep", "personal_record"}
        if v not in allowed:
            raise ValueError(f"data_type must be one of {allowed}")
        return v


class ChunkResult(BaseModel):
    content: str
    metadata: dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    query: str
    results: list[ChunkResult]
