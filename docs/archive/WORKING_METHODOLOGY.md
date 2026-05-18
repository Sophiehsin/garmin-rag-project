# 🛠️ 工作流方法論 - Single Evolving Plan Pattern

**建立日期：** 2026年4月18日  
**版本：** 1.0  
**目的：** 記錄 Garmin RAG 項目的工作流標準

---

## 📌 **核心原則**

本項目採用 **Single Evolving Plan Pattern（單一演進計劃模式）**，與傳統的多文件快照方法不同。

### **相比傳統方法的優勢**

| 傳統方法 | 單一演進計劃 |
|--------|-----------|
| 多個狀態快照文件（計劃、進行中、完成報告等） | 一個計劃文件，全程演進 |
| 信息分散，易於過時 | 信息集中，始終是最新 |
| 難以追蹤完整歷史 | Git commit 記錄清晰 |
| 文檔重複和冗餘 | 無冗餘，高效率 |
| 需要同步多個文件 | 只需維護一個文件 |

---

## 📋 **工作流步驟**

### **1️⃣ 項目開始**

**創建**：單一計劃文檔（例如 `note/plan/plan for part 2.md`）

**內容包含：**
- 項目概述
- 14 個詳細的任務分解
- 每個任務的要求、交付物、注意事項
- 時間軸與里程碑
- 成功條件

**範例：** `plan for part 2.md` (已建立)

### **2️⃣ 進行中**

**持續更新**同一計劃文件：

- 每完成一個任務，在任務描述中**標記完成狀態** ✅
- 添加實際完成時間和實現細節
- 記錄遇到的問題和解決方案
- 更新時間軸（如有延期或加速）
- 新增發現或風險說明

**不做的事：**
- ❌ 不創建新的 `TASK_2_COMPLETED.md` 文件
- ❌ 不創建 `PROGRESS_REPORT_v1.md`, `v2.md` 等快照
- ❌ 不使用文件版本號（如 `plan_v1.md`, `plan_v2.md`）

### **3️⃣ 項目完成**

**添加**完成總結到同一文件的末尾：

- 最終統計（實際 vs 計劃）
- 關鍵成就
- 遇到的挑戰和解決方案
- 教訓總結
- 後續建議

**範例：**
```markdown
## 🎉 Phase 2 完成總結（2026年5月X日）

### 交付成果
- ✅ 任務 1-14 全部完成
- ✅ 單元測試覆蓋率 85%
- ✅ 所有文檔完成

### 實際時間線
- 任務 1: 計劃 2-3h，實際 2.5h ✅
- 任務 2: 計劃 3-4h，實際 4.5h ⚠️（原因：...）
- ...

### 關鍵教訓
1. 時間戳處理比預期複雜
2. 單位轉換需要更多邊界測試
3. ...
```

---

## 📁 **文件組織**

### **計劃文件位置**

```
note/plan/
├── plan for part 2.md          ⭐ 單一演進計劃（Phase 2）
├── plan for part 3.md          ⭐ 未來 Phase 3 計劃
└── plan for part 4.md          ⭐ 未來 Phase 4 計劃
```

### **不應該存在的文件**

```
note/
├── PHASE2_COMPLETION_REPORT.md         ❌ 刪除（內容合併到計劃文件）
├── IMPLEMENTATION_CHECKLIST.md         ❌ 刪除（內容合併到計劃文件）
├── FILE_STRUCTURE_CONFIRMATION.md      ❌ 刪除（內容合併到計劃文件）
├── plan_v1.md, plan_v2.md              ❌ 不使用版本號
└── progress_report_weekly_1.md         ❌ 不創建快照報告
```

### **參考和指南文件（可保留）**

```
note/
├── PROJECT_STRUCTURE_GUIDE.md  ✅ 保留（架構指南，不是狀態快照）
├── skills/
│   └── WORKING_METHODOLOGY.md  ✅ 保留（本文件 - 工作流規範）
└── plan/
    └── plan for part 2.md      ✅ 演進計劃
```

---

## 🔄 **版本控制策略**

### **使用 Git，而非文件版本**

```bash
# ✅ 正確做法 - 提交到同一文件
git add note/plan/plan\ for\ part\ 2.md
git commit -m "Update Phase 2 plan: Task 1 completed"

# ❌ 錯誤做法 - 創建新版本文件
git add note/plan/plan_for_part_2_v1.md
git add note/plan/plan_for_part_2_v2.md
```

### **Commit 訊息規範**

每次更新計劃時，使用清晰的 commit 訊息：

```
# 完成任務
Update Phase 2 plan: Task 1 completed - ZIP analysis
- Implemented analyze_garmin_zip.py
- Generated analysis report
- Extracted 10 core JSON samples

# 遇到問題
Update Phase 2 plan: Task 2 delayed
- Issue: ZIP file too large for memory
- Solution: Implement stream-based extraction
- New ETA: +1 day

# 定期進度更新
Update Phase 2 plan: Progress checkpoint (50%)
- Tasks 1-7 completed
- Tasks 8-9 in progress
- No blockers
```

### **查看歷史變更**

```bash
# 查看計劃文件的完整 git 歷史
git log --oneline note/plan/plan\ for\ part\ 2.md

# 查看特定版本的計劃
git show commit-hash:note/plan/plan\ for\ part\ 2.md

# 對比兩個版本之間的變更
git diff commit-hash1 commit-hash2 note/plan/plan\ for\ part\ 2.md
```

---

## 📝 **計劃文件格式範本**

### **開頭部分（不變）**

```markdown
# Garmin RAG 項目 - 第二步：數據解析服務 (The Parser) 完整計劃

**建立日期：** 2026年4月18日  
**目標：** 開發完整的 Garmin JSON 解析、正規化、切片流程  
**重要性：** 核心重點 - RAG 效果的基礎

---

## 📌 **項目概述**
[原始內容不變]

---

## 🎯 **核心任務分解（14 個待辦項）**
[原始內容不變 - 詳細任務說明]

---

[所有任務 1-14 的完整說明]

---

## 📊 **時間軸與里程碑**
[持續更新此部分]

| 任務 | 工時 | 實際 | 狀態 | 完成日期 |
|------|------|------|------|--------|
| 1. 分析 ZIP 結構 | 2-3h | 2.5h | ✅ | 2026-04-18 |
| 2. ZIP 過濾函數 | 3-4h | | 🔄 | 進行中 |
| 3. ... | ... | ... | ⏳ | 待開始 |

---

## 📝 **進行中的更新日誌**
[新增此部分，記錄重要進展]

### 2026-04-18 - 基礎設施建立完成
- ✅ 11 個文件夾創建
- ✅ 12 個 Python 檔案框架
- ✅ analyze_garmin_zip.py 完成
- 📍 準備開始 Task 1 執行

### 2026-04-XX - Task 1 完成
- ✅ ZIP 分析執行
- 📊 發現 10/10 個核心 JSON
- 📄 生成分析報告
- 🎯 下一步：開始 Task 2

---

## 🎉 **Phase 2 完成總結**
[項目結束時添加此部分]

### 交付成果
- ✅ 所有 14 個任務完成
- ✅ ...

### 實際時間線
- ...

### 關鍵教訓
- ...
```

---

## ✅ **工作流檢查清單**

使用此清單確保遵循方法論：

### **項目開始**
- [ ] 創建單一計劃文檔到 `note/plan/` 目錄
- [ ] 文檔包含所有任務的詳細說明
- [ ] 時間軸和里程碑已定義

### **進行中**
- [ ] 每完成一個任務，更新同一計劃文件
- [ ] 標記任務狀態（✅/🔄/⏳）
- [ ] 記錄實際用時和任何問題
- [ ] 定期 git commit 更新
- [ ] 不創建任何新的狀態快照文件 ❌

### **項目完成**
- [ ] 在計劃文件末尾添加完成總結
- [ ] 最終 commit 說明項目完成
- [ ] 未來計劃文檔已準備（如適用）

---

## 🎓 **為什麼選擇這種方法**

### **單一文件的優勢**

1. **信息完整性**
   - 所有上下文都在一個地方
   - 無需在多個文件之間尋找信息

2. **易於維護**
   - 只需更新一個文件
   - 無需同步多個副本

3. **清晰的歷史**
   - Git 提交記錄就是演進軌跡
   - 可輕易回溯任何時間點的計劃狀態

4. **減少冗餘**
   - 計劃、進度、完成報告都在同一文件
   - 消除信息重複和過期文件

5. **更好的協作**
   - 團隊成員只需看一個文件
   - 合併衝突更少

### **何時使用其他形式**

某些情況下仍需其他文件：

- **指南文檔**（不會變化）：如 `PROJECT_STRUCTURE_GUIDE.md`
- **技能/最佳實踐**（共享知識）：如 `WORKING_METHODOLOGY.md`
- **架構決策**（參考資料）：如 `ADR_*.md` (Architecture Decision Records)

但不應該有：
- ❌ 狀態快照文件
- ❌ 版本號文件
- ❌ 日期帶後綴文件

---

## 💡 **實踐建議**

### **定期更新**
- 每天 5-10 分鐘更新計劃狀態
- 完成任務立即標記
- 遇到問題立即記錄

### **清晰的標記**
```markdown
✅ 完成
🔄 進行中
⏳ 待開始
⚠️ 被阻塞
📝 需要審查
🐛 發現問題
```

### **有意義的提交**
```bash
# ✅ 好
git commit -m "Task 1 complete: ZIP analysis reveals 10/10 core JSON files"

# ❌ 不好
git commit -m "update plan"
```

---

## 🔗 **相關資源**

- [Phase 2 計劃](../plan/plan%20for%20part%202.md) - 主要項目計劃
- [PROJECT_STRUCTURE_GUIDE.md](../PROJECT_STRUCTURE_GUIDE.md) - 架構指南

---

**版本：** 1.0  
**最後更新：** 2026年4月18日  
**作者：** Garmin RAG Project Team

---

## 📢 **反饋與改進**

如果此工作流有任何改進建議，請在相關項目計劃文件中記錄，並在團隊會議中討論。
