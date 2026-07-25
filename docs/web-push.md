# Web Push 與 PWA 推播部署

PTT Alert Hub 使用標準 Web Push。使用者安裝 PWA 並允許通知後，規則命中新文章時即可收到推播。

## 架構

```text
PWA / 瀏覽器
  ↓ Push Subscription
FastAPI Backend
  ↓ PostgreSQL
Crawler Worker
  ↓ VAPID 簽章
瀏覽器 Push Service
  ↓
使用者裝置通知
```

Backend 負責註冊與管理訂閱；Crawler Worker 負責排程命中後發送。因此 Backend 與 Worker 必須使用完全相同的 VAPID 金鑰。

## 產生 VAPID 金鑰

```bash
cd backend
python scripts/generate_vapid_keys.py
```

輸出：

```dotenv
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:admin@example.com
```

每個正式環境只需產生一次。私鑰不可提交到 GitHub。

## Zeabur 環境變數

Backend API 與 Crawler Worker 都加入相同內容：

```dotenv
VAPID_PUBLIC_KEY=產生的公鑰
VAPID_PRIVATE_KEY=產生的私鑰
VAPID_SUBJECT=mailto:你的聯絡信箱
```

設定後依序重新部署：

1. Backend API
2. Crawler Worker
3. Frontend

## 資料庫升級

啟動時會自動：

- 建立 `push_subscriptions`
- 新增 `article_matches.push_notified_at`
- 建立相關索引

既有規則與命中資料不會被刪除。第一次啟用推播時，系統會把該使用者既有命中標記為已處理，只推送啟用後的新文章。

## iPhone / iPad

1. 用 Safari 開啟網站
2. 點擊「分享」
3. 選擇「加入主畫面」
4. 從主畫面開啟 PTT Alert Hub
5. 登入後進入「推播通知」
6. 點擊「啟用這台裝置」
7. 同意通知權限
8. 發送測試通知

## 通知行為

- 一篇文章命中：點擊通知直接開啟 PTT 原文
- 多篇文章命中：點擊通知開啟命中紀錄
- 同一帳號可連結多台裝置
- Push Service 回傳 404 或 410 時會自動停用失效訂閱
- Telegram 與 Web Push 各自記錄送達狀態
- Telegram 未設定時不影響 Web Push
