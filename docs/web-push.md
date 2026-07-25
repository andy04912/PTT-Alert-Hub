# Web Push 與 PWA 推播部署

PTT Alert Hub 使用標準 Web Push。使用者不需要提供 Telegram Bot Token，只要安裝 PWA 並允許通知，即可在規則命中新文章時收到推播。

## 架構

```text
瀏覽器 / iPhone PWA
  ↓ Push Subscription
FastAPI Backend
  ↓ 儲存 endpoint、p256dh、auth
PostgreSQL
  ↑
Crawler Worker
  ↓ VAPID 簽章
瀏覽器 Push Service
  ↓
使用者裝置通知
```

Backend 只負責註冊與管理訂閱；實際排程命中通知由 Crawler Worker 發送。因此 Backend 與 Crawler Worker 必須使用完全相同的 VAPID 金鑰。

## 1. 產生 VAPID 金鑰

在安裝過 Backend 依賴的環境中執行：

```bash
cd backend
python scripts/generate_vapid_keys.py
```

輸出格式：

```dotenv
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:admin@example.com
```

每個正式環境只需要產生一次。請妥善保存私鑰；若更換 VAPID 金鑰，現有瀏覽器訂閱可能需要重新啟用。

## 2. Zeabur 環境變數

在 **Backend API** 與 **Crawler Worker** 兩個服務都加入相同內容：

```dotenv
VAPID_PUBLIC_KEY=產生的公鑰
VAPID_PRIVATE_KEY=產生的私鑰
VAPID_SUBJECT=mailto:你的聯絡信箱
```

注意：

- `VAPID_PUBLIC_KEY` 可以提供給瀏覽器。
- `VAPID_PRIVATE_KEY` 只能存放在 Zeabur Secret／環境變數，不可提交到 GitHub。
- `VAPID_SUBJECT` 建議使用可聯絡的 `mailto:` Email。
- Backend 與 Worker 金鑰不一致時，瀏覽器可以訂閱，但排程推播會失敗。

設定後依序重新部署：

1. Backend API
2. Crawler Worker
3. Frontend

## 3. 資料庫升級

Backend 或 Worker 啟動時會自動：

- 建立 `push_subscriptions` 資料表。
- 新增 `article_matches.push_notified_at`。
- 建立相關索引。

現有規則與命中紀錄不會被刪除。

第一次啟用推播裝置時，系統會把該使用者既有命中標記為已處理，只推送啟用後的新文章，避免歷史通知一次湧入。

## 4. 使用者啟用方式

### iPhone / iPad

1. 使用 Safari 開啟 PTT Alert Hub。
2. 點擊「分享」。
3. 選擇「加入主畫面」。
4. 從主畫面開啟 PTT Alert Hub。
5. 登入後進入「推播通知」。
6. 點擊「啟用這台裝置」。
7. 同意系統通知權限。
8. 點擊「發送測試通知」確認。

iPhone／iPad 必須從加入主畫面的 PWA 開啟，才能使用 Web Push。

### Android / Windows / macOS

1. 使用支援 PWA 的瀏覽器開啟網站。
2. 安裝 PTT Alert Hub，或直接進入「推播通知」。
3. 點擊「啟用這台裝置」。
4. 同意通知權限。
5. 發送測試通知。

## 5. 通知行為

- 一篇文章命中：點擊通知直接開啟該篇 PTT 文章。
- 多篇文章命中：點擊通知開啟「命中紀錄」。
- 同一帳號可連結多台裝置。
- Push Service 回傳 `404` 或 `410` 時，系統會自動停用失效訂閱。
- Telegram 與 Web Push 使用不同的送達欄位，彼此不會互相跳過。
- Telegram 未設定時不會影響 Web Push。

## 6. 安全注意事項

- API 不會將 VAPID 私鑰回傳給前端。
- Push Endpoint 不會顯示在裝置列表中。
- 所有訂閱 API 都需要 JWT，並依目前登入使用者隔離。
- Service Worker 不快取 `/api`，避免帳號或個人資料進入 Cache Storage。
- 網站必須透過 HTTPS 部署；Zeabur 公開網域已符合此要求。
