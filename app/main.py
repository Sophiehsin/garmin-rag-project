"""
FastAPI 入口與 BackgroundTask 配置

本檔案應包含：
1. FastAPI app 實例化與全域設定 (CORS, middleware)
2. 引入並註冊所有 API Router (upload, query, auth)
3. Lifespan / startup event：
   - 初始化資料庫連線池
   - 初始化 Embedding model / LLM client
4. BackgroundTask 配置：
   - 用於檔案上傳後的異步解析與 Embedding 儲存
   - 階段二將在此整合 Supabase 連線
5. 健康檢查端點 (/health)
6. 全域例外處理 (Exception Handler)
"""
