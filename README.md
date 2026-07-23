# PTT Alert Hub

PTT 定時爬蟲與通知規則管理後台。

你可以建立多條監控規則，例如：

- `Tech_Job` 看板，文章標題包含「徵才」。
- `TaichungBun` 看板，文章作者帳號完全符合 `andy123`。

系統會依排程抓取各看板最新文章列表，以文章網址去重，並將同一輪命中的文章合併成一則 Telegram 通知。

## v5 架構調整

v5 已將 API 與定時爬蟲拆成不同程序：

- `backend`：FastAPI、JWT、規則管理、查詢紀錄、手動爬取。
- `crawler-worker`：APScheduler 與定時爬取。
- `database`：PostgreSQL，共享規則、已讀文章、命中、執行紀錄、Worker 狀態與鎖。
- `frontend`：React 管理後台。

API 可以水平擴充成多個 Replica。Crawler Worker 使用資料庫 Leader Lease 選出唯一主節點；即使 Worker 不小心開了兩份，也只有其中一份會建立定時爬取工作。

每次爬取前還會取得全域 Crawl Lock，因此以下情況也不會同時爬 PTT：

- 排程執行時有人按「立即爬取」。
- 多個 API Replica 同時收到手動爬取請求。
- Worker 主節點切換時短暫重疊。

## 系統架構

```text
┌────────────────────────┐
│ React 管理後台          │
└────────────┬───────────┘
             │ /api
┌────────────▼───────────┐
│ FastAPI API             │  可多 Replica
│ JWT / REST / 手動爬取   │
└────────────┬───────────┘
             │
┌────────────▼───────────┐
│ PostgreSQL              │
│ 規則 / 紀錄 / Lease     │
└────────────┬───────────┘
             │
┌────────────▼───────────┐
│ Crawler Worker          │
│ APScheduler / PTT       │
│ Leader Lease / Crawl Lock│
└────────────┬───────────┘
             │
┌────────────▼───────────┐
│ Telegram Bot API        │
└────────────────────────┘
```

## 主要功能

- React + Vite + TypeScript 管理後台。
- FastAPI REST API。
- 獨立 APScheduler Worker。
- PostgreSQL 多服務共享資料。
- Worker Leader Lease 與自動接手。
- 全域 Crawl Lock，避免重複爬取與重複通知。
- 支援標題包含關鍵字。
- 支援作者帳號完全符合。
- 熱門看板、搜尋看板與分類瀏覽。
- 建立規則前實際驗證 PTT 看板。
- 使用文章網址永久去重。
- Telegram 傳送失敗時保留待通知紀錄。
- 同一輪多個命中合併成一則通知。
- 一分鐘排程模式。
- Docker Compose 一鍵啟動。

## 快速啟動

### 1. 建立環境變數

```bash
cp .env.example .env
```

至少修改：

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=請換成強密碼
JWT_SECRET=請換成長度足夠的隨機字串

POSTGRES_PASSWORD=請換成資料庫強密碼

TELEGRAM_BOT_TOKEN=你的 Bot Token
TELEGRAM_CHAT_ID=你的 Chat ID
```

可產生 JWT Secret：

```bash
openssl rand -hex 32
```

### 2. 啟動

```bash
docker compose up --build -d
```

開啟：

- 管理後台：<http://localhost:8080>
- Swagger：<http://localhost:8000/docs>
- API Health Check：<http://localhost:8000/api/health>

查看所有 Log：

```bash
docker compose logs -f
```

只看 Worker：

```bash
docker compose logs -f crawler-worker
```

停止服務：

```bash
docker compose down
```

PostgreSQL 資料保存在 Docker Volume `database-data`。確定要刪除全部資料時才使用：

```bash
docker compose down -v
```

## 本機開發

### Backend API

```bash
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
$env:DATABASE_URL="postgresql+psycopg://ptt_alert_hub:password@localhost:5432/ptt_alert_hub"
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

### Crawler Worker

另開一個終端機，使用相同的 `DATABASE_URL`：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql+psycopg://ptt_alert_hub:password@localhost:5432/ptt_alert_hub"
python -m app.worker
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

開發環境網址：<http://localhost:5173>

## 建立規則

### Tech_Job 標題包含「徵才」

```text
規則名稱：Tech_Job 徵才
看板：Tech_Job
比對方式：標題包含關鍵字
關鍵字：徵才
```

### TaichungBun 指定作者

```text
規則名稱：TaichungBun andy123
看板：TaichungBun
比對方式：作者帳號完全符合
作者帳號：andy123
```

台中板實際代號是 `TaichungBun`；輸入 `Taichung` 時會自動校正。

## 一分鐘排程

後台可設定：

```text
執行間隔：1 分鐘
每個看板掃描頁數：1 頁
```

限制：

- 執行間隔為 1 分鐘時，每個看板最多掃描 2 頁。
- 建議使用 1 頁。
- 所有 PTT 頁面請求至少間隔 2 秒。
- 遇到 `429`、`500`、`502`、`503`、`504` 時自動退避重試。
- 同一篇文章不會重複通知。
- 上一輪尚未完成時，下一輪不會重疊執行。

設定儲存後，Crawler Worker 預設會在 10 秒內讀取新頻率並重新排程。

## 多 Replica 行為

### Backend API

Backend API 可以設定多個 Replica，因為 API 本身不會啟動 APScheduler。所有 Replica 必須連到同一個 PostgreSQL。

### Crawler Worker

建議 Worker 維持 1 Replica，節省資源；但即使平台誤設為 2 個以上，Worker 也會透過資料庫租約選出唯一 Leader。

- Leader 每 10 秒更新租約與 Heartbeat。
- 租約預設 30 秒失效。
- Leader 中斷後，其他 Worker 可以接手。
- 後台「下次排程」資料來自 Worker 寫入 PostgreSQL 的狀態，不依賴特定 API Replica 的記憶體。

### 手動爬取

「立即爬取」仍由收到請求的 API Replica 執行，但會先取得與 Worker 共用的全域 Crawl Lock。因此手動爬取與定時爬取不會同時執行。

## Zeabur 部署方式

建議建立四個服務：

1. PostgreSQL
2. Backend API
3. Crawler Worker
4. Frontend

Backend API 與 Crawler Worker 使用相同 Backend Dockerfile，但啟動命令不同。

### Backend API 啟動命令

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Crawler Worker 啟動命令

```text
python -m app.worker
```

兩個服務都必須設定同一組：

```dotenv
DATABASE_URL=postgresql+psycopg://...
ADMIN_USERNAME=...
ADMIN_PASSWORD=...
JWT_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TIMEZONE=Asia/Taipei
```

建議 Replica：

```text
Backend API：1 或更多
Crawler Worker：1
Frontend：1 或更多
PostgreSQL：平台管理
```

雖然 Crawler Worker 已支援多副本防重，但沒有流量需要分攤，維持 1 個即可。

## 通知行為

一次爬取中的所有新命中文章會合併成一則 Telegram 訊息：

```text
🔔 PTT 新文章通知
本次共 2 篇文章符合 2 條規則。

【Tech_Job】
• [徵才] React 前端工程師
  作者：company_hr
  命中：Tech_Job 徵才

【TaichungBun】
• [閒聊] 台中活動分享
  作者：andy123
  命中：TaichungBun andy123
```

Telegram 單則文字若放不下全部文章，剩餘待通知項目會保留到下一輪；每輪最多傳送一則。

## 舊文章與去重

- 不會通知規則建立前的舊文章。
- 每篇文章以 PTT 文章網址作為唯一鍵。
- 已掃描但未命中的文章也會標記為已讀。
- 新增規則後不會回頭把已讀文章補通知。
- Telegram 傳送失敗時，命中紀錄維持待通知。

## 環境變數

| 名稱 | 說明 | 預設值 |
|---|---|---|
| `APP_NAME` | 系統名稱 | `PTT Alert Hub` |
| `ENVIRONMENT` | 執行環境 | `production` |
| `TIMEZONE` | 排程時區 | `Asia/Taipei` |
| `ADMIN_USERNAME` | 後台帳號 | `admin` |
| `ADMIN_PASSWORD` | 後台密碼 | `change-me-now` |
| `JWT_SECRET` | JWT 簽章密鑰 | 必須修改 |
| `JWT_EXPIRE_MINUTES` | 登入憑證有效分鐘 | `1440` |
| `DATABASE_URL` | PostgreSQL 連線字串 | 本機程式預設可使用 SQLite |
| `POSTGRES_DB` | Compose PostgreSQL DB | `ptt_alert_hub` |
| `POSTGRES_USER` | Compose PostgreSQL User | `ptt_alert_hub` |
| `POSTGRES_PASSWORD` | Compose PostgreSQL Password | 必須修改 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 空白 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 空白 |
| `PTT_REQUEST_DELAY_SECONDS` | PTT 請求最小間隔 | `2.0` |
| `PTT_TIMEOUT_SECONDS` | HTTP Timeout | `15` |
| `CRAWL_LOCK_TTL_SECONDS` | 異常中斷後 Crawl Lock 最長保留秒數 | `1800` |
| `WORKER_SYNC_SECONDS` | Worker 同步設定與租約秒數 | `10` |
| `WORKER_LEASE_TTL_SECONDS` | Worker Leader 租約秒數 | `30` |
| `WORKER_HEARTBEAT_TIMEOUT_SECONDS` | 後台判定 Worker 離線秒數 | `45` |
| `CORS_ORIGINS` | 跨來源白名單 | localhost |

## 資料庫初始化

API 與 Worker 啟動時都會確認資料表存在。使用 PostgreSQL 時，初始化會先取得 PostgreSQL Advisory Lock，避免多個 Replica 同時建立資料表而互相衝突。

目前專案使用 SQLAlchemy `create_all`，尚未導入 Alembic。正式長期維護並需要修改既有欄位時，建議再加入 Alembic Migration。

## PTT 爬取範圍

爬蟲只讀取 PTT 網頁版的看板文章列表，不抓文章全文或推文。請保持合理頻率，並自行確認部署與使用方式符合 PTT 規範。

## 測試

```bash
cd backend
pytest
```

## 專案結構

```text
ptt-alert-hub/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ services/
│  │  │  ├─ distributed_lock.py
│  │  │  ├─ scheduler_service.py
│  │  │  └─ crawl_service.py
│  │  ├─ main.py             # FastAPI API
│  │  ├─ worker.py           # Crawler Worker
│  │  ├─ database.py
│  │  └─ models.py
│  ├─ tests/
│  ├─ Dockerfile
│  └─ pyproject.toml
├─ frontend/
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

## License

MIT

## v6 Zeabur 相容調整

- Frontend Nginx 改用 `BACKEND_HOST` 與 `BACKEND_PORT`，可連到 Zeabur 私有網路中的 Backend。
- 新增 `backend/Dockerfile.worker`，Crawler Worker 不必再手動覆寫啟動命令。
- Backend 會使用 Zeabur 注入的 `PORT`，本機預設仍為 `8000`。
- `DATABASE_URL` 可直接使用 Zeabur 的 `${POSTGRES_CONNECTION_STRING}`；程式會自動轉成 psycopg 3 的 SQLAlchemy URL。
