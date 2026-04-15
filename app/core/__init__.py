"""
核心設定模組

本目錄應包含以下設定檔：
- config.py：環境變數與應用程式設定 (Pydantic BaseSettings)
  - DATABASE_URL (地端 PostgreSQL / 階段二 Supabase)
  - LLM_API_KEY (Claude / Gemini)
  - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
  - EMBEDDING_MODEL 設定
  - CORS 允許的 origins
- security.py：認證與安全相關
  - JWT token 生成與驗證
  - OAuth 2.0 token 管理
  - API Key 驗證 middleware
  - 密碼雜湊工具 (若需要)
- database.py：資料庫引擎與 Session 管理
  - SQLAlchemy / SQLModel engine 建立
  - get_session dependency
"""
