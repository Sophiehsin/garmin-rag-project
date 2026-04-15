"""
Garmin JSON 過濾與解析服務

本檔案應包含：
1. ZIP 檔案解壓縮邏輯
   - 接收上傳的 Garmin 全量 ZIP
   - 從中提取核心 JSON 檔案（約 10 個）

2. 核心 JSON 過濾清單（階段二重點）：
   - summarizedActivities.json：活動摘要（跑步、騎車、游泳等）
   - dailySummaries.json：每日健康摘要
   - sleepData.json：睡眠數據
   - stressData.json：壓力指數
   - heartRate.json：心率數據
   - steps.json：步數統計
   - calories.json：卡路里消耗
   - bodyComposition.json：體組成數據
   - trainingStatus.json：訓練狀態
   - personalRecord.json：個人紀錄

3. JSON 解析與正規化
   - 將原始 Garmin JSON 轉換為統一的內部資料結構
   - 處理時間戳記格式統一 (UTC -> local)
   - 數值單位轉換（公制/英制）

4. 文本切片 (Chunking)
   - 將解析後的數據轉換為適合 Embedding 的文本段落
   - 設定 chunk size 與 overlap 策略
   - 為每個 chunk 加上 metadata（日期、類型、來源檔案）

5. Embedding 生成與儲存
   - 呼叫 Embedding model 產生向量
   - 將向量與 metadata 存入 PostgreSQL + pgvector
"""
