# Garmin Insight RAG - Garmin 健康數據 AI 問答系統

Garmin Insight RAG 是一個基於 RAG（Retrieval-Augmented Generation）架構的健康數據問答系統，專為 Garmin 穿戴裝置用戶設計。只需上傳 Garmin 匯出的 ZIP 資料，系統即會自動解析活動、睡眠、個人紀錄等數據，並讓你以自然語言詢問健康相關問題，獲得 AI 整合後的個人化洞察。

後端以 FastAPI 建置，使用 PostgreSQL + pgvector 儲存向量嵌入，本地 Sentence Transformers 模型（all-MiniLM-L6-v2）生成嵌入向量，並以 Google Gemini（`gemini-2.0-flash`，**有免費方案**）作為 LLM 生成自然語言回答。

---

## 快速開始

1. 複製專案並安裝依賴

    ```bash
    git clone https://github.com/Sophiehsin/garmin-rag-project.git
    cd garmin-rag-project
    python3 -m venv rag.venv && source rag.venv/bin/activate
    pip install -r requirements.txt
    ```

2. 啟動 PostgreSQL + pgvector（需安裝 Docker）

    ```bash
    docker-compose up -d
    ```

3. 啟動 API 服務

    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

4. 上傳 Garmin 匯出 ZIP

    ```bash
    curl -X POST http://localhost:8000/api/v1/upload \
      -F "file=@your_garmin_export.zip"
    ```

5. 以自然語言查詢健康數據

    ```bash
    curl -X POST http://localhost:8000/api/v1/query \
      -H "Content-Type: application/json" \
      -d '{"query": "最近幾次騎車的平均速度如何？", "k": 5}'
    ```

6. 或開啟互動式 API 文件（Swagger UI）

    前往 `http://localhost:8000/docs` 即可直接測試所有端點

---

## 主要功能

- **多類型 Garmin 數據解析**

    自動解析 ZIP 中的三類核心資料：運動活動（跑步、騎車等）、睡眠記錄、個人最佳紀錄，並完整保留所有欄位與單位換算。

- **語意相似度搜尋**

    每筆數據轉換為自然語言文字後生成向量嵌入，透過 pgvector 的餘弦相似度搜尋，快速找出與問題最相關的健康記錄。

- **AI 健康問答**

    結合語意搜尋結果與 Gemini LLM，針對個人數據生成具體、脈絡豐富的健康洞察回答。

- **冪等上傳，無重複資料**

    每份文件以 SHA-256 確定性 ID 識別，重複上傳相同 ZIP 會自動更新而非新增，確保資料庫乾淨。

---

## RAG 資料處理流程

```
Garmin ZIP
    ↓ parse_garmin_zip()        解壓縮、camelCase → snake_case、時間格式統一
    ↓ chunk_garmin_data()       每筆記錄 → 自然語言 Document（含結構化 metadata）
    ↓ embed_and_store()         all-MiniLM-L6-v2 生成 384 維向量，存入 pgvector
    ↓ similarity_search()       餘弦相似度搜尋前 k 筆最相關記錄
    ↓ Claude LLM                整合檢索結果，生成個人化健康洞察
```

---

## 技術特色

- **單位自動換算**：原始 Garmin 數據（距離 cm、速度 dm/s、時長 ms）在文字化時自動換算為人類可讀單位（km、km/h、min:ss/km）
- **跑步 vs. 其他運動**：跑步活動顯示配速（如 5:00/km），其他運動顯示時速（km/h）
- **多格式時間支援**：支援三種 Garmin 時間格式（Unix 毫秒、ISO 8601、英文文字日期）統一轉為 UTC
- **metadata 過濾**：查詢時可依 `data_type`（activity / sleep / personal_record）篩選，精準縮小搜尋範圍
- **Apple Silicon 加速**：自動偵測 MPS / CUDA / CPU，優先使用 MPS 加速嵌入生成

---

## 即將推出的功能

以下功能目前正在規劃或開發中：

- **前端介面**

    開發網頁前端，讓使用者可透過瀏覽器上傳 Garmin ZIP、輸入問題並即時檢視 AI 回答，無需使用 API 工具或命令列。

- **搜尋功能強化**（進行中）

    持續優化語意搜尋品質，包含依日期範圍篩選、支援更多 Garmin 資料類型（如訓練狀態、耐力分數），以及改善多筆結果的排序與相關性。

---

## 專案結構

```
garmin-rag-project/
├── app/
│   ├── main.py                 # FastAPI 入口、CORS、lifespan
│   ├── api/
│   │   ├── schemas.py          # 請求/回應 Pydantic 模型
│   │   ├── dependencies.py     # DI：vector store
│   │   └── routers/
│   │       ├── upload.py       # POST /api/v1/upload
│   │       └── query.py        # POST /api/v1/query
│   ├── services/
│   │   ├── parser.py           # ZIP 解析、key 正規化、時間與單位換算
│   │   ├── chunker.py          # Garmin dict → LangChain Document
│   │   └── embedder.py         # 嵌入生成 + pgvector 儲存
│   ├── core/
│   │   ├── config.py           # 環境變數設定
│   │   └── database.py         # 連線字串
│   └── models/                 # Pydantic + SQLModel 資料模型
├── tests/                      # 72 個測試，全數通過
├── docker-compose.yml          # PostgreSQL + pgvector
└── requirements.txt
```

---

## 測試

```bash
# 執行所有測試（72 個）
pytest -v

# 僅執行不需要資料庫的單元測試
pytest -v -k "not integration"
```

---

## 聯絡與貢獻

若對該專案有興趣，或有任何優化建議，歡迎聯絡我（Sophie / a850132a@gmail.com）共同優化！
