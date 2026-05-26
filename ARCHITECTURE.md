# Garmin Insight RAG — 專案架構與開發指南

> 本文件涵蓋完整系統架構、每個模組的設計邏輯、資料流、關鍵設計決策，以及開發時需要知道的所有細節。

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [技術棧](#2-技術棧)
3. [目錄結構](#3-目錄結構)
4. [完整資料流](#4-完整資料流)
5. [各模組詳解](#5-各模組詳解)
6. [API 端點](#6-api-端點)
7. [資料模型](#7-資料模型)
8. [關鍵設計決策](#8-關鍵設計決策)
9. [Garmin 原始資料單位對照表](#9-garmin-原始資料單位對照表)
10. [環境變數設定](#10-環境變數設定)
11. [本地開發啟動步驟](#11-本地開發啟動步驟)
12. [測試策略](#12-測試策略)
13. [常見問題與注意事項](#13-常見問題與注意事項)

---

## 1. 專案概覽

**Garmin Insight RAG** 是一個基於 RAG（Retrieval-Augmented Generation）架構的個人健康數據問答系統。

使用者上傳 Garmin 穿戴裝置匯出的 ZIP 壓縮檔，系統自動解析其中的三類核心數據（運動活動、睡眠紀錄、個人最佳），將每筆記錄轉換為自然語言文字並存入向量資料庫。使用者接著可以用自然語言提問，系統透過語意相似度搜尋找出最相關的健康記錄，再由 Claude LLM 整合這些資料生成具體的個人化回答。

**系統完成後的能力範例：**
- 「我最近三個月的騎車速度有進步嗎？」
- 「哪幾天的睡眠品質最差？」
- 「我的馬拉松個人最佳是什麼時候創下的？」

---

## 2. 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | HTTP API 服務，async 支援 |
| 向量資料庫 | PostgreSQL + pgvector | 儲存 384 維嵌入向量，餘弦相似度搜尋 |
| ORM | SQLModel（SQLAlchemy + Pydantic） | 資料表定義與操作 |
| 嵌入模型 | sentence-transformers `all-MiniLM-L6-v2` | 本地生成 384 維向量，無需 API Key |
| 向量存取層 | langchain-postgres `PGVector` | pgvector 的現代 LangChain 整合（取代已棄用的 langchain-community） |
| LLM | Google Gemini via `langchain-google-genai` | 生成自然語言健康洞察回答（免費方案：`gemini-2.0-flash`） |
| 資料驗證 | Pydantic v2 | 請求/回應 schema、欄位驗證 |
| 設定管理 | pydantic-settings | 環境變數讀取，支援 `.env` 檔案 |
| 容器化 | Docker + Docker Compose | 本地 PostgreSQL + pgvector 環境 |
| 測試 | pytest + pytest-asyncio | 81 個測試，含 async 測試支援 |
| 硬體加速 | PyTorch（MPS/CUDA/CPU） | 嵌入模型自動選用最佳裝置 |

---

## 3. 目錄結構

```
garmin-rag-project/
│
├── app/                            # 主應用程式
│   ├── main.py                     # FastAPI app 入口
│   ├── core/
│   │   ├── config.py               # 環境變數與設定
│   │   └── database.py             # 資料庫連線字串
│   ├── models/                     # 資料模型（Pydantic + SQLModel）
│   │   ├── activities.py           # 運動活動模型
│   │   ├── sleep.py                # 睡眠紀錄模型
│   │   ├── records.py              # 個人最佳模型
│   │   └── sql_models.py           # 資料庫 ORM 資料表
│   ├── api/
│   │   ├── schemas.py              # API 請求/回應 schema
│   │   ├── dependencies.py         # FastAPI 依賴注入
│   │   └── routers/
│   │       ├── upload.py           # POST /api/v1/upload
│   │       └── query.py            # POST /api/v1/query
│   └── services/                   # 核心業務邏輯
│       ├── parser.py               # ZIP 解析、資料正規化
│       ├── chunker.py              # 文字化與 LangChain Document 轉換
│       ├── embedder.py             # 向量嵌入 + pgvector 儲存
│       └── rag_engine.py           # RAG 推理鏈（Claude LLM）
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── test_parser.py              # 19 tests
│   ├── test_sql_models.py          # 4 tests
│   ├── test_chunker.py             # 21 tests
│   ├── test_embedder.py            # 14 tests
│   ├── test_api.py                 # 14 tests
│   └── test_rag_engine.py          # 9 tests
│
├── data/
│   ├── samples/                    # 真實 Garmin 樣本資料（不進 git）
│   └── [garmin_export].zip         # 匯出的 ZIP 檔（不進 git）
│
├── scripts/
│   ├── analyze_garmin_zip.py       # 分析 ZIP 結構的工具腳本
│   └── test_db_connection.py       # 測試資料庫連線
│
├── docker-compose.yml              # PostgreSQL + pgvector
├── Dockerfile
├── requirements.txt
├── PLAN.md                         # 任務規劃與完成狀態
├── COMPLETION.md                   # 各任務完成摘要
└── ARCHITECTURE.md                 # 本文件
```

---

## 4. 完整資料流

### 上傳流程（ZIP → pgvector）

```
使用者 POST /api/v1/upload（ZIP 檔）
    │
    ▼  routers/upload.py
    │  儲存至暫存檔，驗證是否為合法 ZIP
    │
    ▼  parser.parse_garmin_zip(zip_path)
    │  解壓縮，找出 3 個核心 JSON：
    │    summarizedActivities.json → "summarizedActivities"
    │    sleepData.json            → "sleepData"
    │    personalRecord.json       → "personalRecords"
    │  對所有 key 遞迴執行 camelCase → snake_case
    │  回傳 dict[str, list[dict]]
    │
    ▼  chunker.chunk_garmin_data(parsed)
    │  每筆記錄 → 1 個 LangChain Document
    │    page_content：自然語言散文（給 embedding 用）
    │    metadata：結構化欄位（給 metadata filter 用）
    │  回傳 list[Document]（真實資料約 1,013 筆）
    │
    ▼  embedder.embed_and_store(documents)
    │  對每筆 Document.page_content 生成 384 維向量
    │  計算 SHA-256 確定性 ID（冪等上傳）
    │  以 COSINE 距離策略存入 pgvector
    │
    ▼  回傳 UploadResponse
       {status, documents_stored, breakdown, collection}
```

### 查詢流程（自然語言 → AI 回答）

```
使用者 POST /api/v1/query
    {"query": "...", "k": 5, "data_type": "activity", "use_llm": true}
    │
    ▼  routers/query.py
    │  解析 QueryRequest，組裝 filter_dict（若有 data_type）
    │
    ├─ use_llm=True ──▶  rag_engine.ask(query, store, k, filter_dict)
    │                        │
    │                        ▼ store.similarity_search_with_score()
    │                        │  pgvector 餘弦相似度搜尋，回傳 top-k
    │                        │
    │                        ▼ hits.sort(key=date)
    │                        │  依日期升序排列（防 Lost-in-the-Middle）
    │                        │
    │                        ▼ _build_context(hits)
    │                        │  注入 Date + Type metadata 標籤
    │                        │  超過 12,000 字元截斷
    │                        │
    │                        ▼ await (prompt | ChatAnthropic).ainvoke()
    │                        │  非同步呼叫 Claude，30 秒 timeout
    │                        │
    │                        ▼ 回傳 (answer, hits)
    │
    └─ use_llm=False ─▶  store.similarity_search_with_score()
                          直接回傳 hits，answer=None
    │
    ▼  回傳 QueryResponse
       {query, results: [ChunkResult...], answer: str | null}
```

---

## 5. 各模組詳解

### 5.1 `app/core/config.py` — 設定管理

使用 `pydantic-settings`，所有設定都有預設值（對應本地 Docker 環境），可透過環境變數或 `.env` 檔覆寫。

```python
class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "test123"
    db_name: str = "vectordb"
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_collection: str = "garmin_health"
    google_api_key: str = ""          # 需設定才能使用 LLM 功能（免費方案可用）
    llm_model: str = "gemini-2.0-flash"
```

**注意：** `extra = "ignore"` 讓 `.env` 中有額外欄位也不會報錯。

---

### 5.2 `app/services/parser.py` — 資料解析層

**三個核心功能：**

**① ZIP 解析 `parse_garmin_zip(zip_path)`**

Garmin 匯出的 ZIP 結構複雜（264 個檔案），函式會掃描所有 JSON 檔案名稱，以模糊比對找出目標檔案（不依賴固定路徑）。

目標檔案對應關係：
```
summarizedActivities.json → 鍵名 "summarizedActivities"
sleepData.json            → 鍵名 "sleepData"
personalRecord.json       → 鍵名 "personalRecords"
```

**② 鍵名正規化 `normalize_json_keys(value)`**

遞迴將所有 dict 的 key 從 camelCase 轉為 snake_case：
- `activityId` → `activity_id`
- `startTimeInSeconds` → `start_time_in_seconds`
- `spo2SleepSummary` → `spo2_sleep_summary`（含縮寫）

**③ 時間格式正規化 `normalize_timestamp(ts)`**

Garmin 資料中有三種時間格式，全部統一轉為 UTC datetime：

| 格式 | 範例 | 來源 |
|------|------|------|
| Unix 毫秒 | `1715904000000` | 運動活動 |
| ISO 8601 | `"2024-05-14T15:41:04.0"` | 睡眠記錄 |
| 英文文字 | `"May 15, 2024"` / `"Sat Apr 11 16:00:00 GMT 2026"` | 個人最佳 |

輸入無效時回傳 `None`（不拋例外），呼叫端需自行處理。

---

### 5.3 `app/services/chunker.py` — 文字化與切塊層

**核心邏輯：每筆 Garmin 記錄 → 1 個 LangChain Document**

**`format_activity_as_text(activity)`**

根據活動類型選擇不同的速度表達方式：
- 跑步 → 配速（`5:00/km`）：`pace_sec = 100.0 / float(raw_speed_dms)`
- 其他 → 時速（`km/h`）：`kmh = float(dms) * 36.0`

輸出範例：
```
You completed a cycling session on March 16, 2020, covering 7.91 km in 32min 24sec.
Your average speed was 14.6 km/h with a maximum of 25.3 km/h.
You burned 913 calories. You accumulated 781 m of elevation gain.
```

**`format_sleep_as_text(sleep)`**

包含零除防護：`total = deep + light + rem + awake`，若 total == 0 或全為 None，輸出 "Sleep stage breakdown unavailable"。

**`build_metadata(data_type, record)`**

每個 Document 的 metadata 結構：
```python
{
    "data_type": "activity" | "sleep" | "personal_record",
    "source": "garmin_zip",
    "record_id": int | None,
    "activity_type": "cycling" | "running" | ... | None,
    "user_id": int | None,
    "date": "YYYY-MM-DD" | None,        # 用於 metadata filter 與排序
    "is_current_pr": True | False | None  # 只有 personal_record 有值
}
```

**`chunk_sleep()`** 會跳過「無日期且總睡眠秒數為零」的記錄（Garmin 的空白損壞記錄）。

---

### 5.4 `app/services/embedder.py` — 向量嵌入層

**硬體加速自動偵測：**
```python
if torch.backends.mps.is_available(): return "mps"   # Apple Silicon 優先
if torch.cuda.is_available():         return "cuda"
return "cpu"
```

**冪等上傳（SHA-256 確定性 ID）：**

重複上傳相同 ZIP 不會產生重複資料：
```python
key = f"{data_type}:{record_id}:{date}"        # 一般情況
key = f"content:{doc.page_content}"            # metadata 全空時的 fallback
id  = hashlib.sha256(key.encode()).hexdigest()  # 64 位 hex 字串
```

PGVector 使用此 ID 執行 upsert（`pre_delete_collection=False`）。

**模型快取：** `_embeddings` 為模組層級變數，整個程序生命週期只載入一次（`~90 MB`）。

---

### 5.5 `app/services/rag_engine.py` — RAG 推理層

**使用模型：** Google Gemini（`gemini-2.0-flash`），透過 `langchain-google-genai`，**有免費方案**（每分鐘 15 次、每天 1,500 次）。

**四個生產級強化：**

| 強化項目 | 問題 | 做法 |
|---------|------|------|
| Metadata 注入 | 純文字無法區分 2018 vs 2026 的訓練記錄 | 每段 context 加上 `Date:` 和 `Type:` 標籤 |
| 時序排序 | LLM 對 prompt 中間的資訊吸收較差（Lost-in-the-Middle） | `hits.sort(key=date)` 升序排列，最新資料在末端 |
| 非同步呼叫 | 同步等待 LLM 回應（2–5 秒）會阻塞 FastAPI 執行緒 | `async def ask()` + `await chain.ainvoke()` |
| Token 預算 | 大量記錄可能超出 context 限制或造成意外費用 | 12,000 字元截斷 + `max_output_tokens=1024` |

**Context 格式範例：**
```
[Excerpt 1] (Date: 2020-03-16, Type: activity)
Content: You completed a cycling session on March 16, 2020...

[Excerpt 2] (Date: 2024-05-15, Type: sleep)
Content: On the night of 2024-05-15, you slept for 7 hours...
```

---

### 5.6 `app/main.py` — FastAPI 入口

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embeddings()   # 啟動時預載模型，避免第一個請求緩慢
    yield
```

CORS 設定為 `allow_origins=["*"]`（開發用，正式環境應限制來源）。

---

## 6. API 端點

### `GET /health`
健康檢查。
```json
{"status": "ok"}
```

---

### `POST /api/v1/upload`

接受 Garmin 匯出 ZIP，執行完整解析 → 嵌入 → 儲存流程。

**請求：** `multipart/form-data`，欄位名稱 `file`

**回應：**
```json
{
  "status": "ok",
  "documents_stored": 1013,
  "breakdown": {"activity": 862, "sleep": 95, "personal_record": 56},
  "collection": "garmin_health"
}
```

**錯誤碼：**
- `400` — 非 ZIP 檔 / ZIP 損壞 / 解析失敗
- `422` — 未附上檔案
- `500` — 向量儲存失敗

---

### `POST /api/v1/query`

語意搜尋，可選 Claude LLM 生成回答。

**請求：**
```json
{
  "query": "最近的騎車表現如何？",
  "k": 5,
  "data_type": "activity",    // 可選："activity" | "sleep" | "personal_record"
  "use_llm": true             // true = Claude 回答；false = 僅回傳搜尋結果
}
```

**回應：**
```json
{
  "query": "最近的騎車表現如何？",
  "answer": "根據你的記錄，最近幾次騎車...",   // use_llm=false 時為 null
  "results": [
    {
      "content": "You completed a cycling session on...",
      "metadata": {"data_type": "activity", "date": "2024-03-10", ...},
      "score": 0.847
    }
  ]
}
```

**錯誤碼：**
- `422` — query 為空 / data_type 不合法
- `503` — pgvector 無法連線 / Claude API 失敗（含 timeout）

---

## 7. 資料模型

### Pydantic 驗證模型（`app/models/`）

| 模型 | 檔案 | 欄位數 | 用途 |
|------|------|--------|------|
| `SummarizedActivityModel` | `activities.py` | 45+ | 驗證從 ZIP 解析出的運動活動資料 |
| `SleepDataModel` | `sleep.py` | 50+ | 驗證睡眠紀錄，SpO2 範圍 0–100 |
| `PersonalRecordModel` | `records.py` | 30+ | 驗證個人最佳，支援多種日期格式 |

### SQLModel ORM 資料表（`app/models/sql_models.py`）

| 資料表 | 索引 | 說明 |
|--------|------|------|
| `User` | `id` | 最小使用者表，提供外鍵關聯 |
| `SummarizedActivityDB` | `(user_id, start_time_in_seconds)` | 支援按時間範圍快速查詢 |
| `SleepDataDB` | `(user_id, calendar_date)` | 支援按日期查詢睡眠 |
| `PersonalRecordDB` | `(user_id, personal_record_type)` | 支援按類型篩選 PR |

所有資料表都有 `created_at` 和 `updated_at` 稽核欄位。

---

## 8. 關鍵設計決策

### 8.1 原生單位儲存，轉換在展示層
所有數值以 Garmin 原生單位存入（毫秒、公分、dm/s），在 `chunker.py` 轉換為人類可讀格式。好處是保留最高精度，轉換錯誤也只影響展示層。

### 8.2 UTC 統一時間
三種 Garmin 時間格式全部正規化為 UTC datetime，消除跨時區問題。

### 8.3 snake_case 全面正規化
在解析入口 `normalize_json_keys()` 一次性遞迴轉換，後續所有程式碼只需處理 snake_case。

### 8.4 Pydantic + SQLModel 單一定義
欄位定義只寫一次，同時用於 Pydantic 驗證和 SQLAlchemy ORM，避免重複定義與不一致。

### 8.5 langchain-postgres 取代 langchain-community
`langchain-community` 的 PGVector 已棄用，改用 `langchain-postgres`，API 有差異（`embeddings=` 參數名稱、`use_jsonb=True`）。

### 8.6 FastAPI `dependency_overrides` 測試模式
不使用 `patch()`，改用 `app.dependency_overrides[get_store] = lambda: mock_store`，才能正確攔截 FastAPI 的依賴注入。

---

## 9. Garmin 原始資料單位對照表

> **這是開發時最容易踩坑的地方。** 原始 JSON 的單位與直覺不同。

| 欄位 | 原始單位 | 轉換公式 | 結果單位 |
|------|---------|---------|---------|
| `distance` | 公分（cm） | `÷ 100,000` | 公里（km） |
| `avg_speed` / `max_speed` | 分米/秒（dm/s） | `× 36` | 公里/小時（km/h） |
| `avg_speed`（跑步配速） | 分米/秒（dm/s） | `100 ÷ dms` | 秒/公里，再轉 `mm:ss/km` |
| `duration` | 毫秒（ms） | `÷ 1,000` | 秒；再 `÷ 60` 得分鐘 |
| `begin_timestamp` | Unix 毫秒 | `÷ 1,000` 後轉 datetime | UTC datetime |
| `elevation_gain` | 公尺（m） | 直接使用 | 公尺 |

**轉換範例（`chunker.py` 的 helper 函式）：**
```python
_cm_to_km(791093.99)      # → 7.91 km
_dms_to_kmh(0.4068)       # → 14.6 km/h
_pace_str(0.3331)         # → "5:00/km"  (100 / 0.3331 ≈ 300 秒/km)
_ms_to_hms(1944574.95)    # → "32min 24sec"
```

---

## 10. 環境變數設定

在專案根目錄建立 `.env` 檔案（已列入 `.gitignore`，不會進入 git）：

```env
# 資料庫（Docker 本地開發預設值，通常不需修改）
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=test123
DB_NAME=vectordb

# Embedding 模型
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_COLLECTION=garmin_health

# Gemini LLM（use_llm=true 時必填，免費方案可用）
GOOGLE_API_KEY=AIza...
LLM_MODEL=gemini-2.0-flash
```

**取得 GOOGLE_API_KEY 步驟：** 參考下方第 10.1 節。

---

## 10.1 取得 Google API Key（免費）

**步驟如下：**

1. 前往 **[aistudio.google.com](https://aistudio.google.com)**，用 Google 帳號登入

2. 點選左側選單的 **「Get API key」**

3. 點選 **「Create API key」** → 選擇一個 Google Cloud 專案（或建立新的）

4. 複製產生的 API Key（格式：`AIzaSy...`）

5. 貼入 `.env` 檔案：
   ```env
   GOOGLE_API_KEY=AIzaSy你的金鑰
   ```

6. **重啟伺服器**（`.env` 在啟動時才讀入）：
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

**免費方案限制（`gemini-2.0-flash`）：**

| 限制項目 | 免費額度 |
|---------|---------|
| 每分鐘請求數（RPM） | 15 次 |
| 每天請求數（RPD） | 1,500 次 |
| 每分鐘 Token 數（TPM） | 100 萬 |
| 費用 | 完全免費 |

> 測試用途完全足夠。如需更高吞吐量可升級至付費方案。

---

## 11. 本地開發啟動步驟

```bash
# 1. 建立並啟動虛擬環境
python3 -m venv rag.venv
source rag.venv/bin/activate          # Windows: rag.venv\Scripts\activate

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 啟動 PostgreSQL + pgvector（需要 Docker）
docker-compose up -d

# 4. 確認 .env 已設定（最少需要 DB 設定，LLM 功能另需 API Key）
cp .env.example .env   # 若有範本
# 或直接建立 .env，內容參考上方第 10 節

# 5. 啟動 API 伺服器
uvicorn app.main:app --reload --port 8000

# 6. 確認服務正常
curl http://localhost:8000/health
# 回應：{"status": "ok"}

# 7. 開啟 Swagger UI 互動測試
open http://localhost:8000/docs
```

---

## 12. 測試策略

```bash
# 執行全部測試
pytest -v

# 只執行不需要資料庫的單元測試
pytest -v -k "not integration and not end_to_end"

# 執行特定測試檔
pytest tests/test_chunker.py -v
pytest tests/test_rag_engine.py -v

# 查看覆蓋率
pytest --cov=app tests/
```

**測試分層：**

| 層級 | 說明 | 需要 DB | 需要 API Key |
|------|------|---------|------------|
| 單元測試 | mock 所有外部依賴，純邏輯驗證 | 否 | 否 |
| 整合測試（DB） | 需要 Docker pgvector 運行 | 是 | 否 |
| 整合測試（LLM） | 需要真實 ANTHROPIC_API_KEY | 是 | 是 |

**Async 測試（`test_rag_engine.py`）** 使用 `@pytest.mark.asyncio` 標記，需要 `pytest-asyncio` 套件且設定 `asyncio_mode=strict`。

---

## 13. 常見問題與注意事項

### Q：上傳時出現 `ON CONFLICT DO UPDATE CardinalityViolation`
**原因：** 損壞的睡眠記錄（無日期且總睡眠秒數為零）都生成相同的 SHA-256 ID。  
**解決：** `chunker.chunk_sleep()` 已加入跳過邏輯，`_make_doc_id()` 有 fallback 至 content hash，此問題已修復。

### Q：`test_query_*` 測試出現 503 錯誤
**原因：** 測試沒有設定 `use_llm=False`，預設呼叫 RAG chain，但沒有 API Key 所以失敗。  
**解決：** 純搜尋測試加上 `"use_llm": false`，或用 `app.dependency_overrides` + `AsyncMock` mock `rag_engine.ask`。

### Q：`patch()` 無法 mock FastAPI 端點的依賴注入
**原因：** FastAPI 的 `Depends()` 在執行時才解析，`patch()` 替換的時機不對。  
**解決：** 使用 `app.dependency_overrides[get_store] = lambda: mock_store`，測試後記得 `app.dependency_overrides.clear()`。

### Q：重複上傳同一個 ZIP 會不會產生重複資料？
不會。每筆 Document 的 ID 由 `data_type + record_id + date` 的 SHA-256 決定，pgvector 使用 `pre_delete_collection=False` 執行 upsert。

### Q：第一次查詢很慢？
正常現象。`lifespan` 事件會在啟動時預載 embedding 模型（`~90 MB`），之後快取於記憶體。若仍緩慢，第一次查詢還需要建立 pgvector 連線。

### Q：`use_llm=true` 但 `ANTHROPIC_API_KEY` 沒設定？
端點會回傳 `HTTP 503`，錯誤訊息為 `"RAG chain failed: ..."` 。設定 `.env` 中的 `ANTHROPIC_API_KEY` 後重啟伺服器即可。

### Q：如何新增支援新的 Garmin 資料類型？
1. 在 `app/models/` 新增 Pydantic 模型
2. 在 `app/models/sql_models.py` 新增 SQLModel 資料表
3. 在 `chunker.py` 新增 `format_xxx_as_text()` 和 `chunk_xxx()` 函式
4. 在 `chunk_garmin_data()` 加入新類型的處理
5. 在 `parser.py` 的 `TARGET_JSONS` 加入對應的 JSON 檔案名稱
