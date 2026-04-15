"""
單元測試與 RAG 評測

本目錄應包含：
- test_parser.py：測試 Garmin JSON 解析邏輯
  - ZIP 解壓縮正確性
  - JSON 過濾是否取得正確檔案
  - 數據正規化結果驗證
  - Chunking 策略測試

- test_rag_engine.py：測試 RAG 檢索品質
  - Retrieval 準確度 (Precision@K, Recall@K)
  - 回答忠實度 (Faithfulness)
  - 回答相關性 (Answer Relevance)
  - 使用 RAGAS 或自定義評測框架

- test_calendar.py：測試 Google Calendar 操作
  - Mock Google API 呼叫
  - 行程建立 / 查詢 / 刪除邏輯

- test_api.py：API 端對端測試
  - 使用 TestClient 測試各端點
  - 認證流程測試
  - 上傳與查詢整合測試

- conftest.py：測試共用 fixtures
  - 測試用資料庫 session
  - 樣本 Garmin 數據 fixtures
  - Mock LLM / Embedding 回應
"""
