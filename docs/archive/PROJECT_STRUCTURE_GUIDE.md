# Garmin RAG 項目 - 文件結構指南

**建立日期：** 2026年4月18日  
**目的：** 規範化項目文件組織，確保一致性和可維護性  
**適用版本：** Phase 2 及以後

---

## 📁 **完整項目結構**

```
garmin-rag-project/
├── app/                              # 🔴 核心應用代碼 (生產級)
│   ├── __init__.py
│   ├── main.py                       # FastAPI 應用入口
│   ├── api/                          # API 層 - REST 端點定義
│   │   ├── __init__.py
│   │   ├── dependencies.py           # 依賴注入（認證等）
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py             # POST /api/v1/upload/*
│   │   │   ├── query.py              # GET /api/v1/query/*
│   │   │   └── auth.py               # POST /api/v1/auth/*
│   │   └── schemas.py                # 請求/響應 Pydantic 模型
│   │
│   ├── core/                         # 核心配置層
│   │   ├── __init__.py
│   │   ├── config.py                 # 環境變數、設置
│   │   ├── constants.py              # 常量定義
│   │   └── database.py               # DB 連接、會話管理
│   │
│   ├── models/                       # 🟡 數據模型 (Pydantic + SQLModel)
│   │   ├── __init__.py
│   │   ├── base.py                   # 基礎模型（TimestampMixin 等）
│   │   ├── user.py                   # User 表模型
│   │   ├── garmin_core.py            # 共用的 Garmin 基礎字段
│   │   ├── garmin_activities.py      # SummarizedActivity, PersonalRecord
│   │   ├── garmin_health.py          # DailySummary, SleepData
│   │   ├── garmin_biometrics.py      # StressData, HeartRate, BodyComposition
│   │   ├── garmin_workload.py        # TrainingStatus, CaloriesData, StepsData
│   │   └── schemas.py                # 用於 API 的請求/響應模型
│   │
│   └── services/                     # 🟢 業務邏輯層 (核心工具)
│       ├── __init__.py
│       ├── parser.py                 # ⭐ ZIP 解析、正規化、chunking
│       ├── embedding.py              # Embedding 生成（Phase 3）
│       ├── rag_engine.py             # RAG 查詢引擎（Phase 3）
│       └── calendar.py               # Google Calendar 集成（Phase 3）
│
├── scripts/                          # 🟠 工具腳本 (一次性執行)
│   ├── __init__.py
│   ├── test_db_connection.py         # ✅ 驗證 DB 連接和 pgvector
│   ├── analyze_garmin_zip.py         # 📊 分析 ZIP 結構（Phase 2 任務1）
│   ├── extract_sample_jsons.py       # 📄 提取核心 JSON 樣本（Phase 2）
│   ├── generate_mock_garmin.py       # 🔧 生成 mock Garmin 數據（可選）
│   └── migrate_data.py               # 🗂️ 數據遷移工具（可選）
│
├── tests/                            # 🟣 測試代碼 (pytest)
│   ├── __init__.py
│   ├── conftest.py                   # Pytest 配置和全局 fixtures
│   ├── test_parser.py                # 🧪 parser.py 的單元測試
│   ├── test_models.py                # 🧪 models 的驗證測試
│   ├── test_api.py                   # 🧪 API 端點測試
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── garmin_samples.py         # Mock Garmin 數據樣本
│   │   ├── user_fixtures.py          # Mock User 對象
│   │   └── json/                     # 實際 JSON 樣本文件
│   │       ├── summarizedActivities.json
│   │       ├── dailySummaries.json
│   │       └── ...（其他 9 個核心 JSON）
│   └── integration/
│       ├── __init__.py
│       ├── test_end_to_end.py        # 端到端測試
│       └── test_performance.py       # 性能測試
│
├── data/                             # 📦 數據文件（不含源代碼）
│   ├── 86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip  # 原始 Garmin 導出
│   ├── samples/                      # 提取的核心 JSON 樣本
│   │   ├── summarizedActivities.json
│   │   ├── dailySummaries.json
│   │   └── ...
│   ├── analysis/                     # ZIP 分析結果輸出
│   │   ├── structure_report.json
│   │   └── field_mapping.json
│   └── cache/                        # 臨時緩存（.gitignore）
│       └── .gitkeep
│
├── note/                             # 📝 文檔和筆記
│   ├── plan/
│   │   └── plan for part 2.md        # Phase 2 詳細計劃
│   ├── DATABASE_SETUP_QUESTIONS.md   # DB 設置 Q&A
│   ├── SKILL_CREATE_PROBLEM_NOTES.md # 問題筆記模板
│   ├── PROJECT_STRUCTURE_GUIDE.md    # 👈 本文件
│   ├── GARMIN_ZIP_ANALYSIS.md        # ZIP 結構分析報告（自動生成）
│   └── DATA_PARSING_GUIDE.md         # 數據解析指南（Phase 2 任務13）
│
├── .git/                             # Git 版本控制
├── .gitignore                        # Git 忽略規則
├── docker-compose.yml                # Docker 容器編排
├── Dockerfile                        # Docker 鏡像構建
├── requirements.txt                  # Python 依賴包清單
└── rag.venv/                         # Python 虛擬環境（本地開發）

```

---

## 🎯 **各文件夾的職責**

### **1️⃣ `app/` - 核心應用代碼（生產級）**

**職責：** 包含所有可在生產環境中使用的業務邏輯  
**特點：** 
- 經過測試的代碼
- 遵循設計模式
- 文檔完整
- 易於維護和擴展

#### **`app/main.py`**
- FastAPI 應用初始化
- 註冊所有 routes
- 中間件配置
- 生命週期事件處理
- 全局異常處理

#### **`app/core/`**
```python
config.py       # 環境變數、設置類
constants.py    # 常量（單位、日期格式等）
database.py     # SQLAlchemy 引擎、連接池配置
```

#### **`app/models/`**
```
組織方式（按領域分組）：
├─ base.py                  # 基類、Mixin
├─ user.py                  # User 表 (外鍵關聯點)
├─ garmin_core.py          # 共用字段、時間戳 mixin
├─ garmin_activities.py    # 活動相關 (SummarizedActivity, PersonalRecord)
├─ garmin_health.py        # 健康相關 (DailySummary, SleepData)
├─ garmin_biometrics.py    # 生物特徵 (StressData, HeartRate, BodyComposition)
├─ garmin_workload.py      # 工作負載 (TrainingStatus, CaloriesData, StepsData)
└─ schemas.py              # API 請求/響應 (不含 SQLModel)
```

**命名規則：** 
- SQLModel 類名：`PascalCase`（如 `SummarizedActivity`）
- 資料庫表名：`snake_case`（如 `summarized_activities`）
- Pydantic schema：`{Model}Request`、`{Model}Response`

#### **`app/services/`**

| 文件 | 職責 | 階段 |
|------|------|------|
| `parser.py` | ZIP 解析、正規化、chunking | Phase 2 ⭐ |
| `embedding.py` | 向量化、存儲 | Phase 3 |
| `rag_engine.py` | RAG 查詢、檢索 | Phase 3 |
| `calendar.py` | Google Calendar API | Phase 3 |

#### **`app/api/`**

```python
routers/
├─ upload.py    # POST /api/v1/upload/garmin-zip
├─ query.py     # GET /api/v1/query/ask
└─ auth.py      # POST /api/v1/auth/login

schemas.py      # 所有 API 的 Pydantic 模型
dependencies.py # 依賴注入（get_current_user 等）
```

---

### **2️⃣ `scripts/` - 工具腳本（一次性執行）**

**職責：** 包含開發/維護工具，**不在生產環境運行**  
**特點：**
- 可執行的頂級腳本
- 可直接用 `python scripts/xxx.py` 執行
- 包含 `if __name__ == "__main__":`

#### **分類和用途**

| 腳本 | 用途 | 執行頻率 | 依賴 |
|------|------|--------|------|
| `test_db_connection.py` | ✅ DB 連接驗證、pgvector 檢查 | 首次設置 | DB 已運行 |
| `analyze_garmin_zip.py` | 📊 分析 ZIP 結構（Phase 2 任務1） | Phase 2 開始 | data/ZIP |
| `extract_sample_jsons.py` | 📄 提取核心 JSON（Phase 2） | Phase 2 進行中 | data/ZIP |
| `generate_mock_garmin.py` | 🔧 生成 mock 數據用於測試 | 可選 | - |
| `migrate_data.py` | 🗂️ 數據遷移、初始化 | 需要時 | DB |

#### **標準模板**

```python
#!/usr/bin/env python3
"""
腳本說明：該腳本用於什麼目的

用法：
    python scripts/xxx.py [參數]

示例：
    python scripts/analyze_garmin_zip.py data/sample.zip
"""

import sys
import logging
from pathlib import Path

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函數"""
    pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
```

---

### **3️⃣ `tests/` - 測試代碼**

**職責：** 單元測試、集成測試、性能測試  
**特點：** 使用 pytest，應有 >= 80% 覆蓋率

#### **目錄結構**

```
tests/
├── conftest.py                    # ⭐ Pytest 全局配置
├── fixtures/
│   ├── garmin_samples.py         # Mock Garmin 數據生成函數
│   ├── user_fixtures.py          # Mock User 對象
│   └── json/                     # 實際 JSON 樣本文件
├── test_parser.py                # parser.py 的所有測試
├── test_models.py                # 模型驗證測試
├── test_api.py                   # API 端點測試
└── integration/
    ├── test_end_to_end.py        # 完整流程測試
    └── test_performance.py       # 性能基準測試
```

#### **命名規則**
- 測試文件：`test_*.py`
- 測試函數：`test_*`
- Fixture：統一在 `conftest.py` 中定義
- Mock 數據：在 `fixtures/` 中定義

#### **執行方式**

```bash
# 運行所有測試
pytest

# 運行特定文件
pytest tests/test_parser.py

# 運行特定測試函數
pytest tests/test_parser.py::test_parse_garmin_zip

# 顯示覆蓋率
pytest --cov=app

# 顯示詳細輸出
pytest -v
```

---

### **4️⃣ `data/` - 數據文件（非源代碼）**

**職責：** 存儲 ZIP 檔、提取的 JSON、分析結果  
**特點：** 不含源代碼，應添加到 `.gitignore`

#### **子文件夾**

```
data/
├── 86bcef42-5dc6-415d-b186-49715dc89d2f_1.zip
│   └── 原始 Garmin 導出檔（約 200-500 MB）
│
├── samples/
│   ├── summarizedActivities.json
│   ├── dailySummaries.json
│   ├── sleepData.json
│   ├── stressData.json
│   ├── heartRate.json
│   ├── steps.json
│   ├── calories.json
│   ├── bodyComposition.json
│   ├── trainingStatus.json
│   └── personalRecord.json
│
├── analysis/
│   ├── structure_report.json      # ZIP 結構分析結果
│   └── field_mapping.json         # 欄位映射表
│
└── cache/
    └── .gitkeep
```

#### **.gitignore 規則**

```
# 數據文件（不追蹤）
data/
!data/.gitkeep
!data/README.md
!data/samples/

# 虛擬環境
rag.venv/

# IDE
.vscode/
.idea/
*.pyc
__pycache__/

# 環境變數
.env
.env.local
```

---

### **5️⃣ `note/` - 文檔和筆記**

**職責：** 記錄設計決策、分析結果、指南  
**特點：** Markdown 格式，與代碼同步更新

#### **文件清單**

| 文件 | 內容 | 更新頻率 |
|------|------|--------|
| `PROJECT_STRUCTURE_GUIDE.md` | 👈 本文件 - 文件夾結構指南 | 少更新 |
| `GARMIN_ZIP_ANALYSIS.md` | ZIP 結構分析報告（自動生成） | Phase 2 任務1 |
| `DATA_PARSING_GUIDE.md` | 數據解析指南 | Phase 2 任務13 |
| `DATABASE_SETUP_QUESTIONS.md` | ✅ DB 設置 Q&A | 偶爾 |
| `SKILL_CREATE_PROBLEM_NOTES.md` | ✅ 問題筆記模板 | 參考 |
| `plan/plan for part 2.md` | ✅ Phase 2 完整計劃 | 偶爾 |

---

## ✅ **文件創建一致性檢查表**

### **創建新文件時遵循的規則**

- [ ] **位置正確**：根據上表放在對應文件夾
- [ ] **名稱規則**：遵循 snake_case (Python) 或 kebab-case (文檔)
- [ ] **文件頭部**：包含 docstring 說明用途
- [ ] **編碼**：UTF-8，換行符 LF（Unix）
- [ ] **導入順序**：標準庫 → 第三方 → 本地導入，空行分隔
- [ ] **Docstring**：遵循 Google 或 NumPy 風格
- [ ] **類型提示**：Python 文件應使用類型提示
- [ ] **許可證**（可選）：如有公司規則，添加到文件頭

### **Python 文件模板**

```python
"""
模塊說明：簡短的單行描述

詳細說明（可選）：
    更長的多行說明，說明該模塊的用途、設計決策等

Author: （可選）
Date: （可選）
Version: 1.0
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MyClass:
    """類的簡短說明"""
    
    def method(self) -> str:
        """方法說明"""
        pass


if __name__ == "__main__":
    # 執行示例（腳本文件）
    pass
```

### **Markdown 文件模板**

```markdown
# 標題

**建立日期：** YYYY年M月D日
**目的：** 簡短說明
**狀態：** 草稿/進行中/完成

---

## 📌 概述

... 內容 ...

---

**最後更新：** YYYY年M月D日
```

---

## 📊 **Phase 2 文件創建清單**

| 優先級 | 文件 | 位置 | 責任 | 狀態 |
|------|------|------|------|------|
| ⭐⭐⭐⭐⭐ | `analyze_garmin_zip.py` | `scripts/` | Task 1 | ❌ 待建 |
| ⭐⭐⭐⭐⭐ | `garmin_*.py` (5 個) | `app/models/` | Task 3-4 | ❌ 待建 |
| ⭐⭐⭐⭐⭐ | `parser.py` (完整) | `app/services/` | Task 2-7 | ❌ 待完成 |
| ⭐⭐⭐⭐ | `test_parser.py` | `tests/` | Task 11 | ❌ 待建 |
| ⭐⭐⭐⭐ | `GARMIN_ZIP_ANALYSIS.md` | `note/` | Task 1 輸出 | ❌ 待建 |
| ⭐⭐⭐ | `DATA_PARSING_GUIDE.md` | `note/` | Task 13 | ❌ 待建 |

---

## 🎯 **最佳實踐**

### **1. 導入組織**

```python
# ✅ 正確
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.core.config import settings
from app.models.base import TimestampMixin
```

### **2. 類型提示**

```python
# ✅ 推薦
def parse_zip(
    zip_path: str,
    target_jsons: Optional[List[str]] = None
) -> Dict[str, dict]:
    """解析 ZIP 檔"""
    pass

# ❌ 不推薦
def parse_zip(zip_path, target_jsons=None):
    pass
```

### **3. Docstring 格式**

```python
def normalize_timestamp(
    timestamp: Union[int, float, str],
    source_format: str = "auto"
) -> datetime:
    """
    將 Garmin 時間戳轉換為 UTC datetime
    
    Args:
        timestamp: 原始時間戳
        source_format: 源格式 ("auto", "seconds", "milliseconds")
    
    Returns:
        datetime 對象
    
    Raises:
        ValueError: 無法解析時間戳
    
    Examples:
        >>> normalize_timestamp(1704067200)
        datetime(2024, 1, 1, 0, 0, 0)
    """
    pass
```

### **4. 常量定義**

```python
# app/core/constants.py

# Garmin 核心 JSON 檔案清單
GARMIN_CORE_JSONS = [
    "summarizedActivities.json",
    "dailySummaries.json",
    "sleepData.json",
    "stressData.json",
    "heartRate.json",
    "steps.json",
    "calories.json",
    "bodyComposition.json",
    "trainingStatus.json",
    "personalRecord.json",
]

# 內部單位規範
INTERNAL_UNITS = {
    "distance": "km",
    "speed": "km/h",
    "weight": "kg",
    "temperature": "celsius",
    "energy": "kcal",
}

# 時間戳格式
TIMESTAMP_FORMAT_UTC = "%Y-%m-%dT%H:%M:%SZ"
```

---

## 🔧 **關於 `test_db_connection.py`**

### ✅ **正確位置：`scripts/test_db_connection.py`**

**理由：**
1. 這是一個**一次性執行**的設置驗證工具
2. 不需要在應用運行時調用
3. 遵循與其他設置工具相同的模式
4. 可以直接用 `python scripts/test_db_connection.py` 執行

### **使用場景**

```bash
# 1. 首次 Docker 啟動後，驗證 DB 連接
python scripts/test_db_connection.py

# 2. 如果有 DB 連接問題，執行此腳本排查
python scripts/test_db_connection.py --verbose

# 3. 驗證 pgvector 擴展
python scripts/test_db_connection.py --check-pgvector
```

### **改進建議**

可以將 `test_db_connection.py` 改進為支持更多選項：

```python
# scripts/test_db_connection.py

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--check-pgvector", action="store_true")
    parser.add_argument("--list-tables", action="store_true")
    args = parser.parse_args()
    
    if args.check_pgvector:
        check_pgvector()
    if args.list_tables:
        list_tables()
```

---

## 📋 **下一步行動**

1. **✅ 確認本文檔** - 是否滿足你的需求？
2. **🔄 開始 Phase 2 任務1** - 創建 `scripts/analyze_garmin_zip.py`
3. **📝 生成分析報告** - 保存到 `note/GARMIN_ZIP_ANALYSIS.md`
4. **🗂️ 組織文件夾** - 建立 `data/samples/` 等必要目錄
5. **🧪 開始建立模型** - 在 `app/models/` 中創建 `garmin_*.py`

---

**文檔版本：** 1.0  
**最後更新：** 2026年4月18日
