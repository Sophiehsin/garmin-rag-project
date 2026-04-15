"""
SQLModel / SQLAlchemy 資料模型定義

本目錄應包含以下模型檔案：

1. user.py - 使用者模型
   - User：使用者基本資訊（email, name, google_id）
   - UserToken：OAuth token 儲存（access_token, refresh_token, expires_at）

2. document.py - 文件與向量模型
   - GarminUpload：上傳紀錄（檔案名稱、上傳時間、處理狀態）
   - DocumentChunk：文本切片（content, metadata, source_file）
   - Embedding：向量儲存（使用 pgvector 的 Vector 類型）
     - 欄位：id, chunk_id, embedding (vector), created_at

3. activity.py - Garmin 活動結構化數據
   - Activity：活動摘要（類型、距離、時間、心率、卡路里）
   - DailySummary：每日健康摘要（步數、睡眠、壓力）
   - SleepRecord：睡眠詳細紀錄

4. schemas.py - Pydantic Request/Response Schema
   - QueryRequest：使用者查詢請求
   - QueryResponse：RAG 回應結果
   - UploadResponse：上傳結果回應
   - CalendarEventCreate：建立行程請求
"""
