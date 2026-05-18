# SQL Models & Parser 函数详解与数据处理最佳实践

## 📋 目录
1. [SQL Models 架构说明](#1-sql-models-架构说明)
2. [Parser 函数详解](#2-parser-函数详解)
3. [命名规范与设计哲学](#3-命名规范与设计哲学)
4. [数据处理函数的陷阱与注意事项](#4-数据处理函数的陷阱与注意事项)

---

## 1. SQL Models 架构说明

### 📊 整体设计思路

```python
# SQLModel = SQLAlchemy + Pydantic v2
# 优点：
# ✅ 单一数据定义，既可用于数据库，也可用于API验证
# ✅ 自动生成SQL表
# ✅ 内置字段验证
# ✅ 类型安全
```

### 🏗️ 核心类解析

#### **1. User 表（基础表）**

```python
class User(SQLModel, table=True):
    __tablename__ = "users"  # 显式表名
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(default="", index=True)  # 索引加速查询
```

**为什么这样设计：**
- `table=True` → SQLModel 自动创建表定义
- `primary_key=True` → 数据库主键
- `Optional[int]` + `default=None` → 新插入时自动生成ID
- `index=True` → 为 email 添加索引（常用查询列）

**实际用途：** 所有 Activity、Sleep、PersonalRecord 都通过 `user_id` 外键关联到这个表

---

#### **2. SummarizedActivityDB（活动表）**

```python
class SummarizedActivityDB(SQLModel, table=True):
    __tablename__ = "summarized_activities"
    __table_args__ = (
        Index("idx_activity_user_start", "user_id", "start_time_in_seconds"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    activity_id: int = Field(..., description="...", ge=1)  # ge = greater_equal
    start_time_in_seconds: int = Field(..., ge=0, index=True)
    distance: int = Field(..., ge=0)  # 米
    avg_moving_speed: float = Field(..., ge=0.0)  # m/s
```

**核心设计决策：**

| 设计 | 理由 | 效果 |
|------|------|------|
| `__table_args__` | 复合索引 | 查询 `WHERE user_id = ? AND start_time_in_seconds > ?` 快100倍 |
| `user_id: int` + `foreign_key` | 外键约束 | 防止孤立数据，维护数据完整性 |
| `Field(..., ge=1)` | 验证约束 | activity_id 必须 ≥ 1（拒绝无效值） |
| `start_time_in_seconds` | 毫秒为单位 | Garmin 原始格式，避免转换损失 |
| `avg_moving_speed` | float，m/s | 保留小数点精度，原始单位 |
| `created_at/updated_at` | 审计字段 | 追踪数据变更，支持时间戳查询 |

**字段设计模式：**
```python
# ✅ 好做法：保存原始单位
distance: int = Field(..., description="Distance in meters", ge=0)
avg_speed: float = Field(..., description="Speed in m/s", ge=0.0)

# ❌ 不好做法：丢失精度
distance_km: str = Field(...)  # 应该用 float，不要 str
```

---

#### **3. SleepDataDB（睡眠表）**

```python
class SleepDataDB(SQLModel, table=True):
    __table_args__ = (
        Index("idx_sleep_user_date", "user_id", "calendar_date"),
    )
    
    calendar_date: str = Field(..., description="YYYY-MM-DD format", min_length=10)
    deep_sleep_seconds: int = Field(..., ge=0)  # 秒数
    light_sleep_seconds: int = Field(..., ge=0)
    average_heart_rate: Optional[float] = Field(default=None, ge=0.0)
    overall_sleep_score: Optional[int] = Field(default=None, ge=0, le=100)
```

**特殊考量：**

| 字段 | 设计 | 原因 |
|------|------|------|
| `calendar_date` | str | 便于按日期查询、分组、排序 |
| `sleep_start_timestamp_gmt` | str ISO 8601 | 保持原始数据完整性 |
| `deep_sleep_seconds` | int | 精度足够（秒级），比 float 更快 |
| `overall_sleep_score` | Optional[int] 0-100 | 可能没有分数，范围限制 |
| `le=100` 验证 | 最大值约束 | 数据库级别防止垃圾数据 |

---

#### **4. PersonalRecordDB（个人纪录表）**

```python
class PersonalRecordDB(SQLModel, table=True):
    personal_record_id: int = Field(..., description="...", ge=1)
    personal_record_type: str = Field(..., min_length=1)
    value: float = Field(..., gt=0.0)  # gt = greater_than（不允许0）
    record_unit: str = Field(..., min_length=1)  # "km", "second", etc.
    record_date: str = Field(..., min_length=1)  # 文本日期
```

**设计特点：**
- `value: float` + `gt=0.0` → 拒绝0或负数（不合理的记录）
- `record_unit` → 单位可变，需要配合解析
- `record_date` → 文本格式（多种日期格式支持）

---

### 🔑 关键模式总结

```python
# ✅ 模式1：主键设计
id: Optional[int] = Field(default=None, primary_key=True)
# 为什么 Optional？→ 新插入行时 id 为 None，数据库自动生成

# ✅ 模式2：外键关系
user_id: int = Field(foreign_key="users.id", index=True)
# 两个 index：foreign_key 本身会建立索引，+ 显式 index 用于 JOIN 加速

# ✅ 模式3：复合索引（重要！）
__table_args__ = (
    Index("idx_activity_user_start", "user_id", "start_time_in_seconds"),
)
# 目的：WHERE user_id = X AND start_time > Y 的查询极快

# ✅ 模式4：范围验证
field: int = Field(..., ge=0, le=100)
# ge/le/gt/lt 在数据库层面防止垃圾数据

# ✅ 模式5：可选字段
avg_heart_rate: Optional[float] = Field(default=None, ge=0.0)
# None 意味着数据缺失（可以为空），但如果有值必须 ≥ 0

# ✅ 模式6：审计字段
created_at: datetime = Field(default_factory=datetime.utcnow)
updated_at: datetime = Field(default_factory=datetime.utcnow)
# 跟踪数据生命周期，default_factory 每次调用生成新值
```

---

## 2. Parser 函数详解

### 🔄 处理流程概览

```
Garmin ZIP
    ↓
parse_garmin_zip()          [Task 4] ZIP 提取 + 关键词匹配
    ↓
camel_to_snake()            键名转换
normalize_json_keys()       递归转换 + 类型保持
    ↓
normalize_timestamp()       [Task 5] 时间戳统一→UTC
    ↓
convert_*()                 [Task 6] 单位转换
    ↓
数据库就绪
```

---

### 🔧 核心函数分析

#### **1. camel_to_snake(value: str) → str**

```python
def camel_to_snake(value: str) -> str:
    """Convert camelCase / PascalCase keys to snake_case."""
    if not isinstance(value, str):      # ⚠️ 防守性编程
        return value
    
    # 第1步：替换特殊字符
    value = value.replace("-", "_").replace(" ", "_")
    
    # 第2步：处理 camelCase
    # 正则表达式: (.)([A-Z][a-z]+)
    # 匹配例子: activityType → activity + Type → activity_Type
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    
    # 第3步：处理 acronyms (连续大写字母)
    # 例子: activityID → activity_ID
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    
    # 第4步：全部小写
    return value.lower()
```

**为什么这样设计？**

| 步骤 | 输入 | 输出 | 目的 |
|------|------|------|------|
| 原始 | activityType | activityType | - |
| 第1步 | activity-type | activity_type | 统一分隔符 |
| 第2步 | activityType | activity_Type | 插入分隔符 |
| 第3步 | activity_Type | activity_Type | 处理连续大写 |
| 第4步 | activity_Type | activity_type | 数据库标准 |

**测试覆盖：**
```python
camel_to_snake("activityId") → "activity_id"
camel_to_snake("startTimeInSeconds") → "start_time_in_seconds"
camel_to_snake("ID") → "id"
camel_to_snake("HTTPSConnection") → "https_connection"
```

---

#### **2. normalize_json_keys(value: Any) → Any**

```python
def normalize_json_keys(value: Any) -> Any:
    """Recursively normalize dictionary keys."""
    if isinstance(value, dict):
        # 递归：字典的每个 key 转换，每个 value 也递归处理
        return {camel_to_snake(k): normalize_json_keys(v) 
                for k, v in value.items()}
    
    if isinstance(value, list):
        # 递归：列表中每个元素递归处理
        return [normalize_json_keys(item) for item in value]
    
    return value  # 基础类型（str/int/float）直接返回
```

**为什么递归？**

```python
# 输入：嵌套 JSON
{
    "activityId": 123,
    "activityType": {
        "typeId": 1,
        "typeKey": "cycling"
    },
    "lapMetrics": [
        {"lapTimeSeconds": 60},
        {"lapTimeSeconds": 65}
    ]
}

# 输出：完全转换
{
    "activity_id": 123,
    "activity_type": {
        "type_id": 1,
        "type_key": "cycling"
    },
    "lap_metrics": [
        {"lap_time_seconds": 60},
        {"lap_time_seconds": 65}
    ]
}
```

**处理流程：**
1. 顶层字典 → 转换所有 key
2. 遇到嵌套字典 → 递归调用
3. 遇到列表 → 遍历每个元素，递归处理
4. 遇到基础类型 → 直接返回，不改变值

---

#### **3. _match_core_key(file_name: str, target_keys) → Optional[str]**

```python
def _match_core_key(file_name: str, target_keys: Iterable[str]) -> Optional[str]:
    """匹配 ZIP 内文件到 Garmin 核心类型"""
    
    # 正规化路径（统一分隔符）
    normalized_file_name = file_name.replace("\\", "/").lower()
    
    # 遍历目标类型
    for key in target_keys:
        suffix = CORE_JSON_SUFFIXES.get(key, "").lower()
        if suffix and normalized_file_name.endswith(suffix):
            return key  # 找到匹配
    
    return None  # 不匹配
```

**为什么这样设计？**

```python
# Garmin ZIP 中文件路径可能：
# Windows: DI_CONNECT\DI-Connect-Fitness\...\summarizedActivities.json
# Unix:    DI_CONNECT/DI-Connect-Fitness/.../sleepData.json

# 我们只关心文件名后缀，不关心前面的路径
# 所以用 endswith() 而不是完全路径匹配

# 实际路径可能包含时间戳或用户ID：
# a850132a@gmail.com_4004_summarizedActivities.json
# 2024-05-15_2024-08-23_74303376_sleepData.json
# a850132a@gmail.com_personalRecord.json

# 这三个都正确匹配到各自类型
```

---

#### **4. parse_garmin_zip() - 核心函数**

```python
def parse_garmin_zip(
    zip_path: str,
    target_jsons: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    核心ZIP解析逻辑
    """
    
    # ✅ 步骤1：输入验证
    path = Path(zip_path)
    if not path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")
    
    # ✅ 步骤2：设定目标
    if target_jsons is None:
        target_jsons = DEFAULT_GARMIN_TARGETS  # ["summarizedActivities", "sleepData", "personalRecords"]
    
    # 只保留有效目标
    selected_targets = [key for key in target_jsons if key in CORE_JSON_SUFFIXES]
    if not selected_targets:
        raise ValueError("No valid target_jsons provided")
    
    extracted: Dict[str, Dict[str, Any]] = {}
    
    # ✅ 步骤3：打开 ZIP 并迭代
    with zipfile.ZipFile(path, "r") as archive:
        for member in archive.infolist():
            # 跳过目录
            if member.is_dir():
                continue
            
            # 尝试匹配文件类型
            core_key = _match_core_key(member.filename, selected_targets)
            
            # 跳过不匹配或已提取的文件
            if core_key is None or core_key in extracted:
                continue
            
            # ✅ 步骤4：读取、解析、规范化
            with archive.open(member, "r") as file_obj:
                raw_data = file_obj.read()  # bytes
                payload = json.loads(raw_data.decode("utf-8"))  # dict
                extracted[core_key] = normalize_json_keys(payload)  # 键转换
    
    # ✅ 步骤5：验证完整性
    missing = [key for key in selected_targets if key not in extracted]
    if missing:
        raise KeyError(f"Missing Garmin JSON files in ZIP: {missing}")
    
    return extracted
```

**设计决策说明：**

| 设计 | 理由 |
|------|------|
| `Path.exists()` 检查 | 提前失败，清晰的错误信息 |
| `with zipfile.ZipFile()` | 自动关闭资源，即使发生错误 |
| `if member.is_dir()` 过滤 | 目录不是文件，跳过 |
| `extracted[core_key]` 检查 | 防止文件重复处理 |
| 最后验证 `missing` | 确保 3 个核心文件都存在 |

---

#### **5. normalize_timestamp() - 多格式处理**

```python
def normalize_timestamp(timestamp_value: Any) -> Optional[datetime]:
    """
    三种 Garmin 时间戳格式 → UTC datetime
    """
    
    if timestamp_value is None:
        return None
    
    # ============ 格式1：Unix 毫秒 (Activities) ============
    if isinstance(timestamp_value, (int, float)):
        try:
            return datetime.fromtimestamp(
                timestamp_value / 1000,  # 转换毫秒→秒
                tz=timezone.utc          # 明确 UTC 时区
            )
        except (ValueError, TypeError):
            pass  # 尝试下一个格式
    
    if isinstance(timestamp_value, str):
        # ============ 格式2：ISO 8601 (Sleep) ============
        try:
            iso_str = timestamp_value
            
            # 处理 ".0" 后缀（Garmin特有）
            if iso_str.endswith('.0'):
                iso_str = iso_str[:-2]  # "2024-05-14T15:41:04.0" → "2024-05-14T15:41:04"
            
            # 处理 Z 后缀
            if iso_str.endswith('Z'):
                # "2024-05-14T15:41:04Z" → "2024-05-14T15:41:04+00:00"
                return datetime.fromisoformat(iso_str[:-1] + '+00:00')
            else:
                # 没有时区 → 假定 UTC
                return datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
        
        # ============ 格式3：文本日期 (Personal Records) ============
        text_date_formats = [
            '%B %d, %Y',                    # "May 15, 2024"
            '%Y-%m-%d',                     # "2024-05-15"
            '%a %b %d %H:%M:%S %Z %Y',     # "Sat Apr 11 16:00:00 GMT 2026"
            '%m/%d/%Y',                     # "05/15/2024"
            '%d-%b-%Y',                     # "15-May-2024"
        ]
        
        for fmt in text_date_formats:
            try:
                dt = datetime.strptime(timestamp_value, fmt)
                # 显式设置 UTC（因为 strptime 的 %Z 通常不生成 tzinfo）
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue  # 尝试下一个格式
    
    # 都失败了
    return None
```

**为什么这样逐个尝试？**

```python
# Garmin 数据来自不同源，格式不一致：

# 活动数据：Unix 毫秒
1715904000000

# 睡眠数据：ISO 8601
"2024-05-14T15:41:04.0Z"

# 个人记录：各种文本格式
"May 15, 2024"
"Sat Apr 11 16:00:00 GMT 2026"

# 解决方案：Try-Except-Continue 模式
# ✅ 如果一个格式失败，自动尝试下一个
# ✅ 最后都失败 → 返回 None（不抛错）
```

---

#### **6. 单位转换函数（Task 6）**

```python
def convert_distance_meters_to_km(distance_m: Optional[float]) -> Optional[float]:
    """
    为什么这样设计？
    """
    # ✅ 防守性编程：处理 None
    if distance_m is None:
        return None
    
    try:
        # ✅ 强制转为 float（可能输入是字符串）
        return float(distance_m) / 1000.0
    except (ValueError, TypeError):
        # ✅ 无效输入 → 返回 None，不抛错
        return None
```

**为什么返回 None 而不是抛错？**

```python
# 场景1：缺失数据
distance = None
km = convert_distance_meters_to_km(distance)
# ✅ 返回 None，允许继续处理其他数据
# ❌ 抛错 → 整个数据行处理失败

# 场景2：数据质量问题
distance = "invalid"
km = convert_distance_meters_to_km(distance)
# ✅ 返回 None，可以对整批数据标记
# ❌ 抛错 → 需要捕捉异常，复杂

# 在 ETL 场景中：宽容优于严格
```

---

## 3. 命名规范与设计哲学

### 📛 命名规范

#### **SQL Model 命名**

```python
# ✅ 好：
class SummarizedActivityDB(SQLModel, table=True):
    __tablename__ = "summarized_activities"
#    ↑ 类名用 PascalCase
#                 ↑ 表名用 snake_case
#                    ↑ 明确后缀 DB（数据库模型）

# ❌ 不好：
class Activity(SQLModel, table=True):  # 名称太通用
    __tablename__ = "activity"  # 与 Pydantic 模型重名

class SummarizedActivityModel(SQLModel, table=True):
#                       ↑ 与 Pydantic 混淆
```

#### **Parser 函数命名**

```python
# ✅ 动词 + 对象 模式
parse_garmin_zip()              # 动作清晰：解析
normalize_json_keys()           # 动作+对象
normalize_timestamp()           # 一致的动作名
convert_distance_meters_to_km() # 明确转换方向

# ❌ 不好命名
get_zip()                       # "get" 太模糊
process_data()                  # 对象太模糊
transform()                     # 不知道什么转换
```

#### **私有函数命名**

```python
def _match_core_key(file_name, target_keys):
    #  ↑ 下划线前缀 = 内部函数
    # 这个函数只被 parse_garmin_zip 使用
    # 不应该被其他模块调用
```

---

### 🧠 设计哲学

#### **1. 容错性（Fault Tolerance）**

```python
# ✅ 原则：数据处理优先成功
def normalize_timestamp(value):
    if value is None:
        return None  # 不抛错
    try:
        ...
    except:
        return None  # 失败 → None，不中断

# ❌ 反面：过度严格
def normalize_timestamp_strict(value):
    if value is None:
        raise ValueError("timestamp cannot be None")
    # 任何解析错误 → 整个数据行失败
```

#### **2. 类型安全（Type Hints）**

```python
# ✅ 完整类型提示
def parse_garmin_zip(
    zip_path: str,
    target_jsons: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    ...

# ✅ 优点：
# - IDE 自动完成
# - 静态类型检查（mypy）
# - 文档清晰
# - 减少运行时错误

# ❌ 不好做法
def parse_garmin_zip(zip_path, target_jsons=None):
    # IDE 不知道参数类型
    # mypy 无法检查
```

#### **3. 分离关注（Separation of Concerns）**

```python
# 三个独立职责：
#
# Task 4: ZIP 提取 + 关键词匹配
#   ├─ parse_garmin_zip()      # 知道如何打开 ZIP
#   ├─ _match_core_key()       # 知道如何匹配文件
#   └─ get_garmin_json_names() # 知道如何列举文件
#
# Task 5: 时间戳规范化
#   └─ normalize_timestamp()   # 只处理时间戳
#
# Task 6: 单位转换
#   ├─ convert_distance_*()    # 专门处理距离
#   ├─ convert_speed_*()       # 专门处理速度
#   └─ convert_elevation_*()   # 专门处理高度

# ✅ 每个函数职责单一
# ✅ 易于测试
# ✅ 易于修改
# ✅ 易于复用
```

#### **4. 默认值策略**

```python
# ✅ 模式1：参数有合理默认值
def parse_garmin_zip(
    zip_path: str,
    target_jsons: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    if target_jsons is None:
        target_jsons = DEFAULT_GARMIN_TARGETS
    # 优点：大多数调用不需要指定 target_jsons

# ✅ 模式2：字段有 default_factory
created_at: datetime = Field(default_factory=datetime.utcnow)
# 每次新建时调用 datetime.utcnow()
# 如果用 default=datetime.utcnow()（没括号）会共享同一个值！

# ❌ 错误做法
created_at: datetime = Field(default=datetime.utcnow())
# ❌ 所有行的 created_at 都是相同值（模块加载时刻）
```

---

## 4. 数据处理函数的陷阱与注意事项

### ⚠️ 常见陷阱

#### **陷阱1：浮点数精度损失**

```python
# ❌ 问题
def convert_speed(ms):
    return ms * 3.6  # 浮点乘法

# 测试
convert_speed(10) == 36.0  # ✅
convert_speed(1/3)
# 输出: 1.2000000000000002  ❌ 精度问题

# ✅ 解决
from decimal import Decimal

def convert_speed_precise(ms):
    return float(Decimal(str(ms)) * Decimal('3.6'))

# 但实际上 float 精度对 km/h 足够
# 问题：与数据库精度一致
```

**Garmin RAG 中的处理：**
```python
# 我们接受 float 精度（足够精确到 0.01 m/s）
def convert_speed_ms_to_kmh(speed_ms: Optional[float]) -> Optional[float]:
    if speed_ms is None:
        return None
    try:
        return float(speed_ms) * 3.6  # ✅ float 足够
    except (ValueError, TypeError):
        return None
```

---

#### **陷阱2：时区混乱**

```python
# ❌ 陷阱
from datetime import datetime

timestamp = 1715904000000
# 这是什么时区？

dt = datetime.fromtimestamp(timestamp / 1000)
# ❌ 使用本地时区！
# 在不同服务器上结果不同

# ✅ 解决
from datetime import timezone

dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
# ✅ 明确 UTC
```

**Garmin RAG 中的实现：**
```python
# 所有时间戳都转为 UTC
def normalize_timestamp(timestamp_value: Any) -> Optional[datetime]:
    ...
    # 始终返回带 tzinfo=timezone.utc 的 datetime
    return datetime.fromtimestamp(timestamp_value / 1000, tz=timezone.utc)
    return dt.replace(tzinfo=timezone.utc)
```

---

#### **陷阱3：递归深度限制**

```python
# ❌ 陷阱：无限递归
def normalize_json_keys(value):
    if isinstance(value, dict):
        return {k: normalize_json_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_json_keys(item) for item in value]
    return value

# 如果 JSON 有循环引用：
# { "a": {"b": {"c": {...nested 1000 levels}}}}
# RecursionError: maximum recursion depth exceeded

# ✅ 解决1：增加递归限制
import sys
sys.setrecursionlimit(10000)  # 但不是好方案

# ✅ 解决2：使用迭代（栈）
def normalize_json_keys_iterative(value):
    stack = [value]
    results = []
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for k, v in item.items():
                stack.append(v)
        elif isinstance(item, list):
            for v in item:
                stack.append(v)
    return value

# ✅ 解决3（实际采用）：相信数据
# Garmin JSON 深度不会超过 20 层
# 所以递归是安全的
```

**Garmin RAG 中的实现：**
```python
# Garmin JSON 结构有限（活动、睡眠、记录）
# 最多 2-3 层嵌套，递归完全安全
def normalize_json_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {camel_to_snake(k): normalize_json_keys(v) 
                for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_json_keys(item) for item in value]
    return value
```

---

#### **陷阱4：字符编码问题**

```python
# ❌ 陷阱
with open('file.json', 'r') as f:
    data = json.load(f)
# 在 Windows 上默认是 gbk 编码
# 如果文件是 UTF-8，读取会错误

# ✅ 解决
with open('file.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 或者 ZIP 中的方式：
with zipfile.ZipFile(path, 'r') as archive:
    with archive.open(member, 'r') as file_obj:
        raw_data = file_obj.read()  # bytes
        payload = json.loads(raw_data.decode('utf-8'))  # 明确 UTF-8
```

**Garmin RAG 中的实现：**
```python
# ✅ 明确指定 UTF-8
with archive.open(member, "r") as file_obj:
    raw_data = file_obj.read()
    payload = json.loads(raw_data.decode("utf-8"))  # 明确编码
    extracted[core_key] = normalize_json_keys(payload)
```

---

#### **陷阱5：空值处理不一致**

```python
# ❌ 陷阱：混乱的空值处理
def process_data(value):
    if value:  # 什么是 "false"？
        return value * 2
    return 0

# 问题：
# None, 0, [], "" 都被视为 false
# 但 0 和 "" 可能是有效数据！

process_data(0) → 0  # ❌ 应该返回 0
process_data("") → 0  # ❌ 应该返回 ""
process_data(None) → 0  # ✅ 这个对

# ✅ 显式检查
def process_data(value):
    if value is None:
        return 0
    return value * 2
```

**Garmin RAG 中的实现：**
```python
# ✅ 明确区分 None 和其他值
def convert_distance_meters_to_km(distance_m: Optional[float]) -> Optional[float]:
    if distance_m is None:  # 显式检查 None
        return None
    try:
        return float(distance_m) / 1000.0
    except (ValueError, TypeError):
        return None  # 无效值也返回 None

# 0 会被正确处理为 0
convert_distance_meters_to_km(0) → 0.0  # ✅ 正确
convert_distance_meters_to_km(None) → None  # ✅ 正确
```

---

#### **陷阱6：索引越界**

```python
# ❌ 陷阱
def get_first_element(lst):
    return lst[0]  # 如果 lst 为空？

get_first_element([])  # IndexError!

# ✅ 解决
def get_first_element(lst):
    return lst[0] if lst else None

# 或者
def get_first_element(lst):
    try:
        return lst[0]
    except IndexError:
        return None
```

**Garmin RAG 中的实现：**
```python
# ✅ 使用 endswith() 而不是索引
iso_str = timestamp_value
if iso_str.endswith('.0'):
    iso_str = iso_str[:-2]  # 安全，字符串长度已验证

# ✅ 或者用 try-except
try:
    iso_str = iso_str[:-2]
except IndexError:
    pass  # 不改变 iso_str
```

---

### 💡 最佳实践检查清单

#### **设计阶段**
- [ ] 清晰的职责划分（每个函数做一件事）
- [ ] 类型提示完整（参数、返回值）
- [ ] 异常情况列举（None、无效值、边界值）
- [ ] 文档字符串（功能、参数、返回值、异常）

#### **实现阶段**
- [ ] 输入验证（类型、范围、格式）
- [ ] 防守性编程（检查 None、空集合等）
- [ ] 明确的错误处理（try-except 还是返回 None？）
- [ ] 单位和精度清晰标注

#### **测试阶段**
- [ ] 正常情况（有效输入）
- [ ] 边界情况（0、最大值、最小值）
- [ ] 无效情况（None、错误格式、错误类型）
- [ ] 性能测试（大数据量、深层嵌套）

#### **维护阶段**
- [ ] 日志清晰（包括调试信息）
- [ ] 能否追踪数据流？
- [ ] 能否快速定位错误？
- [ ] 是否有技术债（硬编码值、临时修复等）？

---

### 📋 Garmin RAG 的最佳实践总结

| 方面 | 做法 | 理由 |
|------|------|------|
| **错误处理** | Try-except，返回 None | 数据质量不完美，宽容优于中断 |
| **时区** | 统一 UTC + timezone.utc | 避免跨服务器时区混乱 |
| **单位** | 保存原始单位 | 精度完整，转换在需要时 |
| **空值** | 显式 None 检查 | 区分缺失数据和无效数据 |
| **递归** | 放心使用 | 数据结构已知深度有限 |
| **编码** | 明确指定 UTF-8 | 兼容不同系统 |
| **命名** | 动词 + 明确对象 | 代码自文档化 |
| **类型** | 完整类型提示 | 静态检查 + IDE 支持 |

---

## 总结

### 🎯 三个层级的设计

```
SQL Models (表结构)
    ↓
    ├─ 数据完整性（主键、外键、约束）
    ├─ 查询性能（索引、复合索引）
    └─ 审计追踪（created_at、updated_at）

Parser 函数 (数据处理)
    ↓
    ├─ ZIP 提取（处理文件系统差异）
    ├─ 键名规范化（camelCase → snake_case）
    ├─ 时间戳统一（3 种格式 → UTC）
    └─ 单位转换（原始单位 → 标准单位）

错误处理 (容错能力)
    ↓
    ├─ None 值宽容
    ├─ 无效值不抛错
    ├─ 部分失败继续处理
    └─ 后续可标记或重新处理
```

### ✅ 核心原则

1. **单一职责** - 每个函数做一件事
2. **类型安全** - 完整类型提示和验证
3. **容错性高** - 无效数据不中断流程
4. **可追踪** - 清晰的函数名和日志
5. **易维护** - 分离关注，模块化设计
