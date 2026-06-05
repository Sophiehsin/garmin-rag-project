# Garmin Insight RAG — Full Implementation Plan

## Platform Vision

Multi-user AWS-deployed platform. Each user uploads their Garmin ZIP → system parses
supported sports → user queries their own data in natural language. Data is physically
isolated per user at every layer (vector store, SQL, API).

Example queries the system must handle:
- "近一個月跑步訓練最多是哪種類型？最近覺得累可能是因為什麼？"
  → fetches running sessions + sleep quality → LLM synthesizes explanation
- "我這兩年三鐵成績有沒有進步？"
  → personal_records time-series by type → LLM explains trend
- "我跑步成績這幾年有進步嗎？"
  → personal_records + running activity history

---

## Real Data Profile (sample export)

| Sport | Count | Analysis-ready |
|---|---|---|
| cycling | 484 | yes |
| running | 313 | yes |
| treadmill_running | 2 | too few |
| hiking | 1 | too few |
| other (GENERIC) | 62 | unclassified |
| swimming / triathlon / strength | 0 | platform-only |

Pre-condition for Task 3: manually inspect full Garmin ZIP to verify activity types
before implementing sport-specific formatters.

---

## Priority Order

| # | Task | Complexity | Why this order |
|---|---|---|---|
| 1 | Force user_id + activity_type into metadata | Low | Every later task depends on this |
| 2 | Dedup hash fix (include user_id) | Low | Fix before more data enters |
| 3 | 7-sport prose templates (pending data check) | Low-Med | Better text = better search |
| 4 | JWT auth + privacy filter | Med | Enables multi-user; must precede eval |
| 5 | Async upload + post-upload sport summary | Med | UX foundation; surfaces data sufficiency |
| 6 | Evaluation baseline + golden dataset | Med | Must exist before tuning |
| 7 | Parameter exposure (LLMConfig) | Low | Quick win; measure with eval |
| 8 | Self-querying (multi-type + sports vocab) | Med-High | Needs 1, 4, 6 |
| 9 | Reranking layer (cross-encoder) | Med-High | Needs 6 to prove improvement |
| 10 | Hybrid RAG + secure SQL + trend queries | High | Aggregations + time-series |
| 11 | Frontend skeleton loading | Low | Latency compensation for 8+9 |
| 12 | AWS deployment | Med | Pre-deploy |
| 13 | Frontend auth flow (Google OAuth login) | Low-Med | Required for real use — without this users must paste tokens manually |

---

## Task 1 — Force user_id + activity_type into every chunk metadata

**File:** `app/services/chunker.py`

```python
def chunk_garmin_data(parsed: dict, user_id: str) -> list[Document]:
    """
    Main entry point. user_id now required — injected into every chunk's metadata.
    input:  parsed dict from parse_garmin_zip(), plus the authenticated user's ID
    output: combined list of Documents for all 3 data types
    """

def build_metadata(data_type: str, record: dict, user_id: str) -> dict:
    """
    Returns metadata dict always containing:
      user_id, data_type, activity_type, source, record_id, date, is_current_pr
    user_id and activity_type are now mandatory.
    """
    return {
        "user_id":       user_id,
        "data_type":     data_type,
        "activity_type": _get_activity_type(record, data_type),
        "source":        "garmin_zip",
        "record_id":     _get_record_id(record, data_type),
        "date":          _get_date(record, data_type),
        "is_current_pr": _get_is_current_pr(record, data_type),
    }

def _get_activity_type(record: dict, data_type: str) -> str | None:
    """Returns lowercase activity_type for activities; None for sleep/records."""
```

Callers to update: `app/api/routers/upload.py` — pass `current_user.user_id` into
`chunk_garmin_data()`.

---

## Task 2 — Dedup hash fix (user_id in ID key)

**File:** `app/services/embedder.py`

```python
def _make_doc_id(doc: Document) -> str:
    """
    Deterministic SHA-256 ID. Updated key includes user_id to prevent
    cross-user collisions on the same activity_id.

    Key format: "{user_id}:{data_type}:{record_id}"
    Fallback:   sha256(page_content) for records missing metadata
    Returns:    64-char hex string
    """
```

No signature change on public API (`embed_and_store`, `get_vector_store`).

---

## Task 3 — 7-sport prose templates (pending manual data check)

**File:** `app/services/chunker.py`

```python
def format_activity_as_text(activity: dict) -> str:
    """
    Dispatcher: selects the right formatter based on activity_type.
    Falls back to _format_generic for unknown types.
    """
    formatter = SPORT_FORMATTERS.get(
        activity.get("activity_type", "").lower(),
        _format_generic
    )
    return formatter(activity)

def _format_running(activity: dict) -> str:
    """
    Fields: date, name, distance_km, duration_hms, pace_min_km,
            avg_hr (if present), max_hr (if present), cadence (if present),
            calories, elevation_gain (if present).
    Includes pace. All None fields use graceful fallback strings.
    """

def _format_cycling(activity: dict) -> str:
    """
    Fields: date, name, distance_km, duration_hms, avg_speed_kmh, max_speed_kmh,
            elevation_gain_m, elevation_loss_m, calories, location_name.
    No pace field.
    """

def _format_swimming(activity: dict) -> str:
    """
    Fields: date, distance_km (or laps if distance=0), duration_hms, calories.
    No pace, no elevation.
    """

def _format_triathlon(activity: dict) -> str:
    """
    Fields: date, total duration, total distance, calories.
    Lap count as proxy for legs if per-leg data unavailable. No pace.
    """

def _format_strength(activity: dict) -> str:
    """
    Fields: date, name, duration_hms, calories.
    No pace, no distance, no elevation.
    """

def _format_hiking(activity: dict) -> str:
    """
    Fields: date, name, distance_km, duration_hms, elevation_gain_m,
            elevation_loss_m, calories, location_name.
    No pace.
    """

def _format_mountaineering(activity: dict) -> str:
    """
    Fields: date, name, duration_hms, elevation_gain_m, elevation_loss_m,
            max_elevation_m, min_elevation_m, calories, location_name.
    No pace, de-emphasizes flat distance.
    """

def _format_generic(activity: dict) -> str:
    """
    Fallback for 'other' / GENERIC / unknown types.
    Fields: date, name, duration_hms, distance_km (if > 0), calories.
    """

SPORT_FORMATTERS = {
    "running":             _format_running,
    "treadmill_running":   _format_running,
    "cycling":             _format_cycling,
    "swimming":            _format_swimming,
    "open_water_swimming": _format_swimming,
    "triathlon":           _format_triathlon,
    "strength_training":   _format_strength,
    "hiking":              _format_hiking,
    "mountaineering":      _format_mountaineering,
}
```

Records with < 10 per sport still chunked but metadata carries `"analysis_ready": False`.

---

## Task 4 — JWT auth + privacy filter

**Files:** `app/core/security.py` (new), `app/api/routers/query.py`

```python
# app/core/security.py

def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """
    Creates a signed JWT containing user_id as subject.
    Default expiry: 30 days (configurable via settings).
    Returns: encoded JWT string.
    """

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency. Decodes JWT, validates signature, returns User object.
    Raises HTTP 401 if token missing, expired, or tampered.
    """

async def google_oauth_login() -> RedirectResponse:
    """GET /auth/google — redirects to Google OAuth2 consent screen."""

async def google_oauth_callback(code: str, db: Session = Depends(get_db)) -> dict:
    """
    GET /auth/callback — exchanges code for Google token, upserts User record,
    issues JWT, returns {"access_token": ..., "token_type": "bearer"}.
    """
```

```python
# app/api/routers/query.py — updated endpoint

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    store: PGVector = Depends(get_vector_store),
) -> QueryResponse:
    """
    Hard-injects current_user.user_id into filter_dict before every search.
    pgvector physically cannot return another user's records.
    """
    filter_dict = {"user_id": str(current_user.id)}
    if request.data_type:
        filter_dict["data_type"] = request.data_type
```

---

## Task 5 — Async upload + post-upload sport summary

**File:** `app/api/routers/upload.py`

```python
@router.post("/upload", response_model=UploadAcceptedResponse)
async def upload_zip(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
) -> UploadAcceptedResponse:
    """
    Streams file to tmp disk with shutil.copyfileobj — no 246 MB in RAM.
    Dispatches parse+embed as BackgroundTask.
    Returns immediately: {"status": "processing", "task_id": "xyz"}.
    """

async def _parse_and_embed(tmp_path: str, user_id: str, task_id: str) -> None:
    """
    Background task:
      1. parse_garmin_zip(tmp_path)
      2. chunk_garmin_data(parsed, user_id)
      3. embed_and_store(docs)
      4. compute sport_summary (count per activity_type, analysis_ready flag)
      5. update task_store: status="completed", sport_summary={...}
      6. delete tmp file
    """

@router.get("/upload/status/{task_id}", response_model=UploadStatusResponse)
async def upload_status(task_id: str) -> UploadStatusResponse:
    """
    Returns current task status + sport_summary when completed.
    """

def _build_sport_summary(documents: list[Document]) -> dict:
    """
    Counts records per activity_type from document metadata.
    Sets analysis_ready = count >= 10.
    """
```

New schemas in `app/api/schemas.py`:

```python
class SportInfo(BaseModel):
    count: int
    analysis_ready: bool
    warning: str | None = None

class UploadStatusResponse(BaseModel):
    status: str                              # "processing" | "completed" | "failed"
    sports_found: dict[str, SportInfo] | None = None
    sleep_records: int | None = None
    error: str | None = None
```

---

## Task 6 — Evaluation baseline + golden dataset

**Files:** `scripts/generate_eval_dataset.py` (new), `tests/eval_dataset.json` (new),
`app/services/evaluator.py` (new), `scripts/run_eval.py` (new)

```python
# scripts/generate_eval_dataset.py

def generate_eval_dataset(data_dir: str, output_path: str, n: int = 80) -> None:
    """
    1. parse_garmin_zip() on real sample data
    2. chunk_garmin_data(parsed, user_id="eval_user")
    3. Batch documents to Gemini — generates realistic query + expected answer + doc ID
    4. Throttle: asyncio.sleep(1.5) between batches to avoid rate limits
    5. Write JSON array to output_path
    CLI: python scripts/generate_eval_dataset.py --n 80
    NOTE: manually review tests/eval_dataset.json before committing.
    """
```

```python
# app/services/evaluator.py

def evaluate_retrieval(
    store: PGVector,
    dataset: list[dict],
    k: int = 5,
    filter_dict: dict | None = None,
) -> dict:
    """
    Computes Hit Rate@K and MRR.
    Each dataset entry: {"query", "expected_doc_ids": [...], ...}
    Returns: {"hit_rate": float, "mrr": float, "total": int, "hits": int}
    """

async def evaluate_faithfulness(
    rag_results: list[dict],
    batch_size: int = 5,
    throttle_seconds: float = 1.5,
) -> dict:
    """
    RAGAS + Gemini judge. Scores faithfulness and answer relevance.
    rag_results: list of {"question", "answer", "contexts": [...]}
    Throttles between batches to avoid Gemini rate limits.
    Returns: {"faithfulness": float, "answer_relevance": float}
    """

def compute_hit_rate(results: list[dict]) -> float:
    """Fraction of queries where correct doc_id found in top-K."""

def compute_mrr(results: list[dict]) -> float:
    """Mean(1 / rank_of_first_correct_doc); 0.0 if not found in top-K."""
```

```python
# scripts/run_eval.py

def run_eval(k: int = 5, use_rerank: bool = False, sport_filter: str | None = None):
    """
    CLI:
      python scripts/run_eval.py --k 5
      python scripts/run_eval.py --k 15 --rerank
      python scripts/run_eval.py --k 5 --sport running
    Prints per-sport table + overall numbers.
    """
```

Add `ragas` to `requirements.txt`.

---

## Task 7 — Parameter exposure (LLMConfig)

**File:** `app/api/schemas.py`

```python
class LLMConfig(BaseModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=64, le=8192)
    k: int = Field(default=15, ge=1, le=30)
    top_n: int = Field(default=5, ge=1, le=15)
    use_rerank: bool = True

class QueryRequest(BaseModel):
    query: str
    k: int = 5
    data_type: str | None = None
    use_llm: bool = True
    llm_config: LLMConfig | None = None
```

**File:** `app/services/rag_engine.py`

```python
def _build_llm(temperature: float = 0.2, max_output_tokens: int = 1024) -> ChatGoogleGenerativeAI:
    """Accepts explicit params. Default temperature = 0.2 for factual RAG."""

async def ask(
    query: str,
    store: PGVector,
    k: int = 15,
    top_n: int = 5,
    filter_dict: dict | None = None,
    use_rerank: bool = True,
    temperature: float = 0.2,
    max_output_tokens: int = 1024,
) -> tuple[str, list[tuple[Document, float]]]:
    """Updated to accept all LLMConfig fields as kwargs."""
```

---

## Task 8 — Self-querying retriever (multi-type + sports vocabulary)

**File:** `app/services/rag_engine.py`

```python
async def _build_filter(
    query: str,
    user_id: str,
    base_filter: dict | None = None,
) -> list[dict]:
    """
    Async Gemini pre-pass before vector search.
    System prompt instructs Gemini to:
      1. Translate colloquial terms → standard activity_type values
         ("bike" → "cycling", "jog" → "running", "tri" → "triathlon")
      2. Detect multi-type queries (running + sleep for fatigue questions)
      3. Always inject user_id into every filter dict
      4. Output JSON: list of filter dicts

    Single-type:  "my long bike rides"
      → [{"user_id": "u1", "data_type": "activity", "activity_type": "cycling"}]

    Multi-type:   "why am I tired running lately"
      → [{"user_id": "u1", "data_type": "activity", "activity_type": "running"},
         {"user_id": "u1", "data_type": "sleep"}]

    Uses ainvoke() — fully async, never blocks event loop.
    """

async def ask(...):
    """
    Updated flow:
      1. _build_filter(query, user_id) → list of filter dicts
      2. similarity_search_with_score() for each filter (asyncio.gather)
      3. Merge + deduplicate hits
      4. rerank(query, merged_hits, top_n) if use_rerank
      5. _build_context(hits) → string
      6. LLM.ainvoke(context + query) → answer
    """
```

---

## Task 9 — Reranking layer

**File:** `app/services/reranker.py` (new)

```python
_reranker: CrossEncoder | None = None   # module-level lazy cache

def load_reranker() -> CrossEncoder:
    """
    Lazy-loads cross-encoder/ms-marco-MiniLM-L-6-v2 on first call (~67 MB).
    Subsequent calls return cached instance.
    """

def _sigmoid(x: float) -> float:
    """Maps raw logit to (0.0, 1.0)."""
    return 1.0 / (1.0 + math.exp(-x))

def _rerank_sync(
    query: str,
    hits: list[tuple[Document, float]],
    top_n: int,
) -> list[tuple[Document, float]]:
    """
    Synchronous cross-encoder scoring. Wrapped in to_thread — not called directly.
    Scores each (query, doc.page_content) pair.
    Applies sigmoid to normalize logits → 0.0–1.0 (matches ChunkResult.score).
    Returns top_n hits sorted by cross-encoder score descending.
    """

async def rerank(
    query: str,
    hits: list[tuple[Document, float]],
    top_n: int = 5,
) -> list[tuple[Document, float]]:
    """
    Public async API. Wraps _rerank_sync in asyncio.to_thread() —
    CPU-bound ops never block FastAPI's event loop under concurrent requests.
    """
    return await asyncio.to_thread(_rerank_sync, query, hits, top_n)
```

---

## Task 10 — Hybrid RAG + secure SQL + trend queries

**File:** `app/services/sql_retriever.py` (new)

```python
def get_readonly_engine() -> Engine:
    """
    SQLAlchemy engine using a dedicated read-only PostgreSQL account.
    GRANT SELECT only — no DROP/DELETE/INSERT/UPDATE.
    Connection string from settings.readonly_db_url.
    """

async def route_query(query: str, user_id: str) -> str:
    """
    Classifies query intent via Gemini:
      "aggregation" → sql_aggregation
      "trend"       → sql_trend
      "semantic"    → vector + rerank (default)
    Returns: "sql_aggregation" | "sql_trend" | "vector"
    """

async def sql_aggregation(query: str, user_id: str) -> str:
    """
    LangChain SQLDatabaseChain on read-only engine.
    System prompt enforces WHERE user_id = :uid in every generated SQL.
    Returns: plain text answer with exact numbers.
    """

async def sql_trend(record_type: str, user_id: str) -> list[dict]:
    """
    Direct SQL for time-series personal record comparison.

    SELECT record_type, value, record_unit, record_date
    FROM personal_records
    WHERE user_id = :uid AND record_type = :record_type
    ORDER BY record_date ASC;

    Returns: list of {date, value, unit} oldest→newest.
    LLM receives this list and explains the trend in prose.
    """

async def hybrid_ask(
    query: str,
    store: PGVector,
    user_id: str,
    llm_config: LLMConfig | None = None,
) -> str:
    """
    Top-level dispatcher used by query endpoint.
    Calls route_query() → dispatches to sql_aggregation / sql_trend / vector+rerank.
    """
```

---

## Task 11 — Frontend skeleton loading

**File:** `frontend/app/components/QuerySection.tsx`

```tsx
// States: idle | loading | streaming | done | error

function SkeletonAnswer(): JSX.Element {
    // 3 animate-pulse grey bars mimicking answer text lines
}

function SkeletonSources(): JSX.Element {
    // 2 animate-pulse grey cards mimicking source citation cards
}

const STATUS_MESSAGES = [
    "Analyzing your training intent...",
    "Ranking results across your history...",
    "Generating insight...",
]
// cycle through messages every 1.5s while state === "loading"
// switch to streaming display as soon as first token arrives
```

---

## Task 13 — Frontend auth flow (Google OAuth login)

**Context:** Backend OAuth endpoints (`/auth/google`, `/auth/callback`) are fully implemented.
The frontend `QuerySection.tsx` already reads the token from `localStorage.getItem("token")`.
What's missing: a login page, the callback handler, and a logout button.

**Files:**
- `frontend/app/page.tsx` — add login gate (show login button if no token)
- `frontend/app/auth/callback/page.tsx` (NEW) — handle OAuth redirect, store token
- `frontend/app/components/LoginButton.tsx` (NEW) — "Login with Google" button
- `frontend/app/components/LogoutButton.tsx` (NEW) — clears token from localStorage

```tsx
// frontend/app/components/LoginButton.tsx
// Redirects to GET /auth/google (backend handles Google consent screen)
<a href={`${API_URL}/auth/google`}>Login with Google</a>

// frontend/app/auth/callback/page.tsx
// Reads ?access_token= from URL query params (or hash)
// → localStorage.setItem("token", access_token)
// → router.push("/")  redirect back to home

// frontend/app/page.tsx  — login gate
const token = localStorage.getItem("token")
if (!token) return <LoginButton />
return <QuerySection />
```

**Backend callback change needed:**
Currently `google_oauth_callback` returns JSON `{"access_token": "..."}`.
For the browser flow it should instead redirect to:
`http://localhost:3000/auth/callback?access_token=<jwt>`
so the frontend page can pick it up.

Update `app/core/security.py`:
```python
async def google_oauth_callback(code: str, db: Session) -> RedirectResponse:
    ...
    access_token = create_access_token(str(user.id))
    frontend_url = settings.frontend_url  # e.g. http://localhost:3000
    return RedirectResponse(url=f"{frontend_url}/auth/callback?access_token={access_token}")
```

Add to `app/core/config.py`:
```python
frontend_url: str = "http://localhost:3000"
```

**Verification:**
1. Open `http://localhost:3000` → sees login button (no token in localStorage)
2. Click login → Google consent → redirected back → token stored in localStorage
3. Page shows QuerySection — upload and query work without manual token handling
4. Logout clears token → login button reappears

---

## Task 12 — AWS deployment

| Component | Service | Notes |
|---|---|---|
| FastAPI backend | EC2 t3.small (2 vCPU, 2 GB) | min for local embedding model |
| Next.js frontend | EC2 t3.micro or Vercel | |
| PostgreSQL + pgvector | RDS PostgreSQL 15 | enable pgvector extension |
| ZIP storage | S3 + presigned URL | frontend uploads directly, bypasses backend |
| Containers | ECR + ECS Fargate | auto-scaling |
| Load balancer | ALB | read_timeout = 60s (covers reranker latency) |
| Secrets | Secrets Manager | DB URL, Google OAuth, API keys |

Pre-prod RAM cut (swap local models for cloud APIs):
- all-MiniLM-L6-v2 → OpenAI Embeddings or Jina Embeddings API
- cross-encoder → Cohere Rerank or Jina Rerank API
- RAM: 2 GB → less than 512 MB → can use t3.micro

---

## Files changed summary

| File | Tasks | New? |
|---|---|---|
| `app/services/chunker.py` | 1, 3 | — |
| `app/services/embedder.py` | 2 | — |
| `app/core/security.py` | 4 | NEW |
| `app/api/routers/query.py` | 4, 7 | — |
| `app/api/routers/upload.py` | 5 | — |
| `app/api/schemas.py` | 5, 7 | — |
| `scripts/generate_eval_dataset.py` | 6 | NEW |
| `tests/eval_dataset.json` | 6 | NEW |
| `app/services/evaluator.py` | 6 | NEW |
| `scripts/run_eval.py` | 6 | NEW |
| `requirements.txt` | 6 | — |
| `app/services/rag_engine.py` | 7, 8 | — |
| `app/services/reranker.py` | 9 | NEW |
| `app/services/sql_retriever.py` | 10 | NEW |
| `frontend/app/components/QuerySection.tsx` | 11 | — |
| `frontend/app/page.tsx` | 13 | — |
| `frontend/app/auth/callback/page.tsx` | 13 | NEW |
| `frontend/app/components/LoginButton.tsx` | 13 | NEW |
| `frontend/app/components/LogoutButton.tsx` | 13 | NEW |
| `app/core/security.py` | 13 | — |
| `app/core/config.py` | 13 | — |

---

## Verification at each task

| Task | How to verify |
|---|---|
| 1 | Upload ZIP → inspect stored metadata in pgvector: user_id present on all chunks |
| 2 | Upload same ZIP twice → document count stays the same (no duplicates) |
| 3 | Inspect generated prose: cycling has no pace field; running has pace |
| 4 | No JWT → 401; user A token → zero results from user B's activity IDs |
| 5 | Upload returns task_id instantly; /status/{task_id} returns sport card with counts |
| 6 | python scripts/run_eval.py --k 5 → baseline Hit Rate / MRR / Faithfulness per sport |
| 7 | Re-run eval with --temperature 0.0 vs 0.5 → compare numbers |
| 8 | "bike ride" query → filter shows activity_type: cycling; "why tired" → two filters |
| 9 | python scripts/run_eval.py --k 15 --rerank → Hit Rate + MRR >= baseline |
| 10 | "total km this month?" → exact SQL number; "improved over 2 years?" → time-series |
| 13 | Open localhost:3000 → login button shown → Google login → token in localStorage → QuerySection loads |
| All | pytest tests/ -v → no regressions |
