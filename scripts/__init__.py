"""
開發工具腳本 - 一次性執行的實用工具

本目錄的腳本不在生產環境運行，用於：
- 環境驗證（test_db_connection.py）
- 數據分析（analyze_garmin_zip.py）
- 數據提取（extract_sample_jsons.py）
- 數據遷移（migrate_data.py）
- Mock 數據生成（generate_mock_garmin.py）

所有腳本都可以用 python scripts/xxx.py 直接執行

Phase 2 優先：
  ✅ test_db_connection.py - DB 連接驗證
  🟠 analyze_garmin_zip.py - ZIP 結構分析（Task 1）
"""
