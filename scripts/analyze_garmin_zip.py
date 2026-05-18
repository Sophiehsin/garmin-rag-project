#!/usr/bin/env python3
"""
Garmin ZIP 檔結構分析工具 - Phase 2 Task 1

用途：
    掃描 Garmin 全量導出 ZIP 檔，分析其內部結構，確認 10 個核心 JSON 檔的
    具體名稱、路徑、大小、以及字段結構。生成詳細的分析報告。

用法：
    python scripts/analyze_garmin_zip.py <zip_path> [options]

示例：
    python scripts/analyze_garmin_zip.py data/garmin_export.zip
    python scripts/analyze_garmin_zip.py data/garmin_export.zip --verbose
    python scripts/analyze_garmin_zip.py data/garmin_export.zip --output analysis.json

輸出：
    - 控制台：詳細分析結果
    - data/analysis/structure_report.json：ZIP 結構報告
    - data/analysis/field_mapping.json：欄位映射表
    - note/GARMIN_ZIP_ANALYSIS.md：Markdown 格式分析報告
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import zipfile
from datetime import datetime

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 預期的 10 個核心 Garmin JSON 檔案
EXPECTED_GARMIN_JSONS = [
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


class GarminZipAnalyzer:
    """Garmin ZIP 檔分析器"""

    def __init__(self, zip_path: str, verbose: bool = False):
        """
        初始化分析器

        Args:
            zip_path: ZIP 檔路徑
            verbose: 是否顯示詳細輸出

        Raises:
            FileNotFoundError: ZIP 檔不存在
            zipfile.BadZipFile: ZIP 檔損壞
        """
        self.zip_path = Path(zip_path)
        self.verbose = verbose

        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP 檔不存在: {self.zip_path}")

        try:
            self.zip_file = zipfile.ZipFile(self.zip_path, 'r')
        except zipfile.BadZipFile as e:
            raise zipfile.BadZipFile(f"ZIP 檔損壞: {e}")

        self.analysis: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "zip_path": str(self.zip_path),
            "zip_size_mb": self.zip_path.stat().st_size / (1024 * 1024),
            "total_files": len(self.zip_file.namelist()),
        }

    def analyze(self) -> Dict[str, Any]:
        """
        執行完整分析

        Returns:
            分析結果字典
        """
        logger.info(f"開始分析 ZIP 檔: {self.zip_path}")
        logger.info(f"ZIP 大小: {self.analysis['zip_size_mb']:.2f} MB")
        logger.info(f"總檔案數: {self.analysis['total_files']}")

        # 分析所有檔案
        self._analyze_file_structure()

        # 查找並分析 JSON 檔案
        self._find_and_analyze_json_files()

        # 生成報告
        self._generate_report()

        logger.info("分析完成")
        return self.analysis

    def _analyze_file_structure(self) -> None:
        """分析檔案結構"""
        logger.info("\n📁 分析檔案結構...")

        structure = defaultdict(list)
        total_size = 0

        for file_info in self.zip_file.infolist():
            file_name = file_info.filename
            file_size = file_info.file_size
            
            # 跳過 0 KB 的檔案和目錄
            if file_size == 0 and file_info.is_dir():
                continue
                
            total_size += file_size

            # 提取目錄層級
            parts = Path(file_name).parts
            if len(parts) > 0:
                top_level = parts[0]
                structure[top_level].append({
                    "name": file_name,
                    "size_kb": file_size / 1024,
                    "is_dir": file_info.is_dir(),
                })

        self.analysis["directory_structure"] = {
            k: {
                "file_count": len(v),
                "total_size_mb": sum(f["size_kb"] for f in v) / 1024,
                "files": [f for f in v if f["size_kb"] > 0][:5]  # 過濾 0 KB 並取前 5 個
            }
            for k, v in structure.items()
            if len([f for f in v if f["size_kb"] > 0]) > 0  # 過濾掉沒有有效檔案的資料夾
        }
        self.analysis["total_size_mb"] = total_size / (1024 * 1024)

        if self.verbose:
            logger.info("\n目錄結構:")
            for dir_name, info in self.analysis["directory_structure"].items():
                logger.info(
                    f"  {dir_name}: "
                    f"{info['file_count']} 檔案, "
                    f"{info['total_size_mb']:.2f} MB"
                )

    def _find_and_analyze_json_files(self) -> None:
        """尋找並分析 JSON 檔案"""
        logger.info("\n📄 尋找 JSON 檔案...")

        json_files = [n for n in self.zip_file.namelist() if n.endswith('.json')]
        logger.info(f"找到 {len(json_files)} 個 JSON 檔案")

        # 找到核心 JSON 檔案
        core_jsons = {}
        for expected in EXPECTED_GARMIN_JSONS:
            for json_file in json_files:
                if json_file.endswith(expected):
                    core_jsons[expected] = json_file
                    break

        self.analysis["core_jsons_found"] = len(core_jsons)
        self.analysis["core_jsons"] = {}

        # 分析每個核心 JSON 的結構
        for expected_name, actual_path in core_jsons.items():
            logger.info(f"  分析: {actual_path}...")

            try:
                with self.zip_file.open(actual_path) as f:
                    json_data = json.load(f)

                analysis = self._analyze_json_structure(json_data, actual_path)
                self.analysis["core_jsons"][expected_name] = analysis

                if self.verbose:
                    logger.info(f"    ✓ {expected_name}")
                    logger.info(f"      路徑: {actual_path}")
                    logger.info(f"      元素: {analysis['element_count']}")
                    logger.info(f"      欄位: {', '.join(list(analysis['sample_fields'].keys())[:5])}")

            except Exception as e:
                logger.warning(f"    ✗ 無法分析 {expected_name}: {e}")
                self.analysis["core_jsons"][expected_name] = {
                    "error": str(e),
                    "path": actual_path
                }

        # 列出所有 JSON 檔案（以備參考）
        self.analysis["all_json_files"] = {
            "count": len(json_files),
            "files": json_files[:20]  # 列出前 20 個
        }

    def _analyze_json_structure(
        self, 
        json_data: Any, 
        file_path: str
    ) -> Dict[str, Any]:
        """
        分析 JSON 檔案的結構

        Args:
            json_data: 解析後的 JSON 數據
            file_path: JSON 檔案路徑

        Returns:
            結構分析結果
        """
        result = {
            "path": file_path,
            "type": type(json_data).__name__,
            "element_count": 0,
            "sample_fields": {},
            "field_types": {},
        }

        # 如果是列表
        if isinstance(json_data, list):
            result["element_count"] = len(json_data)

            if len(json_data) > 0:
                # 分析第一個元素的欄位
                first_elem = json_data[0]
                if isinstance(first_elem, dict):
                    result["sample_fields"] = first_elem
                    result["field_types"] = {
                        k: type(v).__name__
                        for k, v in first_elem.items()
                    }

                    # 掃描所有元素，找出所有可能的欄位
                    all_fields = set()
                    for elem in json_data:
                        if isinstance(elem, dict):
                            all_fields.update(elem.keys())

                    result["all_possible_fields"] = sorted(list(all_fields))

        # 如果是字典
        elif isinstance(json_data, dict):
            result["element_count"] = len(json_data)
            result["sample_fields"] = json_data
            result["field_types"] = {
                k: type(v).__name__
                for k, v in json_data.items()
            }

        return result

    def _generate_report(self) -> None:
        """生成分析報告"""
        logger.info("\n📊 生成報告...")

        # 建立 analysis 目錄
        analysis_dir = Path("data/analysis")
        analysis_dir.mkdir(parents=True, exist_ok=True)

        # 保存 JSON 報告
        report_path = analysis_dir / "structure_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ 已保存結構報告: {report_path}")

        # 生成 Markdown 報告
        self._generate_markdown_report()

    def _generate_markdown_report(self) -> None:
        """生成 Markdown 格式的分析報告"""
        note_dir = Path("note")
        note_dir.mkdir(parents=True, exist_ok=True)

        report_path = note_dir / "GARMIN_ZIP_ANALYSIS.md"

        content = f"""# Garmin ZIP 檔結構分析報告

**分析日期：** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  
**ZIP 檔路徑：** `{self.analysis['zip_path']}`  
**ZIP 檔大小：** {self.analysis['zip_size_mb']:.2f} MB  
**總檔案數：** {self.analysis['total_files']}

---

## 📋 **分析摘要**

| 項目 | 值 |
|------|-----|
| **ZIP 大小** | {self.analysis['zip_size_mb']:.2f} MB |
| **總檔案數** | {self.analysis['total_files']} |
| **找到的核心 JSON** | {self.analysis['core_jsons_found']}/10 |
| **所有 JSON 檔案** | {self.analysis['all_json_files']['count']} 個 |

---

## ✅ **核心 JSON 檔案清單**

"""

        # 列出找到的核心 JSON 檔案
        if self.analysis['core_jsons_found'] > 0:
            content += "### 找到的檔案\n\n"
            for json_name, analysis in self.analysis['core_jsons'].items():
                if 'error' not in analysis:
                    content += f"""#### {json_name}
- **路徑：** `{analysis['path']}`
- **類型：** {analysis['type']}
- **元素數：** {analysis['element_count']}
- **欄位數：** {len(analysis['sample_fields'])}
- **主要欄位：** {', '.join(list(analysis['sample_fields'].keys())[:5])}

"""
        else:
            content += "### ⚠️ 未找到任何核心 JSON 檔案\n\n"

        # 列出缺失的檔案
        missing_jsons = set(EXPECTED_GARMIN_JSONS) - set(self.analysis['core_jsons'].keys())
        if missing_jsons:
            content += f"""### 缺失的檔案 ({len(missing_jsons)})

"""
            for json_name in sorted(missing_jsons):
                content += f"- ❌ {json_name}\n"
            content += "\n"

        # 詳細欄位映射
        content += """---

## 🗂️ **詳細欄位映射**

"""
        for json_name, analysis in self.analysis['core_jsons'].items():
            if 'error' not in analysis and 'all_possible_fields' in analysis:
                content += f"""### {json_name}

**所有欄位：** ({len(analysis.get('all_possible_fields', []))} 個)

"""
                fields = analysis.get('all_possible_fields', [])
                for field in fields[:20]:  # 最多顯示 20 個欄位
                    field_type = analysis['field_types'].get(field, 'unknown')
                    content += f"- `{field}` ({field_type})\n"

                if len(fields) > 20:
                    content += f"\n... 及其他 {len(fields) - 20} 個欄位\n"

                content += "\n"

        # 目錄結構
        content += """---

## 📁 **ZIP 內部目錄結構**

"""
        for dir_name, info in self.analysis['directory_structure'].items():
            content += f"### `{dir_name}/`\n"
            content += f"- 檔案數：{info['file_count']}\n"
            content += f"- 總大小：{info['total_size_mb']:.2f} MB\n\n"

        # 所有 JSON 檔案列表
        content += f"""---

## 📄 **所有 JSON 檔案清單** ({self.analysis['all_json_files']['count']} 個)

"""
        for json_file in self.analysis['all_json_files']['files']:
            content += f"- `{json_file}`\n"

        if len(self.analysis['all_json_files']['files']) < self.analysis['all_json_files']['count']:
            remaining = self.analysis['all_json_files']['count'] - len(self.analysis['all_json_files']['files'])
            content += f"\n... 及其他 {remaining} 個檔案\n"

        # 建議
        content += f"""---

## 💡 **分析建議**

### 核心 JSON 檔案覆蓋率
- **已找到：** {self.analysis['core_jsons_found']}/10
- **覆蓋率：** {self.analysis['core_jsons_found'] * 10:.0f}%

"""

        if self.analysis['core_jsons_found'] == 10:
            content += "✅ **所有核心 JSON 檔案都已找到！** 可以開始數據模型定義。\n"
        elif self.analysis['core_jsons_found'] >= 8:
            content += "⚠️ **大部分核心 JSON 已找到。** 缺失的檔案可能使用不同的命名方式或不適用於此 Garmin 設備。\n"
        else:
            content += "❌ **核心 JSON 檔案不足。** 請檢查 ZIP 檔內容，確認導出時包含所有必要數據。\n"

        content += f"""

### 下一步
1. 複查分析結果是否符合預期
2. 若有未找到的檔案，檢查 ZIP 內是否使用了不同的命名方式
3. 提取核心 JSON 樣本到 `data/samples/`
4. 開始定義 Pydantic 數據模型

---

**報告自動生成** - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✓ 已保存 Markdown 報告: {report_path}")

    def extract_core_jsons(self) -> None:
        """提取核心 JSON 檔案到 data/samples/"""
        logger.info("\n💾 提取核心 JSON 檔案...")

        samples_dir = Path("data/samples")
        samples_dir.mkdir(parents=True, exist_ok=True)

        extracted_count = 0
        for json_name, analysis in self.analysis['core_jsons'].items():
            if 'error' not in analysis:
                actual_path = analysis['path']

                try:
                    # 讀取 JSON 檔案
                    with self.zip_file.open(actual_path) as f:
                        json_data = json.load(f)

                    # 保存到 samples 目錄
                    output_path = samples_dir / json_name
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)

                    logger.info(f"✓ 已提取: {json_name}")
                    extracted_count += 1

                except Exception as e:
                    logger.warning(f"✗ 提取失敗 {json_name}: {e}")

        logger.info(f"\n已提取 {extracted_count} 個檔案到 data/samples/")

    def close(self) -> None:
        """關閉 ZIP 檔"""
        self.zip_file.close()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="分析 Garmin ZIP 檔結構",
        epilog="示例: python scripts/analyze_garmin_zip.py data/garmin_export.zip --verbose"
    )
    parser.add_argument(
        "zip_path",
        help="Garmin ZIP 檔路徑"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="顯示詳細輸出"
    )
    parser.add_argument(
        "--extract", "-e",
        action="store_true",
        help="提取核心 JSON 檔案到 data/samples/"
    )

    args = parser.parse_args()

    try:
        analyzer = GarminZipAnalyzer(args.zip_path, verbose=args.verbose)
        analysis = analyzer.analyze()

        if args.extract:
            analyzer.extract_core_jsons()

        analyzer.close()

        # 打印摘要
        logger.info("\n" + "=" * 60)
        logger.info("✅ 分析完成")
        logger.info(f"找到 {analysis['core_jsons_found']}/10 個核心 JSON 檔案")
        logger.info(f"報告已保存到:")
        logger.info(f"  - data/analysis/structure_report.json")
        logger.info(f"  - note/GARMIN_ZIP_ANALYSIS.md")
        logger.info("=" * 60)

        return 0

    except FileNotFoundError as e:
        logger.error(f"❌ 錯誤: {e}")
        return 1
    except zipfile.BadZipFile as e:
        logger.error(f"❌ ZIP 檔損壞: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ 未預期的錯誤: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
