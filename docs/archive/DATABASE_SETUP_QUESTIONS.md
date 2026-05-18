# Garmin RAG 項目 - 資料庫設置常見問題與解決方案

**建立日期：** 2026年4月18日  
**項目：** 本地 PostgreSQL + pgvector 資料庫設置

---

## 疑問 1：Docker Daemon 如何確認在運行？

**問題：**
執行 `docker-compose up -d` 時出現錯誤訊息，無法啟動容器

**根本問題：**
Docker daemon 未運行

**錯誤訊息：**
```
unable to get image 'pgvector/pgvector:pg16': Cannot connect to the Docker daemon 
at unix:///Users/sophieliu/.docker/run/docker.sock. Is the docker daemon running?
```

**解決方案：**
1. 執行 `docker ps` 檢查連線狀態
2. 若失敗，在 macOS 執行 `open /Applications/Docker.app` 啟動 Docker Desktop
3. 等待 1-2 分鐘讓 daemon 完全啟動
4. 再次執行 `docker ps` 驗證

**其他小筆記：**
- 你已確認 Docker 可用（執行過 `docker --help`）
- 重啟 Docker Desktop 後應該就能正常運作

---

## 疑問 2：如何透過 Microsoft 工具連接到 PostgreSQL？

**問題：**
想使用 Microsoft 的工具連接本地 PostgreSQL 資料庫

**根本問題：**
不知道有哪些 Microsoft 工具可以連接 PostgreSQL

**解決方案：**
有多種選擇：

1. **VS Code PostgreSQL Extension（推薦）**
   - 在 VS Code 安裝 PostgreSQL 擴展
   - 側邊欄新增連線，填入 localhost、5432、postgres、test123、vectordb
   - 可直接在 VS Code 執行 SQL 查詢

2. **DBeaver Community**（獨立工具）
   - 下載安裝 DBeaver
   - 新建 PostgreSQL 連線
   - 填入同樣的連線資訊

3. **pgAdmin 4**（Web 管理介面）
   - 在 docker-compose.yml 新增 pgAdmin 服務
   - 從瀏覽器訪問 `http://localhost:5050`

4. **psql**（命令行工具）
   - 執行 `brew install postgresql` 安裝 PostgreSQL client
   - 使用 `psql -h localhost -U postgres -d vectordb -p 5432`

**其他小筆記：**
- VS Code PostgreSQL Extension 是最方便的選擇
- 所有工具都使用相同的連線資訊：localhost:5432、user: postgres、password: test123

---

## 疑問 3：如何確認 pgvector 擴展已安裝？

**問題：**
不確定 pgvector 擴展是否真的安裝在資料庫中

**根本問題：**
缺乏驗證方法

**解決方案：**
有三種方法驗證：

1. **使用 psql 命令行（最直接）**
   ```bash
   psql -h localhost -U postgres -d vectordb -p 5432
   # 密碼：test123
   
   vectordb=# SELECT * FROM pg_extension WHERE extname = 'vector';
   ```
   看到結果表示已安裝

2. **使用 VS Code PostgreSQL Extension**
   - 新建查詢
   - 執行 SQL：`SELECT * FROM pg_extension WHERE extname = 'vector';`
   - 在結果面板查看

3. **使用 Python + psycopg2（我們最終採用的方式）**
   ```bash
   python scripts/test_db_connection.py
   ```
   輸出 `✅ pgvector 已安裝` 表示成功

**其他小筆記：**
- 最可靠的是 Python 測試方法，因為它同時測試連線和擴展
- 如果擴展未安裝，Python 腳本會自動執行 `CREATE EXTENSION IF NOT EXISTS vector;`

---

## 疑問 4：VS Code PostgreSQL Extension 連線失敗 - 資料庫名稱錯誤

**問題：**
VS Code PostgreSQL Extension 無法連接到資料庫

**錯誤訊息：**
```
pgsql: Failed to connect: Connection error: connection failed: connection to 
server at "127.0.0.1", port 5432 failed: FATAL: database "vsctordb" does not exist
```

**根本問題：**
資料庫名稱拼錯了
- 輸入的：`vsctordb` ❌
- 正確的：`vectordb` ✅

**解決方案：**
修正 VS Code PostgreSQL Extension 中的連線設定：
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Password: `test123`
- Database: `vectordb` ← **確保拼寫正確**

**其他小筆記：**
- 這是最常見的連線失敗原因之一
- 確認 docker-compose.yml 中的 `POSTGRES_DB=vectordb` 設定

---

## 疑問 5：在 docker-compose.yml 新增 pgAdmin 服務是否會增加運算效能負擔？

**問題：**
擔心新增 pgAdmin 會增加系統運算負擔

**根本問題：**
不知道 pgAdmin 的資源消耗量

**解決方案：**
不會有顯著影響

**詳細分析：**

| 項目 | 影響程度 |
|-----|--------|
| pgAdmin 容器記憶體佔用 | 約 100-200 MB（輕量級） |
| Postgres 資料庫本身 | 完全不受影響 |
| 開發環境機器 | 可忽略（本地有充足資源） |
| 部署環境 | 只有資源非常有限時才考慮 |

**何時應該移除 pgAdmin：**
- 只有在資源極度有限的環境（如樹莓派）才考慮移除
- 一般開發機器沒必要移除

**其他小筆記：**
- pgAdmin 很方便用來視覺化查看資料庫結構
- 如果偏好用 psql 或 VS Code 就夠了，pgAdmin 是可選的
- docker-compose.yml 中新增 pgAdmin 的範例：
  ```yaml
  pgadmin:
    image: dpage/pgadmin4:latest
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    depends_on:
      - db
  ```

---

## 疑問 6：psql 會在哪裡執行？

**問題：**
不知道 psql 命令應該在哪個環境執行

**根本問題：**
對命令行工具和容器的連接方式不了解

**解決方案：**
psql 在 **本地 macOS 終端機** 執行

**詳細流程：**
```
Mac 終端機 
  → psql 客戶端（本地安裝）
  → 連接到 localhost:5432
  → Docker 容器中的 Postgres
```

**前置步驟：**
1. 先安裝 PostgreSQL client：`brew install postgresql`
2. 再執行 psql 命令

**執行方式：**
```bash
psql -h localhost -U postgres -d vectordb -p 5432
# 輸入密碼：test123
```

**其他小筆記：**
- psql 是本地工具，不在 Docker 容器內執行
- 它通過網路連接到容器內的 Postgres
- 你已經確認 Docker 容器在 port 5432 對外開放

---

## 疑問 7：VS Code PostgreSQL Extension 中「New Query」vs「Run Query」的區別

**問題：**
不知道這兩個選項的區別和各自的用途

**根本問題：**
對 VS Code 擴展的操作方式不熟悉

**解決方案：**

| 選項 | 功能 | 何時用 | 操作步驟 |
|-----|------|--------|---------|
| **New Query** | 開啟新的 SQL 編輯器視窗 | 寫長的 SQL 或想保存查詢 | 資料庫右鍵 → New Query → 輸入 SQL → Ctrl+Enter |
| **Run Query** | 直接執行預先選中的 SQL 文本 | 快速執行小段 SQL | 先選中 SQL 文本 → 右鍵 → Run Query |

**使用情境：**
- **新建查詢驗證 pgvector：** 用 New Query
- **執行 SELECT 1 快速測試：** 用 Run Query

**其他小筆記：**
- New Query 會建立可保存的 `.sql` 檔案
- Run Query 適合臨時、一次性的查詢
- 兩種方式都能執行 SQL，區別只在工作流程

---

## 疑問 8：psql 命令找不到

**問題：**
執行 psql 時出現 `command not found` 錯誤

**錯誤訊息：**
```
zsh: command not found: psql
```

**根本問題：**
PostgreSQL client 工具未安裝在系統上

**解決方案：**
```bash
# 用 Homebrew 安裝 PostgreSQL client
brew install postgresql

# 驗證安裝成功
psql --version

# 連接到資料庫
psql -h localhost -U postgres -d vectordb -p 5432
```

**其他小筆記：**
- 這只需要做一次
- 安裝後 psql 就可以在任何目錄使用

---

## 疑問 9：VS Code PostgreSQL Extension 執行查詢但沒有結果輸出

**問題：**
在 VS Code PostgreSQL Extension 中執行查詢，但看不到結果

**根本問題：**
結果面板可能在另一個標籤頁，或 VS Code 擴展設定有問題

**解決方案：**
1. **檢查結果面板位置**
   - 結果應該出現在：下方的「輸出」面板、新的「結果」分頁，或側邊欄查詢結果區域
   - 嘗試在不同面板切換查看

2. **先執行簡單查詢測試**
   ```sql
   SELECT 1;
   ```
   - 如果也看不到結果，表示 VS Code 擴展有問題

3. **重新啟動 VS Code**
   - 有時擴展會出現暫時故障

4. **改用 psql 命令行驗證**
   - 這樣可以確認資料庫本身沒問題

**其他小筆記：**
- psql 命令行是最可靠的驗證方式
- 如果 psql 能看到結果而 VS Code 不行，表示是擴展問題

---

## 疑問 10：如何在虛擬環境中執行 Python？

**問題：**
執行 Python 和 pip 命令時出現 `command not found` 錯誤

**錯誤訊息：**
```
zsh: command not found: python
zsh: command not found: pip
zsh: command not found: py
```

**根本問題：**
Python 虛擬環境（venv）沒有被激活

**解決方案：**

1. **激活虛擬環境（推薦方式）**
   ```bash
   source rag.venv/bin/activate
   ```
   - 看到提示符前出現 `(rag.venv)` 表示已激活
   - 激活後 `python` 和 `pip` 就可用了

2. **激活後就能正常使用：**
   ```bash
   # 安裝套件
   pip install psycopg2-binary

   # 執行 Python 指令稿
   python scripts/test_db_connection.py
   ```

3. **替代方案（不激活 venv）**
   ```bash
   # 直接使用 venv 的完整路徑
   ./rag.venv/bin/python scripts/test_db_connection.py
   ./rag.venv/bin/pip install psycopg2-binary
   ```

**其他小筆記：**
- 激活 venv 只在當前終端機視窗有效
- 重新開啟終端機需要再次激活
- 推薦方式是激活 venv，這樣會更方便
- 提示符會顯示 `(rag.venv)` 是激活的視覺提示

---

## 📚 快速參考

### 資料庫連線資訊
```
Host:     localhost
Port:     5432
User:     postgres
Password: test123
Database: vectordb
```

### 常用命令
```bash
# 激活虛擬環境
source rag.venv/bin/activate

# 啟動 Docker 容器
docker-compose up -d

# 檢查容器狀態
docker-compose ps

# 安裝 psycopg2-binary
pip install psycopg2-binary

# 運行連線測試
python scripts/test_db_connection.py

# 用 psql 連接資料庫
psql -h localhost -U postgres -d vectordb -p 5432
```

### 相關檔案位置
- `docker-compose.yml` - Docker 配置
- `requirements.txt` - Python 依賴
- `scripts/test_db_connection.py` - 資料庫連線測試
- `rag.venv/` - Python 虛擬環境

---

**最後更新時間：** 2026年4月18日
