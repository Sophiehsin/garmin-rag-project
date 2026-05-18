# 🔍 Garmin 實際數據結構分析

**生成日期**：2026年4月18日  
**分析工具**：scripts/analyze_garmin_zip.py  
**ZIP 檔**：data/86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip  
**ZIP 大小**：172.01 MB  

---

## 📊 **計劃 vs 實際對比**

| 指標 | 原計劃 | 實際情況 | 差異 |
|------|-------|--------|------|
| **核心 JSON 檔** | 10 個 | 3 個 | -70% |
| **Pydantic 模型** | 10 個 | 3 個 | -70% |
| **SQLModel 模型** | 10 個 | 3 個 | -70% |
| **總開發工時** | 50-65h | 25-35h | -50% |
| **所有 JSON 檔** | - | 214 個 | 信息極豐富 |

---

## 🎯 **實際核心數據（3 種類型）**

### **1️⃣ summarizedActivities.json** 
**活動記錄 - 運動健身數據**

#### 文件信息
- **路徑**：`DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json`
- **結構**：`[{ summarizedActivitiesExport: [...] }]`
- **數據量**：多個活動（2000+ 年度積累）
- **時間範圍**：2019-至今

#### 數據模型
```python
class SummarizedActivity(BaseModel):
    # 基本信息
    activityId: int
    name: str
    activityType: str  # "cycling", "running", etc.
    
    # 時間 (毫秒級 Unix 時間戳)
    startTimeGmt: int  # e.g., 1584405978000
    startTimeLocal: int
    duration: float  # 毫秒
    elapsedDuration: float
    movingDuration: float
    
    # 距離與高度
    distance: float  # 米
    elevationGain: float
    elevationLoss: float
    minElevation: float
    maxElevation: float
    
    # 速度與步幅
    avgSpeed: float  # m/s
    maxSpeed: float
    avgFractionalCadence: float
    maxFractionalCadence: float
    
    # 熱量與心率
    calories: float
    
    # 位置信息
    startLatitude: float
    startLongitude: float
    locationName: Optional[str]
    
    # 設備與標籤
    deviceId: int
    userProfileId: int
    lapCount: int
    favorite: bool
    purposeful: bool
    pr: bool  # Personal Record
    elevationCorrected: bool
    
    # UUID
    uuidMsb: int
    uuidLsb: int
    timeZoneId: int
    eventTypeId: int
    rule: str
    sportType: str
    autoCalcCalories: bool
    atpActivity: bool
    parent: bool
    maxVerticalSpeed: float
    summarizedDiveInfo: dict
```

#### 關鍵特點
✅ 毫秒級時間戳 (需轉換為秒或 datetime)  
✅ 距離單位：米 (m)  
✅ 速度單位：米/秒 (m/s)  
✅ 包含 GPS 位置信息  
✅ 多年積累，數據豐富  

---

### **2️⃣ sleepData.json**
**睡眠數據 - 健康監測**

#### 文件信息
- **路徑**：`DI_CONNECT/DI-Connect-Wellness/2024-05-15_2024-08-23_74303376_sleepData.json`
- **結構**：`[{...}, {...}, ...]` - 直接列表
- **數據量**：100 條記錄
- **時間範圍**：2024年5月-8月

#### 數據模型
```python
class SleepData(BaseModel):
    # 時間 (ISO 8601 字符串格式)
    sleepStartTimestampGMT: str  # "2024-05-14T15:41:04.0"
    sleepEndTimestampGMT: str
    calendarDate: str  # "2024-05-15" - YYYY-MM-DD
    
    # 睡眠階段（秒數）
    deepSleepSeconds: int
    lightSleepSeconds: int
    remSleepSeconds: int
    awakeSleepSeconds: int
    unmeasurableSeconds: int
    
    # 呼吸數據
    averageRespiration: float
    lowestRespiration: float
    highestRespiration: float
    
    # 睡眠評分 (詳細評分系統)
    sleepScores: SleepScores  # 包含 10+ 個評分維度
    
    # SPO2 與心率
    spo2SleepSummary: {
        userProfilePk: int
        deviceId: int
        sleepMeasurementStartGMT: str
        sleepMeasurementEndGMT: str
        averageSPO2: float  # 血氧飽和度
        averageHR: float    # 平均心率
        lowestSPO2: float
    }
    
    # 其他
    awakeCount: int
    avgSleepStress: float
    restlessMomentCount: int
    sleepWindowConfirmationType: str  # "ENHANCED_CONFIRMED_FINAL"
    retro: bool
```

#### SleepScores 子模型
```python
class SleepScores(BaseModel):
    overallScore: int          # 總體評分
    qualityScore: int          # 質量評分
    durationScore: int         # 時長評分
    recoveryScore: int         # 恢復評分
    deepScore: int            # 深度睡眠評分
    remScore: int             # REM 睡眠評分
    lightScore: int           # 淺度睡眠評分
    awakeningsCountScore: int # 覺醒次數評分
    awakeTimeScore: int       # 覺醒時長評分
    combinedAwakeScore: int
    restfulnessScore: int
    interruptionsScore: int
    feedback: str             # "NEGATIVE_NOT_ENOUGH_REM" 等
    insight: str              # "NEGATIVE_STRENUOUS_EXERCISE" 等
```

#### 關鍵特點
✅ ISO 8601 時間格式 (字符串)  
✅ 睡眠評分系統詳細 (10+ 維度)  
✅ 包含 SPO2 (血氧) 和心率數據  
✅ 數據結構清晰，易於解析  
✅ 數據量適中 (100 條)  

---

### **3️⃣ personalRecord.json**
**個人紀錄 - 個人最佳成績**

#### 文件信息
- **路徑**：`DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_personalRecord.json`
- **結構**：`[{ personalRecords: [...] }]` - 包含子列表
- **數據量**：10+ 條不同類型的紀錄
- **紀錄類型**：最佳距離、最多步數、最長連續、最快速度等

#### 數據模型
```python
class PersonalRecord(BaseModel):
    personalRecordId: int
    personalRecordType: str  # "Best Half Marathon", "Most Steps in a Day", etc.
    value: float  # 紀錄值 (單位取決於類型)
    
    # 時間 (文本格式)
    prStartTimeGMT: str  # "Sat Apr 11 16:00:00 GMT 2026"
    createdDate: str  # "2019-01-11" - YYYY-MM-DD
    
    # 狀態
    activityId: int  # 0 表示非活動相關的紀錄
    current: bool
    confirmed: bool
```

#### 常見紀錄類型
- `"Current Goal Streak"` - 當前目標連續天數
- `"Most Steps in a Day"` - 最多步數（日）
- `"Most Steps in a Week"` - 最多步數（週）
- `"Most Steps in a Month"` - 最多步數（月）
- `"Best Half Marathon"` - 最佳半馬時間
- `"Longest Goal Streak"` - 最長連續目標天數
- `"Farthest Cycle"` - 最遠騎行距離
- `"Best 40km Cycle"` - 最佳 40km 騎行成績
- `"Max Elevation Gain"` - 最大爬升高度
- `"Best 10km Run"` - 最佳 10km 跑步時間

#### 關鍵特點
✅ 紀錄類型多樣  
✅ 時間格式為文本 (需解析)  
✅ Value 單位根據紀錄類型不同  
✅ 包含當前和歷史紀錄  

---

## ⏰ **時間格式統一規範**

需要處理 **3 種不同的時間格式**：

| 格式 | 示例 | 來源 | 轉換目標 |
|------|------|------|--------|
| 毫秒級 Unix | `1584405978000` | Activities | UTC datetime |
| ISO 8601 | `"2024-05-14T15:41:04.0"` | Sleep | UTC datetime |
| 文本格式 | `"Sat Apr 11 16:00:00 GMT 2026"` | Records | UTC datetime |

### 轉換函數設計
```python
def normalize_timestamp(
    value: Union[int, float, str],
    source_type: str = "auto"
) -> datetime:
    """
    統一轉換為 UTC datetime
    
    Args:
        value: 時間值
        source_type: "milliseconds", "iso8601", "text", "auto"
    
    Returns:
        datetime (UTC)
    """
```

---

## 📏 **單位標準化規範**

### 內部統一單位系統

| 量度 | 內部單位 | 需轉換的單位 |
|------|--------|-----------|
| **距離** | km | 米 (activities) → km |
| **速度** | km/h | m/s (activities) → km/h |
| **高度** | m | 保持 m |
| **時間** | s | 毫秒 (activities) → s |
| **血氧** | % | 直接使用 |
| **心率** | bpm | 直接使用 |
| **呼吸** | breaths/min | 直接使用 |

### 轉換公式
```python
# 距離：米 → 公里
km = meters / 1000

# 速度：m/s → km/h
km_h = m_s * 3.6

# 時間：毫秒 → 秒
seconds = milliseconds / 1000
```

---

## 🎯 **修訂的任務清單**

基於實際數據結構，將 14 個任務簡化為 13 個精簡任務：

### Phase 2A: 基礎模型 (Tasks 1-4)
- ✅ **Task 1** - ZIP 分析 (COMPLETED)
- **Task 2** - 定義 Pydantic 模型 (3 個)
- **Task 3** - 定義 SQLModel 模型 (3 個)
- **Task 4** - 實作 ZIP 過濾函數

### Phase 2B: 數據正規化 (Tasks 5-7)
- **Task 5** - 時間戳正規化 (3 種格式)
- **Task 6** - 單位轉換 (距離、速度、時間)
- **Task 7** - JSON 解析與驗證

### Phase 2C: Chunking (Tasks 8-9)
- **Task 8** - 設計 Chunking 策略
- **Task 9** - 實作 Chunking 函數

### Phase 2D: 測試與文檔 (Tasks 10-13)
- **Task 10** - 單元測試
- **Task 11** - API 整合
- **Task 12** - 項目文檔
- **Task 13** - E2E 測試

**總計工時**：約 25-35 小時（相比原計劃 50-65h 減少 50%）

---

## 🗂️ **提取的樣本文件**

已從 ZIP 中提取核心 JSON 樣本到 `data/samples/`：

```
data/samples/
├── summarizedActivities.json      ✅ 活動記錄
├── sleepData.json                 ✅ 睡眠數據 (100 條)
└── personalRecord.json            ✅ 個人紀錄
```

可用於：
- 模型定義和驗證
- 單元測試 fixtures
- 手動檢查和分析

---

## 💡 **下一步建議**

1. **立即開始 Task 2** - 基於此文檔定義 3 個 Pydantic 模型
2. **細化時間戳處理** - 編寫 normalize_timestamp() 測試用例
3. **設計單位轉換** - 創建轉換常量和函數
4. **快速驗證** - 用樣本數據測試模型和轉換函數

---

**文檔版本**：1.0  
**最後更新**：2026-04-18  
**作者**：Garmin RAG Project Analysis

