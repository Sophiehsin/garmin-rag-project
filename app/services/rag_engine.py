"""
LangChain 檢索與 LLM 串接服務

本檔案應包含：
1. Vector Store 初始化
   - 使用 LangChain 的 PGVector 作為 vector store
   - 連接 PostgreSQL + pgvector
   - 設定 similarity search 參數 (top_k, threshold)

2. Retriever 建構
   - 建立 LangChain Retriever
   - 支援 metadata filtering（按日期範圍、活動類型篩選）
   - 可選：MMR (Maximal Marginal Relevance) 以提升結果多樣性

3. Prompt Template 設計
   - System prompt：定義 AI 健康助理角色與回答風格
   - 加入 Garmin 數據上下文的 template
   - 支援多輪對話的 prompt 組合

4. LLM Chain 串接
   - 整合 Claude 3.5 Sonnet / Gemini 1.5 Pro
   - 可選：地端 Ollama (Llama 3 / Mistral) 用於測試
   - RetrievalQA Chain 或 ConversationalRetrievalChain
   - 設定 temperature, max_tokens 等參數

5. 查詢處理流程
   - 接收使用者自然語言問題
   - 執行 retrieval -> augmentation -> generation
   - 回傳結構化回應（答案 + 引用來源 + 相關數據）

6. RAG 評測輔助（配合 tests/ 使用）
   - 提供評測用的 retrieval 結果匯出
   - 支援 faithfulness / relevance 等指標計算
"""
