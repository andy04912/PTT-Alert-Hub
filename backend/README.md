# PTT Alert Hub Backend

同一份 Python Package 提供兩種程序：

- API：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Crawler Worker：`python -m app.worker`

API 不啟動排程器；Worker 使用 APScheduler、資料庫 Leader Lease 與 Crawl Lock，確保多程序環境下只有一個排程工作實際爬取 PTT。
