"""
資料庫遷移與一次性腳本

本目錄應包含：
- init_db.py：初始化資料庫 schema、建立 pgvector extension
- seed_data.py：匯入測試用 Garmin 樣本數據
- migrate.py：資料庫遷移腳本（或整合 Alembic）
- cleanup.py：清理過期 embedding、暫存檔案等
"""
