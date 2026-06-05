"""API request/response Pydantic schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Upload schemas (Tasks 5)
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Synchronous upload response (legacy / direct mode)."""
    status: str
    documents_stored: int
    breakdown: dict[str, int]
    collection: str


class UploadAcceptedResponse(BaseModel):
    """Immediate response when upload is accepted for background processing."""
    status: str       # always "processing"
    task_id: str


class SportInfo(BaseModel):
    count: int
    analysis_ready: bool
    warning: Optional[str] = None


class UploadStatusResponse(BaseModel):
    status: str                                     # "processing" | "completed" | "failed"
    sports_found: Optional[dict[str, SportInfo]] = None
    sleep_records: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# LLM config (Task 7)
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=64, le=8192)
    k: int = Field(default=15, ge=1, le=30)
    top_n: int = Field(default=5, ge=1, le=15)
    use_rerank: bool = True


# ---------------------------------------------------------------------------
# Query schemas (Tasks 7)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    k: int = 5
    data_type: Optional[str] = None
    use_llm: bool = True
    llm_config: Optional[LLMConfig] = None

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
    answer: Optional[str] = None
