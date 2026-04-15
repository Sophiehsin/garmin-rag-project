# Garmin RAG Project - Dockerfile
#
# 本檔案應包含：
# 1. Base image：python:3.11-slim
# 2. 系統依賴安裝（libpq-dev 等 PostgreSQL 相關）
# 3. pip install requirements.txt
# 4. 複製應用程式碼
# 5. 暴露 port 8000
# 6. 啟動指令：uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# 階段三部署至 Render.com 時使用此 Dockerfile
