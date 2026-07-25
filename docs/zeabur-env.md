# Zeabur 環境變數清單

## Backend

```dotenv
ADMIN_EMAIL=你的管理員 Email
ADMIN_DISPLAY_NAME=Brady
ADMIN_PASSWORD=你的管理員密碼
VAPID_PUBLIC_KEY=產生的公鑰
VAPID_PRIVATE_KEY=產生的私鑰
VAPID_SUBJECT=mailto:你的聯絡 Email
```

保留既有：`APP_NAME`、`ENVIRONMENT`、`TIMEZONE`、`JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`DATABASE_URL`、PTT 與 Worker 相關設定。

## Crawler Worker

```dotenv
ADMIN_EMAIL=與 Backend 相同
ADMIN_DISPLAY_NAME=與 Backend 相同
ADMIN_PASSWORD=與 Backend 相同
VAPID_PUBLIC_KEY=與 Backend 相同
VAPID_PRIVATE_KEY=與 Backend 相同
VAPID_SUBJECT=與 Backend 相同
```

並保留：

```dotenv
ZBPACK_DOCKERFILE_PATH=Dockerfile.worker
```

## Frontend

不需要 VAPID 私鑰。保留：

```dotenv
BACKEND_HOST=${PTT_ALERT_HUB_HOST}
BACKEND_PORT=8080
```
