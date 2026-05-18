# Garmin RAG 項目 - 第二步：數據解析服務 (The Parser) 完整計劃

**建立日期：** 2026年4月18日  
**目標：** 開發完整的 Garmin JSON 解析、正規化、切片流程  
**重要性：** 核心重點 - RAG 效果的基礎

---

## 📌 **項目概述**

第二步是整個項目中最複雜的部分。Garmin 的原始 JSON 資料非常龐雜且不規則，如果這一步沒做好，後面的 RAG 效果會大打折扣。本計劃涵蓋從 ZIP 解析到文本切片的完整流程。

---

## 🎯 **核心任務分解（精簡 13 個待辦項 - 基於實際數據）**

### **第一級：基礎模型定義（任務 1-3）**
定義 3 個核心 Pydantic/SQLModel 模型

---

### **✅ 任務 1：分析 Garmin ZIP 結構 - 已完成**

**優先級：** ⭐⭐⭐⭐⭐ 最高  
**實際工時：** 2.5 小時  
**狀態：** ✅ 完成

#### 完成內容
- ✅ 運行 analyze_garmin_zip.py 工具
- ✅ 找到 3 個核心 JSON 檔案（而非計劃的 10 個）
- ✅ 提取所有樣本到 data/samples/
- ✅ 生成分析報告 (Markdown + JSON)
- ✅ 詳細文檔：note/GARMIN_ACTUAL_DATA_STRUCTURE.md

#### 實際找到的數據
1. **summarizedActivities.json** - 活動記錄 (2000+ 條)
2. **sleepData.json** - 睡眠數據 (100 條)
3. **personalRecord.json** - 個人紀錄 (10+ 條)

#### 路徑映射
```
DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json
DI_CONNECT/DI-Connect-Wellness/2024-05-15_2024-08-23_74303376_sleepData.json
DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_personalRecord.json
```

#### 時間戳格式
- Activities: 毫秒級 Unix 時間戳 (1584405978000)
- Sleep: ISO 8601 字符串 ("2024-05-14T15:41:04.0")
- Records: 文本格式 ("Sat Apr 11 16:00:00 GMT 2026")

---

### **任務 2：定義 3 個 Pydantic 數據模型**

**優先級：** ⭐⭐⭐⭐⭐ 最高  
**預計工時：** 3-4 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 1 完成

#### 目標
在 `app/models/` 中為 3 個實際 JSON 類型定義 Pydantic v2 模型，用於數據驗證和序列化。

#### 需要創建的 3 個模型

##### 1. **SummarizedActivity** - `app/models/activities.py`
活動記錄模型（2000+ 條數據）

**必要欄位：**
- `activityId: int` - 活動 ID
- `name: str` - 活動名稱
- `activityType: str` - 活動類型 (cycling, running, etc.)
- `startTimeGmt: int` - 開始時間（毫秒級）
- `duration: float` - 時長（毫秒）
- `distance: float` - 距離（米）
- `calories: float` - 熱量消耗

**可選欄位：**
- `elevationGain: Optional[float]` - 爬升高度（米）
- `elevationLoss: Optional[float]` - 下降高度（米）
- `avgSpeed: Optional[float]` - 平均速度 (m/s)
- `maxSpeed: Optional[float]` - 最大速度 (m/s)
- `startLatitude: Optional[float]` - 開始緯度
- `startLongitude: Optional[float]` - 開始經度
- `locationName: Optional[str]` - 地點名稱
- `deviceId: Optional[int]` - 設備 ID
- `lapCount: Optional[int]` - 圈數
- `favorite: Optional[bool]` - 收藏標記
- `pr: Optional[bool]` - 個人紀錄標記
- `minElevation: Optional[float]` - 最低高度
- `maxElevation: Optional[float]` - 最高高度

**時間戳處理：**
- 輸入：毫秒級 Unix 時間戳 (int)
- 輸出：UTC datetime (使用 @field_validator 轉換)

##### 2. **SleepData** - `app/models/sleep.py`
睡眠數據模型（100 條數據）

**必要欄位：**
- `sleepStartTimestampGMT: str` - 睡眠開始 (ISO 8601)
- `sleepEndTimestampGMT: str` - 睡眠結束 (ISO 8601)
- `calendarDate: str` - 日期 (YYYY-MM-DD)
- `deepSleepSeconds: int` - 深度睡眠（秒）
- `lightSleepSeconds: int` - 淺度睡眠（秒）
- `remSleepSeconds: int` - REM 睡眠（秒）
- `awakeSleepSeconds: int` - 覺醒時間（秒）

**可選欄位：**
- `averageRespiration: Optional[float]` - 平均呼吸
- `lowestRespiration: Optional[float]` - 最低呼吸
- `highestRespiration: Optional[float]` - 最高呼吸
- `awakeCount: Optional[int]` - 覺醒次數
- `avgSleepStress: Optional[float]` - 平均睡眠壓力
- `restlessMomentCount: Optional[int]` - 不安時刻數
- `sleepScores: Optional[dict]` - 睡眠評分 (10+ 維度)
- `spo2SleepSummary: Optional[dict]` - SPO2 摘要
- `unmeasurableSeconds: Optional[int]` - 無法測量時間
- `sleepWindowConfirmationType: Optional[str]` - 確認類型
- `retro: Optional[bool]` - 回溯標記
- `napList: Optional[list]` - 午睡列表

**時間戳處理：**
- 輸入：ISO 8601 字符串
- 輸出：UTC datetime (使用 @field_validator 解析)

##### 3. **PersonalRecord** - `app/models/records.py`
個人紀錄模型（10+ 條數據）

**必要欄位：**
- `personalRecordId: int` - 紀錄 ID
- `personalRecordType: str` - 紀錄類型 (e.g., "Best Half Marathon")
- `value: float` - 紀錄值
- `prStartTimeGMT: str` - 紀錄開始時間（文本格式）
- `createdDate: str` - 創建日期 (YYYY-MM-DD)

**可選欄位：**
- `activityId: Optional[int]` - 關聯活動 ID (0 表示無)
- `current: Optional[bool]` - 是否為當前紀錄
- `confirmed: Optional[bool]` - 是否已確認

**時間戳處理：**
- 輸入：文本格式 ("Sat Apr 11 16:00:00 GMT 2026")
- 輸出：UTC datetime (使用 @field_validator 解析)

#### 具體要求
- [ ] 使用 Pydantic v2 最新語法
- [ ] 所有時間戳欄位使用 datetime 類型（通過 @field_validator 轉換）
- [ ] 數值欄位使用 Annotated 添加範圍限制 (如 distance > 0)
- [ ] 使用 Field() 添加描述、示例、默認值
- [ ] 為可選欄位使用 Optional[Type] 或設定 default=None
- [ ] 實作 @field_validator 進行數據驗證
- [ ] 提供完整的 docstring
- [ ] 為每個模型編寫單元測試

#### 交付物
- 3 個完整的 Pydantic 模型文件
- 每個模型的單元測試 (tests/test_models.py)
- 模型驗證範例

#### 注意事項
- 時間戳轉換在任務 5 統一處理，這裡只定義欄位結構
- 單位轉換在任務 6 統一處理
- 使用 config 設置 validate_default=True, use_attribute_docstrings=True

---

### **任務 3：定義 3 個 SQLModel 資料庫模型**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 2-3 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 2 完成

#### 目標
將 3 個 Pydantic 模型升級為 SQLModel，使其可直接映射到 PostgreSQL 表。

#### Task 3 計劃概覽
- 將 `SummarizedActivity`、`SleepData`、`PersonalRecord` 三個現有模型轉成 SQLModel
- 為每個模型新增 `id` 主鍵、`user_id` 外鍵、`created_at` / `updated_at` 時間戳
- 設定 SQLModel 表名、複合索引、關聯關係以及表配置
- 建立資料庫遷移或初始化腳本，並撰寫對應測試

#### 需要創建的 3 個 SQLModel

| Pydantic 模型 | SQLModel 類 | 表名 | 主要索引 |
|-------------|-----------|------|--------|
| SummarizedActivity | SummarizedActivityDB | summarized_activities | (user_id, start_time_gmt) |
| SleepData | SleepDataDB | sleep_data | (user_id, calendar_date) |
| PersonalRecord | PersonalRecordDB | personal_records | (user_id, personal_record_type) |

#### 具體要求

**每個 SQLModel 需要添加：**

- [ ] 主鍵：`id: int = Field(primary_key=True)`
- [ ] 外鍵：`user_id: int = Field(foreign_key="user.id")`
- [ ] 時間戳：
  - `created_at: datetime = Field(default_factory=datetime.utcnow)`
  - `updated_at: datetime = Field(default_factory=datetime.utcnow)`
- [ ] 表配置：`table: str = "table_name"` (in Config class)
- [ ] 索引策略：複合索引 (user_id, date/timestamp)
- [ ] 關聯：SQLAlchemy relationship 到 User 表

**表定義示例：**
```python
class SummarizedActivityDB(SummarizedActivity, table=True):
    __tablename__ = "summarized_activities"
    
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 複合索引
    __table_args__ = (
        Index("idx_user_time", "user_id", "start_time_gmt"),
    )
```

#### 交付物
- 3 個完整的 SQLModel 定義文件
- 資料庫遷移腳本 (使用 Alembic 或手動 SQL)
- SQLModel 單元測試

#### 注意事項
- 保持 Pydantic 的驗證邏輯（使用 from_attributes=True）
- 時間戳自動管理由資料庫觸發器或應用層負責
- 外鍵關聯必須指向 User 表

---

### **任務 4：實作 ZIP 過濾函數**

**優先級：** ⭐⭐⭐⭐⭐ 最高  
**預計工時：** 2-3 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 1 完成

#### 目標
在 `app/services/parser.py` 中實作 `parse_garmin_zip()` 函數，安全高效地提取 3 個核心 JSON 檔。

#### 函數簽名
```python
def parse_garmin_zip(
    zip_path: str,
    target_jsons: List[str] = None
) -> Dict[str, dict]:
    """
    解析 Garmin ZIP，提取 3 個核心 JSON
    
    Args:
        zip_path: ZIP 檔路徑
        target_jsons: 要提取的 JSON 名稱列表（默認為全部 3 個）
    
    Returns:
        {
            "summarizedActivities": {...},
            "sleepData": {...},
            "personalRecords": {...}
        }
    
    Raises:
        FileNotFoundError: ZIP 不存在
        ValueError: ZIP 損壞
        KeyError: 核心 JSON 缺失
    """
```

#### 具體要求
- [ ] 使用實際檔案路徑（見 Task 1 的路徑映射）
- [ ] 流式解壓（不一次性載入全部）
- [ ] 只提取 3 個核心 JSON，忽略其他 200+ 檔案
- [ ] JSON 內容驗證 (json.loads)
- [ ] 返回 dict 格式
- [ ] 完整的日誌記錄和異常處理
- [ ] 性能：172 MB ZIP 應在 5 秒內完成

#### 交付物
- 完整的 `parse_garmin_zip()` 實現
- 單元測試（使用實際 ZIP 或 mock）

#### 實現提示
```python
# 核心文件路徑（來自 Task 1 分析）
CORE_JSON_PATHS = {
    "summarizedActivities": "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json",
    "sleepData": "DI_CONNECT/DI-Connect-Wellness/2024-05-15_2024-08-23_74303376_sleepData.json",
    "personalRecords": "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_personalRecord.json"
}
```

---

### **任務 5：實作時間戳正規化函數**

**優先級：** ⭐⭐⭐⭐⭐ 最高  
**預計工時：** 2-3 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 1 完成

#### 目標
在 `app/services/parser.py` 中實作時間戳正規化函數，處理 3 個不同的時間戳格式。

#### 函數簽名
```python
def normalize_timestamp(
    timestamp: Union[int, float, str],
    source_format: str = "auto",
    target_timezone: str = "UTC"
) -> datetime:
    """
    將 Garmin 時間戳轉換為統一的 UTC datetime
    
    Args:
        timestamp: 原始時間戳（可以是毫秒、秒或字符串）
        source_format: 源時間戳格式 ("auto", "seconds", "milliseconds", "date_str")
        target_timezone: 目標時區（默認 UTC）
    
    Returns:
        datetime 對象（UTC）
    
    Raises:
        ValueError: 無法解析時間戳
    """
```

#### 3 種時間格式

| 數據源 | 格式 | 例子 | 處理方法 |
|------|------|------|---------|
| summarizedActivities | 毫秒 Unix 時間戳 | `1715904000000` | ÷ 1000 + datetime.fromtimestamp() |
| sleepData | ISO 8601 字符串 | `"2024-05-15T22:30:00Z"` | fromisoformat() |
| personalRecords | 文本格式 | `"May 15, 2024"` | strptime('%b %d, %Y') |

#### 具體要求
- [ ] Activities（毫秒）：`int / 1000` → `datetime.fromtimestamp()`
- [ ] Sleep（ISO 8601）：使用 `datetime.fromisoformat()` 處理
- [ ] Records（文本）：使用 `datetime.strptime()` 解析
- [ ] 全部返回 UTC datetime
- [ ] 完整的異常處理
- [ ] 時區感知（設置為 UTC）
- [ ] 性能：應在毫秒級別內完成單個轉換

#### 交付物
- 完整的 `normalize_timestamp()` 函數
- 配套的單元測試（覆蓋邊界情況）

#### 注意事項
- 需要考慮 Garmin 設備的時區設置
- 不同 Garmin 產品的時間戳格式可能不同

---

### **任務 6：實作單位轉換函數**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 1-2 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 無

#### 目標
轉換 Garmin 數據的單位為國際標準單位（公里、km/h）。

#### 轉換規則

| 字段 | 原始單位 | 目標單位 | 公式 |
|------|---------|---------|------|
| distance | 米 | 公里 | × 0.001 |
| avgMovingSpeed | m/s | km/h | × 3.6 |
| maxMovingSpeed | m/s | km/h | × 3.6 |
| elevation | 米 | 米 | 無需轉換 |

#### 函數簽名
```python
def convert_units(value: float, unit_type: str) -> float:
    """
    轉換 Garmin 數據單位
    
    Args:
        value: 原始值
        unit_type: 單位類型 ("distance", "speed", "elevation")
    
    Returns:
        轉換後的值
    """
```

#### 具體要求
- [ ] 距離：米 → 公里（÷ 1000）
- [ ] 速度：m/s → km/h（× 3.6）
- [ ] 保留 2 位小數
- [ ] 處理 None 和 0 值
- [ ] 完整文檔

#### 交付物
- `app/services/parser.py` 中的 `convert_units()` 函數
- 單元測試

---

### **任務 7：實作 JSON 解析與驗證**

**優先級：** ⭐⭐⭐⭐⭐ 最高  
**預計工時：** 5-6 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 2, 3, 5, 6 完成

#### 目標
在 `app/services/parser.py` 中實作 `normalize_garmin_data()` 函數，將原始 Garmin JSON 轉換為驗證後的模型對象。

#### 函數簽名
```python
def normalize_garmin_data(
    raw_jsons: Dict[str, dict],
    user_id: int,
    target_unit_system: str = "metric"
) -> Dict[str, List[BaseModel]]:
    """
    將原始 Garmin JSON 轉換為標準化模型對象
    
    Args:
        raw_jsons: parse_garmin_zip() 的返回值
        user_id: 用戶 ID（用於外鍵關聯）
        target_unit_system: 目標單位系統 ("metric" 或 "imperial")
    
    Returns:
        {
            "summarized_activities": [SummarizedActivity(...), ...],
            "daily_summaries": [DailySummary(...), ...],
            ...
        }
    """
```

#### 具體要求
- [ ] 為每個 JSON 類型實作對應的解析函數：
  - `_parse_summarized_activities()`
  - `_parse_daily_summaries()`
  - `_parse_sleep_data()`
  - 等等（10 個）

- [ ] 對每個 JSON 元素進行：
  - 時間戳正規化（調用任務 5 的函數）
  - 單位轉換（調用任務 6 的函數）
  - Pydantic 驗證（通過 model_validate）

- [ ] 處理缺失和不規則數據：
  - 缺失必要欄位時，記錄警告但不中斷
  - 提供默認值（如 calories=0 等）
  - 過濾掉無效記錄（如未來日期）

- [ ] 異常處理和日誌：
  - 記錄每個 JSON 檔的解析進度
  - 統計跳過或修正的記錄數
  - 返回解析報告

- [ ] 性能：
  - 應能在 5 秒內處理 10000+ 條記錄

#### 交付物
- 完整的 `normalize_garmin_data()` 函數和 10 個子函數
- 解析報告模型（包含成功/失敗統計）
- 單元測試

#### 注意事項
- 某些欄位在不同 Garmin 版本中可能不存在
- 需要靈活處理缺失欄位

---

### **第二級：文本切片與向量化準備（任務 8-9）**
準備數據以供 Embedding 和 RAG 查詢使用。

---

### **任務 8：設計 Chunking 策略**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 2-3 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 7 完成

#### 目標
規劃和設計如何將結構化數據轉換為適合 Embedding 的文本段落。

#### 具體要求
- [ ] 定義全局 Chunking 參數：
  - **Chunk Size：** 建議 500-1000 tokens（約 2-4 KB 文本）
  - **Overlap：** 建議 10-20%（避免重要信息丟失）
  - **Separator：** "\n\n" 或 "\n" 等

- [ ] 為各 JSON 類型設計差異化策略：

  | 類型 | Chunk Size | Overlap | 策略 |
  |------|-----------|---------|------|
  | SummarizedActivity | 1000 tokens | 10% | 按活動類型分組 |
  | DailySummary | 500 tokens | 20% | 按週分組 |
  | SleepData | 300 tokens | 15% | 按睡眠階段分組 |
  | StressData | 200 tokens | 25% | 高頻率數據，多重疊 |
  | HeartRateData | 200 tokens | 25% | 時間序列數據 |
  | StepsData | 300 tokens | 20% | 日數據 |
  | CaloriesData | 300 tokens | 20% | 日數據 |
  | BodyComposition | 500 tokens | 10% | 低頻率，單條記錄 |
  | TrainingStatus | 600 tokens | 15% | 按訓練週期分組 |
  | PersonalRecord | 800 tokens | 5% | 重要記錄，低重疊 |

- [ ] 設計 Metadata 架構：
  ```python
  metadata = {
      "data_type": "sleep_data",  # JSON 類型
      "date": "2026-04-18",       # 記錄日期
      "time_range": "08:00-12:00", # 時間範圍（如適用）
      "chunk_index": 1,            # 同一記錄的 chunk 序號
      "total_chunks": 5,           # 該記錄的總 chunk 數
      "source_file": "sleepData.json",
      "user_id": 123,              # 用於查詢過濾
      "keywords": ["sleep", "light_sleep", "22:00-08:00"]  # 便於檢索
  }
  ```

- [ ] 定義文本格式模板（每種 JSON 類型一個）：
  - SummarizedActivity：日期、類型、距離、時間、卡路里等
  - DailySummary：日期、步數、熱量、活動時間等
  - 等等

- [ ] 考慮特殊情況：
  - 極長的記錄（如月度報告）
  - 極短的記錄
  - 包含多個活動的綜合數據

#### 交付物
- 詳細的 Chunking 策略文檔
- Metadata 架構定義
- 文本模板示例

#### 注意事項
- Chunk size 直接影響 Embedding 質量和成本
- Overlap 需要平衡重複 embedding 和信息完整性

---

### **任務 9：實作 Chunking 函數**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 4-5 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 7, 8 完成

#### 目標
在 `app/services/parser.py` 中實作 `chunk_garmin_data()` 函數，將結構化數據轉為可 embedding 的文本塊。

#### 函數簽名
```python
def chunk_garmin_data(
    normalized_data: Dict[str, List[BaseModel]],
    strategy: str = "default",
    chunk_configs: Dict = None
) -> List[Tuple[str, dict]]:
    """
    將標準化 Garmin 數據分割成文本 chunks
    
    Args:
        normalized_data: normalize_garmin_data() 的返回值
        strategy: chunking 策略 ("default", "time_series", "summary" 等)
        chunk_configs: 自定義配置 (覆蓋默認值)
    
    Returns:
        [(text, metadata), (text, metadata), ...]
    """
```

#### 具體要求
- [ ] 為每個 JSON 類型實作專用的 chunking 子函數：
  - `_chunk_activities()`
  - `_chunk_daily_summaries()`
  - `_chunk_sleep_data()`
  - 等等

- [ ] 文本生成邏輯：
  - 創建人類可讀的文本摘要
  - 包含關鍵指標和統計數據
  - 使用結構化格式（標題、列表等）

- [ ] 實現多種策略：
  - "default"：按任務 8 定義的標準策略
  - "time_series"：保留時間序列信息
  - "summary"：生成高級摘要
  - "detailed"：包含所有詳細信息

- [ ] Overlap 實現：
  - 確保相鄰 chunks 有重疊內容
  - 避免重要信息的丟失

- [ ] 為每個 chunk 附加 metadata：
  - 確保包含所有必要的上下文信息

- [ ] 性能優化：
  - 應能在 2 秒內處理 10000+ 條記錄

#### 交付物
- 完整的 `chunk_garmin_data()` 函數和子函數
- 文本模板集合
- 單元測試

#### 注意事項
- 文本質量直接影響 RAG 檢索效果
- 需要反覆調整和測試文本格式

---

### **第三級：集成與測試（任務 10-14）**
將所有組件集成並驗證整體流程。

---

### **任務 10：更新 requirements.txt**

**優先級：** ⭐⭐⭐ 中等  
**預計工時：** 1 小時  
**責任人：** （待分配）  
**狀態：** 未開始

#### 目標
取消註釋或添加第二步所需的 Python 依賴包。

#### 需要的依賴包
```
# 數據模型與數據庫
sqlmodel                  # SQLAlchemy + Pydantic 整合
sqlalchemy
psycopg2-binary
pgvector

# RAG 框架
langchain
langchain-community
langchain-anthropic (可選)
anthropic

# 數據處理
pandas
numpy
pydantic>=2.0
pydantic-settings

# 時間與時區
pytz
python-dateutil

# 測試
pytest
pytest-asyncio
pytest-mock
pytest-cov
```

#### 具體要求
- [ ] 取消註釋必要的依賴
- [ ] 檢查版本兼容性
- [ ] 添加新的依賴（如 pytz 等）
- [ ] 驗證無衝突依賴

#### 交付物
- 更新後的 requirements.txt
- 虛擬環境更新命令

---

### **任務 11：實作單元測試**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 6-8 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 2-9 完成

#### 目標
為 parser.py 的所有核心函數編寫全面的單元測試。

#### 需要測試的函數

1. **test_parse_garmin_zip()**
   - 正常 ZIP 檔解析
   - 損壞的 ZIP 檔
   - 缺失核心 JSON
   - 大型 ZIP 檔性能測試
   - 流式解壓

2. **test_normalize_timestamp()**
   - 秒級時間戳轉換
   - 毫秒級時間戳轉換
   - ISO 8601 字符串
   - 日期字符串
   - 缺失/None 值
   - 無效時間戳
   - 邊界情況（1970-01-01, 2038-01-19）
   - 時區轉換

3. **test_unit_conversion()**
   - 距離轉換
   - 速度轉換
   - 重量轉換
   - 溫度轉換
   - 能量轉換
   - 邊界值（0, 負數, 極大值）
   - 不支持的單位

4. **test_normalize_garmin_data()**
   - 各 JSON 類型的完整解析
   - 缺失欄位處理
   - 無效數據過濾
   - 單位轉換集成
   - 時間戳轉換集成
   - 錯誤統計

5. **test_chunk_garmin_data()**
   - 各種 chunking 策略
   - 文本質量檢查
   - Metadata 完整性
   - Overlap 檢查
   - 大量數據性能測試

#### 具體要求
- [ ] 使用 pytest 框架
- [ ] 為每個函數至少編寫 3-5 個測試用例
- [ ] 使用 mock 對象模擬 Garmin 數據
- [ ] 測試覆蓋率 >= 80%
- [ ] 創建 fixtures 以便重用測試數據
- [ ] 測試運行時間 < 30 秒（不含集成測試）

#### 交付物
- `tests/test_parser.py` 文件
- Mock 數據文件（`tests/fixtures/`）
- 測試覆蓋率報告

#### 注意事項
- Mock 數據應盡可能真實
- 需要驗證異常拋出

---

### **任務 12：整合到 API 端點**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 4-5 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 2-9 完成

#### 目標
在 `app/api/` 中建立上傳端點，集成 parser 的完整流程。

#### 需要創建的端點

1. **POST /api/v1/upload/garmin-zip**
   ```python
   @router.post("/upload/garmin-zip")
   async def upload_garmin_zip(
       file: UploadFile = File(...),
       current_user: User = Depends(get_current_user)
   ) -> dict:
       """
       上傳 Garmin ZIP 檔並進行解析
       """
   ```

   - 接收 ZIP 檔上傳
   - 驗證檔案類型和大小（建議 <= 1GB）
   - 調用 `parse_garmin_zip()`
   - 調用 `normalize_garmin_data()`
   - 調用 `chunk_garmin_data()`
   - 返回解析結果摘要

2. **GET /api/v1/upload/status/{upload_id}**
   - 查詢上傳和解析進度
   - 返回已處理的記錄數

#### 具體要求
- [ ] 創建 `UploadResponse` 和 `UploadStatusResponse` 模型
- [ ] 實現檔案驗證邏輯
- [ ] 添加錯誤處理和詳細的日誌記錄
- [ ] 返回清晰的解析報告
- [ ] 支持後台異步處理（使用 BackgroundTask）
- [ ] 添加 API 文檔 (docstring + OpenAPI)

#### 交付物
- 完整的上傳 API 路由
- 請求/響應模型定義
- 整合測試

#### 注意事項
- 後續階段會添加異步 Embedding 存儲
- 當前版本只需返回解析結果

---

### **任務 13：建立項目文檔**

**優先級：** ⭐⭐⭐ 中等  
**預計工時：** 3-4 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 1-12 完成

#### 目標
創建詳細的數據解析指南文檔，供團隊和用戶參考。

#### 文檔內容
建立 `docs/DATA_PARSING_GUIDE.md` 文件，包含：

1. **概述**
   - 解析流程整體架構
   - 10 個支持的 JSON 類型列表

2. **支持的 Garmin JSON 類型詳細說明**
   - 每個 JSON 類型的欄位清單
   - 示例數據
   - 數據范圍與限制

3. **解析流程架構圖**
   - ZIP 上傳 → 過濾 → 正規化 → 驗證 → Chunking
   - 各步驟的角色和職責

4. **模型欄位映射表**
   | JSON 類型 | Pydantic 模型 | 資料庫表 | 核心欄位 |
   |----------|------------|--------|--------|
   | ... | ... | ... | ... |

5. **單位和時間戳規範**
   - 內部統一的單位系統（公制）
   - 時間戳格式（UTC ISO 8601）
   - 單位轉換表

6. **Chunking 策略說明**
   - 各種類型的 chunking 參數
   - Metadata 架構
   - 文本模板示例

7. **常見問題解答**
   - 時間戳轉換常見錯誤
   - 單位混亂的排查
   - 缺失欄位的處理

8. **API 使用示例**
   ```bash
   curl -X POST http://localhost:8000/api/v1/upload/garmin-zip \
     -F "file=@garmin_export.zip" \
     -H "Authorization: Bearer <token>"
   ```

9. **性能指標**
   - 典型解析時間
   - 記憶體消耗
   - 向量化成本預估

10. **故障排查**
    - 常見錯誤訊息和解決方案
    - 日誌位置和解讀方法

#### 交付物
- `docs/DATA_PARSING_GUIDE.md` 文件
- 架構圖（可使用 Mermaid）
- 示例 JSON 檔案

#### 注意事項
- 文檔應清晰易懂
- 包含豐富的示例和圖表

---

### **任務 14：驗證與測試整體流程**

**優先級：** ⭐⭐⭐⭐ 很高  
**預計工時：** 4-5 小時  
**責任人：** （待分配）  
**狀態：** 未開始  
**依賴：** 任務 2-12 完成

#### 目標
使用實際或樣本 Garmin 數據進行端到端測試，驗證整個解析流程的正確性和性能。

#### 測試計劃

1. **數據準備**
   - [ ] 獲取真實 Garmin ZIP 樣本或創建樣本
   - [ ] 多個規模的測試數據（小、中、大）

2. **端到端流程測試**
   - [ ] 上傳 ZIP → 驗證接收
   - [ ] 過濾 → 驗證 10 個 JSON 都被提取
   - [ ] 解析 → 驗證所有記錄被正確解析
   - [ ] 正規化 → 驗證時間戳、單位轉換正確
   - [ ] Chunking → 驗證文本質量和 metadata

3. **數據質量檢查**
   - [ ] 檢查無數據丟失
   - [ ] 檢查異常值過濾正確
   - [ ] 檢查 metadata 完整性
   - [ ] 驗證 Chunk 大小在預期範圍

4. **性能測試**
   - [ ] 小型數據集（< 100 KB）：應在 1 秒完成
   - [ ] 中型數據集（1-10 MB）：應在 5 秒完成
   - [ ] 大型數據集（> 100 MB）：應在 30 秒完成
   - [ ] 記憶體峰值不應超過 500 MB

5. **錯誤場景測試**
   - [ ] 損壞的 ZIP 檔
   - [ ] 缺失必要 JSON 檔
   - [ ] 格式不規則的數據
   - [ ] 無效的時間戳
   - [ ] 不支持的單位

6. **API 集成測試**
   - [ ] 正常上傳流程
   - [ ] 文件驗證（大小、類型）
   - [ ] 響應格式驗證
   - [ ] 錯誤訊息清晰度

#### 具體要求
- [ ] 編寫集成測試腳本 (`tests/test_integration_parser.py`)
- [ ] 創建性能測試基準線
- [ ] 文檔記錄測試結果
- [ ] 確認所有測試通過後進入下一階段

#### 交付物
- 集成測試代碼
- 性能測試報告
- 測試結果文檔

#### 注意事項
- 需要獲取真實的 Garmin 數據進行測試
- 如果無法獲得，應創建逼真的模擬數據
- 性能基準應記錄在案

---

## 📊 **時間軸與里程碑**

| 任務 | 工時 | 依賴 | 計劃開始 | 計劃完成 |
|------|------|------|--------|--------|
| 1. 分析 ZIP 結構 | 2-3h | - | Week 1 | Week 1 |
| 2. ZIP 過濾函數 | 3-4h | T1 | Week 1 | Week 1 |
| 3. Pydantic 模型 | 4-5h | T1 | Week 1 | Week 2 |
| 4. SQLModel 模型 | 3-4h | T3 | Week 2 | Week 2 |
| 5. 時間戳函數 | 3-4h | T1 | Week 2 | Week 2 |
| 6. 單位轉換函數 | 2-3h | T1 | Week 2 | Week 2 |
| 7. 解析驗證 | 5-6h | T2-6 | Week 2 | Week 3 |
| 8. Chunking 策略 | 2-3h | T7 | Week 3 | Week 3 |
| 9. Chunking 函數 | 4-5h | T7-8 | Week 3 | Week 3 |
| 10. Requirements | 1h | T9 | Week 3 | Week 3 |
| 11. 單元測試 | 6-8h | T2-9 | Week 3-4 | Week 4 |
| 12. API 端點 | 4-5h | T2-9 | Week 4 | Week 4 |
| 13. 文檔 | 3-4h | T1-12 | Week 4 | Week 4 |
| 14. E2E 測試 | 4-5h | T2-12 | Week 4 | Week 4 |

**總計：** 約 50-65 小時開發工作

---

## ✅ **成功條件**

本階段完成的條件：

- [ ] 所有 14 個任務都標記為完成
- [ ] 單元測試覆蓋率 >= 80%
- [ ] 端到端測試通過
- [ ] 所有文檔完整
- [ ] 代碼通過 code review
- [ ] 性能指標達到預期

---

## 📝 **額外筆記**

- **版本控制：** 在 Git 中為各任務創建分支 (feature/parser-zip, feature/parser-models 等)
- **Code Review：** 每個關鍵任務完成後進行 code review
- **團隊溝通：** 每週召開進度同步會議
- **風險管理：** 如無法獲得真實 Garmin 數據，需提前創建樣本

---

**文檔版本：** 2.0 - 合併為單一演進文檔  
**最後更新：** 2026年4月18日

---

## 🎯 **Phase 2 基礎設施建設完成總結**

### **✅ 已完成的工作**

#### **1. 文件夾結構（11 個新文件夾）**
```
data/samples/              # 樣本 JSON 提取目錄 ✅
data/analysis/             # 分析結果輸出目錄 ✅
data/cache/                # 臨時緩存目錄 ✅
tests/fixtures/            # 測試 fixtures ✅
tests/fixtures/json/       # JSON 樣本文件 ✅
tests/integration/         # 集成測試 ✅
app/api/routers/           # API 路由 ✅
```

#### **2. Python 檔案框架（12 個）**
✅ `app/core/config.py`, `constants.py`, `database.py`  
✅ `app/models/base.py`  
✅ `app/api/schemas.py`, `dependencies.py`, `routers/__init__.py`  
✅ `tests/conftest.py`, `fixtures/garmin_samples.py`, `fixtures/user_fixtures.py`  
✅ `scripts/__init__.py`（已更新）

#### **3. 核心工具開發**
🔥 **`scripts/analyze_garmin_zip.py`** (~400 行)
- ✅ ZIP 結構掃描
- ✅ JSON 檔案檢測和深度分析
- ✅ 報告生成（JSON + Markdown）
- ✅ 樣本提取功能
- ✅ 完整日誌記錄

**使用方式：**
```bash
# 執行分析
python scripts/analyze_garmin_zip.py data/86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip --verbose --extract

# 查看結果
cat note/GARMIN_ZIP_ANALYSIS.md
ls -la data/samples/
```

#### **4. 文檔準備**
✅ `PROJECT_STRUCTURE_GUIDE.md` - 完整組織規範  
✅ 本文檔作為單一演進計劃

### **📊 統計資訊**
| 項目 | 數量 |
|------|------|
| 新增文件夾 | 11 個 |
| 新增 Python 檔案 | 12 個 |
| 新增代碼行數 | ~500 行 |
| 核心工具 (analyze_garmin_zip.py) | ~400 行 |

### **🚀 Task 1 準備完畢**
- 工具已實現
- 可立即執行：`python scripts/analyze_garmin_zip.py data/86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip --verbose --extract`
- 預期輸出：結構報告 + Markdown 分析 + 樣本 JSON

### **📋 文件清理**
以下快照文件已刪除（內容合併到此計劃文件）：
- ❌ PHASE2_COMPLETION_REPORT.md
- ❌ IMPLEMENTATION_CHECKLIST.md  
- ❌ FILE_STRUCTURE_CONFIRMATION.md

**理由：** 遵循新工作流 - 單一計劃文件全程演進，不創建新的狀態快照文件。

---

## 📝 **工作流方法論**

已建立 `note/skills/WORKING_METHODOLOGY.md` 文件，記錄：
- ✅ 單一計劃文件策略
- ✅ 進度更新方式
- ✅ 文件組織原則

---

## 🎯 **Task 1 完成 - 實際數據結構分析（2026-04-18）**

### **✅ 執行結果**

運行命令成功：
```bash
python scripts/analyze_garmin_zip.py data/86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip --verbose --extract
```

### **📊 實際找到的核心數據**

與計劃的 10 個預期 JSON 不同，實際只有 **3 個主要 JSON 檔**：

#### **1. summarizedActivities.json** ✅ 活動紀錄
- **路徑**：`DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json`
- **數據量**：包含多個活動記錄
- **主要欄位**：
  - `activityId`, `name`, `activityType`
  - `startTimeGmt`, `duration`, `distance`, `calories`
  - `elevationGain`, `elevationLoss`, `avgSpeed`, `maxSpeed`
  - `startLatitude`, `startLongitude`
  - `deviceId`, `lapCount`, `favorite`, `pr`
- **活動類型**：cycling, running 等
- **時間格式**：毫秒級 Unix 時間戳 (e.g., 1584405978000)

#### **2. sleepData.json** ✅ 睡眠數據
- **路徑**：`DI_CONNECT/DI-Connect-Wellness/2024-05-15_2024-08-23_74303376_sleepData.json`
- **數據量**：100 條睡眠記錄
- **主要欄位**：
  - 時間：`sleepStartTimestampGMT`, `sleepEndTimestampGMT`, `calendarDate`
  - 睡眠階段：`deepSleepSeconds`, `lightSleepSeconds`, `remSleepSeconds`, `awakeSleepSeconds`
  - 呼吸：`averageRespiration`, `lowestRespiration`, `highestRespiration`
  - SPO2：`spo2SleepSummary` (sub-object with averageSPO2, averageHR, lowestSPO2)
  - 評分：`sleepScores` (overallScore, qualityScore, durationScore, recoveryScore...)
  - 其他：`awakeCount`, `avgSleepStress`, `retro`
- **時間格式**：ISO 8601 字符串 (e.g., "2024-05-14T15:41:04.0")

#### **3. personalRecord.json** ✅ 個人紀錄
- **路徑**：`DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_personalRecord.json`
- **數據量**：包含多個個人紀錄（最佳成績、目標等）
- **主要欄位**：
  - `personalRecordId`, `activityId`
  - `personalRecordType`：e.g., "Best Half Marathon", "Most Steps in a Day", "Longest Goal Streak"
  - `value`：紀錄值
  - `prStartTimeGMT`：紀錄開始時間（字符串格式）
  - `createdDate`, `current`, `confirmed`
- **時間格式**：文本格式 (e.g., "Sat Apr 11 16:00:00 GMT 2026")

### **📋 缺失的文件**

以下 7 個預期文件在此 ZIP 中未找到：
- ❌ dailySummaries.json
- ❌ stressData.json
- ❌ heartRate.json
- ❌ steps.json
- ❌ calories.json
- ❌ bodyComposition.json
- ❌ trainingStatus.json

**原因**：此 ZIP 導出的用戶數據可能不完整，或僅包含部分數據類型

### **🎯 調整后的數據結構設計**

基於實際數據，重新定義要建立的模型：

#### **實際需要建立的 3 個模型**

1. **SummarizedActivityModel** - 活動記錄
   - 活動基本信息、時間、距離、高度、速度、熱量
   - 位置信息、設備信息

2. **SleepDataModel** - 睡眠數據
   - 睡眠時間段、各階段時長
   - 呼吸、SPO2、心率統計
   - 睡眠評分系統

3. **PersonalRecordModel** - 個人紀錄
   - 紀錄類型、數值、時間
   - 關聯活動 ID、當前/歷史狀態

#### **新任務分解**

根據實際數據調整後續任務：

| 原計劃 | 實際調整 | 說明 |
|------|--------|------|
| 10 個 Pydantic 模型 | 3 個 Pydantic 模型 | 只有 3 種數據類型 |
| 10 個 SQLModel | 3 個 SQLModel | 對應 3 種數據類型 |
| 14 個任務 | 8-10 個精簡任務 | 聚焦於實際數據 |
| ~50-65 工時 | ~25-35 工時 | 工作量減少約 50% |

### **⏭️ 下一步 - Task 2 開始**

準備以下工作：

1. **創建 3 個 Pydantic 模型**
   - `app/models/activities.py` - SummarizedActivityModel
   - `app/models/sleep.py` - SleepDataModel  
   - `app/models/records.py` - PersonalRecordModel

2. **實作 ZIP 過濾函數**
   - 修改 `parse_garmin_zip()` 以適應實際路徑
   - 過濾 3 個核心 JSON 檔

3. **實作時間戳正規化**
   - 毫秒級時間戳轉換
   - ISO 8601 字符串解析
   - 文本格式時間解析

4. **定義單位規範**
   - 距離：公里 (km)
   - 速度：公里/小時 (km/h)
   - 時間：秒 (s)

### **📊 數據量估計**

| 類型 | 數據量 | 備註 |
|------|--------|------|
| 活動記錄 | ~2000+ | 多年積累 |
| 睡眠記錄 | 100 | 2024年 5-8 月 |
| 個人紀錄 | 10+ | 多種類型紀錄 |


