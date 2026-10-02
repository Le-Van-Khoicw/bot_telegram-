"""One-time Google Sheets -> PostgreSQL migration.

Run with DATABASE_URL configured while STORAGE_BACKEND can remain `sheets`:
    python migrate_sheets_to_postgres.py

The script is intentionally idempotent: each destination table is replaced in
one transaction-like operation, so it can be run again immediately before the
final cutover.
"""

import json
import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from db_storage import PostgresWorksheet, get_postgres_spreadsheet


load_dotenv()


def google_spreadsheet():
    sheet_id = os.getenv("GSHEET_ID", "").strip()
    if not sheet_id:
        raise RuntimeError("GSHEET_ID đang trống")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    raw = os.getenv("GOOGLE_JSON_CONTENT", "").strip()
    if raw:
        credentials = Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    else:
        path = os.getenv("GSVC_JSON", "").strip()
        if not path or not os.path.exists(path):
            raise RuntimeError("Thiếu GOOGLE_JSON_CONTENT hoặc file GSVC_JSON")
        credentials = Credentials.from_service_account_file(path, scopes=scopes)
    return gspread.authorize(credentials).open_by_key(sheet_id)


def main() -> None:
    if not os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError("Hãy cấu hình DATABASE_URL trước khi migrate")
    source = google_spreadsheet()
    destination = get_postgres_spreadsheet()
    total_rows = 0
    for source_ws in source.worksheets():
        values = source_ws.get_all_values()
        if not values or not any(str(value).strip() for value in values[0]):
            print(f"SKIP {source_ws.title}: không có header")
            continue
        target = PostgresWorksheet(destination, source_ws.title, [str(v) for v in values[0]])
        target.replace_all(values)
        migrated = max(0, len(values) - 1)
        stored = max(0, len(target.get_all_values()) - 1)
        if stored != migrated:
            raise RuntimeError(
                f"{source_ws.title}: nguồn có {migrated} dòng nhưng PostgreSQL có {stored} dòng"
            )
        total_rows += migrated
        print(f"OK   {source_ws.title}: {migrated} dòng (đã đối chiếu)")
    print(f"Hoàn tất: {total_rows} dòng. Chưa tự bật STORAGE_BACKEND=postgres.")


if __name__ == "__main__":
    main()
