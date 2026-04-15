"""
API 路由模組

本目錄應包含以下路由檔案：
- upload.py：處理 Garmin ZIP 檔案上傳、觸發 BackgroundTask 進行解析
- query.py：接收使用者自然語言查詢，呼叫 RAG Engine 回傳結果
- auth.py：Google OAuth 2.0 授權流程 (登入、callback、token refresh)
- calendar.py：Google Calendar 相關 API 端點 (建立事件、查詢行程)

每個路由檔使用 APIRouter 定義，在 main.py 中統一註冊。
"""
