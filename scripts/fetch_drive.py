# scripts/fetch_drive.py
import os, json
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]
SA_JSON   = os.environ["SERVICE_ACCOUNT_JSON"]
OUT_DIR   = Path(__file__).parent.parent / "data"
OUT_DIR.mkdir(exist_ok=True)

def main():
    creds   = Credentials.from_service_account_info(
        json.loads(SA_JSON),
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)

    # 列出資料夾內所有 .json 檔
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name contains '.json' and trashed=false",
        fields="files(id, name)"
    ).execute()

    for f in results.get("files", []):
        content = service.files().get_media(fileId=f["id"]).execute()
        (OUT_DIR / f["name"]).write_bytes(content)
        print(f"  ✅ 同步 {f['name']}")

if __name__ == "__main__":
    main()