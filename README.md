# Gama_PM

Gama 專案月報的公開頁面（GitHub Pages）：選月份，看當月各版本的進度分類。純靜態單頁 `index.html`，只讀 `data/` 下的 `manifest.json` 與 `YYYY-MM.json`，沒有後端。

- 資料來源：GitHub Actions（`.github/workflows/sync.yml`）每天台灣時間 08:00 用 service account 從 Google Drive 拉月報 JSON 到 `data/`，有變動才 commit。設定放 repo secrets（`DRIVE_FOLDER_ID`、`SERVICE_ACCOUNT_JSON`）。
- 與 gama-pm-dashboard 的關係：dashboard 的「月報」tab 讀同格式的月報資料；本 repo 是月報的免登入公開副本。
- 失敗通知：同步失敗時 workflow 會推 Telegram（secrets `TG_TOKEN`、`TG_CHAT_ID`）。
- 注意：這是 public repo，不要放內網位址、帳密或 Drive 資料夾 ID。
