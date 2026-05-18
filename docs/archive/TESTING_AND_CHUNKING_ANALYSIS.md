# 测试数据来源与 Task 7 Chunking 策略分析

## 📋 目录
1. [当前测试数据验证](#1-当前测试数据验证)
2. [Task 7 Chunking 策略详解](#2-task-7-chunking-策略详解)
3. [实现建议与最佳实践](#3-实现建议与最佳实践)

---

## 1. 当前测试数据验证

### 📊 测试现状总结

```
测试分为两类：
✅ 单元测试 (Unit Tests)           ❌ 集成测试 (Integration Tests)
├─ 不依赖真实数据                   ├─ 使用真实数据
├─ 快速、可重复                     ├─ 慢、可能不稳定
└─ 19 个 Parser + 4 个 SQL 模型    └─ 未实现
```

### 🔍 Test Parser 数据来源分析

#### **第1类：模拟数据（Mock/Synthetic Data）**

```python
# ❌ tests/test_parser.py 中的模拟数据
def test_parse_garmin_zip_extracts_three_core_files(tmp_path: Path):
    archive_path = tmp_path / "garmin_export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json",
            json.dumps({"activityId": 123, "distance": 10000})
            #                        ↑ 完全模拟的数据
            #                           不是真实 Garmin 数据
        )
```

**特点：**
- ✅ 优点：快速、可重复、不依赖真实 ZIP 文件
- ❌ 缺点：不测试真实 Garmin 数据的复杂性

#### **第2类：采样数据（Sample Data）**

```
✅ 真实 Garmin 数据存储在：
/data/samples/
├─ summarizedActivities.json  (42,384 行！)
├─ sleepData.json
└─ personalRecord.json
```

**现状：**
- 📂 **有真实数据，但测试没用**
- summarizedActivities.json 包含 2000+ 真实活动记录
- 但 test_parser.py 中完全用模拟数据

### 📋 Test SQL Models 数据来源

```python
# tests/test_sql_models.py
def test_summarized_activity_db_defaults_and_required_fields():
    activity = SummarizedActivityDB(
        user_id=1,
        activity_id=123456,        # ❌ 模拟数据
        activity_type="cycling",   # ❌ 模拟数据
        start_time_in_seconds=1715904000000,  # ❌ 虚拟时间
        duration=3600,             # ❌ 虚拟值
        distance=10000,            # ❌ 虚拟值
        ...
    )
```

**问题：**
- 所有测试都用硬编码的虚拟值
- 从未加载真实 Garmin 数据
- 无法发现真实数据的问题（如异常值、缺失字段）

---

### 🚨 建议的改进方案

#### **方案1：添加集成测试**

```python
# tests/integration/test_parser_with_real_data.py

import json
from pathlib import Path
from app.services.parser import normalize_json_keys

def test_parser_with_real_summarized_activities():
    """使用真实 Garmin 数据测试"""
    
    # 加载真实数据
    real_data_path = Path("data/samples/summarizedActivities.json")
    with open(real_data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # 测试规范化
    normalized = normalize_json_keys(raw_data)
    
    # 验证转换
    assert isinstance(normalized, list)
    assert len(normalized) > 0
    
    # 检查第一条记录
    first_record = normalized[0]['summarized_activities_export'][0]
    assert 'activity_id' in first_record  # ✅ 键已转换
    assert first_record['activity_id'] > 0
    assert 'activity_type' in first_record
    assert first_record['start_time_gmt'] > 0


def test_timestamp_normalization_with_real_data():
    """使用真实时间戳测试"""
    
    real_data_path = Path("data/samples/summarizedActivities.json")
    with open(real_data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    activities = raw_data[0]['summarizedActivitiesExport']
    
    from app.services.parser import normalize_timestamp
    
    for activity in activities[:10]:  # 测试前10条
        ts = activity['startTimeGmt']
        dt = normalize_timestamp(ts)
        
        assert dt is not None
        assert dt.tzinfo is not None  # 必须有时区信息
        assert str(dt.tzinfo) == 'UTC'
```

**优点：**
- ✅ 使用真实 Garmin 数据
- ✅ 发现边界情况和异常值
- ✅ 增加信心

**缺点：**
- ❌ 测试速度较慢
- ❌ 依赖文件系统

#### **方案2：使用 Fixtures 缓存真实数据**

```python
# tests/conftest.py

import json
from pathlib import Path
import pytest

@pytest.fixture(scope="session")
def real_summarized_activities():
    """加载一次，在整个测试会话中复用"""
    path = Path("data/samples/summarizedActivities.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture(scope="session")
def real_sleep_data():
    path = Path("data/samples/sleepData.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 使用：
def test_with_real_data(real_summarized_activities):
    # real_summarized_activities 已缓存
    assert len(real_summarized_activities[0]['summarizedActivitiesExport']) > 0
```

**优点：**
- ✅ 保持真实数据测试
- ✅ 优化性能（缓存）
- ✅ 易于重用

#### **方案3：创建精简的真实数据样本**

```python
# tests/fixtures/real_garmin_samples.py

REAL_ACTIVITY_SAMPLE = {
    "summarizedActivitiesExport": [
        {
            "activityId": 4667415185,
            "activityType": "cycling",
            "startTimeGmt": 1584405978000.0,
            "duration": 1944574.951171875,
            "distance": 791093.994140625,
            "elevationGain": 781.441593170166,
            "elevationLoss": 1168.911075592041,
            "avgSpeed": 0.4067999839782715,
            "maxSpeed": 0.703499984741211,
            "calories": 913.4243599999999,
            "lapCount": 2,
            "favorite": False,
            "pr": False,
        }
    ]
}

# 优点：
# ✅ 保留真实值的复杂性
# ✅ 快速加载
# ✅ 避免整个 42K 行文件
```

---

## 2. Task 7 Chunking 策略详解

### 🎯 概念理解

```
RAG 流程：

问题 "我最近跑步速度怎样？"
    ↓
文本检索 (返回相关 chunks)
    ↓
↓─────────────────────────────────┐
│ Task 7 Chunking 的关键作用      │
│ 将 JSON 分割成可检索的文本      │
│─────────────────────────────────┤
│ 原始：{"activityId": 123, ...}  │
│ 转换：                          │
│   "On 2024-05-15, I ran 5 km   │
│    at average speed 10 km/h,    │
│    burned 500 calories"         │
│ 检索：速度、卡路里等关键词      │
└─────────────────────────────────┘
    ↓
Embedding 向量化
    ↓
向量数据库存储
```

### 📐 Chunking 参数详解

#### **1. Chunk Size（块大小）**

```
问题：如何定义块大小？

答案：用 Token 计数
- 1 Token ≈ 4 个英文字符 ≈ 1-2 个汉字
- 1000 Token ≈ 4 KB 文本

示例：
"On May 15, 2024, I ran 5.2 km in 30 minutes at 10.4 km/h speed..."
 ↑
 ~50 tokens

推荐范围：
- 活动记录（复杂）：800-1000 tokens
- 睡眠数据（中等）：500-700 tokens
- 步数统计（简单）：200-300 tokens
```

**为什么要不同的大小？**

```python
# ❌ 所有类型用 1000 tokens
chunk = """
Activity ID: 123456
Type: cycling
Distance: 5.2 km
Speed: 10.4 km/h
Calories: 500
...
"""
# 问题：睡眠数据只有 3 句话，却强制成 1000 tokens
#      会被填充垃圾信息，质量差

# ✅ 根据类型调整大小
Activity: 1000 tokens  # 复杂，有多个嵌套字段
Sleep: 500 tokens      # 中等，主要是数值
Steps: 300 tokens      # 简单，只有几个字段
```

#### **2. Overlap（重叠比例）**

```
问题：为什么需要 overlap？

例子：
Chunk 1: "On May 15-16, I ran 5km... (sleep was 8h)"
Chunk 2: "Sleep was 8h, HR: 60-80... next day activity"
          ↑ 重叠内容
         
优点：
✅ 跨越块边界的问题仍能检索到相关信息
✅ "我周末如何？" → 可以检索到周末 chunk
✅ 避免关键信息在块边界处丢失

实现方式：
Chunk 1：第 1-100 行
Chunk 2：第 90-190 行  # 重叠 10 行（10%）
Chunk 3：第 180-280 行 # 重叠 10 行（10%）
```

**为什么不同类型的 overlap 不同？**

```python
# 高频数据（心率、压力）：高 overlap（20-25%）
# 原因：数据多、变化快，容易错过
# Chunk 1: HR 时间段 08:00-10:00
# Chunk 2: HR 时间段 09:50-11:50  # 重叠 1 小时 10 分钟

# 低频数据（个人记录）：低 overlap（5-10%）
# 原因：数据少、重要度高，不需要重叠
# Chunk 1: PR 1 (破纪录 1)
# Chunk 2: PR 2 (破纪录 2)   # 基本无关，不需要重叠
```

#### **3. Separator（分隔符）**

```python
# ❌ 不好的分隔
text = "activity 1 activity 2 activity 3 activity 4"
# 无法清晰识别块的开始和结束

# ✅ 好的分隔
text = """
==== Activity 1 ====
Date: 2024-05-15
Type: cycling
Distance: 5 km
---

==== Activity 2 ====
Date: 2024-05-14
Type: running
Distance: 10 km
"""
# 清晰的层级结构，模型能识别块的界限
```

---

### 📋 Garmin 数据的 Chunking 策略

#### **核心思想**

```
原始 JSON（机器可读）
    ↓
格式化文本（人类可读）
    ↓
语义化文本（LLM 可理解）
    ↓
Embedding 向量
    ↓
向量数据库检索
```

#### **为各类型设计的具体策略**

##### **1. SummarizedActivity（活动）**

```python
# 设计：按活动类型和日期组织

Chunk Size: 1000 tokens
Overlap: 10%
Reason: 活动数据复杂，字段多

文本模板：
```
═════════════════════════════════════════
Activity Report: Cycling on May 15, 2024
═════════════════════════════════════════

📍 Location: New Taipei City
⏱️ Duration: 32 minutes, 15 seconds
📏 Distance: 7.91 km
🏃 Speed: 4.07 m/s avg, 7.04 m/s max (equivalent to 14.65 km/h avg, 25.33 km/h max)
📈 Elevation: +781 m gain, -1169 m loss
❤️ Calories: 913 kcal
🔄 Laps: 2
⭐ Personal Record: No

Technical Details:
- Device ID: 3979286568
- Elevation Range: 905 - 2667 m
- Cadence: Not tracked
```

**设计说明：**
- ✅ 转换单位（m/s → km/h）
- ✅ 突出关键指标
- ✅ 保留完整信息
- ✅ 易于语义搜索

##### **2. SleepData（睡眠）**

```python
# 设计：按日期和睡眠质量分组

Chunk Size: 500 tokens
Overlap: 15%
Reason: 睡眠数据结构简单，但时间序列很长

文本模板：
```
═════════════════════════════════════════
Sleep Analysis: May 14-15, 2024
═════════════════════════════════════════

📅 Date: 2024-05-15
⏰ Sleep Time: 22:30 (May 14) - 06:30 (May 15)
⏱️ Total Duration: 8 hours

Sleep Composition:
  🔵 Deep Sleep: 7200 seconds (2 hours) - 25%
  🟢 Light Sleep: 10800 seconds (3 hours) - 45%
  🟡 REM Sleep: 1800 seconds (0.5 hours) - 15%
  ⚪ Awake: 1800 seconds (0.5 hours) - 15%

Heart Rate During Sleep:
  Average: 60 bpm
  Range: 55-85 bpm
  Quality: Normal

Sleep Score: 78/100 (Good)
Recovery: Adequate
```

**设计说明：**
- ✅ 清晰的时间范围
- ✅ 转换秒数为可读格式
- ✅ 百分比便于理解
- ✅ 包含健康指标

##### **3. PersonalRecord（个人记录）**

```python
# 设计：记录本身就简洁，不需过度分割

Chunk Size: 800 tokens
Overlap: 5%（很少重叠）
Reason: 每条记录都是独立的里程碑

文本模板：
```
═════════════════════════════════════════
🏆 Personal Record Achieved
═════════════════════════════════════════

Record Type: Fastest 5K Run
Activity Type: Running
Value: 20 minutes 15 seconds
Date Achieved: April 11, 2026

Performance Stats:
- Average Speed: 14.81 km/h
- Distance: 5 km
- Elevation Gain: 45 m
- Calories Burned: 450 kcal

Previous Record: 21 minutes 30 seconds (March 2026)
Improvement: 1 minute 15 seconds faster (5.8% improvement)
```

**设计说明：**
- ✅ 突出成就感
- ✅ 包含对比信息
- ✅ 重要记录不分割

---

### 🔧 Metadata 架构

```python
metadata = {
    # 必需字段
    "data_type": "summarized_activity",      # 数据类型
    "record_id": 4667415185,                 # 原始记录ID
    "chunk_index": 1,                        # 当前是第几个chunk
    "total_chunks": 3,                       # 总共有几个chunk
    
    # 时间字段
    "date": "2024-05-15",                    # 主要日期
    "start_time": "2024-05-15T12:00:00Z",   # 开始时间（如适用）
    "end_time": "2024-05-15T12:32:00Z",     # 结束时间（如适用）
    
    # 检索字段
    "keywords": [                             # RAG 检索关键词
        "cycling",
        "outdoor activity", 
        "7.91km",
        "new taipei",
        "2 hours"
    ],
    
    # 上下文字段
    "user_id": 74303376,                     # 用户ID
    "source_file": "summarizedActivities.json",
    "activity_type": "cycling",              # 活动类型（如适用）
    "location": "New Taipei City",           # 位置（如适用）
    
    # 质量字段
    "has_location": True,                    # 是否有地理位置
    "has_elevation": True,                   # 是否有高度数据
    "quality_score": 0.95                    # 质量评分 0-1
}
```

**为什么这样设计？**

```python
# 查询示例：
# Q: "我最近在台北的活动"

# 搜索过程：
# 1. 文本检索：{"location": "taipei"} → 找到文本chunks
# 2. 向量检索：embedding("cycling activities") → 向量相似性
# 3. 时间过滤：{"date": ["2024-05-01", "2024-05-31"]}
# 4. 用户过滤：{"user_id": 74303376}

# metadata 提供精确过滤，文本提供语义检索
```

---

### 📊 Chunking 示例流程

```python
# 输入：单个活动记录
activity = {
    "activityId": 4667415185,
    "activityType": "cycling",
    "name": "新店區 Cycling",
    "startTimeGmt": 1584405978000,
    "distance": 791093.99,
    "avgSpeed": 0.4067,
    "maxSpeed": 0.7035,
    ...  # 更多字段
}

# 处理步骤1：选择 chunking 策略
strategy = "default"  # 对活动使用默认策略
chunk_size = 1000     # tokens
overlap_ratio = 0.10  # 10%

# 处理步骤2：将 JSON 转为文本
formatted_text = """
═════════════════════════════════════════
Activity Report: Cycling on March 16, 2020
═════════════════════════════════════════

📍 Location: New Taipei City
⏱️ Duration: 32 minutes 22 seconds
📏 Distance: 7.91 km
🏃 Speed: 1.46 km/h avg, 2.53 km/h max
❤️ Calories: 913 kcal
...
"""

# 处理步骤3：分割文本
# 计算 token 数 → 按大小分割
# Chunk 1: 第 1-1000 tokens
# Chunk 2: 第 900-1900 tokens  # 重叠 100 tokens

# 处理步骤4：生成 metadata
metadata_1 = {
    "data_type": "summarized_activity",
    "record_id": 4667415185,
    "chunk_index": 1,
    "total_chunks": 1,  # 假设只有 1 个 chunk
    "date": "2020-03-16",
    "keywords": ["cycling", "7.91km", "taipei"],
    "user_id": 74303376,
}

# 输出
chunks = [
    (formatted_text, metadata_1)
]
```

---

## 3. 实现建议与最佳实践

### ✅ 立即可实现的改进（高优先级）

#### **改进1：添加真实数据集成测试**

```python
# tests/integration/test_with_real_data.py

import pytest
from pathlib import Path
import json
from app.services.parser import normalize_json_keys, normalize_timestamp

@pytest.fixture(scope="session")
def real_data():
    """加载真实 Garmin 样本数据"""
    samples = {}
    for file in ["summarizedActivities", "sleepData", "personalRecord"]:
        path = Path(f"data/samples/{file}.json")
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                samples[file] = json.load(f)
    return samples

def test_normalize_real_summarized_activities(real_data):
    """测试真实活动数据的规范化"""
    if 'summarizedActivities' not in real_data:
        pytest.skip("Real data not available")
    
    data = real_data['summarizedActivities']
    normalized = normalize_json_keys(data)
    
    # 验证结构
    assert isinstance(normalized, list)
    assert len(normalized) > 0
    assert 'summarized_activities_export' in normalized[0]
    
    # 验证字段转换
    activities = normalized[0]['summarized_activities_export']
    for activity in activities[:5]:
        assert 'activity_id' in activity
        assert 'activity_type' in activity
        assert 'start_time_gmt' in activity
        assert activity['activity_id'] > 0


def test_timestamp_handling_with_real_data(real_data):
    """验证时间戳处理"""
    if 'summarizedActivities' not in real_data:
        pytest.skip("Real data not available")
    
    data = real_data['summarizedActivities']
    activities = data[0]['summarizedActivitiesExport']
    
    for activity in activities[:10]:
        ts = activity['startTimeGmt']
        dt = normalize_timestamp(ts)
        
        assert dt is not None
        assert dt.tzinfo is not None
        assert '2020' in str(dt) or '2021' in str(dt) or '2022' in str(dt)
```

#### **改进2：统一测试数据源**

```python
# tests/conftest.py（集中管理 fixtures）

import json
from pathlib import Path
import pytest

# 真实数据缓存
_REAL_DATA_CACHE = {}

@pytest.fixture(scope="session")
def garmin_real_data():
    """统一的真实 Garmin 数据接口"""
    global _REAL_DATA_CACHE
    
    if not _REAL_DATA_CACHE:
        for file_type in ['summarizedActivities', 'sleepData', 'personalRecord']:
            path = Path(f"data/samples/{file_type}.json")
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    _REAL_DATA_CACHE[file_type] = json.load(f)
    
    return _REAL_DATA_CACHE


@pytest.fixture(scope="function")
def sample_activity_record():
    """单个活动记录样本"""
    return {
        "activityId": 4667415185,
        "activityType": "cycling",
        "name": "新店區 Cycling",
        "startTimeGmt": 1584405978000.0,
        "distance": 791093.994140625,
        "duration": 1944574.951171875,
        "avgSpeed": 0.4067999839782715,
        "maxSpeed": 0.703499984741211,
        "calories": 913.4243599999999,
        "lapCount": 2,
        "favorite": False,
        "pr": False,
    }
```

---

### 🎯 Task 7 实现路线图

#### **Phase 1: 设计（2-3 小时）**

```
✅ Week 1:
1. 确定各数据类型的 chunk size
   └─ 活动：1000 tokens
   └─ 睡眠：500 tokens
   └─ 记录：800 tokens

2. 设计文本模板（HTML/Markdown 风格）
   └─ 每个数据类型 1 个模板

3. 定义 metadata 架构
   └─ 包含 15-20 个字段

4. 制定 overlap 策略
   └─ 不同类型不同比例
```

#### **Phase 2: 实现（4-5 小时）**

```
✅ Week 2-3:
1. 实现 chunk_garmin_data() 主函数
2. 实现各类型的 chunking 子函数
3. 实现 overlap 逻辑
4. 优化性能（目标：2秒处理 10K+ 记录）
5. 添加单元测试
```

#### **Phase 3: 优化（2-3 小时）**

```
✅ Week 4:
1. 文本质量审核
2. 测试各种策略效果
3. 性能优化
4. 文档补充
```

---

### 💡 核心实现代码框架

```python
# app/services/chunker.py（新文件）

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken  # 计算 token 数

@dataclass
class ChunkConfig:
    """Chunk 配置"""
    chunk_size: int = 1000      # tokens
    overlap_ratio: float = 0.1   # 10%
    strategy: str = "default"


class GarminChunker:
    """Garmin 数据 chunking 处理器"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def chunk_garmin_data(
        self,
        normalized_data: Dict[str, List[Dict]],
        strategy: str = "default"
    ) -> List[Tuple[str, Dict]]:
        """主入口函数"""
        chunks = []
        
        # 处理各类型
        if 'summarized_activities' in normalized_data:
            chunks.extend(self._chunk_activities(
                normalized_data['summarized_activities'],
                strategy
            ))
        
        if 'sleep_data' in normalized_data:
            chunks.extend(self._chunk_sleep_data(
                normalized_data['sleep_data'],
                strategy
            ))
        
        if 'personal_records' in normalized_data:
            chunks.extend(self._chunk_personal_records(
                normalized_data['personal_records'],
                strategy
            ))
        
        return chunks
    
    def _chunk_activities(self, activities: List, strategy: str):
        """处理活动数据"""
        chunks = []
        config = self._get_config_for_type('activity', strategy)
        
        for activity in activities:
            # 格式化为文本
            text = self._format_activity(activity)
            
            # 分割文本
            text_chunks = self._split_text_with_overlap(
                text,
                config.chunk_size,
                config.overlap_ratio
            )
            
            # 生成 metadata
            for i, chunk in enumerate(text_chunks):
                metadata = {
                    'data_type': 'summarized_activity',
                    'record_id': activity.get('activity_id'),
                    'chunk_index': i,
                    'total_chunks': len(text_chunks),
                    'date': activity.get('start_time_gmt_date'),  # 需转换
                    'keywords': self._extract_keywords(activity),
                }
                chunks.append((chunk, metadata))
        
        return chunks
    
    def _format_activity(self, activity: Dict) -> str:
        """将活动 JSON 转为可读文本"""
        # 转换单位
        distance_km = activity.get('distance', 0) / 1000
        speed_kmh = activity.get('avg_moving_speed', 0) * 3.6
        
        # 格式化
        text = f"""
═════════════════════════════════════════
Activity Report: {activity.get('activity_type', 'Unknown')}
═════════════════════════════════════════

📍 Location: {activity.get('location_name', 'Unknown')}
⏱️ Duration: {activity.get('duration', 0) / 1000 / 60:.0f} minutes
📏 Distance: {distance_km:.2f} km
🏃 Speed: {speed_kmh:.2f} km/h avg
❤️ Calories: {activity.get('calories', 0):.0f} kcal
⭐ Personal Record: {'Yes' if activity.get('pr') else 'No'}
"""
        return text
    
    def _split_text_with_overlap(
        self,
        text: str,
        chunk_size: int,
        overlap_ratio: float
    ) -> List[str]:
        """按 token 数分割，并添加重叠"""
        tokens = self.tokenizer.encode(text)
        
        chunks = []
        overlap_tokens = int(chunk_size * overlap_ratio)
        start = 0
        
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            start = end - overlap_tokens  # 重叠
        
        return chunks
    
    def _extract_keywords(self, activity: Dict) -> List[str]:
        """提取关键词用于检索"""
        keywords = [
            activity.get('activity_type', ''),
            activity.get('location_name', ''),
            f"{int(activity.get('distance', 0) / 1000)}km",
        ]
        return [k for k in keywords if k]
    
    def _get_config_for_type(self, data_type: str, strategy: str) -> ChunkConfig:
        """根据数据类型和策略获取配置"""
        configs = {
            'activity': ChunkConfig(chunk_size=1000, overlap_ratio=0.10),
            'sleep': ChunkConfig(chunk_size=500, overlap_ratio=0.15),
            'record': ChunkConfig(chunk_size=800, overlap_ratio=0.05),
        }
        return configs.get(data_type, self.config)
```

---

### 📝 推荐的文档结构

```
app/services/
├── parser.py           # 现有：ZIP 解析、规范化、转换
└── chunker.py          # 新增：Chunking 策略

docs/
├── CHUNKING_STRATEGY.md        # 设计文档
├── CHUNKING_IMPLEMENTATION.md  # 实现指南
└── METADATA_SCHEMA.md          # Metadata 规范

tests/
├── integration/
│   └── test_chunking_real_data.py
└── unit/
    ├── test_chunker_activities.py
    ├── test_chunker_sleep.py
    └── test_chunker_records.py
```

---

## 总结

### 📊 当前测试状态

```
✅ 已有：19 个 Parser 单元测试 + 4 个 SQL 模型测试
❌ 缺少：真实数据集成测试
💡 建议：添加 fixtures 加载 data/samples 中的真实数据
```

### 🎯 Task 7 Chunking 预计实现

```
核心思想：
JSON 数据 → 人类可读文本 → 语义化内容 → 向量化

关键参数：
├─ Chunk Size：按数据类型不同（300-1000 tokens）
├─ Overlap：按数据特性不同（5%-25%）
├─ Text Template：每个数据类型专属格式
└─ Metadata：15-20 个字段用于检索和过滤

预计工时：
├─ 设计阶段：2-3 小时
├─ 实现阶段：4-5 小时
└─ 优化阶段：2-3 小时
```

### ✅ 立即行动

1. **今日：** 添加真实数据集成测试
2. **本周：** 完成 Task 7 设计文档
3. **下周：** 开始 Task 7 实现
