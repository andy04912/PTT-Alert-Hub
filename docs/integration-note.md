# Stacked PR 整合說明

原本的 PWA 與 Web Push 分支建立於個人帳號分支之上。由於個人帳號 PR 使用 Squash Merge，後續 stacked branch 不再共享相同提交歷史，因此本分支從最新 `main` 重新套用最終檔案內容，避免將重複提交與衝突帶入正式分支。
