#!/usr/bin/env python3
"""
GAMA 月報同步腳本
從 Google Sheets 撈取資料，產生月報 JSON 檔案

使用方式：
  python scripts/fetch_sheets.py

環境變數（需在 GitHub Actions Secrets 設定）：
  GOOGLE_SHEETS_ID     - Google Sheet 的 ID（URL 中的長字串）
  GOOGLE_SERVICE_ACCOUNT_JSON - Service Account 金鑰 JSON 字串
"""

import os
import json
import re
from pathlib import Path
from datetime import date, datetime
from collections import defaultdict

# ── Google Sheets API ──────────────────────────────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ 缺少依賴，請執行：pip install gspread google-auth")
    raise

# ── 設定 ───────────────────────────────────────────────────────────────────────
SHEET_ID = os.environ["GOOGLE_SHEETS_ID"]
SA_JSON  = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]  # JSON 字串

# Google Sheets 分頁名稱對應
TAB_RELEASED   = "Released"    # 欄位：Year, Month, End Date, Project Name, Summary
TAB_TESTING    = "Testing"     # 欄位：Year, Month, Start Date, Project Name, Summary
TAB_IN_PROGRESS = "InProgress" # 欄位：Year, Month, Project Name, Summary

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 連線 Google Sheets ─────────────────────────────────────────────────────────
def get_sheet_client():
    sa_info = json.loads(SA_JSON)
    creds = Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return gspread.authorize(creds)

# ── 讀取分頁資料（自動跳過空列） ───────────────────────────────────────────────
def read_tab(sheet, tab_name):
    ws = sheet.worksheet(tab_name)
    rows = ws.get_all_records()
    return [r for r in rows if any(str(v).strip() for v in r.values())]

# ── 日期格式化 ─────────────────────────────────────────────────────────────────
def fmt_date(val):
    """將各種日期格式統一為 YYYY-MM-DD"""
    if not val:
        return ""
    val = str(val).strip()
    # 已是 YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", val):
        return val
    # MM/DD/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", val)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    # YYYY/MM/DD
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", val)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return val

# ── 主流程 ─────────────────────────────────────────────────────────────────────
def main():
    today = date.today().isoformat()
    print(f"🔄 同步開始 {today}")

    client = get_sheet_client()
    sheet  = client.open_by_key(SHEET_ID)

    # 讀取三個分頁
    released_rows    = read_tab(sheet, TAB_RELEASED)
    testing_rows     = read_tab(sheet, TAB_TESTING)
    in_progress_rows = read_tab(sheet, TAB_IN_PROGRESS)

    # 依 (year, month) 分組
    months: dict[tuple, dict] = defaultdict(lambda: {
        "released": [], "testing": [], "inProgress": []
    })

    for r in released_rows:
        key = (int(r["Year"]), int(r["Month"]))
        months[key]["released"].append({
            "endDate": fmt_date(r.get("End Date", "")),
            "name":    str(r.get("Project Name", "")).strip(),
            "summary": str(r.get("Summary", "")).strip(),
        })

    for r in testing_rows:
        key = (int(r["Year"]), int(r["Month"]))
        months[key]["testing"].append({
            "startDate": fmt_date(r.get("Start Date", "")),
            "name":      str(r.get("Project Name", "")).strip(),
            "summary":   str(r.get("Summary", "")).strip(),
        })

    for r in in_progress_rows:
        key = (int(r["Year"]), int(r["Month"]))
        months[key]["inProgress"].append({
            "name":    str(r.get("Project Name", "")).strip(),
            "summary": str(r.get("Summary", "")).strip(),
        })

    # 產生每月 JSON
    generated_keys = []
    for (year, month), sections in sorted(months.items()):
        file_key = f"{year}-{month:02d}"
        payload = {
            "year":  year,
            "month": month,
            "generated": today,
            "kpi": {
                "released":   len(sections["released"]),
                "testing":    len(sections["testing"]),
                "inProgress": len(sections["inProgress"]),
            },
            "sections": sections,
        }
        out_path = OUTPUT_DIR / f"{file_key}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ 產生 {out_path.name}")
        generated_keys.append(file_key)

    if not generated_keys:
        print("⚠️  未找到任何資料，請確認 Google Sheets 格式正確")
        return

    # 更新 manifest.json
    def month_label(key):
        y, m = key.split("-")
        return f"{y}年{int(m)}月"

    latest = generated_keys[-1]
    manifest = {
        "latest": latest,
        "months": [
            {"key": k, "label": month_label(k)}
            for k in reversed(generated_keys)  # 最新在前
        ]
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 更新 manifest.json（latest: {latest}，共 {len(generated_keys)} 個月份）")
    print("🎉 同步完成")

if __name__ == "__main__":
    main()
