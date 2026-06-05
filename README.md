# Garmin Insight RAG — Garmin 健康數據 AI 問答系統

Garmin Insight RAG 是一個基於 RAG（Retrieval-Augmented Generation）架構的健康數據問答系統，專為 Garmin 穿戴裝置用戶設計。上傳你的 Garmin 匯出資料後，即可用自然語言詢問個人運動表現、睡眠品質與個人紀錄，獲得 AI 整合後的個人化健康洞察。

後端以 FastAPI 建置，使用 PostgreSQL + pgvector 儲存向量嵌入，本地 Sentence Transformers 模型（all-MiniLM-L6-v2）生成嵌入向量，並以 Google Gemini（**有免費方案**）作為 LLM 生成自然語言回答。

---

## 第一步：匯出你的 Garmin 資料

1. 登入 [Garmin 帳戶資料管理頁面](https://www.garmin.com/zh-TW/account/datamanagement/exportdata/)
2. 點擊「**匯出你的資料**」
3. 等待 Garmin 寄送下載連結至你的信箱（通常需要數分鐘至數小時）
4. 下載 `.zip` 壓縮檔，即為本系統所需的上傳檔案

> 匯出檔案包含你所有的運動活動、睡眠記錄與個人最佳紀錄，系統會自動解析其中的核心資料。

---

## 使用流程

```
① 至 Garmin 官網匯出資料 → 下載 ZIP
         ↓
② 上傳 ZIP 至本系統
   POST /api/v1/upload
         ↓ 背景解析（數秒至數十秒）
③ 系統自動解析活動、睡眠、個人紀錄
   並將所有資料向量化存入資料庫
         ↓
④ 用自然語言詢問你的健康數據
   POST /api/v1/query
         ↓
⑤ AI 根據你的個人資料生成回答
```

---

## 你可以問什麼？

上傳完成後，可以用中文或英文詢問：

**運動表現**
- 「我最近一個月騎車的平均速度是多少？」
- 「這兩年跑步成績有進步嗎？」
- 「我最長的一次騎車是哪一天？距離多少？」
- 「最近幾次跑步的配速趨勢如何？」

**睡眠品質**
- 「上週睡眠品質如何？」
- 「最近覺得累，可能跟睡眠有關嗎？」
- 「我的深睡比例通常是多少？」

**個人紀錄**
- 「我的跑步最佳紀錄是什麼時候創下的？」
- 「這兩年三鐵成績有沒有進步？」

**綜合分析**
- 「近一個月訓練最多的是哪種運動？最近覺得累可能是什麼原因？」
- 「我的騎車成績這幾年有沒有穩定進步？」

---

## 快速開始

### 安裝與啟動

```bash
# 1. 複製專案並安裝依賴
git clone https://github.com/Sophiehsin/garmin-rag-project.git
cd garmin-rag-project
python3 -m venv rag.venv && source rag.venv/bin/activate
pip install -r requirements.txt

# 2. 設定環境變數
echo "GOOGLE_API_KEY=你的Gemini金鑰" > .env

# 3. 啟動 PostgreSQL + pgvector（需安裝 Docker）
docker-compose up -d

# 4. 啟動後端 API
uvicorn app.main:app --reload --port 8000
```

取得 Gemini API 金鑰：[Google AI Studio](https://aistudio.google.com/app/apikey)（免費）

### 建立帳號並取得 Token

```bash
python3 -c "
from app.core.security import create_access_token
from app.core.database import get_engine
from app.models.sql_models import User
from sqlmodel import Session, SQLModel

engine = get_engine()
SQLModel.metadata.create_all(engine)
with Session(engine) as db:
    user = User(email='test@example.com')
    db.add(user)
    db.commit()
    db.refresh(user)
    print(create_access_token(str(user.id)))
"
```

複製印出的 Token，後續上傳與查詢都需要帶入。

### 上傳 Garmin ZIP

```bash
TOKEN="貼上你的token"

curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/garmin_export.zip"

# 回傳：{"status": "processing", "task_id": "xxx"}
```

### 查詢上傳進度

```bash
curl http://localhost:8000/api/v1/upload/status/xxx
# 回傳：{"status": "completed", "sports_found": {...}, "sleep_records": 420}
```

### 開始詢問

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "最近幾次騎車的平均速度如何？"}'
```

### 使用 Swagger UI（最方便）

開啟 `http://localhost:8000/docs`，點擊右上角 **Authorize** 貼入 Token，即可在瀏覽器中直接測試所有端點。

---

## 主要功能

- **多運動格式解析**：跑步、騎車、游泳、三鐵、重訓、健行、登山等 7 種運動各有專屬文字格式，配速/速度/爬升依運動類型自動選用
- **語意相似度搜尋**：每筆資料向量化後透過 pgvector 餘弦相似度搜尋，找出最相關的歷史記錄
- **Cross-encoder 重排序**：搜尋結果再以 cross-encoder 模型重新評分，提升回答品質
- **混合 SQL + RAG 查詢**：統計性問題（「總共騎了幾公里？」）走 SQL，趨勢問題走時間序列查詢，語義問題走向量搜尋
- **自我查詢理解**：系統自動將口語詞彙（「騎車」→ cycling、「慢跑」→ running）對應至正確的資料類型
- **多用戶資料隔離**：每位使用者的資料以 JWT + user_id 完全隔離，無法互相存取
- **冪等上傳**：重複上傳相同 ZIP 自動更新而非新增，資料庫保持乾淨

---

## RAG 資料處理流程

```
Garmin ZIP
    ↓ parse_garmin_zip()       解壓縮、camelCase → snake_case、時間格式統一
    ↓ chunk_garmin_data()      每筆記錄 → 自然語言 Document（含結構化 metadata）
    ↓ embed_and_store()        all-MiniLM-L6-v2 生成 384 維向量，存入 pgvector
    ↓ similarity_search()      餘弦相似度搜尋最相關記錄
    ↓ rerank()                 cross-encoder 重新評分，取前 N 筆
    ↓ Gemini LLM               整合檢索結果，生成個人化健康洞察
```

---

## 技術特色

- **單位自動換算**：原始 Garmin 數據（距離 cm、速度 dm/s、時長 ms）在文字化時自動換算為人類可讀單位（km、km/h、min:ss/km）
- **多格式時間支援**：支援三種 Garmin 時間格式（Unix 毫秒、ISO 8601、英文文字日期）統一轉為 UTC
- **metadata 過濾**：查詢時可依 `data_type`（activity / sleep / personal_record）篩選
- **Apple Silicon 加速**：自動偵測 MPS / CUDA / CPU，優先使用 MPS 加速嵌入生成
- **非同步上傳**：大型 ZIP 串流寫入磁碟，背景解析，API 立即回傳不阻塞

---

## 專案結構

```
garmin-rag-project/
├── app/
│   ├── main.py                 # FastAPI 入口、CORS、/auth/* 路由
│   ├── api/
│   │   ├── schemas.py          # 請求/回應 Pydantic 模型（含 LLMConfig）
│   │   ├── dependencies.py     # DI：vector store
│   │   └── routers/
│   │       ├── upload.py       # POST /api/v1/upload（非同步背景任務）
│   │       └── query.py        # POST /api/v1/query（混合 SQL + RAG）
│   ├── services/
│   │   ├── parser.py           # ZIP 解析、key 正規化、時間與單位換算
│   │   ├── chunker.py          # Garmin dict → LangChain Document（7 種運動格式）
│   │   ├── embedder.py         # 嵌入生成 + pgvector 儲存（確定性 ID）
│   │   ├── rag_engine.py       # 自我查詢 + 平行搜尋 + Gemini 生成
│   │   ├── reranker.py         # Cross-encoder 重排序（非同步）
│   │   ├── sql_retriever.py    # 混合路由：統計/趨勢 → SQL，語義 → RAG
│   │   └── evaluator.py        # Hit Rate@K、MRR、Gemini 忠實度評分
│   ├── core/
│   │   ├── config.py           # 環境變數設定
│   │   ├── database.py         # SQLAlchemy 引擎 + get_db()
│   │   └── security.py         # JWT 工具函式 + Google OAuth
│   └── models/                 # Pydantic + SQLModel 資料模型
├── frontend/                   # Next.js 16 前端（含骨架載入動畫）
├── scripts/
│   ├── generate_eval_dataset.py  # 產生評測資料集
│   └── run_eval.py               # 執行 Hit Rate / MRR / Faithfulness 評測
├── tests/                      # 81 個測試，全數通過
├── docker-compose.yml          # PostgreSQL + pgvector
└── requirements.txt
```

---

## 測試

```bash
# 執行所有測試
pytest tests/ -v

# 僅執行不需要資料庫的單元測試
pytest tests/ -v -k "not integration"
```

---

## 聯絡與貢獻

若對該專案有興趣，或有任何優化建議，歡迎聯絡（Sophie / a850132a@gmail.com）！
