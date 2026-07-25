# PTT Alert Hub

PTT Alert Hub 是一個定時監控 PTT 看板文章列表的個人通知服務。

使用者可以自行註冊帳號，建立獨立的看板規則，例如：

- `Tech_Job` 看板，文章標題包含「徵才」。
- `TaichungBun` 看板，文章作者帳號等於 `andy123`。

Crawler Worker 會將啟用規則依看板分組，同一個看板每輪只爬一次，再分別比對每位使用者的規則。

## 目前開發階段

`feature/personal-accounts` 已完成第一階段：

- Email 自助註冊。
- Email 與密碼登入。
- Argon2 密碼雜湊。
- JWT 綁定資料庫使用者 ID。
- 每個使用者只能管理自己的規則。
- 每個使用者只能查看自己的命中紀錄。
- 系統設定、手動爬取與全站爬取紀錄只開放管理員。
- 既有規則會在資料庫升級時自動歸到 Bootstrap 管理員。
- 同一個 PTT 看板仍然只會爬一次，不會因使用者增加而重複請求。

下一階段預計加入：

- PWA 安裝。
- Service Worker。
- Web Push 訂閱。
- 每位使用者的手機與桌面推播通知。

目前 Telegram 為過渡通知方式，只會發送 Bootstrap 管理員自己的命中內容，避免其他使用者的資料被送到管理員 Chat ID。

## 系統架構

```text
瀏覽器 / PWA（下一階段）
        │
        ▼
React + Vite 管理介面
        │ /api
        ▼
FastAPI API
- 註冊 / 登入
- 個人規則
- 個人命中紀錄
- 管理員系統功能
        │
        ▼
PostgreSQL
- users
- rules
- seen_articles
- article_matches
- crawl_runs
- runtime_locks
- worker_state
        ▲
        │
Crawler Worker
- APScheduler
- Leader Lease
- Crawl Lock
- PTT 列表爬取
- 多使用者規則比對
```

## 權限模型

### 一般使用者

可以使用：

- 註冊與登入。
- 個人總覽。
- 個人規則 CRUD。
- 看板搜尋與看板驗證。
- 個人命中紀錄。

不能使用：

- 修改全域爬取頻率。
- 手動觸發全站爬取。
- 查看全站爬取紀錄。
- 測試管理員 Telegram 通知。

### 系統管理員

Bootstrap 管理員除了一般功能外，還可以：

- 修改全域爬取頻率。
- 手動執行爬取。
- 查看全站爬取紀錄。
- 測試 Telegram 通知。

## 密碼安全

密碼不會以明文寫入資料庫。

Backend 使用 `pwdlib[argon2]` 產生與驗證 Argon2 密碼雜湊。

JWT 的 `sub` 儲存使用者資料庫 ID，不再使用固定管理員名稱。

## 環境變數

建立本機環境設定：

```bash
cp .env.example .env
```

至少修改：

```dotenv
ADMIN_EMAIL=你的管理員Email
ADMIN_DISPLAY_NAME=你的顯示名稱
ADMIN_PASSWORD=請換成強密碼
JWT_SECRET=請換成長度足夠的隨機字串

POSTGRES_PASSWORD=請換成資料庫強密碼

TELEGRAM_BOT_TOKEN=你的BotToken
TELEGRAM_CHAT_ID=你的ChatID
```

Windows PowerShell 產生 JWT Secret：

```powershell
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$rng.Dispose()
$jwt_secret = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
$jwt_secret
```

### 管理員相容行為

新版本優先讀取：

```dotenv
ADMIN_EMAIL=admin@example.com
```

若部署環境仍只有舊的：

```dotenv
ADMIN_USERNAME=admin
```

系統會建立：

```text
admin@local.invalid
```

建議部署前明確新增 `ADMIN_EMAIL`，避免忘記實際登入 Email。

## Docker Compose

啟動：

```bash
docker compose up --build -d
```

開啟：

- 前端：<http://localhost:8080>
- Swagger：<http://localhost:8000/docs>
- Health Check：<http://localhost:8000/api/health>

查看 Log：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

## 本機開發

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

### Crawler Worker

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Zeabur 服務

同一個 GitHub Repo 建立四個服務：

| 服務 | Root Directory | Dockerfile | 公開網域 |
|---|---|---|---|
| PostgreSQL | 不適用 | Zeabur Database | 否 |
| Backend | `backend` | `Dockerfile` | 否 |
| Crawler Worker | `backend` | `Dockerfile.worker` | 否 |
| Frontend | `frontend` | `Dockerfile` | 是 |

### Backend 環境變數

```dotenv
APP_NAME=PTT Alert Hub
ENVIRONMENT=production
TIMEZONE=Asia/Taipei

ADMIN_EMAIL=你的管理員Email
ADMIN_DISPLAY_NAME=你的顯示名稱
ADMIN_PASSWORD=你的強密碼
JWT_SECRET=你的JWTSecret
JWT_EXPIRE_MINUTES=1440

DATABASE_URL=${POSTGRES_CONNECTION_STRING}

TELEGRAM_BOT_TOKEN=你的BotToken
TELEGRAM_CHAT_ID=你的ChatID

PTT_BASE_URL=https://www.ptt.cc
PTT_REQUEST_DELAY_SECONDS=2.0
PTT_TIMEOUT_SECONDS=15
CRAWL_LOCK_TTL_SECONDS=1800

WORKER_SYNC_SECONDS=10
WORKER_LEASE_TTL_SECONDS=30
WORKER_HEARTBEAT_TIMEOUT_SECONDS=45
```

### Crawler Worker 環境變數

```dotenv
ZBPACK_DOCKERFILE_PATH=Dockerfile.worker
ENVIRONMENT=production
TIMEZONE=Asia/Taipei
DATABASE_URL=${POSTGRES_CONNECTION_STRING}
TELEGRAM_BOT_TOKEN=你的BotToken
TELEGRAM_CHAT_ID=你的ChatID
PTT_BASE_URL=https://www.ptt.cc
PTT_REQUEST_DELAY_SECONDS=2.0
PTT_TIMEOUT_SECONDS=15
CRAWL_LOCK_TTL_SECONDS=1800
WORKER_SYNC_SECONDS=10
WORKER_LEASE_TTL_SECONDS=30
WORKER_HEARTBEAT_TIMEOUT_SECONDS=45
```

### Frontend 環境變數

```dotenv
BACKEND_HOST=${PTT_ALERT_HUB_HOST}
BACKEND_PORT=8080
```

Frontend Nginx 會監聽 Zeabur 注入的 `$PORT`。

## 資料庫升級

API 與 Worker 啟動時會：

1. 建立 `users` 資料表。
2. 檢查 `rules.user_id`。
3. 檢查 `article_matches.user_id`。
4. 建立缺少的索引。
5. 建立 Bootstrap 管理員。
6. 將舊規則與舊命中回填給 Bootstrap 管理員。

PostgreSQL 初始化期間會使用 Advisory Lock，避免 Backend 與 Worker 同時修改結構。

這一階段仍採輕量升級程序；後續資料模型變複雜時應導入 Alembic。

## 一分鐘排程

管理員可以設定：

```text
執行間隔：1 分鐘
每個看板掃描：1 頁
```

限制：

- 一分鐘模式最多掃描每板 2 頁。
- 建議每板 1 頁。
- PTT 請求之間至少間隔 2 秒。
- `429`、`500`、`502`、`503`、`504` 會退避重試。
- 多個使用者監控同一個看板時，每輪仍只爬一次。

## 測試

Backend：

```bash
cd backend
pytest
```

Frontend：

```bash
cd frontend
npm run build
```

## 專案結構

```text
PTT-Alert-Hub/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ services/
│  │  ├─ main.py
│  │  ├─ worker.py
│  │  ├─ database.py
│  │  └─ models.py
│  ├─ tests/
│  ├─ Dockerfile
│  ├─ Dockerfile.worker
│  └─ pyproject.toml
├─ frontend/
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

## License

MIT
