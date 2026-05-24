import os
import re
import io
import logging
import random
import string
import asyncio
import time
import math
import base64
import hmac
import hashlib
import struct
import urllib.request
import json
from html import escape as html_escape
from telegram.constants import ChatAction, ParseMode
from gspread.cell import Cell
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
load_dotenv()
from telegram import (
    Update,
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MenuButtonCommands,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

from mail_reader import MailReaderError, read_inbox_messages
SHEETS_LOCK = asyncio.Lock()
HANGVE_LOCK = asyncio.Lock()
# ================== LOGGING ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("khoivan_store_bot")

# ================== CONFIG ==================
SHOP_NAME = os.getenv("SHOP_NAME", "Khoi Van Store").strip()
BOT_TOKEN = (os.getenv("BOT_TOKEN", "").strip() or "PUT_YOUR_BOT_TOKEN_HERE")

GSHEET_ID = os.getenv("GSHEET_ID", "").strip()  # khuyên để ENV
GSVC_JSON = os.getenv("GSVC_JSON", "").strip()

TAB_ORDERS = os.getenv("ORDERS_TAB", "ORDERS").strip()
TAB_PRODUCTS = os.getenv("PRODUCTS_TAB", "PRODUCTS").strip()
TAB_POOL = os.getenv("POOL_TAB", "POOL").strip()
TAB_RES = os.getenv("RESERVATIONS_TAB", "RESERVATIONS").strip()
TAB_USERS = os.getenv("USERS_TAB", "USERS").strip()
TAB_FUL = os.getenv("FULFILLMENTS_TAB", "FULFILLMENTS").strip()
_ws_users = None

def parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in re.split(r"[,\s]+", raw or ""):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", "6261937216"))

ORDER_TTL_SECONDS = min(int(os.getenv("ORDER_TTL_SECONDS", "300")), 300)  # tối đa 5 phút
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh").strip() or "Asia/Ho_Chi_Minh"
LOCAL_TZ = ZoneInfo(APP_TIMEZONE)

# BIDV
PAYMENT_INFO = {
    "bank_code": os.getenv("BANK_CODE", "BIDV").strip(),
    "bank_name": os.getenv("BANK_NAME", "BIDV").strip(),
    "bank_owner": os.getenv("BANK_OWNER", "NGUYEN VAN MINH").strip(),
    "bank_number": os.getenv("BANK_NUMBER", "8867625524").strip(),
    "note_template": os.getenv("NOTE_TEMPLATE", "{order_id}").strip(),
}
# Support
SUPPORT_ADMIN_NAME = os.getenv("SUPPORT_ADMIN_NAME", "Le Van Khoi").strip()
SUPPORT_ZALO = os.getenv("SUPPORT_ZALO", "0329279225").strip()
SUPPORT_ZALO_LINK = os.getenv("SUPPORT_ZALO_LINK", "https://zalo.me/0329279225").strip()
SUPPORT_TELE = os.getenv("SUPPORT_TELE", "@khoivancw").strip()
SUPPORT_TELE_LINK = os.getenv("SUPPORT_TELE_LINK", "https://t.me/khoivancw").strip()

# ================== GLOBAL STATE ==================
_gs_client = None
_gs_sheet = None
_ws_orders = None
_ws_products = None
_ws_pool = None
_ws_res = None
_ws_ful = None


PENDING_QTY: Dict[int, Dict[str, Any]] = {}  # user_id -> {"product_id": ...}

# ✅ Cache for qty selections to avoid long callback_data (Telegram limit 64 bytes)
# session_id -> {"pid": ..., "created_at": timestamp}
SELECTED_QTY_CACHE: Dict[str, Dict[str, Any]] = {}
SESSION_EXPIRY_SECONDS = 600  # 10 minutes
CHECKOUT_IN_PROGRESS: set[int] = set()


BANK_CODE_ALIASES = {
    # VietQR uses bank BIN/acqId. Keep common typos/short names safe.
    "MSB": "970426",
    "MBS": "970426",
}


def normalized_bank_code() -> str:
    code = PAYMENT_INFO["bank_code"].strip().upper()
    return BANK_CODE_ALIASES.get(code, code)

def cleanup_expired_sessions():
    """Remove sessions older than EXPIRY timeout"""
    now = time.time()
    expired = [sid for sid, data in SELECTED_QTY_CACHE.items()
               if now - data.get("created_at", now) > SESSION_EXPIRY_SECONDS]
    for sid in expired:
        del SELECTED_QTY_CACHE[sid]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired qty sessions")

# ================== HELPERS ==================
_CACHE = {
    "products": {"ts": 0.0, "data": []},
    "stock": {"ts": 0.0, "data": {}},
}

LAST_MAIL_INPUT: Dict[int, str] = {}
def _ts() -> float:
    return time.time()

def invalidate_stock_cache():
    _CACHE["stock"]["ts"] = 0.0

def load_products_cached(ttl: int = 30) -> List[Dict[str, Any]]:
    if _ts() - _CACHE["products"]["ts"] < ttl and _CACHE["products"]["data"]:
        return _CACHE["products"]["data"]
    data = load_products()
    _CACHE["products"] = {"ts": _ts(), "data": data}
    return data

def normalize_order_ref(s: str) -> str:
    # giữ chữ/số, bỏ hết ký tự lạ như '-', ' ', '.', ...
    return re.sub(r"[^A-Za-z0-9]", "", (s or "")).upper()

def stock_count_ready_by_code_cached(ttl: int = 5) -> Dict[str, int]:
    if _ts() - _CACHE["stock"]["ts"] < ttl and _CACHE["stock"]["data"]:
        return _CACHE["stock"]["data"]
    data = stock_count_ready_by_code()
    _CACHE["stock"] = {"ts": _ts(), "data": data}
    return data


def money_vnd(value: Any) -> str:
    return f"{normalize_int(value, 0):,}".replace(",", ".") + "đ"


async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None) -> None:
    if not ADMIN_IDS:
        return
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning("notify admin failed admin_id=%s: %s", admin_id, e)


async def admin_customer_text(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    username = ""
    full_name = ""
    try:
        chat = await context.bot.get_chat(user_id)
        username = (chat.username or "").strip()
        full_name = (chat.full_name or "").strip()
    except Exception:
        pass

    if not username and not full_name:
        try:
            profile = await gs_call(get_user_profile, user_id)
            username = (profile.get("username") or "").strip()
            full_name = (profile.get("full_name") or profile.get("name") or "").strip()
        except Exception:
            pass

    parts = []
    if username:
        parts.append(f"@{username.lstrip('@')}")
    if full_name:
        parts.append(full_name)
    parts.append(str(user_id))
    return " | ".join(parts)

async def gs_call(fn, *args, **kwargs):
    # ✅ serialize gspread calls + chạy trong thread để bot không bị đơ
    async with SHEETS_LOCK:
        return await asyncio.to_thread(fn, *args, **kwargs)

def now_dt() -> datetime:
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def now_str() -> str:
    return now_dt().strftime("%Y-%m-%d %H:%M:%S")

def fmt_price(vnd: int) -> str:
    return f"{vnd:,} đ".replace(",", ".")

def normalize_int(v: Any, default: int = 0) -> int:
    try:
        s = str(v).strip().replace(".", "").replace(",", "")
        return int(float(s))
    except Exception:
        return default

def normalize_bool(v: Any, default: bool = True) -> bool:
    raw = str(v or "").strip().lower()
    if not raw:
        return default
    if raw in {"0", "false", "no", "off", "tat", "tắt"}:
        return False
    if raw in {"1", "true", "yes", "on", "bat", "bật"}:
        return True
    return default

def parse_product_dt(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("T", " ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raw = f"{raw} 23:59:59"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            pass
    return None

def calculate_time_based_price(base_price: int, duration_days: int, expires_at: Any) -> Dict[str, Any]:
    """
    Gia hien tai = gia goc * so ngay con lai / tong so ngay.
    Neu san pham khong co duration_days/expires_at thi giu nguyen gia goc.
    """
    base_price = normalize_int(base_price, 0)
    duration_days = normalize_int(duration_days, 0)
    expire_dt = parse_product_dt(expires_at)
    if base_price <= 0 or duration_days <= 0 or not expire_dt:
        return {
            "price": base_price,
            "base_price": base_price,
            "duration_days": duration_days,
            "remaining_days": "",
            "expires_at": str(expires_at or "").strip(),
            "is_time_priced": False,
        }

    remaining_seconds = (expire_dt - now_dt()).total_seconds()
    remaining_days = max(0, math.ceil(remaining_seconds / 86400))
    billable_days = min(remaining_days, duration_days)
    current_price = round(base_price * billable_days / duration_days) if billable_days > 0 else 0

    return {
        "price": current_price,
        "base_price": base_price,
        "duration_days": duration_days,
        "remaining_days": remaining_days,
        "expires_at": expire_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "is_time_priced": True,
    }

def product_price_note(product: Dict[str, Any]) -> str:
    if not product.get("is_time_priced"):
        return ""
    remaining_days = normalize_int(product.get("remaining_days"), 0)
    duration_days = normalize_int(product.get("duration_days"), 0)
    base_price = normalize_int(product.get("base_price"), normalize_int(product.get("price"), 0))
    expires_at = str(product.get("expires_at") or "").strip()
    if remaining_days <= 0:
        return f"⏳ Giá theo hạn sử dụng: sản phẩm đã hết date ({expires_at})."
    return (
        f"⏳ Giá tự giảm theo hạn sử dụng: giá gốc {fmt_price(base_price)} / "
        f"{duration_days} ngày, còn {remaining_days} ngày, hết hạn {expires_at}."
    )

def price_note_from_values(base_price: int, duration_days: int, remaining_days: Any, expires_at: str) -> str:
    remaining = normalize_int(remaining_days, 0)
    duration = normalize_int(duration_days, 0)
    base = normalize_int(base_price, 0)
    if base <= 0 or duration <= 0 or not expires_at:
        return ""
    if remaining <= 0:
        return f"Giá theo hạn sử dụng: item đã hết date ({expires_at})."
    return f"Giá tự giảm theo hạn sử dụng: giá gốc {fmt_price(base)} / {duration} ngày, còn {remaining} ngày, hết hạn {expires_at}."

def stock_item_pricing(row: List[str], headers: Dict[str, int], fallback_price: int = 0, enable_time_pricing: bool = True) -> Dict[str, Any]:
    def cell(key: str) -> str:
        col = headers.get(key.lower())
        return row[col - 1].strip() if col and col - 1 < len(row) else ""

    fallback_price = normalize_int(fallback_price, 0)
    item_base_price = normalize_int(cell("base_price") or cell("price"), 0)
    duration_days = normalize_int(cell("duration_days") or cell("total_days"), 0)
    expires_at = cell("expires_at") or cell("expire_at") or cell("expiry_at")
    if not enable_time_pricing or duration_days <= 0 or not expires_at:
        return calculate_time_based_price(fallback_price, 0, "")
    base_price = item_base_price if item_base_price > 0 else fallback_price
    return calculate_time_based_price(base_price, duration_days, expires_at)

def generate_order_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    # KHÔNG có dấu '-'
    return f"ORD{now_dt().strftime('%Y%m%d%H%M%S')}{suffix}"

def build_vietqr_image_url(order_id: str, amount: int) -> str:
    """QR động theo order_id (addInfo) bằng img.vietqr.io"""
    from urllib.parse import quote

    # note_template có thể là "{order_id}" hoặc "VM{order_id}"...
    raw_note = PAYMENT_INFO["note_template"].format(order_id=order_id)

    # ✅ ép nội dung CK về dạng sạch: bỏ '-' và mọi ký tự lạ
    add_info = normalize_order_ref(raw_note)

    bank = normalized_bank_code()
    acc  = PAYMENT_INFO["bank_number"].strip()
    name = PAYMENT_INFO["bank_owner"].strip()

    return (
        f"https://img.vietqr.io/image/{bank}-{acc}-compact2.png"
        f"?amount={int(amount)}"
        f"&addInfo={quote(add_info)}"
        f"&accountName={quote(name)}"
    )


def checkout_keyboard_pending_with_qr(order_id: str, qr_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Mở QR thanh toán", url=qr_url)],
        [
            InlineKeyboardButton("✅ Xác nhận đã thanh toán", callback_data=f"confirm|{order_id}"),
            InlineKeyboardButton("❌ Huỷ đơn", callback_data=f"cancel|{order_id}"),
        ],
        [InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")],
    ])


async def fetch_qr_bytes(url: str, timeout: int = 12) -> Optional[bytes]:
    """Tải ảnh QR về bytes để tránh Telegram tự fetch URL (hay lỗi không hiện QR)."""
    def _dl() -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    try:
        data = await asyncio.to_thread(_dl)
        return data if data and len(data) > 100 else None
    except Exception as e:
        logger.warning("fetch_qr_bytes failed: %s", e)
        return None

def remaining_seconds(created_at: str, ttl_seconds: int) -> int:
    try:
        created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        expire_at = created + timedelta(seconds=ttl_seconds)
        return int((expire_at - now_dt()).total_seconds())
    except Exception:
        return 0

def format_countdown(seconds: int) -> str:
    if seconds <= 0:
        return "0 giây"
    m, s = divmod(seconds, 60)
    return f"{m} phút {s} giây" if m > 0 else f"{s} giây"

def build_checkout_caption_with_countdown(
    order_id: str,
    product_name: str,
    unit_price: int,
    qty: int,
    total: int,
    remain_seconds: int,
    status_line: str = "⏳ *ĐANG CHỜ THANH TOÁN*",
    price_note: str = "",
) -> str:
    remain_text = format_countdown(remain_seconds)
    bank_acc = PAYMENT_INFO["bank_number"]
    bank_code = normalized_bank_code()
    safe_product_name = escape_markdown(str(product_name), version=1)

    pay_note = normalize_order_ref(order_id) # hàm của bạn đã bỏ ký tự lạ
    price_note_line = f"ℹ️ {price_note}\n" if price_note else ""

    return (
        f"{status_line}\n\n"
        f"🧾 Mã đơn: `{order_id}`\n"
        f"📦 SP: *{safe_product_name}* — {fmt_price(unit_price)}\n"
        f"{price_note_line}"
        f"🔢 SL: *{qty}*\n"
        f"💰 Tổng: *{fmt_price(total)}*\n\n"
        f"⏳ *Hết hạn sau:* `{remain_text}`\n\n"
        f"📌 *Thanh toán:*\n"
        f"• STK: `{bank_acc}`\n"
        f"• Bank: `{bank_code}`\n"
        f"• Nội dung CK: `{pay_note}`"
    )

async def edit_checkout_message(
    bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    parse_mode: str = "Markdown",
) -> None:
    """Edit caption nếu là photo; nếu không phải photo thì edit text."""
    try:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return
    except Exception:
        pass
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception:
        pass

def _safe_secret(s: str) -> str:
    # tránh vỡ Markdown nếu secret có dấu `
    return (s or "").replace("`", "'").strip()


def delivery_copy_message(title: str, order_id: str, stock_code: str, qty: int, delivered_at: str, secrets_plain: List[str]) -> str:
    copy_block = "\n".join(secrets_plain).strip() or "(trống)"
    return (
        f"{html_escape(title)}\n\n"
        f"🧾 Mã đơn: {html_escape(order_id)}\n"
        f"📦 SP: {html_escape(stock_code)}\n"
        f"🔢 SL: {qty}\n"
        f"⏱ Thời gian: {html_escape(delivered_at)}\n\n"
        "📋 COPY ĐƠN VỪA MUA:\n"
        f"<pre>{html_escape(copy_block)}</pre>\n"
        "🔐 Lấy OTP ngay tại bot:\n"
        "1. Chạm giữ khối đơn ở trên rồi Sao chép.\n"
        "2. Dán thẳng vào bot này.\n"
        "3. Bot sẽ tự đọc mail hoặc lấy mã 2FA nếu đơn có dữ liệu phù hợp.\n\n"
        "🔐 Nếu là tài khoản, vui lòng đổi mật khẩu ngay sau khi đăng nhập."
    )

# ================== GOOGLE SHEETS ==================

def upsert_user(chat_id: int, username: str = "", full_name: str = "") -> None:
    """Lưu chat_id user vào tab USERS (nếu có rồi thì update updated_at)."""
    init_sheets()
    if not _ws_users:
        return

    vals = _ws_users.get_all_values()
    if not vals:
        raise RuntimeError("USERS thiếu header row")

    h = {str(x).strip().lower(): i for i, x in enumerate(vals[0], start=1)}
    c_chat = h.get("chat_id")
    if not c_chat:
        raise RuntimeError("USERS cần cột chat_id")

    # tìm row theo chat_id
    rownum = None
    for idx in range(2, len(vals) + 1):
        r = vals[idx - 1]
        cid = r[c_chat - 1].strip() if c_chat - 1 < len(r) else ""
        if cid == str(chat_id):
            rownum = idx
            break

    now = now_str()

    # helper update cell theo key
    def set_cell(rn: int, key: str, value: str):
        col = h.get(key.lower())
        if col:
            _ws_users.update_cell(rn, col, value)

    if rownum:
        # update
        set_cell(rownum, "username", username or "")
        set_cell(rownum, "full_name", full_name or "")
        set_cell(rownum, "updated_at", now)
    else:
        # append new row
        row_values = [""] * len(h)
        def put(key: str, value: str):
            col = h.get(key.lower())
            if col:
                row_values[col - 1] = value
        put("chat_id", str(chat_id))
        put("username", username or "")
        put("full_name", full_name or "")
        put("updated_at", now)
        _ws_users.append_row(row_values, value_input_option="USER_ENTERED")


def get_all_user_chat_ids() -> List[int]:
    init_sheets()
    if not _ws_users:
        return []
    vals = _ws_users.get_all_values()
    if not vals or len(vals) < 2:
        return []
    h = {str(x).strip().lower(): i for i, x in enumerate(vals[0], start=1)}
    c_chat = h.get("chat_id")
    if not c_chat:
        return []
    out = []
    for r in vals[1:]:
        cid = r[c_chat - 1].strip() if c_chat - 1 < len(r) else ""
        if cid.isdigit():
            out.append(int(cid))
    return out


def get_user_profile(chat_id: int) -> Dict[str, str]:
    init_sheets()
    if not _ws_users:
        return {}
    target = str(chat_id)
    for row in get_all_records(_ws_users):
        cid = (row.get("chat_id") or row.get("user_id") or "").strip()
        if cid == target:
            return row
    return {}

# def init_sheets():
#     global _gs_client, _gs_sheet, _ws_orders, _ws_products, _ws_pool, _ws_res, _ws_users

#     # giữ nguyên phần check return
#     if _ws_orders and _ws_products and _ws_pool and _ws_res and _ws_users:
#         return

#     if not GSHEET_ID:
#         raise RuntimeError("GSHEET_ID empty (hãy set ENV GSHEET_ID)")
#     if not os.path.exists(GSVC_JSON):
#         raise RuntimeError(f"GSVC_JSON not found: {GSVC_JSON}")

#     scopes = [
#         "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive",
#     ]
#     creds = Credentials.from_service_account_file(GSVC_JSON, scopes=scopes)
#     _gs_client = gspread.authorize(creds)
#     _gs_sheet = _gs_client.open_by_key(GSHEET_ID)

#     _ws_orders = _gs_sheet.worksheet(TAB_ORDERS)
#     _ws_products = _gs_sheet.worksheet(TAB_PRODUCTS)
#     _ws_pool = _gs_sheet.worksheet(TAB_POOL)
#     _ws_res = _gs_sheet.worksheet(TAB_RES)
#     _ws_users = _gs_sheet.worksheet(TAB_USERS)



def init_sheets():
    global _gs_client, _gs_sheet, _ws_orders, _ws_products, _ws_pool, _ws_res, _ws_users, _ws_ful

    if _ws_orders and _ws_products and _ws_pool and _ws_res and _ws_users:
        return

    if not GSHEET_ID:
        raise RuntimeError("GSHEET_ID empty (hãy set ENV GSHEET_ID)")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # --- SỬA LẠI ĐOẠN NÀY ĐỂ BỎ QUA CHECK FILE VẬT LÝ ---
    json_content = os.getenv("GOOGLE_JSON_CONTENT")

    if json_content:
        # Nếu có biến môi trường (Ưu tiên số 1 trên Render)
        try:
            json_info = json.loads(json_content)
            creds = Credentials.from_service_account_info(json_info, scopes=scopes)
            logger.info("✅ Nạp GSheet Creds từ Environment Variable")
        except Exception as e:
            logger.error(f"❌ Lỗi đọc GOOGLE_JSON_CONTENT: {e}")
            raise
    else:
        # Nếu không có (Chạy ở máy nhà), lúc này mới tìm file
        if os.path.exists(GSVC_JSON):
            creds = Credentials.from_service_account_file(GSVC_JSON, scopes=scopes)
            logger.info("🏠 Nạp GSheet Creds từ file JSON cục bộ")
        else:
            # Nếu cả 2 đều không có thì mới báo lỗi
            raise RuntimeError("❌ Không tìm thấy thông tin xác thực Google (cả Env và File)")

    # ------------------------------

    _gs_client = gspread.authorize(creds)
    _gs_sheet = _gs_client.open_by_key(GSHEET_ID)

    _ws_orders = _gs_sheet.worksheet(TAB_ORDERS)
    _ws_products = _gs_sheet.worksheet(TAB_PRODUCTS)
    _ws_pool = _gs_sheet.worksheet(TAB_POOL)
    _ws_res = _gs_sheet.worksheet(TAB_RES)
    _ws_users = _gs_sheet.worksheet(TAB_USERS)
    try:
        _ws_ful = _gs_sheet.worksheet(TAB_FUL)
    except Exception:
        _ws_ful = None
def headers_map(ws) -> Dict[str, int]:
    headers = ws.row_values(1)
    return {str(h).strip().lower(): i for i, h in enumerate(headers, start=1)}

def get_all_records(ws) -> List[Dict[str, str]]:
    values = ws.get_all_values()
    if not values or len(values) < 2:
        return []
    headers = [str(h).strip() for h in values[0]]
    rows = []
    for r in values[1:]:
        d = {}
        for i, h in enumerate(headers):
            d[h] = r[i].strip() if i < len(r) else ""
        rows.append(d)
    return rows

# ================== PRODUCTS + STOCK ==================
def load_products() -> List[Dict[str, Any]]:
    init_sheets()
    rows = get_all_records(_ws_products)
    out: List[Dict[str, Any]] = []
    for r in rows:
        product_id = (r.get("product_id") or "").strip()
        name = (r.get("name") or "").strip()
        stock_code = (r.get("stock_code") or "").strip()
        base_price = normalize_int(r.get("price"), 0)
        duration_days = normalize_int(r.get("duration_days") or r.get("total_days"), 0)
        expires_at = (r.get("expires_at") or r.get("expire_at") or r.get("expiry_at") or "").strip()
        pricing_enabled = normalize_bool(r.get("pricing_enabled"), True)
        pricing = calculate_time_based_price(base_price, duration_days, expires_at if pricing_enabled else "")

        # ✅ lấy mô tả riêng từng sản phẩm (từ cột description)
        desc = (r.get("description") or "").strip()

        if product_id and stock_code and name:
            out.append({
                "product_id": product_id,
                "name": name,
                "price": pricing["price"],
                "base_price": pricing["base_price"],
                "duration_days": pricing["duration_days"],
                "remaining_days": pricing["remaining_days"],
                "expires_at": pricing["expires_at"],
                "is_time_priced": pricing["is_time_priced"],
                "pricing_enabled": pricing_enabled,
                "stock_code": stock_code,
                "description": desc,   # ✅ thêm field
            })
    return out


def stock_count_ready_by_code() -> Dict[str, int]:
    init_sheets()
    rows = get_all_records(_ws_pool)
    cnt: Dict[str, int] = {}
    for r in rows:
        sc = (r.get("stock_code") or "").strip()
        st = (r.get("status") or "").strip().upper()
        if sc and st == "READY":
            cnt[sc] = cnt.get(sc, 0) + 1
    return cnt

def stock_price_preview_by_code(
    fallback_prices: Optional[Dict[str, int]] = None,
    pricing_enabled_by_code: Optional[Dict[str, bool]] = None,
) -> Dict[str, Dict[str, Any]]:
    init_sheets()
    rows = _ws_pool.get_all_values()
    if not rows or len(rows) < 2:
        return {}
    headers = {str(h).strip().lower(): i for i, h in enumerate(rows[0], start=1)}
    c_stock = headers.get("stock_code")
    c_status = headers.get("status")
    if not (c_stock and c_status):
        return {}

    fallback_prices = fallback_prices or {}
    pricing_enabled_by_code = pricing_enabled_by_code or {}
    previews: Dict[str, Dict[str, Any]] = {}
    preview_order: Dict[str, Tuple[str, int]] = {}
    for rownum, row in enumerate(rows[1:], start=2):
        stock_code = row[c_stock - 1].strip() if c_stock - 1 < len(row) else ""
        status = row[c_status - 1].strip().upper() if c_status - 1 < len(row) else ""
        if not stock_code or status != "READY":
            continue
        pricing = stock_item_pricing(
            row,
            headers,
            fallback_prices.get(stock_code, 0),
            pricing_enabled_by_code.get(stock_code, True),
        )
        if normalize_int(pricing.get("price"), 0) <= 0:
            continue
        expires_at = str(pricing.get("expires_at") or "9999-12-31 23:59:59")
        key = (expires_at, rownum)
        if stock_code not in previews or key < preview_order[stock_code]:
            previews[stock_code] = pricing
            preview_order[stock_code] = key
    return previews

def find_product_by_id(pid: str) -> Optional[Dict[str, Any]]:
    for p in load_products_cached():
        if p["product_id"] == pid:
            return p
    return None

def find_product_by_stock_code(stock_code: str) -> Optional[Dict[str, Any]]:
    for p in load_products_cached():
        if p["stock_code"] == stock_code:
            return p
    return None

# ================== POOL + RESERVATIONS ==================
def reserve_items_from_pool(
    stock_code: str,
    qty: int,
    order_id: str,
    hold_seconds: int,
    fallback_price: int = 0,
    enable_time_pricing: bool = True,
) -> List[Dict[str, Any]]:
    """
    Lấy qty item READY từ POOL theo stock_code -> set HELD + hold_order_id/hold_at/hold_expires_at
    + append RESERVATIONS
    """
    init_sheets()
    rows = _ws_pool.get_all_values()
    if not rows or len(rows) < 2:
        return []

    hmap = {str(h).strip().lower(): i for i, h in enumerate(rows[0], start=1)}
    col_item_id = hmap.get("item_id")
    col_stock = hmap.get("stock_code")
    col_secret = hmap.get("secret")
    col_status = hmap.get("status")
    col_hold_oid = hmap.get("hold_order_id")
    col_hold_at = hmap.get("hold_at")
    col_hold_exp = hmap.get("hold_expires_at")

    if not (col_item_id and col_stock and col_secret and col_status):
        raise RuntimeError("POOL thiếu cột bắt buộc (item_id, stock_code, secret, status)")

    now = now_str()
    exp = (now_dt() + timedelta(seconds=hold_seconds)).strftime("%Y-%m-%d %H:%M:%S")

    ready_items: List[Tuple[int, Dict[str, Any]]] = []
    for idx in range(2, len(rows) + 1):
        r = rows[idx - 1]
        sc = r[col_stock - 1].strip() if col_stock - 1 < len(r) else ""
        st = r[col_status - 1].strip().upper() if col_status - 1 < len(r) else ""
        if sc == stock_code and st == "READY":
            item_id = r[col_item_id - 1].strip() if col_item_id - 1 < len(r) else ""
            secret = r[col_secret - 1].strip() if col_secret - 1 < len(r) else ""
            pricing = stock_item_pricing(r, hmap, fallback_price, enable_time_pricing)
            if normalize_int(pricing.get("price"), 0) <= 0:
                continue
            ready_items.append((idx, {
                "item_id": item_id,
                "stock_code": sc,
                "secret": secret,
                **pricing,
            }))

    def item_sort_key(item: Tuple[int, Dict[str, Any]]) -> Tuple[str, int]:
        expires_at = str(item[1].get("expires_at") or "9999-12-31 23:59:59")
        return (expires_at, item[0])

    selected = sorted(ready_items, key=item_sort_key)[:qty]

    if len(selected) < qty:
        return []

    # ✅ mark HELD in POOL (BATCH UPDATE - nhanh hơn nhiều)
    cells: List[Cell] = []
    for rownum, _item in selected:
        cells.append(Cell(rownum, col_status, "HELD"))
        if col_hold_oid:
            cells.append(Cell(rownum, col_hold_oid, order_id))
        if col_hold_at:
            cells.append(Cell(rownum, col_hold_at, now))
        if col_hold_exp:
            cells.append(Cell(rownum, col_hold_exp, exp))

    _ws_pool.update_cells(cells, value_input_option="USER_ENTERED")

    # append RESERVATIONS rows
    res_hmap = headers_map(_ws_res)
    rows_to_append = []
    for _, item in selected:
        row_values = [""] * len(res_hmap)
        def put(key: str, val: str):
            c = res_hmap.get(key.lower())
            if c:
                row_values[c - 1] = val

        put("order_id", order_id)
        put("item_id", item["item_id"])
        put("stock_code", stock_code)
        put("reserved_at", now)
        put("expires_at", exp)
        put("released_at", "")
        put("sold_at", "")

        rows_to_append.append(row_values)

    _ws_res.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    invalidate_stock_cache()
    return [item for _, item in selected]

def release_hold_by_order(order_id: str, mark_status: str) -> int:
    """
    Trả kho: POOL HELD -> READY nếu hold_order_id=order_id
    + RESERVATIONS.released_at
    + ORDERS.status = mark_status
    """
    init_sheets()

    pool_vals = _ws_pool.get_all_values()
    if not pool_vals or len(pool_vals) < 2:
        return 0
    ph = {str(h).strip().lower(): i for i, h in enumerate(pool_vals[0], start=1)}
    c_status = ph.get("status")
    c_hold_oid = ph.get("hold_order_id")
    c_hold_at = ph.get("hold_at")
    c_hold_exp = ph.get("hold_expires_at")
    if not (c_status and c_hold_oid):
        return 0

    released = 0
    pool_cells: List[Cell] = []
    for idx in range(2, len(pool_vals) + 1):
        r = pool_vals[idx - 1]
        hold_oid = r[c_hold_oid - 1].strip() if c_hold_oid - 1 < len(r) else ""
        st = r[c_status - 1].strip().upper() if c_status - 1 < len(r) else ""
        if hold_oid == order_id and st == "HELD":
            pool_cells.append(Cell(idx, c_status, "READY"))
            pool_cells.append(Cell(idx, c_hold_oid, ""))
            if c_hold_at:
                pool_cells.append(Cell(idx, c_hold_at, ""))
            if c_hold_exp:
                pool_cells.append(Cell(idx, c_hold_exp, ""))
            released += 1
    if pool_cells:
        _ws_pool.update_cells(pool_cells, value_input_option="USER_ENTERED")

    # RESERVATIONS.released_at
    res_vals = _ws_res.get_all_values()
    if res_vals and len(res_vals) >= 2:
        rh = {str(h).strip().lower(): i for i, h in enumerate(res_vals[0], start=1)}
        c_oid = rh.get("order_id")
        c_rel = rh.get("released_at")
        if c_oid and c_rel:
            res_cells: List[Cell] = []
            released_at = now_str()
            for idx in range(2, len(res_vals) + 1):
                r = res_vals[idx - 1]
                oid = r[c_oid - 1].strip() if c_oid - 1 < len(r) else ""
                if oid == order_id:
                    res_cells.append(Cell(idx, c_rel, released_at))
            if res_cells:
                _ws_res.update_cells(res_cells, value_input_option="USER_ENTERED")

    set_order_fields(order_id, {"status": mark_status})
    if released:
        invalidate_stock_cache()
    return released


def release_expired_held_items_from_pool() -> int:
    """Trả READY các item HELD đã quá hạn, kể cả khi order/job bị kẹt."""
    init_sheets()

    pool_vals = _ws_pool.get_all_values()
    if not pool_vals or len(pool_vals) < 2:
        return 0

    ph = {str(h).strip().lower(): i for i, h in enumerate(pool_vals[0], start=1)}
    c_status = ph.get("status")
    c_hold_oid = ph.get("hold_order_id")
    c_hold_at = ph.get("hold_at")
    c_hold_exp = ph.get("hold_expires_at")
    if not c_status:
        return 0

    now = now_dt()
    cells: List[Cell] = []
    released = 0

    for rownum in range(2, len(pool_vals) + 1):
        row = pool_vals[rownum - 1]
        st = row[c_status - 1].strip().upper() if c_status - 1 < len(row) else ""
        if st != "HELD":
            continue

        expired = False
        if c_hold_exp:
            exp_s = row[c_hold_exp - 1].strip() if c_hold_exp - 1 < len(row) else ""
            exp_dt = parse_dt(exp_s)
            expired = bool(exp_dt and exp_dt <= now)

        if not expired and c_hold_at:
            hold_s = row[c_hold_at - 1].strip() if c_hold_at - 1 < len(row) else ""
            hold_dt = parse_dt(hold_s)
            expired = bool(hold_dt and (hold_dt + timedelta(seconds=ORDER_TTL_SECONDS)) <= now)

        if not expired:
            continue

        cells.append(Cell(rownum, c_status, "READY"))
        if c_hold_oid:
            cells.append(Cell(rownum, c_hold_oid, ""))
        if c_hold_at:
            cells.append(Cell(rownum, c_hold_at, ""))
        if c_hold_exp:
            cells.append(Cell(rownum, c_hold_exp, ""))
        released += 1

    if cells:
        _ws_pool.update_cells(cells, value_input_option="USER_ENTERED")
        invalidate_stock_cache()

    return released

def mark_sold_and_get_secrets(order_id: str) -> List[Dict[str, str]]:
    """
    Khi giao: POOL HELD (hold_order_id=order_id) -> SOLD + sold_at/sold_order_id
    Update RESERVATIONS.sold_at
    Return list items with secret
    """
    init_sheets()
    pool_vals = _ws_pool.get_all_values()
    if not pool_vals or len(pool_vals) < 2:
        return []

    ph = {str(h).strip().lower(): i for i, h in enumerate(pool_vals[0], start=1)}
    c_item_id = ph.get("item_id")
    c_stock = ph.get("stock_code")
    c_secret = ph.get("secret")
    c_status = ph.get("status")
    c_hold_oid = ph.get("hold_order_id")
    c_sold_oid = ph.get("sold_order_id")
    c_sold_at = ph.get("sold_at")

    if not (c_hold_oid and c_status and c_secret):
        return []

    items: List[Dict[str, str]] = []
    for idx in range(2, len(pool_vals) + 1):
        r = pool_vals[idx - 1]
        hold_oid = r[c_hold_oid - 1].strip() if c_hold_oid - 1 < len(r) else ""
        st = r[c_status - 1].strip().upper() if c_status - 1 < len(r) else ""
        if hold_oid == order_id and st == "HELD":
            item_id = r[c_item_id - 1].strip() if c_item_id and c_item_id - 1 < len(r) else ""
            stock_code = r[c_stock - 1].strip() if c_stock and c_stock - 1 < len(r) else ""
            secret = r[c_secret - 1].strip() if c_secret - 1 < len(r) else ""

            # mark SOLD
            _ws_pool.update_cell(idx, c_status, "SOLD")
            if c_sold_oid:
                _ws_pool.update_cell(idx, c_sold_oid, order_id)
            if c_sold_at:
                _ws_pool.update_cell(idx, c_sold_at, now_str())

            items.append({"item_id": item_id, "stock_code": stock_code, "secret": secret})

    # update RESERVATIONS.sold_at
    res_vals = _ws_res.get_all_values()
    if res_vals and len(res_vals) >= 2:
        rh = {str(h).strip().lower(): i for i, h in enumerate(res_vals[0], start=1)}
        c_oid = rh.get("order_id")
        c_sold = rh.get("sold_at")
        if c_oid and c_sold:
            for idx in range(2, len(res_vals) + 1):
                r = res_vals[idx - 1]
                oid = r[c_oid - 1].strip() if c_oid - 1 < len(r) else ""
                if oid == order_id:
                    _ws_res.update_cell(idx, c_sold, now_str())

    invalidate_stock_cache()
    return items

# ================== ORDERS ==================
def append_order(order_row: Dict[str, Any]) -> None:
    init_sheets()
    h = headers_map(_ws_orders)
    if not h:
        raise RuntimeError("ORDERS thiếu header row")

    row_values = [""] * len(h)

    def put(key: str, value: Any):
        c = h.get(key.lower())
        if c:
            row_values[c - 1] = "" if value is None else str(value)

    put("order_id", order_row.get("order_id", ""))
    put("user_id", order_row.get("user_id", ""))
    put("stock_code", order_row.get("stock_code", ""))
    put("qty", order_row.get("qty", ""))
    put("total", order_row.get("total", ""))
    put("status", order_row.get("status", "PENDING"))
    put("qr_msg_id", order_row.get("qr_msg_id", ""))
    put("paid_at", order_row.get("paid_at", ""))
    put("tx_id", order_row.get("tx_id", ""))
    put("delivered_at", order_row.get("delivered_at", ""))
    put("deliver_text", order_row.get("deliver_text", ""))
    put("created_at", order_row.get("created_at", now_str()))

    _ws_orders.append_row(row_values, value_input_option="USER_ENTERED")

def get_order(order_id: str) -> Optional[Dict[str, str]]:
    init_sheets()
    vals = _ws_orders.get_all_values()
    if not vals or len(vals) < 2:
        return None

    h = {str(x).strip().lower(): i for i, x in enumerate(vals[0], start=1)}
    c_oid = h.get("order_id")
    if not c_oid:
        return None

    target = normalize_order_ref(order_id)

    for idx in range(2, len(vals) + 1):
        r = vals[idx - 1]
        raw_oid = r[c_oid - 1].strip() if c_oid - 1 < len(r) else ""
        if normalize_order_ref(raw_oid) == target:
            d = {}
            for k, c in h.items():
                d[k] = r[c - 1].strip() if c - 1 < len(r) else ""
            d["_rownum"] = str(idx)
            return d
    return None


def set_order_fields(order_id: str, updates: Dict[str, Any]) -> None:
    init_sheets()
    o = get_order(order_id)
    if not o:
        return
    rownum = int(o["_rownum"])
    h = headers_map(_ws_orders)
    for k, v in updates.items():
        c = h.get(k.lower())
        if c:
            _ws_orders.update_cell(rownum, c, "" if v is None else str(v))

def list_user_orders(user_id: int, limit: int = 10) -> List[Dict[str, str]]:
    init_sheets()
    vals = _ws_orders.get_all_values()
    if not vals or len(vals) < 2:
        return []
    h = {str(x).strip().lower(): i for i, x in enumerate(vals[0], start=1)}
    c_uid = h.get("user_id")
    if not c_uid:
        return []
    rows: List[Dict[str, str]] = []
    for idx in range(2, len(vals) + 1):
        r = vals[idx - 1]
        uid = r[c_uid - 1].strip() if c_uid - 1 < len(r) else ""
        if uid == str(user_id):
            d = {}
            for k, c in h.items():
                d[k] = r[c - 1].strip() if c - 1 < len(r) else ""
            rows.append(d)

    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return rows[:limit]


# ================== FULFILLMENTS (optional) ==================
def append_fulfillment(order_id: str, item_id: str, stock_code: str, secret: str, delivered_at: str) -> None:
    init_sheets()
    if not _ws_ful:
        return
    h = headers_map(_ws_ful)
    if not h:
        return
    row_values = [""] * len(h)

    def put(key: str, value: Any):
        c = h.get(key.lower())
        if c:
            row_values[c - 1] = "" if value is None else str(value)

    put("order_id", order_id)
    put("item_id", item_id)
    put("stock_code", stock_code)
    put("secret", secret)
    put("delivered_at", delivered_at)
    _ws_ful.append_row(row_values, value_input_option="USER_ENTERED")

def append_fulfillments_bulk(order_id: str, items: List[Dict[str, str]], delivered_at: str) -> None:
    """
    Append nhiều dòng vào sheet FULFILLMENTS chỉ 1 lần (nhanh hơn nhiều).
    items: list dict có keys: item_id, stock_code, secret
    """
    init_sheets()
    if not _ws_ful:
        return

    h = headers_map(_ws_ful)
    if not h:
        return

    rows_to_append: List[List[str]] = []

    for it in items:
        row_values = [""] * len(h)

        def put(key: str, value: Any):
            c = h.get(key.lower())
            if c:
                row_values[c - 1] = "" if value is None else str(value)

        put("order_id", order_id)
        put("item_id", it.get("item_id", ""))
        put("stock_code", it.get("stock_code", ""))
        put("secret", it.get("secret", ""))
        put("delivered_at", delivered_at)

        rows_to_append.append(row_values)

    # ✅ append 1 lần
    _ws_ful.append_rows(rows_to_append, value_input_option="USER_ENTERED")


def get_fulfillment_secrets(order_id: str) -> List[str]:
    """Lấy secret đã giao từ sheet FULFILLMENTS (dùng để resend khi đơn DELIVERED)."""
    init_sheets()
    if not _ws_ful:
        return []
    try:
        vals = _ws_ful.get_all_values()
        if not vals or len(vals) < 2:
            return []
        h = {str(x).strip().lower(): i for i, x in enumerate(vals[0])}
        c_oid = h.get("order_id")
        c_secret = h.get("secret")
        if c_oid is None or c_secret is None:
            return []
        out = []
        for r in vals[1:]:
            oid = r[c_oid].strip() if c_oid < len(r) else ""
            if oid == order_id:
                sec = r[c_secret].strip() if c_secret < len(r) else ""
                if sec:
                    out.append(sec)
        return out
    except Exception:
        return []

# ================== UI: MAIN MENU ==================
BTN_PRODUCTS = "🛍 Sản phẩm".replace("\ufe0f","")
BTN_SUPPORT  = "💬 Hỗ trợ".replace("\ufe0f","")
BTN_ORDERS   = "📦 Đơn hàng".replace("\ufe0f","")
BTN_GAME     = "🎲 Game".replace("\ufe0f","")
BTN_2FA      = "🔐 2FA".replace("\ufe0f","")
BTN_MAIL     = "📬 Đọc mail".replace("\ufe0f","")


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(BTN_PRODUCTS), KeyboardButton(BTN_SUPPORT)],
        [KeyboardButton(BTN_GAME), KeyboardButton(BTN_ORDERS)],
        [KeyboardButton(BTN_2FA), KeyboardButton(BTN_MAIL)],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)



def welcome_text(user_fullname: str) -> str:
    return (
        f"👋 *Xin chào {user_fullname}!* \n\n"
        f"*{SHOP_NAME}* rất vui được phục vụ bạn.\n\n\n"
        "✅ Hàng số chuẩn • giao tự động 24/7\n\n"
        "⚡️ Thanh toán nhanh • VietQR / chuyển khoản\n\n"
        "🛡 Bảo mật riêng tư • thông tin được bảo vệ tuyệt đối\n\n\n"
        "📌 *Lệnh nhanh:*\n\n"
        "/start - Menu chính\n\n"
        "/shop - Xem sản phẩm\n\n"
        "/orders - Đơn hàng của bạn\n\n"
        "/game - Chơi game\n\n"
        "/support - Hỗ trợ\n\n"
        "/2fa - Lấy mã 2FA từ secret\n\n"
        f"🫡 “Mỗi đơn hàng bạn đặt tại {SHOP_NAME} không chỉ là một sản phẩm — đó là sự tin tưởng bạn gửi gắm, "
        "và là cam kết chúng tôi luôn giữ trọn.”\n\n"
    )



# ================== SUPPORT ==================
def support_text() -> str:
    return (
        "💬 *HỖ TRỢ & CHĂM SÓC KHÁCH HÀNG*\n\n"
        "Nếu bạn gặp bất kỳ vấn đề nào, cứ nhắn mình nhé:\n\n\n"
        f"👤 *Phụ trách:* {SUPPORT_ADMIN_NAME}\n\n"
        f"📱 *Zalo:* `{SUPPORT_ZALO}`\n\n"
        f"✈️ *Telegram:* {SUPPORT_TELE}\n\n"
        "🤝 Mình luôn sẵn sàng hỗ trợ bạn *bất kể giờ nào* (có thể phản hồi chậm hơn vào giờ khuya).\n\n"
        "👉 Bấm nút bên dưới để liên hệ ngay."
    )



def support_kb() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    if SUPPORT_ZALO_LINK:
        rows.append([InlineKeyboardButton("📱 Nhắn Zalo", url=SUPPORT_ZALO_LINK)])
    if SUPPORT_TELE_LINK:
        rows.append([InlineKeyboardButton("✈️ Nhắn Telegram", url=SUPPORT_TELE_LINK)])
    rows.append([InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def quick_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛍 Sản phẩm", callback_data="go_products"),
            InlineKeyboardButton("📦 Đơn hàng", callback_data="go_orders"),
        ],
        [
            InlineKeyboardButton("🔐 2FA", callback_data="2fa_help"),
            InlineKeyboardButton("📬 Đọc mail", callback_data="mail_help"),
        ],
        [InlineKeyboardButton("🔄 Đọc lại thư", callback_data="mail_repeat")],
        [InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")],
    ])


def mail_retry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Đọc lại mail này", callback_data="mail_repeat")],
        [
            InlineKeyboardButton("🛍 Sản phẩm", callback_data="go_products"),
            InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main"),
        ],
    ])


def buy_suggestion_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Đi mua hàng", callback_data="go_products")],
        [InlineKeyboardButton("✨ Gợi ý sản phẩm", callback_data="refresh_stock")],
    ])


def stock_update_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Đi mua hàng", callback_data="go_products")],
        [InlineKeyboardButton("✨ Làm mới gợi ý", callback_data="refresh_stock")],
    ])


def welcome_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛍 Sản phẩm", callback_data="go_products"),
            InlineKeyboardButton("📦 Đơn hàng", callback_data="go_orders"),
        ],
        [
            InlineKeyboardButton("✨ Cập nhật kho", callback_data="refresh_stock"),
            InlineKeyboardButton("💬 Hỗ trợ", callback_data="go_support"),
        ],
        [
            InlineKeyboardButton("🔐 2FA", callback_data="2fa_help"),
            InlineKeyboardButton("📬 Đọc mail", callback_data="mail_help"),
        ],
    ])


async def stock_update_text() -> str:
    products = await gs_call(load_products_cached)
    stock_ready = await gs_call(stock_count_ready_by_code_cached)
    available = [
        (product, stock_ready.get(product["stock_code"], 0))
        for product in products
        if stock_ready.get(product["stock_code"], 0) > 0
    ]
    available.sort(key=lambda item: item[1], reverse=True)
    total = sum(qty for _, qty in available)

    lines = [
        "📦 *CẬP NHẬT KHO HÀNG ✨*",
        "",
        f"🕒 Cập nhật: `{escape_markdown(now_str(), version=1)}`",
        f"📊 Sản phẩm còn hàng: *{len(available)}* | Tổng tồn: *{total}*",
        "",
        "*Tồn kho hiện tại:*",
        "",
    ]
    if not available:
        lines.append("⛔ Hiện chưa có sản phẩm còn hàng.")
    else:
        for product, qty in available[:8]:
            icon = "🟢" if qty >= 5 else "🟡"
            lines.append(
                f"{icon} 📘 *{product['name']}*\n"
                f"• Số lượng: *{qty}*  • Giá: *{fmt_price(product['price'])}*"
            )
    lines.extend(["", "👉 Bấm *Đi mua hàng* để chọn sản phẩm cần mua."])
    return "\n".join(lines)


async def send_support(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=chat_id,
        text=support_text(),
        parse_mode="Markdown",
        reply_markup=support_kb(),
    )

# ================== UI: PRODUCTS ==================
def build_products_menu_kb(
    products: List[Dict[str, Any]],
    stock_ready: Dict[str, int],
) -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []

    for p in products:
        sc = p["stock_code"]
        ready = stock_ready.get(sc, 0)

        # Format theo yêu cầu: "Tên | 15.000 vnđ | Số Lượng Còn : 5"
        price_text = fmt_price(p["price"]).replace(" đ", " vnđ")
        remaining = p.get("remaining_days")
        date_text = f"|Còn: {remaining} ngày" if p.get("is_time_priced") and str(remaining).isdigit() else ""
        label = f"{p['name']} | {price_text}{date_text}|SL: {ready}"

        buttons.append([InlineKeyboardButton(label, callback_data=f"pdetail|{p['product_id']}")])

    # 2 nút nhanh
    buttons.append([
        InlineKeyboardButton("📦 Đơn hàng", callback_data="go_orders"),
        InlineKeyboardButton("💬 Hỗ trợ", callback_data="go_support"),
    ])

    buttons.append([
        InlineKeyboardButton("🔐 2FA", callback_data="2fa_help"),
        InlineKeyboardButton("📬 Đọc mail", callback_data="mail_help"),
    ])

    # Menu chính
    buttons.append([InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")])

    return InlineKeyboardMarkup(buttons)


def product_detail_text(p: Dict[str, Any], ready_qty: int) -> str:
    status = "✅ *Còn hàng*" if ready_qty > 0 else "⛔ *Hết hàng*"

    # ✅ mô tả lấy từ sheet
    desc = (p.get("description") or "").strip()
    if not desc:
        desc = "Chưa có mô tả."

    # tránh vỡ Markdown vì dấu `
    desc = desc.replace("`", "'")

    return (
        f"📦 *{p['name']}*\n\n"
        f"💰 Giá: *{fmt_price(p['price'])}*\n"
        f"{product_price_note(p)}\n"
        f"📦 Còn lại: *{ready_qty}*\n"
        f"📝 *Mô tả:*\n{desc}\n"
        f"📌 Trạng thái: {status}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Thanh toán xong hệ thống *giao tự động*.\n"
        "👇 Chọn chức năng bên dưới:"
    )


def product_detail_kb(pid: str, ready_qty: int, current_price: int = 1) -> InlineKeyboardMarkup:
    rows = []
    if ready_qty > 0:
        rows.append([InlineKeyboardButton("🛒 Mua ngay", callback_data=f"buy|{pid}")])
    elif SUPPORT_TELE_LINK:
        rows.append([InlineKeyboardButton("💬 Liên hệ hỗ trợ", url=SUPPORT_TELE_LINK)])

    rows.append([InlineKeyboardButton("⬅️ Quay lại menu sản phẩm", callback_data="back_products")])
    rows.append([InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def qty_select_text(p: Dict[str, Any]) -> str:
    return (
        f"🔢 *Chọn số lượng* cho *{p['name']}*\n\n"

        "👇 Chọn nhanh bên dưới hoặc nhập tuỳ chỉnh:"
    )

def qty_callback(pid: str, qty: int) -> str:
    data = f"qtypid|{pid}|{qty}"
    if len(data.encode("utf-8")) <= 64:
        return data

    import uuid
    cleanup_expired_sessions()
    session_id = str(uuid.uuid4())[:8]
    SELECTED_QTY_CACHE[session_id] = {"pid": pid, "created_at": time.time()}
    return f"qty|{session_id}|{qty}"


def qty_custom_callback(pid: str) -> str:
    data = f"qtycustompid|{pid}"
    if len(data.encode("utf-8")) <= 64:
        return data

    import uuid
    cleanup_expired_sessions()
    session_id = str(uuid.uuid4())[:8]
    SELECTED_QTY_CACHE[session_id] = {"pid": pid, "created_at": time.time()}
    return f"qtycustom|{session_id}"


def qty_select_kb(pid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data=qty_callback(pid, 1)),
         InlineKeyboardButton("2", callback_data=qty_callback(pid, 2))],
        [InlineKeyboardButton("5", callback_data=qty_callback(pid, 5)),
         InlineKeyboardButton("10", callback_data=qty_callback(pid, 10))],
        [InlineKeyboardButton("✏️ Tùy chỉnh", callback_data=qty_custom_callback(pid))],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data=f"pdetail_back|{pid}")],
    ])

def checkout_keyboard_pending(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Xác nhận đã thanh toán", callback_data=f"confirm|{order_id}"),
            InlineKeyboardButton("❌ Huỷ đơn", callback_data=f"cancel|{order_id}"),
        ],
        [InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")],
    ])

def checkout_keyboard_done() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")]])

# ================== COMMANDS ==================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # ✅ LƯU USER
    await gs_call(upsert_user, update.effective_chat.id, user.username or "", user.full_name or "")

    await update.message.reply_text(
        welcome_text(user.full_name),
        parse_mode="Markdown",
        reply_markup=welcome_inline_kb(),
    )

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_products(update.effective_user.id, context)

async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_orders(update.effective_user.id, context)

async def cmd_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_support(update.effective_user.id, context)


async def setup_bot_commands(app: Application) -> None:
    commands = [
        BotCommand("start", "Menu chính"),
        BotCommand("shop", "Xem sản phẩm"),
        BotCommand("sanpham", "Xem sản phẩm"),
        BotCommand("orders", "Đơn hàng của bạn"),
        BotCommand("support", "Hỗ trợ"),
        BotCommand("hotro", "Hỗ trợ"),
        BotCommand("2fa", "Lấy mã 2FA"),
        BotCommand("mail", "Đọc hòm thư"),
    ]
    try:
        await app.bot.set_my_commands(commands)
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Telegram command menu registered")
    except Exception:
        logger.exception("register telegram command menu failed")


async def cmd_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *GAME*\n\n"

        "Tính năng này sẽ được cập nhật sớm.\n\n"
        "👉 Hiện tại bạn bấm 🛍 *Sản phẩm* để mua nhé.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


def looks_like_mail_account(text: str) -> bool:
    text = (text or "").strip()
    return "@" in text and ("|" in text or "----" in text)


def normalize_menu_text(text: str) -> str:
    text = (text or "").replace("\ufe0f", "")
    text = re.sub(r"[^\wÀ-ỹ\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.casefold().split())


def extract_totp_secrets(raw: str) -> List[str]:
    text = (raw or "").strip()
    if not text:
        return []

    # Support otpauth://totp/...?...secret=XXXX links too.
    uri_secrets = re.findall(r"(?:^|[?&])secret=([A-Za-z2-7=\s]+)", text, flags=re.IGNORECASE)
    if uri_secrets:
        return [s.strip() for s in uri_secrets if s.strip()]

    secrets: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            line = parts[-1] if parts else line
        candidate = re.sub(r"[^A-Za-z2-7=]", "", line).upper()
        if len(candidate) >= 12 and re.fullmatch(r"[A-Z2-7=]+", candidate):
            secrets.append(candidate)
    return secrets


def looks_like_totp_secret(text: str) -> bool:
    if "@" in (text or "") or "|" in (text or ""):
        return False
    return bool(extract_totp_secrets(text))


def generate_totp(secret: str, now: Optional[int] = None, step: int = 30, digits: int = 6) -> Tuple[str, int]:
    clean = re.sub(r"[^A-Za-z2-7=]", "", secret or "").upper()
    if not clean:
        raise ValueError("Secret rỗng")
    clean += "=" * ((8 - len(clean) % 8) % 8)
    key = base64.b32decode(clean, casefold=True)
    current = int(now if now is not None else time.time())
    counter = current // step
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits), step - (current % step)


async def send_2fa_help(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🔐 *LẤY MÃ 2FA*\n\n"
            "Cách 1:\n"
            "`/2fa SECRET`\n\n"
            "Cách 2:\n"
            "Gửi thẳng secret 2FA vào chat.\n\n"
            "Cách 3:\n"
            "Reply tin có secret rồi gõ `/2fa`.\n\n"
            "Bot sẽ tạo mã 6 số hiện tại giống Google Authenticator."
        ),
        parse_mode="Markdown",
        reply_markup=quick_actions_kb(),
    )


async def send_2fa_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str):
    secrets = extract_totp_secrets(raw)
    if not secrets:
        await send_2fa_help(update.effective_chat.id, context)
        return

    lines = ["🔐 *Mã 2FA hiện tại*"]
    for idx, secret in enumerate(secrets[:10], start=1):
        try:
            code, remain = generate_totp(secret)
            lines.append(f"\n{idx}) `{code}` - còn *{remain}s*")
        except Exception:
            lines.append(f"\n{idx}) Secret không hợp lệ")
    if len(secrets) > 10:
        lines.append(f"\n\nChỉ xử lý 10 secret đầu tiên. Còn {len(secrets) - 10} secret chưa hiển thị.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=quick_actions_kb())


async def cmd_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = " ".join(context.args).strip()
    if not raw and update.message.reply_to_message:
        raw = (update.message.reply_to_message.text or "").strip()

    if not raw:
        return await send_2fa_help(update.effective_chat.id, context)

    return await send_2fa_from_text(update, context, raw)


async def render_mail_result(loading_msg, raw: str):
    try:
        result = await asyncio.to_thread(read_inbox_messages, raw, 1)
    except MailReaderError as e:
        await loading_msg.edit_text(
            f"❌ Không đọc được mail:\n{e}\n\nBạn bấm Đọc lại mail này để thử lại, khỏi cần dán lại chuỗi mail.",
            reply_markup=mail_retry_kb(),
        )
        return
    except Exception as e:
        logger.exception("cmd_mail failed")
        await loading_msg.edit_text(
            f"❌ Lỗi không xác định khi đọc mail:\n{e}\n\nBạn bấm Đọc lại mail này để thử lại, khỏi cần dán lại chuỗi mail.",
            reply_markup=mail_retry_kb(),
        )
        return

    email = escape_markdown(result.get("email", ""), version=2)
    messages = result.get("messages") or []
    if not messages:
        await loading_msg.edit_text(
            f"Không thấy mail nào trong inbox của `{email}`\\.",
            parse_mode="MarkdownV2",
            reply_markup=mail_retry_kb(),
        )
        return

    lines = [f"*Inbox:* `{email}`"]
    latest_msg = messages[0]
    latest_code = (latest_msg.get("codes") or "").split(",", 1)[0].strip()
    if latest_code:
        code_md = escape_markdown(latest_code, version=2)
        lines.extend(["", f"*Mã mới nhất:* `{code_md}`"])

    for idx, msg in enumerate(messages, start=1):
        sender = escape_markdown(msg.get("from", ""), version=2)
        time_text = escape_markdown(msg.get("time", ""), version=2)
        subject = escape_markdown(msg.get("subject", ""), version=2)
        preview = escape_markdown((msg.get("preview", "") or "")[:350], version=2)
        codes = escape_markdown(msg.get("codes", ""), version=2)

        block = [
            "",
            f"*{idx}\\. {subject}*",
            f"From: `{sender}`",
            f"Time: `{time_text}`",
        ]
        if codes:
            block.append(f"Code: `{codes}`")
        if preview:
            block.append(preview)
        lines.extend(block)

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3900] + "\n..."

    try:
        await loading_msg.edit_text(
            text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=quick_actions_kb(),
        )
    except Exception as exc:
        logger.exception("render mail markdown failed")
        safe_email = result.get("email", "")
        await loading_msg.edit_text(
            f"❌ Đọc được mail nhưng lỗi định dạng hiển thị Telegram.\nMail: {safe_email}\nLỗi: {exc}",
            disable_web_page_preview=True,
            reply_markup=mail_retry_kb(),
        )


async def read_mail_from_text(update: Update, raw: str):
    if update.effective_user:
        LAST_MAIL_INPUT[update.effective_user.id] = raw
    loading_msg = await update.message.reply_text("Đang đọc hòm thư...")
    await render_mail_result(loading_msg, raw)


async def read_mail_again(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    raw = LAST_MAIL_INPUT.get(user_id, "").strip()
    if not raw:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Chưa có hòm thư gần nhất để đọc lại. Bạn gửi chuỗi mail hoặc dùng /mail trước nhé.",
            reply_markup=quick_actions_kb(),
        )
        return
    loading_msg = await context.bot.send_message(chat_id=chat_id, text="Đang đọc lại hòm thư...")
    await render_mail_result(loading_msg, raw)


async def cmd_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = " ".join(context.args).strip()
    if not raw and update.message.reply_to_message:
        raw = (update.message.reply_to_message.text or "").strip()

    if not raw:
        await update.message.reply_text(
            "Dùng: `/mail email|refresh_token|client_id`\n"
            "Hoặc gửi thẳng chuỗi `email|refresh_token|client_id` vào chat.",
            parse_mode="Markdown",
            reply_markup=quick_actions_kb(),
        )
        return

    await read_mail_from_text(update, raw)


async def send_mail_help(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📬 *ĐỌC HÒM THƯ*\n\n"
            "Cách 1:\n"
            "`/mail email|refresh_token|client_id`\n\n"
            "Cách 2:\n"
            "Gửi thẳng chuỗi `email|refresh_token|client_id` vào chat.\n\n"
            "Cách 3:\n"
            "Reply tin chứa chuỗi mail rồi gõ `/mail`.\n\n"
            "Bot sẽ đọc mail mới nhất và tự bắt mã số nếu có."
        ),
        parse_mode="Markdown",
        reply_markup=quick_actions_kb(),
    )

# ================== PRODUCTS FLOW ==================
async def show_products(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        products = await gs_call(load_products_cached)
        stock_ready = await gs_call(stock_count_ready_by_code_cached)
        fallback_prices = {p["stock_code"]: int(p["price"]) for p in products}
        pricing_enabled = {p["stock_code"]: bool(p.get("pricing_enabled", True)) for p in products}
        stock_prices = await gs_call(stock_price_preview_by_code, fallback_prices, pricing_enabled)
        products = [{**p, **stock_prices.get(p["stock_code"], {})} for p in products]
    except Exception as e:
        logger.exception("show_products error")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Lỗi Google Sheets:\n{e}",
            reply_markup=main_menu_keyboard(),
        )
        return

    if not products:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Chưa có sản phẩm trong tab PRODUCTS.",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = (
        "🛍 *MENU SẢN PHẨM*\n\n"
        "👉 Chọn sản phẩm bên dưới:"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=build_products_menu_kb(products, stock_ready),
    )

async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str):
    q = update.callback_query
    await q.answer()

    p = await gs_call(find_product_by_id, pid)
    if not p:
        return await q.edit_message_text("❌ Không tìm thấy sản phẩm.")

    ready_map = await gs_call(stock_count_ready_by_code_cached)
    ready = ready_map.get(p["stock_code"], 0)
    stock_prices = await gs_call(
        stock_price_preview_by_code,
        {p["stock_code"]: int(p["price"])},
        {p["stock_code"]: bool(p.get("pricing_enabled", True))},
    )
    p = {**p, **stock_prices.get(p["stock_code"], {})}
    await q.edit_message_text(
        product_detail_text(p, ready),
        parse_mode="Markdown",
        reply_markup=product_detail_kb(pid, ready, int(p["price"])),
    )

async def ask_qty(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str):
    q = update.callback_query
    await q.answer()

    p = await gs_call(find_product_by_id, pid)
    if not p:
        return await q.edit_message_text("❌ Không tìm thấy sản phẩm.")

    await q.edit_message_text(
        qty_select_text(p),
        parse_mode="Markdown",
        reply_markup=qty_select_kb(pid),
    )

async def set_custom_qty_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str, session_id: str = ""):
    q = update.callback_query
    await q.answer()

    p = await gs_call(find_product_by_id, pid)
    if not p:
        return await q.edit_message_text("❌ Không tìm thấy sản phẩm.")

    # có thể xoá/giữ tin cũ tuỳ bạn
    try:
        await q.message.delete()
    except Exception:
        pass

    # Clear the session from cache since we're proceeding with custom input
    if session_id:
        SELECTED_QTY_CACHE.pop(session_id, None)

    await prompt_custom_qty(context, q.from_user.id, {**p, "product_id": pid})

async def prompt_custom_qty(context: ContextTypes.DEFAULT_TYPE, user_id: int, p: Dict[str, Any], note: str = ""):
    # ✅ re-arm trạng thái nhập số lượng
    PENDING_QTY[user_id] = {"product_id": p["product_id"]}

    text = (note + "\n\n" if note else "") + f"✏️ Nhập số lượng muốn mua cho *{p['name']}* (>=1):"
    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Quay lại", callback_data=f"buy|{p['product_id']}")
        ]]),
    )

async def handle_custom_qty_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id not in PENDING_QTY:
        return False

    pid = PENDING_QTY[user_id]["product_id"]
    p = await gs_call(find_product_by_id, pid)
    if not p:
        PENDING_QTY.pop(user_id, None)
        await update.message.reply_text("❌ Sản phẩm không tồn tại.", reply_markup=main_menu_keyboard())
        return True

    t = (update.message.text or "").strip()
    if not t.isdigit() or int(t) <= 0:
        await update.message.reply_text(
            "❗ Vui lòng nhập số nguyên >= 1.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Quay lại", callback_data=f"buy|{pid}")
            ]])
        )
        return True

    qty = int(t)

    ok = await checkout_flow(user_id, p, qty, context, edit_query=None, from_custom_qty=True)

    if ok:
        PENDING_QTY.pop(user_id, None)  # ✅ chỉ pop khi tạo đơn OK
    # nếu fail thì giữ PENDING_QTY để user nhập lại

    return True


async def qty_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str, qty: int):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    user_id = q.from_user.id
    if user_id in CHECKOUT_IN_PROGRESS:
        try:
            await q.answer("Đơn trước đang tạo, đợi xíu nha.", show_alert=False)
        except Exception:
            pass
        return

    CHECKOUT_IN_PROGRESS.add(user_id)
    try:
        p = await gs_call(find_product_by_id, pid)
        if not p:
            return await q.edit_message_text("❌ Không tìm thấy sản phẩm.")
        ok = await checkout_flow(user_id, p, qty, context, edit_query=q)
        if not ok:
            return
    except Exception as e:
        logger.exception("checkout from qty button failed pid=%s qty=%s user=%s", pid, qty, user_id)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ Lỗi khi tạo đơn.\n"
                    "Bạn thử bấm mua lại giúp mình. Nếu vẫn lỗi, gửi admin ảnh màn hình này nhé."
                ),
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            logger.warning("failed to notify user after checkout error: %s", e)
    finally:
        CHECKOUT_IN_PROGRESS.discard(user_id)

# ================== JOBS ==================
def remove_jobs_by_prefix(app: Application, prefix: str):
    if not app.job_queue:
        return
    for j in app.job_queue.jobs():
        if j.name and j.name.startswith(prefix):
            try:
                j.schedule_removal()
            except Exception:
                pass

async def countdown_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    order_id = data.get("order_id", "")
    user_id = int(data.get("user_id") or 0)

    order = await gs_call(get_order, order_id)
    if not order:
        context.job.schedule_removal()
        return

    status = (order.get("status") or "").upper()
    if status != "PENDING":
        context.job.schedule_removal()
        return

    qr_msg_id = (order.get("qr_msg_id") or "").strip()
    if not qr_msg_id.isdigit():
        return

    remain = remaining_seconds(order.get("created_at", ""), ORDER_TTL_SECONDS)
    if remain <= 0:
        context.job.schedule_removal()
        return

    p = await gs_call(find_product_by_stock_code, order.get("stock_code", ""))
    if not p:
        return
    order_qty = normalize_int(order.get("qty"), 1)
    order_total = normalize_int(order.get("total"), 0)
    order_unit_price = order_total // order_qty if order_qty > 0 else int(p["price"])

    caption = build_checkout_caption_with_countdown(
        order_id=order_id,
        product_name=p["name"],
        unit_price=order_unit_price,
        qty=order_qty,
        total=order_total,
        remain_seconds=remain,
        status_line="⏳ *ĐANG CHỜ THANH TOÁN*",
    )
    qr_url = build_vietqr_image_url(order_id, normalize_int(order.get("total"), 0))
    caption_with_link = caption

    await edit_checkout_message(
        bot=context.bot,
        chat_id=user_id,
        message_id=int(qr_msg_id),
        text=caption_with_link,
        reply_markup=checkout_keyboard_pending(order_id),
        parse_mode="Markdown",
    )

async def ttl_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    order_id = str(data.get("order_id", "")).strip()
    user_id = int(data.get("user_id") or 0)
    if not order_id or not user_id:
        return

    order = await gs_call(get_order, order_id)
    if not order:
        return

    st = (order.get("status") or "PENDING").upper()
    if st in ("PAID", "DELIVERED", "CANCELLED", "EXPIRED"):
        return

    released = await gs_call(release_hold_by_order, order_id, "EXPIRED")

    qr_msg_id = (order.get("qr_msg_id") or "").strip()
    if qr_msg_id.isdigit():
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=int(qr_msg_id))
        except Exception:
            pass

    remove_jobs_by_prefix(context.application, f"countdown_{order_id}")

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"⌛ Đơn `{order_id}` đã *hết hạn* (quá {ORDER_TTL_SECONDS//60} phút) nên đã bị huỷ.\n"
            f"✅ Đã trả kho: *{released}* item.\n\n"
            "Bạn tạo đơn mới nếu vẫn muốn mua nhé."
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

    customer_text = await admin_customer_text(context, user_id)
    await notify_admins(
        context,
        (
            "⌛ *Đơn hết hạn đã huỷ*\n"
            f"Order: `{escape_markdown(order_id, version=2)}`\n"
            f"Khách: {escape_markdown(customer_text, version=2)}\n"
            f"Stock: `{escape_markdown(str(order.get('stock_code', '')), version=2)}`\n"
            f"SL: `{escape_markdown(str(order.get('qty', '')), version=2)}`\n"
            f"Tổng: *{escape_markdown(money_vnd(order.get('total', 0)), version=2)}*\n"
            f"Trả kho: *{released}* item"
        ),
    )

async def schedule_ttl(app: Application, user_id: int, order_id: str):
    if not app.job_queue:
        return
    app.job_queue.run_once(
        ttl_job,
        when=ORDER_TTL_SECONDS,
        data={"user_id": user_id, "order_id": order_id},
        name=f"ttl_{order_id}",
    )

# ================== CHECKOUT ==================
async def checkout_flow(
    user_id: int,
    product: Dict[str, Any],
    qty: int,
    context: ContextTypes.DEFAULT_TYPE,
    edit_query=None,
    from_custom_qty: bool = False,
) -> bool:
    pid = (product.get("product_id") or "").strip()
    if not pid:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Lỗi dữ liệu sản phẩm (thiếu product_id). Vui lòng thử lại từ /shop.",
            reply_markup=main_menu_keyboard(),
        )
        return False

    async def _ask_retry(note: str) -> None:
        PENDING_QTY[user_id] = {"product_id": pid}
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{note}\n\n✏️ Nhập lại số lượng cho *{product['name']}* (>=1):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Quay lại", callback_data=f"buy|{pid}")
            ]]),
        )

    # ✅ đọc stock bằng cache + thread
    ready_map = await gs_call(stock_count_ready_by_code_cached)
    ready = ready_map.get(product["stock_code"], 0)

    if qty > ready:
        msg = f"❌ Kho không đủ.\nCòn lại: {ready} | Bạn chọn: {qty}"
        if from_custom_qty:
            await _ask_retry(msg)
            return False
        if edit_query:
            try:
                await edit_query.edit_message_text(msg)
            except Exception:
                pass
        else:
            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=main_menu_keyboard())
        return False

    order_id = generate_order_id()
    created_at = now_str()
    # ✅ giữ kho chạy trong thread
    reserved_items = await gs_call(
        reserve_items_from_pool,
        product["stock_code"], qty, order_id, ORDER_TTL_SECONDS, int(product["price"]), bool(product.get("pricing_enabled", True))
    )
    if len(reserved_items) < qty:
        msg = "❌ Không thể giữ kho (POOL). Vui lòng nhập lại số lượng hoặc thử lại."
        if from_custom_qty:
            await _ask_retry(msg)
            return False
        if edit_query:
            try:
                await edit_query.edit_message_text(msg)
            except Exception:
                pass
        else:
            await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=main_menu_keyboard())
        return False

    total = sum(normalize_int(item.get("price"), int(product["price"])) for item in reserved_items)
    unit_price = round(total / qty) if qty > 0 else int(product["price"])
    price_notes = []
    first_item = reserved_items[0] if reserved_items else {}
    if first_item.get("is_time_priced"):
        price_notes.append(price_note_from_values(
            normalize_int(first_item.get("base_price"), int(product["price"])),
            normalize_int(first_item.get("duration_days"), 0),
            first_item.get("remaining_days"),
            str(first_item.get("expires_at") or ""),
        ))
    if qty > 1 and len({normalize_int(item.get("price"), 0) for item in reserved_items}) > 1:
        price_notes.append("Đơn có nhiều item khác hạn, tổng tiền được cộng theo giá từng item.")
    price_note = " ".join(note for note in price_notes if note)
    qr_url = build_vietqr_image_url(order_id, total)

    # ✅ cho user thấy bot đang làm việc
    try:
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_PHOTO)
    except Exception:
        pass

    # ✅ tải QR song song (giảm timeout để khỏi đứng lâu)
    qr_task = asyncio.create_task(fetch_qr_bytes(qr_url, timeout=6))

    # ✅ lưu order trong thread
    await gs_call(append_order, {
        "order_id": order_id,
        "user_id": user_id,
        "stock_code": product["stock_code"],
        "qty": qty,
        "total": total,
        "status": "PENDING",
        "qr_msg_id": "",
        "paid_at": "",
        "tx_id": "",
        "delivered_at": "",
        "deliver_text": "",
        "created_at": created_at,
    })

    if edit_query:
        try:
            await edit_query.delete_message()
        except Exception:
            pass

    caption = build_checkout_caption_with_countdown(
        order_id=order_id,
        product_name=product["name"],
        unit_price=unit_price,
        qty=qty,
        total=total,
        remain_seconds=ORDER_TTL_SECONDS,
        status_line="⏳ *ĐANG CHỜ THANH TOÁN*",
        price_note=price_note or product_price_note(product),
    )

    # ✅ lấy qr bytes (nếu fail -> None)
    try:
        img_bytes = await qr_task
    except Exception:
        img_bytes = None

    qr_msg_id = ""
    try:
        if img_bytes:
            bio = io.BytesIO(img_bytes)
            bio.name = "vietqr.png"
            m = await context.bot.send_photo(
                chat_id=user_id,
                photo=bio,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=checkout_keyboard_pending(order_id),
            )
        else:
            m = await context.bot.send_photo(
                chat_id=user_id,
                photo=qr_url,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=checkout_keyboard_pending(order_id),
            )

        qr_msg_id = str(m.message_id)
        await gs_call(set_order_fields, order_id, {"qr_msg_id": qr_msg_id})

    except Exception as e:
        logger.error("❌ send_photo failed for %s | qr_url=%s | err=%s", order_id, qr_url, e)
        try:
            m = await context.bot.send_message(
                chat_id=user_id,
                text=caption + "\n\n🔗 Nếu ảnh QR không hiện, bấm nút *Mở QR thanh toán* bên dưới.",
                parse_mode="Markdown",
                reply_markup=checkout_keyboard_pending_with_qr(order_id, qr_url),
                disable_web_page_preview=True,
            )
        except Exception as msg_err:
            logger.error("❌ send fallback checkout text failed for %s | err=%s", order_id, msg_err)
            plain_text = (
                "⏳ ĐANG CHỜ THANH TOÁN\n\n"
                f"🧾 Mã đơn: {order_id}\n"
                f"📦 SP: {product['name']} - {fmt_price(int(product['price']))}\n"
                f"🔢 SL: {qty}\n"
                f"💰 Tổng: {fmt_price(total)}\n\n"
                f"⏳ Hết hạn sau: {format_countdown(ORDER_TTL_SECONDS)}\n\n"
                "📌 Thanh toán:\n"
                f"• STK: {PAYMENT_INFO['bank_number']}\n"
                f"• Bank: {normalized_bank_code()}\n"
                f"• Nội dung CK: {normalize_order_ref(order_id)}\n\n"
                "🔗 Nếu ảnh QR không hiện, bấm nút Mở QR thanh toán bên dưới."
            )
            m = await context.bot.send_message(
                chat_id=user_id,
                text=plain_text,
                reply_markup=checkout_keyboard_pending_with_qr(order_id, qr_url),
                disable_web_page_preview=True,
            )
        qr_msg_id = str(m.message_id)
        await gs_call(set_order_fields, order_id, {"qr_msg_id": qr_msg_id})

    await schedule_ttl(context.application, user_id, order_id)

    if context.application.job_queue and qr_msg_id:
        context.application.job_queue.run_repeating(
            countdown_job,
            interval=60,
            first=60,
            data={"order_id": order_id, "user_id": user_id},
            name=f"countdown_{order_id}",
        )

    customer_text = await admin_customer_text(context, user_id)
    await notify_admins(
        context,
        (
            "🛒 *Đơn mới đang chờ thanh toán*\n"
            f"Order: `{escape_markdown(order_id, version=2)}`\n"
            f"Khách: {escape_markdown(customer_text, version=2)}\n"
            f"Sản phẩm: {escape_markdown(str(product.get('name', product['stock_code'])), version=2)}\n"
            f"Stock: `{escape_markdown(str(product['stock_code']), version=2)}`\n"
            f"SL: `{qty}`\n"
            f"Tổng: *{escape_markdown(money_vnd(total), version=2)}*\n"
            f"Tạo lúc: `{escape_markdown(created_at, version=2)}`"
        ),
    )

    return True




# ================== CONFIRM / CANCEL ==================
async def confirm_paid(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    q = update.callback_query
    await q.answer()

    order = await gs_call(get_order, order_id)
    if not order:
        try:
            return await q.edit_message_caption(caption="❌ Không tìm thấy đơn.", parse_mode="Markdown")
        except Exception:
            return await context.bot.send_message(
                chat_id=q.from_user.id,
                text="❌ Không tìm thấy đơn.",
                reply_markup=main_menu_keyboard(),
            )
    if (order.get("user_id") or "").strip() != str(q.from_user.id):
        await q.answer("⛔ Bạn không có quyền thao tác đơn này.", show_alert=True)
        return

    status = (order.get("status", "") or "PENDING").upper()
    stock_code = (order.get("stock_code") or "").strip()

    # Nếu chưa PAID -> thông báo kiểm tra
    if status not in ("PAID", "DELIVERED"):
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=(
                "⏳ *Đang kiểm tra giao dịch...*\n\n"
                "⌛ Vui lòng đợi trong giây lát...\n\n"
                "*CHƯA TÌM THẤY GIAO DỊCH*\n"
                "Hệ thống chưa phát hiện thanh toán của bạn.\n\n"
                "💡 Vui lòng:\n"
                "• Đợi thêm vài giây\n"
                "• Kiểm tra lại nội dung chuyển khoản\n"
                "• Thử lại sau"
            ),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    # ================== RESEND nếu đã DELIVERED ==================
    if status == "DELIVERED":
        delivered_at = (order.get("delivered_at") or now_str()).strip()

        deliver_text_plain = (order.get("deliver_text") or "").strip()
        secrets_plain: List[str] = []

        # Ưu tiên từ ORDERS.deliver_text (dạng "1) xxx")
        if deliver_text_plain and deliver_text_plain != "(trống)":
            for line in deliver_text_plain.splitlines():
                line = line.strip()
                if not line:
                    continue
                if ")" in line:
                    sec = line.split(")", 1)[1].strip()
                else:
                    sec = line.lstrip("-").strip()
                if sec:
                    secrets_plain.append(_safe_secret(sec))

        # Fallback: FULFILLMENTS
        if not secrets_plain:
            secrets_plain = [_safe_secret(x) for x in await gs_call(get_fulfillment_secrets, order_id)]

        secrets_md = [f"{i}) `{_safe_secret(s)}`" for i, s in enumerate(secrets_plain, start=1)]
        qty_val = normalize_int(order.get("qty"), len(secrets_plain) if secrets_plain else 1)

        # edit checkout message -> best effort
        delivered_caption = (
            "✅ *ĐƠN ĐÃ GIAO TRƯỚC ĐÓ*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🧾 *Mã đơn:* `{order_id}`\n"
            f"📦 *SP:* `{stock_code}`\n"
            f"⏱ *Thời gian:* {delivered_at}\n\n"
            "📩 Mình đang gửi lại thông tin đơn cho bạn..."
        )
        try:
            await q.edit_message_caption(caption=delivered_caption, parse_mode="Markdown", reply_markup=None)
        except Exception:
            pass

        # >=5 -> gửi file + preview
        if qty_val >= 5 or len(secrets_plain) >= 5:
            preview_n = 2
            preview_md = "\n".join(secrets_md[:preview_n]) if secrets_md else "(trống)"
            more_count = max(0, len(secrets_md) - preview_n)

            direct_text = delivery_copy_message(
                "✅ ĐƠN ĐÃ GIAO — GỬI LẠI",
                order_id,
                stock_code,
                qty_val,
                delivered_at,
                [f"{i}) {s}" for i, s in enumerate(secrets_plain, start=1)],
            )
            for start in range(0, len(direct_text), 3800):
                chunk = direct_text[start:start + 3800]
                await context.bot.send_message(
                    chat_id=q.from_user.id,
                    text=chunk,
                    parse_mode=ParseMode.HTML if len(direct_text) <= 3800 else None,
                    reply_markup=main_menu_keyboard() if start + 3800 >= len(direct_text) else None,
                    disable_web_page_preview=True,
                )

            content = (
                f"ORDER: {order_id}\n"
                f"PRODUCT: {stock_code}\n"
                f"QTY: {qty_val}\n"
                f"DELIVERED_AT: {delivered_at}\n"
                "====================\n"
                + "\n".join([f"{i}) {s}" for i, s in enumerate(secrets_plain, start=1)]) +
                "\n"
            )
            bio = io.BytesIO(content.encode("utf-8"))
            bio.name = f"{order_id}.txt"

            await context.bot.send_document(
                chat_id=q.from_user.id,
                document=bio,
                caption=(
                    "✅ *ĐƠN ĐÃ GIAO — GỬI LẠI*\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"🧾 *Mã đơn:* `{order_id}`\n"
                    f"📦 *SP:* `{stock_code}`\n"
                    f"🔢 *SL:* *{qty_val}*\n\n"
                    "👀 *Preview (1–2 dòng):*\n"
                    f"{preview_md}\n"
                    f"{'…' if more_count > 0 else ''}\n\n"
                    "📎 *File .txt dự phòng, nội dung đầy đủ đã gửi ở tin nhắn phía trên*.\n"
                    "🔐 *Lấy OTP:* copy đơn vừa mua ở tin nhắn trên rồi dán thẳng vào bot."
                ),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard(),
            )
            return

        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=delivery_copy_message(
                "✅ ĐƠN ĐÃ GIAO — GỬI LẠI",
                order_id,
                stock_code,
                qty_val,
                delivered_at,
                [f"{i}) {s}" for i, s in enumerate(secrets_plain, start=1)],
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(),
        )
        return

    # ================== GIAO HÀNG khi status=PAID ==================
    items = await gs_call(mark_sold_and_get_secrets, order_id)
    # Fallback: nếu không tìm thấy HELD nhưng fulfillments đã có -> coi như delivered và resend
    if not items:
        secrets = await gs_call(get_fulfillment_secrets, order_id)
        if secrets:
            await gs_call(set_order_fields, order_id, {"status": "DELIVERED"})
            return await confirm_paid(update, context, order_id)

        await context.bot.send_message(
            chat_id=q.from_user.id,
            text="❌ Không tìm thấy item HELD để giao (POOL).",
            reply_markup=main_menu_keyboard(),
        )
        return


    delivered_at = now_str()

    secrets_plain = []
    secrets_md = []
    for i, it in enumerate(items, start=1):
        sec = _safe_secret(it.get("secret", ""))
        if not sec:
            continue
        secrets_plain.append(f"{i}) {sec}")
        secrets_md.append(f"{i}) `{sec}`")

    deliver_text_plain = "\n".join(secrets_plain) if secrets_plain else "(trống)"
    deliver_text_md = "\n".join(secrets_md) if secrets_md else "(trống)"

    await gs_call(append_fulfillments_bulk, order_id, items, delivered_at)

    await gs_call(set_order_fields, order_id, {
        "status": "DELIVERED",
        "delivered_at": delivered_at,
        "deliver_text": deliver_text_plain
    })

    # stop countdown job
    remove_jobs_by_prefix(context.application, f"countdown_{order_id}")

    # edit checkout message -> best effort
    delivered_caption = (
        "✅ *ĐÃ GIAO HÀNG*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *Mã đơn:* `{order_id}`\n"
        f"📦 *SP:* `{stock_code}`\n"
        f"⏱ *Thời gian:* {delivered_at}\n\n"
        "📩 Mình đã gửi thông tin nhận được ở tin nhắn bên dưới."
    )
    try:
        await q.edit_message_caption(caption=delivered_caption, parse_mode="Markdown", reply_markup=checkout_keyboard_done())
    except Exception:
        try:
            await q.edit_message_text(text=delivered_caption, parse_mode="Markdown", reply_markup=checkout_keyboard_done())
        except Exception:
            pass

    qty_val = normalize_int(order.get("qty"), len(secrets_plain) if secrets_plain else len(items))

    await notify_admins(
        context,
        (
            "✅ *Đơn đã giao thành công*\n"
            f"Order: `{escape_markdown(order_id, version=2)}`\n"
            f"Khách: `{q.from_user.id}`\n"
            f"Stock: `{escape_markdown(stock_code, version=2)}`\n"
            f"SL: `{qty_val}`\n"
            f"Tổng: *{escape_markdown(money_vnd(order.get('total')), version=2)}*\n"
            f"Giao lúc: `{escape_markdown(delivered_at, version=2)}`"
        ),
    )

    # >=5 -> gửi file + preview
    if qty_val >= 5 or len(secrets_plain) >= 5:
        preview_n = 2
        preview_md = "\n".join(secrets_md[:preview_n]) if secrets_md else "(trống)"
        more_count = max(0, len(secrets_md) - preview_n)

        direct_text = delivery_copy_message(
            "✅ MUA HÀNG THÀNH CÔNG",
            order_id,
            stock_code,
            qty_val,
            delivered_at,
            secrets_plain,
        )
        for start in range(0, len(direct_text), 3800):
            chunk = direct_text[start:start + 3800]
            await context.bot.send_message(
                chat_id=q.from_user.id,
                text=chunk,
                parse_mode=ParseMode.HTML if len(direct_text) <= 3800 else None,
                reply_markup=main_menu_keyboard() if start + 3800 >= len(direct_text) else None,
                disable_web_page_preview=True,
            )

        content = (
            f"ORDER: {order_id}\n"
            f"PRODUCT: {stock_code}\n"
            f"QTY: {qty_val}\n"
            f"DELIVERED_AT: {delivered_at}\n"
            "====================\n"
            + deliver_text_plain +
            "\n"
        )
        bio = io.BytesIO(content.encode("utf-8"))
        bio.name = f"{order_id}.txt"

        await context.bot.send_document(
            chat_id=q.from_user.id,
            document=bio,
            caption=(
                "✅ *MUA HÀNG THÀNH CÔNG*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🧾 *Mã đơn:* `{order_id}`\n"
                f"📦 *SP:* `{stock_code}`\n"
                f"🔢 *SL:* *{qty_val}*\n\n"
                "👀 *Preview (1–2 dòng):*\n"
                f"{preview_md}\n"
                f"{'…' if more_count > 0 else ''}\n\n"
                "📎 *File .txt dự phòng, nội dung đầy đủ đã gửi ở tin nhắn phía trên*.\n"
                "🔐 *Lấy OTP:* copy đơn vừa mua ở tin nhắn trên rồi dán thẳng vào bot.\n"
                "🔐 Nếu là tài khoản, vui lòng *đổi mật khẩu ngay* sau khi đăng nhập."
            ),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=delivery_copy_message(
            "✅ MUA HÀNG THÀNH CÔNG",
            order_id,
            stock_code,
            qty_val,
            delivered_at,
            secrets_plain,
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    q = update.callback_query
    await q.answer()

    order = await gs_call(get_order,order_id)
    if not order:
        await context.bot.send_message(chat_id=q.from_user.id, text="❌ Không tìm thấy đơn.", reply_markup=main_menu_keyboard())
        return
    # ✅ CHECK QUYỀN
    if (order.get("user_id") or "").strip() != str(q.from_user.id):
        await q.answer("⛔ Bạn không có quyền huỷ đơn này.", show_alert=True)
        return

    st = (order.get("status") or "PENDING").upper()
    if st in ("DELIVERED",):
        await context.bot.send_message(chat_id=q.from_user.id, text="✅ Đơn đã giao, không thể huỷ.", reply_markup=main_menu_keyboard())
        return

    released = await gs_call(release_hold_by_order,order_id, "CANCELLED")

    qr_msg_id = (order.get("qr_msg_id") or "").strip()
    if qr_msg_id.isdigit():
        try:
            await context.bot.delete_message(chat_id=q.from_user.id, message_id=int(qr_msg_id))
        except Exception:
            pass

    remove_jobs_by_prefix(context.application, f"countdown_{order_id}")

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=f"❌ Đã huỷ đơn `{order_id}`.\n✅ Trả kho: *{released}* item.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

# ================== ORDERS SCREEN ==================
# ✅ Thêm hàm này (đặt ở gần restore_pending_jobs cũng được)
async def bootstrap_job(context: ContextTypes.DEFAULT_TYPE):
    await restore_pending_jobs(context.application)


async def release_overdue_pending_job(context: ContextTypes.DEFAULT_TYPE):
    """Quét định kỳ để trả HELD nếu bot/Render bị restart làm mất job TTL."""
    try:
        orphan_released = await gs_call(release_expired_held_items_from_pool)
        if orphan_released:
            logger.info("✅ Auto released expired HELD items from pool=%s", orphan_released)
    except Exception as e:
        logger.error("release_expired_held_items_from_pool failed: %s", e)

    try:
        pending = await gs_call(list_pending_orders)
    except Exception as e:
        logger.error("release_overdue_pending_job failed: %s", e)
        return

    expired_count = 0
    released_total = 0
    for order in pending:
        order_id = (order.get("order_id") or "").strip()
        user_id_s = (order.get("user_id") or "").strip()
        created_at_s = (order.get("created_at") or "").strip()
        qr_msg_id_s = (order.get("qr_msg_id") or "").strip()
        created_dt = parse_dt(created_at_s)
        if not order_id or not created_dt:
            continue
        if (created_dt + timedelta(seconds=ORDER_TTL_SECONDS)) > now_dt():
            continue

        released = await gs_call(release_hold_by_order, order_id, "EXPIRED")
        expired_count += 1
        released_total += released
        remove_jobs_by_prefix(context.application, f"countdown_{order_id}")
        remove_jobs_by_prefix(context.application, f"ttl_{order_id}")

        if released and user_id_s.isdigit():
            user_id = int(user_id_s)
            if qr_msg_id_s.isdigit():
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=int(qr_msg_id_s))
                except Exception:
                    pass
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⌛ Đơn `{order_id}` đã *hết hạn* nên hệ thống đã huỷ.\n"
                        f"✅ Đã trả kho: *{released}* item.\n\n"
                        "Bạn tạo đơn mới nếu vẫn muốn mua nhé."
                    ),
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard(),
                )
            except Exception:
                pass

        if user_id_s.isdigit():
            customer_text = await admin_customer_text(context, int(user_id_s))
        else:
            customer_text = user_id_s or "unknown"
        await notify_admins(
            context,
            (
                "⌛ *Đơn hết hạn đã huỷ*\n"
                f"Order: `{escape_markdown(order_id, version=2)}`\n"
                f"Khách: {escape_markdown(customer_text, version=2)}\n"
                f"Stock: `{escape_markdown(str(order.get('stock_code', '')), version=2)}`\n"
                f"SL: `{escape_markdown(str(order.get('qty', '')), version=2)}`\n"
                f"Tổng: *{escape_markdown(money_vnd(order.get('total', 0)), version=2)}*\n"
                f"Trả kho: *{released}* item"
            ),
        )

    if expired_count:
        logger.info("✅ Auto released overdue orders=%s items=%s", expired_count, released_total)


async def restore_pending_jobs(app: Application):
    """Khôi phục TTL/Countdown cho các đơn PENDING khi bot vừa chạy lại."""
    if not app.job_queue:
        return

    try:
        pending = await gs_call(list_pending_orders)
    except Exception as e:
        logger.error("restore_pending_jobs failed: %s", e)
        return

    for o in pending:
        order_id = (o.get("order_id") or "").strip()
        user_id_s = (o.get("user_id") or "").strip()
        created_at_s = (o.get("created_at") or "").strip()
        qr_msg_id_s = (o.get("qr_msg_id") or "").strip()

        if not order_id or not user_id_s.isdigit():
            continue
        user_id = int(user_id_s)

        created_dt = parse_dt(created_at_s)
        if not created_dt:
            continue

        # thời gian còn lại
        expire_dt = created_dt + timedelta(seconds=ORDER_TTL_SECONDS)
        remain = int((expire_dt - now_dt()).total_seconds())

        # Nếu đã quá hạn -> trả kho + xoá QR + báo user (best effort)
        if remain <= 0:
            released = await gs_call(release_hold_by_order, order_id, "EXPIRED")

            # dọn job cũ nếu có (phòng trường hợp trùng)
            remove_jobs_by_prefix(app, f"countdown_{order_id}")
            remove_jobs_by_prefix(app, f"ttl_{order_id}")

            if not released:
                continue

            # xoá tin QR nếu có
            if qr_msg_id_s.isdigit():
                try:
                    await app.bot.delete_message(chat_id=user_id, message_id=int(qr_msg_id_s))
                except Exception:
                    pass

            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⌛ Đơn `{order_id}` đã *hết hạn* nên hệ thống đã huỷ.\n"
                        f"✅ Đã trả kho: *{released}* item.\n\n"
                        "Bạn tạo đơn mới nếu vẫn muốn mua nhé."
                    ),
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard(),
                )
            except Exception:
                pass
            continue

        # Nếu còn hạn -> schedule TTL theo remain
        app.job_queue.run_once(
            ttl_job,
            when=remain,
            data={"user_id": user_id, "order_id": order_id},
            name=f"ttl_{order_id}",
        )

        # schedule countdown nếu có qr_msg_id
        if qr_msg_id_s.isdigit():
            app.job_queue.run_repeating(
                countdown_job,
                interval=60,
                first=60,
                data={"order_id": order_id, "user_id": user_id},
                name=f"countdown_{order_id}",
            )

    logger.info("✅ Restored jobs for %s pending orders", len(pending))



def parse_dt(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime((s or "").strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def list_pending_orders() -> List[Dict[str, str]]:
    """Lấy tất cả orders status=PENDING để khôi phục job sau khi bot restart."""
    init_sheets()
    vals = _ws_orders.get_all_values()
    if not vals or len(vals) < 2:
        return []
    h = {str(x).strip().lower(): i for i, x in enumerate(vals[0], start=1)}

    c_status = h.get("status")
    if not c_status:
        return []

    out = []
    for idx in range(2, len(vals) + 1):
        r = vals[idx - 1]
        st = r[c_status - 1].strip().upper() if c_status - 1 < len(r) else ""
        if st == "PENDING":
            d = {}
            for k, c in h.items():
                d[k] = r[c - 1].strip() if c - 1 < len(r) else ""
            out.append(d)
    return out




def status_emoji(status: str) -> str:
    s = (status or "").upper()
    if s == "PENDING":
        return "⏳"
    if s == "PAID":
        return "✅"
    if s == "DELIVERED":
        return "🎁"
    if s == "CANCELLED":
        return "❌"
    if s == "EXPIRED":
        return "⌛"
    return "⏳"

async def show_orders(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        orders = await gs_call(list_user_orders, user_id, 50)  # ✅ Increase limit to 50
    except Exception as e:
        logger.exception("show_orders error")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Lỗi Google Sheets:\n{e}",
            reply_markup=main_menu_keyboard(),
        )
        return
    if not orders:
        await context.bot.send_message(
            chat_id=user_id,
            text="📦 *ĐƠN HÀNG ĐÃ MUA*\n\n(Trống)\n\nBấm 🛍 Sản phẩm để mua.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["📦 *ĐƠN HÀNG ĐÃ MUA*\n", "Danh sách 10 đơn gần nhất:\n", "━━━━━━━━━━━━━━━━"]
    kb_rows = []

    for o in orders[:10]:  # ✅ Show first 10 instead of 5
        oid = o.get("order_id", "")
        sc = o.get("stock_code", "")
        qty = o.get("qty", "")
        total = normalize_int(o.get("total"), 0)
        created = o.get("created_at", "")
        st = o.get("status", "PENDING")
        emoji = status_emoji(st)

        lines.append(
            f"\n`{oid}`\n"
            f"SP: `{sc}` | SL: *{qty}*\n"
            f"Tổng: *{fmt_price(total)}*\n"
            f"📅 {created}\n"
            f"📌 Trạng thái: {emoji} *{st}*\n"
            "━━━━━━━━━━━━━━━━"
        )

        p = await gs_call(find_product_by_stock_code, sc)
        if p:
            kb_rows.append([InlineKeyboardButton(f"🔁 Mua lại: {p['name']}", callback_data=f"rebuy|{p['product_id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Menu chính", callback_data="back_main")])

    await context.bot.send_message(
        chat_id=user_id,
        text="\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )

# ================== ACCOUNT ==================
async def show_account(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user):
    orders = await gs_call(list_user_orders, user.id, 200)
    count = len(orders)
    total_spent = sum(normalize_int(o.get("total"), 0) for o in orders)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "👤 *TÀI KHOẢN*\n\n"
            f"• Họ tên: *{user.full_name}*\n"
            f"• Username: @{user.username if user.username else '—'}\n"
            f"• User ID: `{user.id}`\n\n"
            f"📦 Tổng đơn: *{count}*\n"
            f"💰 Tổng đã mua: *{fmt_price(total_spent)}*"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

# ================== TEXT ROUTER ==================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_custom_qty_input(update, context):
        return

    user = update.effective_user
    try:
        await gs_call(upsert_user, update.effective_chat.id, user.username or "", user.full_name or "")
    except Exception:
        logger.exception("upsert_user failed")

    text = (update.message.text or "").strip()
    text = text.replace("\ufe0f", "")
    text = " ".join(text.split())
    menu_text = normalize_menu_text(text)

    if looks_like_mail_account(text):
        return await read_mail_from_text(update, text)
    if looks_like_totp_secret(text):
        return await send_2fa_from_text(update, context, text)

    if text == BTN_PRODUCTS or "sản phẩm" in menu_text or "san pham" in menu_text:
        return await show_products(user.id, context)
    if text == BTN_SUPPORT or "hỗ trợ" in menu_text or "ho tro" in menu_text:
        return await send_support(user.id, context)
    if text == BTN_ORDERS or "đơn hàng" in menu_text or "don hang" in menu_text:
        return await show_orders(user.id, context)
    if text == BTN_GAME or menu_text == "game":
        return await cmd_game(update, context)
    if text == BTN_2FA or menu_text in {"2fa", "ma 2fa", "mã 2fa"}:
        return await send_2fa_help(user.id, context)
    if text == BTN_MAIL or "đọc mail" in menu_text or "doc mail" in menu_text:
        return await send_mail_help(user.id, context)

    await update.message.reply_text("Bấm menu để sử dụng nhé.", reply_markup=main_menu_keyboard())


# ================== CALLBACK ROUTER ==================
async def run_hangve_broadcast(context: ContextTypes.DEFAULT_TYPE, admin_chat_id: int, custom_text: str) -> None:
    if HANGVE_LOCK.locked():
        await context.bot.send_message(chat_id=admin_chat_id, text="Đang có một lượt /hangve chạy rồi, đợi xong giúp mình nhé.")
        return

    async with HANGVE_LOCK:
        text = custom_text
        reply_markup = buy_suggestion_kb()
        if not text:
            try:
                text = await stock_update_text()
                reply_markup = stock_update_kb()
            except Exception:
                logger.exception("build stock update failed")
                text = "✅ *HÀNG ĐÃ VỀ*\n\n🔥 Sản phẩm đã có hàng lại!\n👉 Bấm nút bên dưới để mua nhé."

        user_ids = await gs_call(get_all_user_chat_ids)
        ok = fail = 0
        for cid in user_ids:
            try:
                await context.bot.send_message(
                    chat_id=cid,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
                ok += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                fail += 1
                logger.warning("send hangve fail chat_id=%s err=%s", cid, e)

        await context.bot.send_message(chat_id=admin_chat_id, text=f"Đã gửi: {ok} | Lỗi: {fail}")


# ✅ Gửi nền để Telegram không retry cùng một lệnh /hangve nhiều lần.
async def cmd_hangve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    text = " ".join(context.args).strip()
    await update.message.reply_text("Đã nhận /hangve, đang gửi nền...")
    asyncio.create_task(run_hangve_broadcast(context, update.effective_chat.id, text))



async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = (q.data or "").strip()

    # ✅ NÚT NHANH: Đơn hàng / Hỗ trợ
    if data == "go_products":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await show_products(q.from_user.id, context)

    if data == "go_orders":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await show_orders(q.from_user.id, context)

    if data == "go_support":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await send_support(q.from_user.id, context)

    if data == "refresh_stock":
        await q.answer("Đang cập nhật kho...")
        try:
            text = await stock_update_text()
            await q.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=stock_update_kb(),
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.exception("refresh stock callback failed")
            await q.answer(f"Lỗi cập nhật kho: {exc}", show_alert=True)
        return

    if data == "mail_help":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await send_mail_help(q.from_user.id, context)

    if data == "mail_repeat":
        await q.answer("Đang đọc lại thư...")
        return await read_mail_again(q.message.chat_id, q.from_user.id, context)

    if data == "2fa_help":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await send_2fa_help(q.from_user.id, context)

    if data == "back_main":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=welcome_text(q.from_user.full_name),
            parse_mode="Markdown",
            reply_markup=welcome_inline_kb(),
        )
        return

    if data == "back_products":
        await q.answer()
        try:
            await q.message.delete()
        except Exception:
            pass
        return await show_products(q.from_user.id, context)

    if data.startswith("pdetail|"):
        pid = data.split("|", 1)[1]
        return await show_product_detail(update, context, pid)

    if data.startswith("pdetail_back|"):
        pid = data.split("|", 1)[1]
        return await show_product_detail(update, context, pid)

    if data.startswith("buy|"):
        pid = data.split("|", 1)[1]
        return await ask_qty(update, context, pid)

    if data.startswith("qty|"):
        # ✅ FIX: Extract from session cache instead of callback_data
        _, session_id, qty_s = data.split("|", 2)
        cached = SELECTED_QTY_CACHE.get(session_id, {})
        pid = cached.get("pid", "")
        if not pid:
            created_at = cached.get("created_at", 0)
            expired_secs = int(time.time() - created_at) if created_at else 0
            if created_at and expired_secs > SESSION_EXPIRY_SECONDS:
                msg = f"❌ Session hết hạn ({expired_secs}s). Vui lòng bấm 'Mua ngay' lại."
            else:
                msg = "❌ Session không hợp lệ. Vui lòng quay lại chọn sản phẩm."
            await q.answer(msg, show_alert=True)
            return
        try:
            qty = int(qty_s)
            if qty <= 0:
                await q.answer("❌ Số lượng phải > 0", show_alert=True)
                return
            await q.answer("Đang tạo đơn...")
            SELECTED_QTY_CACHE.pop(session_id, None)
            return await qty_chosen(update, context, pid, qty)
        except (ValueError, TypeError):
            await q.answer("❌ Số lượng không hợp lệ", show_alert=True)
            return

    if data.startswith("qtypid|"):
        _, pid, qty_s = data.split("|", 2)
        try:
            qty = int(qty_s)
            if qty <= 0:
                await q.answer("❌ Số lượng phải > 0", show_alert=True)
                return
            await q.answer("Đang tạo đơn...")
            return await qty_chosen(update, context, pid, qty)
        except (ValueError, TypeError):
            await q.answer("❌ Số lượng không hợp lệ", show_alert=True)
            return

    if data.startswith("qtycustom|"):
        # ✅ FIX: Extract from session cache instead of callback_data
        session_id = data.split("|", 1)[1]
        cached = SELECTED_QTY_CACHE.get(session_id, {})  # Use .get() to check without removing
        pid = cached.get("pid", "")
        if not pid:
            created_at = cached.get("created_at", 0)
            expired_secs = int(time.time() - created_at) if created_at else 0
            if created_at and expired_secs > SESSION_EXPIRY_SECONDS:
                msg = f"❌ Session hết hạn ({expired_secs}s). Vui lòng bấm 'Mua ngay' lại."
            else:
                msg = "❌ Session không hợp lệ. Vui lòng quay lại chọn sản phẩm."
            await q.answer(msg, show_alert=True)
            return
        return await set_custom_qty_prompt(update, context, pid, session_id)

    if data.startswith("qtycustompid|"):
        pid = data.split("|", 1)[1]
        return await set_custom_qty_prompt(update, context, pid)

    if data.startswith("confirm|"):
        oid = data.split("|", 1)[1]
        return await confirm_paid(update, context, oid)

    if data.startswith("cancel|"):
        oid = data.split("|", 1)[1]
        return await cancel_order(update, context, oid)

    if data.startswith("rebuy|"):
        pid = data.split("|", 1)[1]
        if q.from_user.id in CHECKOUT_IN_PROGRESS:
            await q.answer("Đơn trước đang tạo, đợi xíu nha.")
            return
        p = await gs_call(find_product_by_id, pid)
        if not p:
            await q.answer("Không tìm thấy sản phẩm", show_alert=True)
            return
        await q.answer("Đang tạo đơn...")
        CHECKOUT_IN_PROGRESS.add(q.from_user.id)
        try:
            return await checkout_flow(q.from_user.id, p, 1, context, edit_query=q)
        except Exception:
            logger.exception("checkout from rebuy failed pid=%s user=%s", pid, q.from_user.id)
            await context.bot.send_message(
                chat_id=q.from_user.id,
                text="❌ Lỗi khi tạo đơn. Bạn thử lại giúp mình nhé.",
                reply_markup=main_menu_keyboard(),
            )
            return
        finally:
            CHECKOUT_IN_PROGRESS.discard(q.from_user.id)

    await q.answer()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error:
        logger.error(
            "Unhandled telegram error",
            exc_info=(type(context.error), context.error, context.error.__traceback__),
        )
    else:
        logger.error("Unhandled telegram error without exception object")
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Bot vừa gặp lỗi xử lý. Bạn thử lại giúp mình nhé.",
                reply_markup=main_menu_keyboard(),
            )
    except Exception:
        logger.exception("failed to send generic error message")


def configure_application(app: Application) -> Application:
    if not app.job_queue:
        logger.warning("⚠️ JobQueue not available. Install: pip install python-telegram-bot[job-queue]")
    else:
        # ✅ khôi phục TTL/Countdown cho các đơn PENDING sau restart
        app.job_queue.run_once(bootstrap_job, when=2, name="bootstrap_restore")
        app.job_queue.run_repeating(
            release_overdue_pending_job,
            interval=60,
            first=20,
            name="release_overdue_pending",
        )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["shop", "sanpham"], cmd_shop))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler(["support", "hotro"], cmd_support))
    app.add_handler(CommandHandler("game", cmd_game))
    app.add_handler(CommandHandler("hangve", cmd_hangve))
    app.add_handler(CommandHandler("mail", cmd_mail))
    app.add_handler(CommandHandler("2fa", cmd_2fa))
    app.add_handler(CommandHandler("otp", cmd_2fa))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_error_handler(error_handler)
    return app


def build_application() -> Application:
    try:
        init_sheets()
        logger.info("✅ Sheets OK: %s", GSHEET_ID)
    except Exception as e:
        logger.error("❌ init_sheets error: %s", e)

    app = Application.builder().token(BOT_TOKEN).post_init(setup_bot_commands).build()
    return configure_application(app)


# ================== MAIN ==================
def main():
    app = build_application()
    logger.info("✅ Bot running...")
    app.run_polling(drop_pending_updates=True, stop_signals=False)


if __name__ == "__main__":
    main()
