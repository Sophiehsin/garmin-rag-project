# Garmin Insight RAG — Garmin 健康數據 AI 問答系統

Garmin Insight RAG 是一個基於 RAG（Retrieval-Augmented Generation）架構的健康數據問答系統，專為 Garmin 穿戴裝置用戶設計。上傳你的 Garmin 匯出資料後，即可用自然語言詢問個人運動表現、睡眠品質與個人紀錄，獲得 AI 整合後的個人化健康洞察。

---

## 如何使用

### 步驟一：匯出你的 Garmin 資料

1. 登入 [Garmin 帳戶資料管理頁面](https://www.garmin.com/zh-TW/account/datamanagement/exportdata/)
2. 點擊「**匯出你的資料**」
3. 等待 Garmin 寄送下載連結至你的信箱（通常需要數分鐘至數小時）
4. 下載 `.zip` 壓縮檔，即為本系統所需的上傳檔案

> 匯出檔案包含你所有的運動活動、睡眠記錄與個人最佳紀錄，系統會自動解析其中的核心資料。

---

### 步驟二：上傳 ZIP 開始使用

取得 ZIP 後，透過 API 上傳：

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_garmin_export.zip"
```

系統會在背景自動解析資料，回傳 `task_id`，可用以下指令查詢進度：

```bash
curl http://localhost:8000/api/v1/upload/status/{task_id}
# {"status": "completed", "sports_found": {"running": {...}, "cycling": {...}}, "sleep_records": 420}
```

---

### 步驟三：詢問你的健康數據

上傳完成後，即可用中文或英文詢問：

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "最近幾次騎車的平均速度如何？"}'
```

---

## 你可以問什麼？

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

## 想先試試看？使用範例資料

還沒有 Garmin 帳號或還沒匯出資料？可以先用我們提供的範例資料體驗系統：

**下載範例資料：[`data/demo/garmin_demo.zip`](data/demo/garmin_demo.zip)**

此範例包含：
- **70 筆跑步記錄**
- **20 筆騎車記錄**
- **10 筆其他運動記錄**（健行、重訓等）
- **30 筆睡眠記錄**
- **56 筆個人最佳紀錄**

> 所有個人識別資訊（用戶 ID、裝置 ID、GPS 座標、活動名稱）均已移除或替換為虛構數值，資料內容（速度、距離、睡眠時長等）保持真實。

上傳方式與真實資料相同：

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/demo/garmin_demo.zip"
```

上傳完成後，可以試著詢問：
- 「我最近跑步的配速是多少？」
- 「騎車距離最長的一次是哪天？」
- 「睡眠深睡比例通常是多少？」

---

## 主要功能

- **多運動格式解析**：跑步（含配速）、騎車（含速度）、游泳、三鐵、重訓、健行、登山各有專屬文字格式
- **語意相似度搜尋**：每筆資料向量化後透過 pgvector 餘弦相似度搜尋，找出最相關的歷史記錄
- **Cross-encoder 重排序**：搜尋結果再以 cross-encoder 模型重新評分，提升回答品質
- **混合 SQL + RAG 查詢**：統計性問題（「總共騎了幾公里？」）走 SQL，趨勢問題走時間序列，語義問題走向量搜尋
- **自我查詢理解**：自動將口語詞彙（「騎車」→ cycling、「慢跑」→ running）對應至正確資料類型
- **多用戶資料隔離**：每位使用者的資料以 JWT + user_id 完全隔離，無法互相存取
- **非同步上傳**：大型 ZIP 串流寫入磁碟，背景解析，API 立即回傳不阻塞

---

## 技術架構

後端：FastAPI + PostgreSQL + pgvector
嵌入模型：`all-MiniLM-L6-v2`（384 維，本地執行，支援 Apple Silicon MPS 加速）
LLM：Google Gemini（`gemini-2.5-flash`，**有免費方案**）
重排序：`cross-encoder/ms-marco-MiniLM-L-6-v2`
前端：Next.js 16 + Tailwind CSS v4

---

## 聯絡與貢獻

若對該專案有興趣，或有任何優化建議，歡迎聯絡（Sophie / a850132a@gmail.com）！
