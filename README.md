# Telegram Shop Bot

Bot ban hang Telegram dung Google Sheets hoac PostgreSQL de quan ly san pham, ton kho, don hang va SePay webhook de xu ly thanh toan.

## File chinh

- `main.py`: entrypoint tren Render, chay FastAPI webhook va Telegram bot.
- `bot_shop.py`: logic bot Telegram.
- `sepay_webhook.py`: endpoint xu ly webhook SePay va giao hang.
- `mail_reader.py`: doc mail Microsoft Graph khi dung lenh mail.
- `import_pool.py`: tien ich import stock vao Google Sheets.
- `backup_manager.py`: tien ich backup Google Sheets.

## Bien moi truong

Copy `.env.example` thanh `.env` khi chay local. Tren Render, them cac bien nay trong tab Environment:

```env
BOT_TOKEN=
STORAGE_BACKEND=sheets
DATABASE_URL=
GSHEET_ID=
GOOGLE_JSON_CONTENT=
SEPAY_API_KEY=
BANK_CODE=MB
BANK_NAME=MBBANK
BANK_OWNER=LE VAN KHOI
BANK_NUMBER=0329279225
NOTE_TEMPLATE={order_id}
```

`GOOGLE_JSON_CONTENT` la toan bo noi dung file Google service account JSON. Khong commit `.env` hoac `service_account.json`.

## Chuyen tu Google Sheets sang PostgreSQL

Ung dung mac dinh van dung Sheets de viec deploy code moi khong lam gian doan bot. Quy trinh chuyen an toan:

1. Tao PostgreSQL (co the dung Supabase) va them `DATABASE_URL` vao may chay migration.
2. Giu `STORAGE_BACKEND=sheets`, chay `python migrate_sheets_to_postgres.py` de copy tat ca worksheet sang PostgreSQL.
3. Kiem tra so dong ma script bao cao va thu Admin Web.
4. Tren Render dat `DATABASE_URL`, doi `STORAGE_BACKEND=postgres`, sau do redeploy.

Co the chay lai migration ngay truoc buoc 4. Moi bang duoc thay the trong mot transaction: neu copy loi thi du lieu cu trong bang PostgreSQL van con nguyen. Khong xoa Google Sheets ngay; giu lai lam ban doi chieu/backup trong giai doan dau.

Tab `Kho hang` trong Admin Web la giao dien quan ly du lieu `POOL`: them lo hang, doi trang thai va xoa item. Item dang `HELD` khong duoc xoa vi dang gan voi mot don hang.

## Chay local

```bash
pip install -r requirements.txt
python main.py
```

## Deploy Render

- Service type: Web Service
- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`

Sau deploy, log dung se co:

```text
Nạp GSheet Creds từ Environment Variable
Sheets OK
Bot running
Uvicorn running on http://0.0.0.0:10000
```

## Bao mat

Neu token bot hoac Google service account key da lo, tao token/key moi va cap nhat lai Render Environment.
