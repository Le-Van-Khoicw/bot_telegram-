import logging
import os
import random
import string
from typing import Any, Dict, List

import requests
from gspread.cell import Cell

import bot_shop as shop

MATERIALS_TAB = "MATERIALS"
MATERIALS_HEADERS = ["id", "value", "status", "note", "created_at", "updated_at"]
MATERIALS_COLLECTION = os.getenv("FIREBASE_MATERIALS_COLLECTION", "materials").strip() or "materials"
GPT_MARKS_TAB = "GPT_MARKS"
GPT_MARK_HEADERS = ["key", "value", "status", "note", "subject", "updated_at"]
logger = logging.getLogger("admin_services")

_firebase_ready = False
_firestore_client = None


def _records(ws) -> List[Dict[str, str]]:
    return shop.get_all_records(ws) if ws else []


def _headers(ws) -> Dict[str, int]:
    return shop.headers_map(ws) if ws else {}


def _row_from_headers(headers: Dict[str, int], data: Dict[str, Any]) -> List[str]:
    row = [""] * len(headers)
    for key, value in data.items():
        col = headers.get(key.lower())
        if col:
            row[col - 1] = "" if value is None else str(value)
    return row


def _make_item_id(stock_code: str) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{stock_code.strip().upper()}-{shop.now_dt().strftime('%Y%m%d%H%M%S')}-{suffix}"


def _secret_key(value: Any) -> str:
    raw = str(value or "").strip()
    first_part = raw.split("|", 1)[0].split("----", 1)[0].strip() or raw
    return first_part.lower()


def _gpt_marks_ws(update_header: bool = True):
    shop.init_sheets()
    try:
        ws = shop._gs_sheet.worksheet(GPT_MARKS_TAB)
    except Exception:
        try:
            ws = shop._gs_sheet.add_worksheet(title=GPT_MARKS_TAB, rows=1000, cols=len(GPT_MARK_HEADERS))
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise
            ws = shop._gs_sheet.worksheet(GPT_MARKS_TAB)
        ws.update("A1:F1", [GPT_MARK_HEADERS], value_input_option="USER_ENTERED")
        return ws

    if update_header:
        try:
            headers = [str(h).strip().lower() for h in ws.row_values(1)]
        except Exception:
            headers = []
        if not any(headers):
            ws.update("A1:F1", [GPT_MARK_HEADERS], value_input_option="USER_ENTERED")
    return ws


def load_gpt_marks() -> List[Dict[str, str]]:
    rows = _records(_gpt_marks_ws(update_header=False))
    rows.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return rows


def _plain_stock_update_text() -> str:
    products = shop.load_products_cached()
    stock_ready = shop.stock_count_ready_by_code_cached()
    available = [
        (product, stock_ready.get(product["stock_code"], 0))
        for product in products
        if stock_ready.get(product["stock_code"], 0) > 0
    ]
    available.sort(key=lambda item: item[1], reverse=True)
    total = sum(qty for _, qty in available)

    lines = [
        "📦 CẬP NHẬT KHO HÀNG ✨",
        "",
        f"🕒 Cập nhật: {shop.now_str()}",
        f"📊 Sản phẩm còn hàng: {len(available)} | Tổng tồn: {total}",
        "",
        "Tồn kho hiện tại:",
        "",
    ]
    if not available:
        lines.append("⛔ Hiện chưa có sản phẩm còn hàng.")
    else:
        for product, qty in available[:8]:
            icon = "🟢" if qty >= 5 else "🟡"
            lines.append(
                f"{icon} 📘 {product['name']}\n"
                f"• Số lượng: {qty}  • Giá: {shop.fmt_price(product['price'])}"
            )
    lines.extend(["", "👉 Bấm Đi mua hàng để chọn sản phẩm cần mua."])
    return "\n".join(lines)


def broadcast_stock_update() -> Dict[str, Any]:
    if not shop.BOT_TOKEN or shop.BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN chưa cấu hình")

    user_ids = shop.get_all_user_chat_ids()
    text = _plain_stock_update_text()
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 Đi mua hàng", "callback_data": "go_products"}],
            [{"text": "✨ Làm mới gợi ý", "callback_data": "refresh_stock"}],
        ]
    }
    url = f"https://api.telegram.org/bot{shop.BOT_TOKEN}/sendMessage"
    ok = fail = 0
    failed: List[str] = []

    for chat_id in user_ids:
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "reply_markup": reply_markup,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if response.ok:
                ok += 1
            else:
                fail += 1
                failed.append(f"{chat_id}: {response.status_code} {response.text[:120]}")
        except Exception as exc:
            fail += 1
            failed.append(f"{chat_id}: {exc}")
    return {"ok": True, "sent": ok, "failed": fail, "total": len(user_ids), "errors": failed[:10]}


def save_gpt_marks(data: Dict[str, Any]) -> Dict[str, Any]:
    ws = _gpt_marks_ws()
    current = load_gpt_marks()
    by_key = {str(item.get("key") or "").strip().lower(): item for item in current if item.get("key")}
    now = shop.now_str()

    migrated_count = 0
    for material in load_materials():
        note = str(material.get("note") or "").strip()
        note_upper = note.upper()
        if not note_upper.startswith(("GPT_PLUS", "OPENAI_DIE")):
            continue
        value = str(material.get("value") or "").strip()
        key = _secret_key(value)
        if not key:
            continue
        by_key[key] = {
            "key": key,
            "value": value,
            "status": "BANNED" if note_upper.startswith("OPENAI_DIE") else "PLUS",
            "note": note,
            "subject": note,
            "updated_at": str(material.get("updated_at") or material.get("created_at") or now),
        }
        migrated_count += 1

    for raw in data.get("items") or []:
        if not isinstance(raw, dict):
            continue
        value = str(raw.get("value") or "").strip()
        key = str(raw.get("key") or "").strip().lower() or _secret_key(value)
        if not key:
            continue
        status = str(raw.get("status") or "").strip().upper()
        if status not in ("PLUS", "BANNED", "DIE"):
            continue
        by_key[key] = {
            "key": key,
            "value": value,
            "status": "BANNED" if status == "DIE" else status,
            "note": str(raw.get("note") or ""),
            "subject": str(raw.get("subject") or ""),
            "updated_at": now,
        }

    rows = [GPT_MARK_HEADERS]
    for item in sorted(by_key.values(), key=lambda x: x.get("updated_at") or "", reverse=True):
        rows.append([str(item.get(h) or "") for h in GPT_MARK_HEADERS])

    target_rows = max(len(rows), len(current) + 1, 2)
    blank = [""] * len(GPT_MARK_HEADERS)
    payload = rows + [blank for _ in range(target_rows - len(rows))]
    ws.update(f"A1:F{target_rows}", payload, value_input_option="RAW")
    return {
        "ok": True,
        "saved": len(rows) - 1,
        "items": rows_to_gpt_marks(rows[1:]),
        "migrated_materials": migrated_count,
    }


def rows_to_gpt_marks(rows: List[List[str]]) -> List[Dict[str, str]]:
    return [dict(zip(GPT_MARK_HEADERS, row)) for row in rows if any(row)]


def cleanup_gpt_marks_from_materials() -> int:
    try:
        materials = load_materials()
        cleaned = [
            item for item in materials
            if not str(item.get("note") or "").upper().startswith(("GPT_PLUS", "OPENAI_DIE"))
        ]
        removed = len(materials) - len(cleaned)
        if removed > 0:
            save_materials({"items": cleaned, "force_clear": len(cleaned) == 0})
        return removed
    except Exception as exc:
        logger.warning("cleanup GPT marks from MATERIALS failed: %s", exc)
        return 0


def _firestore():
    global _firebase_ready, _firestore_client
    if _firestore_client is not None:
        return _firestore_client
    if _firebase_ready:
        return None
    _firebase_ready = True

    try:
        import json
        import firebase_admin
        from firebase_admin import credentials, firestore
    except Exception as exc:
        logger.warning("firebase-admin chua san sang, fallback MATERIALS sang Google Sheet: %s", exc)
        return None

    json_content = os.getenv("FIREBASE_JSON_CONTENT", "").strip()
    cred_file = os.getenv("FIREBASE_CREDENTIALS_FILE", "").strip()
    try:
        if not firebase_admin._apps:
            if json_content:
                info = json.loads(json_content)
                cred = credentials.Certificate(info)
            elif cred_file:
                cred = credentials.Certificate(cred_file)
            elif os.path.exists("bot_tele.json"):
                cred = credentials.Certificate("bot_tele.json")
            else:
                logger.warning("Khong co FIREBASE_JSON_CONTENT/FIREBASE_CREDENTIALS_FILE de dung Firestore")
                return None
            firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client()
        return _firestore_client
    except Exception as exc:
        logger.warning("init Firestore failed, fallback MATERIALS sang Google Sheet: %s", exc)
        return None


def _normalize_material(raw: Dict[str, Any], now: str) -> Dict[str, str]:
    value = str(raw.get("value") or "").strip()
    status = str(raw.get("status") or "NEW").strip().upper()
    if status not in ("NEW", "OK", "BAD"):
        status = "NEW"
    return {
        "id": str(raw.get("id") or "").strip() or f"MAT-{shop.now_dt().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
        "value": value,
        "status": status,
        "note": str(raw.get("note") or ""),
        "created_at": str(raw.get("created_at") or now),
        "updated_at": now,
    }


def _load_materials_firestore() -> List[Dict[str, str]]:
    db = _firestore()
    if not db:
        return []
    docs = db.collection(MATERIALS_COLLECTION).stream()
    rows: List[Dict[str, str]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        value = str(data.get("value") or "").strip()
        if not value:
            continue
        row = {key: str(data.get(key) or "") for key in MATERIALS_HEADERS}
        row["id"] = row["id"] or doc.id
        rows.append(row)
    if not rows:
        rows = _migrate_materials_sheet_to_firestore(db)
    rows.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return rows


def _migrate_materials_sheet_to_firestore(db) -> List[Dict[str, str]]:
    col = db.collection(MATERIALS_COLLECTION)
    meta_ref = col.document("__meta__")
    try:
        if meta_ref.get().exists:
            return []
    except Exception:
        return []

    try:
        rows = _records(_materials_ws(update_header=False))
    except Exception as exc:
        logger.warning("Khong migrate MATERIALS tu Sheet duoc: %s", exc)
        rows = []

    now = shop.now_str()
    migrated: List[Dict[str, str]] = []
    for raw in rows:
        if not str(raw.get("value") or "").strip():
            continue
        material = _normalize_material(raw, now)
        col.document(material["id"]).set(material, merge=True)
        migrated.append(material)

    meta_ref.set({"migrated_at": now, "source": "google_sheet", "count": len(migrated)}, merge=True)
    return migrated


def _save_materials_firestore(data: Dict[str, Any]) -> Dict[str, Any]:
    db = _firestore()
    if not db:
        return {"ok": False, "firebase": False, "items": []}

    col = db.collection(MATERIALS_COLLECTION)
    now = shop.now_str()
    current = _load_materials_firestore()
    by_value = {item.get("value", ""): item for item in current if item.get("value")}
    by_id = {item.get("id", ""): item for item in current if item.get("id")}
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list):
        raise ValueError("items must be a list")

    def delete_ids(item_ids: List[str]) -> None:
        ids = []
        seen = set()
        for raw_id in item_ids:
            item_id = str(raw_id or "").strip()
            if item_id and item_id not in seen:
                seen.add(item_id)
                ids.append(item_id)
        if not ids:
            return
        batch = db.batch()
        count = 0
        for item_id in ids:
            batch.delete(col.document(item_id))
            count += 1
            if count >= 450:
                batch.commit()
                batch = db.batch()
                count = 0
        if count:
            batch.commit()

    deleted_ids: List[str] = []
    if bool(data.get("force_clear")):
        deleted_ids.extend(str(item.get("id") or "").strip() for item in current if item.get("id"))

    for raw_id in data.get("deleted_ids") or []:
        item_id = str(raw_id or "").strip()
        if item_id:
            deleted_ids.append(item_id)

    delete_ids(deleted_ids)

    seen_values = set()
    saved_items: List[Dict[str, str]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        material = _normalize_material(raw, now)
        if not material["value"] or material["value"] in seen_values:
            continue
        seen_values.add(material["value"])

        existing = by_id.get(material["id"]) or by_value.get(material["value"])
        if existing:
            material["id"] = existing["id"]
            material["created_at"] = existing.get("created_at") or material["created_at"]

        col.document(material["id"]).set(material, merge=True)
        saved_items.append(material)

    if bool(data.get("prefer_local")) or deleted_ids or bool(data.get("force_clear")):
        saved_items.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        return {"ok": True, "firebase": True, "saved": len(saved_items), "items": saved_items}

    items = _load_materials_firestore()
    return {"ok": True, "firebase": True, "saved": len(items), "items": items}


def _materials_ws(update_header: bool = True):
    shop.init_sheets()
    try:
        ws = shop._gs_sheet.worksheet(MATERIALS_TAB)
    except Exception:
        try:
            ws = shop._gs_sheet.add_worksheet(title=MATERIALS_TAB, rows=1000, cols=len(MATERIALS_HEADERS))
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise
            ws = shop._gs_sheet.worksheet(MATERIALS_TAB)
        ws.update("A1:F1", [MATERIALS_HEADERS], value_input_option="USER_ENTERED")
        return ws

    if update_header:
        try:
            headers = [str(h).strip().lower() for h in ws.row_values(1)]
        except Exception:
            headers = []
        if not any(headers):
            ws.update("A1:F1", [MATERIALS_HEADERS], value_input_option="USER_ENTERED")
    return ws


def load_materials() -> List[Dict[str, str]]:
    if _firestore():
        try:
            return _load_materials_firestore()
        except Exception as exc:
            logger.warning("load MATERIALS tu Firestore loi, fallback sang Google Sheet: %s", exc)
    rows = _records(_materials_ws(update_header=False))
    rows.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return rows


def save_materials(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        firestore_result = _save_materials_firestore(data)
        if firestore_result.get("firebase"):
            return firestore_result
    except Exception as exc:
        logger.warning("save MATERIALS vao Firestore loi, fallback sang Google Sheet: %s", exc)

    ws = _materials_ws()
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list):
        raise ValueError("items must be a list")
    force_clear = bool(data.get("force_clear"))
    existing_items = _records(ws)

    now = shop.now_str()
    rows = [MATERIALS_HEADERS]
    seen = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        value = str(raw.get("value") or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        status = str(raw.get("status") or "NEW").strip().upper()
        if status not in ("NEW", "OK", "BAD"):
            status = "NEW"
        item_id = str(raw.get("id") or "").strip() or f"MAT-{shop.now_dt().strftime('%Y%m%d%H%M%S')}-{len(rows)}"
        rows.append([
            item_id,
            value,
            status,
            str(raw.get("note") or ""),
            str(raw.get("created_at") or now),
            now,
        ])

    if len(rows) == 1 and existing_items and not force_clear:
        return {"ok": True, "saved": len(existing_items), "items": existing_items, "skipped_empty_save": True}

    try:
        # Same spirit as adding stock: keep saving to one Sheet write request.
        # Blank trailing rows clear old MATERIALS rows when the list shrinks.
        target_rows = max(len(rows), len(existing_items) + 1, 2)
        blank = [""] * len(MATERIALS_HEADERS)
        payload = rows + [blank for _ in range(target_rows - len(rows))]
        ws.update(f"A1:F{target_rows}", payload, value_input_option="RAW")
    except Exception as exc:
        logger.exception("save_materials failed: rows=%s force_clear=%s", len(rows) - 1, force_clear)
        raise RuntimeError(f"Không lưu được MATERIALS: {exc}") from exc

    items = [
        dict(zip(MATERIALS_HEADERS, row))
        for row in rows[1:]
    ]
    return {"ok": True, "saved": len(rows) - 1, "items": items}


def snapshot(limit: int = 100, pool_limit: int = 2000, include_materials: bool = False) -> Dict[str, Any]:
    shop.init_sheets()
    products = shop.load_products()
    pool = _records(shop._ws_pool)
    orders = _records(shop._ws_orders)
    users = _records(shop._ws_users)
    reservations = _records(shop._ws_res)
    fulfillments = _records(shop._ws_ful)
    materials = []
    if include_materials:
        try:
            materials = load_materials()
        except Exception as exc:
            logger.warning("load MATERIALS failed during snapshot: %s", exc)

    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    limit = max(1, min(int(limit or 100), 300))
    pool_limit = max(1, min(int(pool_limit or 2000), 30000))

    status_counts: Dict[str, int] = {}
    revenue = 0
    user_stats: Dict[str, Dict[str, int]] = {}
    for order in orders:
        status = (order.get("status") or "UNKNOWN").strip().upper()
        uid = (order.get("user_id") or "").strip()
        total = shop.normalize_int(order.get("total"), 0)
        status_counts[status] = status_counts.get(status, 0) + 1
        if status in ("PAID", "DELIVERED"):
            revenue += total
            if uid:
                user_stats.setdefault(uid, {"orders": 0, "spent": 0})
                user_stats[uid]["orders"] += 1
                user_stats[uid]["spent"] += total

    stock_counts: Dict[str, Dict[str, int]] = {}
    for item in pool:
        code = (item.get("stock_code") or "").strip()
        status = (item.get("status") or "UNKNOWN").strip().upper()
        if not code:
            continue
        stock_counts.setdefault(code, {"READY": 0, "HELD": 0, "SOLD": 0, "OTHER": 0})
        if status in stock_counts[code]:
            stock_counts[code][status] += 1
        else:
            stock_counts[code]["OTHER"] += 1

    product_rows = []
    for product in products:
        code = product.get("stock_code", "")
        counts = stock_counts.get(code, {"READY": 0, "HELD": 0, "SOLD": 0, "OTHER": 0})
        product_rows.append({
            "product_id": product.get("product_id", ""),
            "name": product.get("name", ""),
            "stock_code": code,
            "price": product.get("price", 0),
            "description": product.get("description", ""),
            **counts,
        })

    user_rows = []
    for user in users:
        uid = (user.get("chat_id") or user.get("user_id") or "").strip()
        stats = user_stats.get(uid, {"orders": 0, "spent": 0})
        row = dict(user)
        row["orders"] = stats["orders"]
        row["spent"] = stats["spent"]
        user_rows.append(row)
    user_rows.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    delivery_rows = []
    seen_delivery_orders = set()
    for row in fulfillments:
        delivery_rows.append(dict(row))
        oid = (row.get("order_id") or "").strip()
        if oid:
            seen_delivery_orders.add(oid)

    for order in orders:
        oid = (order.get("order_id") or "").strip()
        status = (order.get("status") or "").strip().upper()
        if not oid or oid in seen_delivery_orders or status != "DELIVERED":
            continue
        delivery_rows.append({
            "order_id": oid,
            "item_id": "",
            "stock_code": order.get("stock_code", ""),
            "secret": order.get("deliver_text", ""),
            "delivered_at": order.get("delivered_at", ""),
            "user_id": order.get("user_id", ""),
            "qty": order.get("qty", ""),
        })

    delivery_rows.sort(key=lambda x: x.get("delivered_at", ""), reverse=True)

    result = {
        "generated_at": shop.now_str(),
        "timezone": shop.APP_TIMEZONE,
        "summary": {
            "orders": len(orders),
            "revenue": revenue,
            "status_counts": status_counts,
            "users": len(users),
            "stock_ready": sum(v.get("READY", 0) for v in stock_counts.values()),
            "stock_held": sum(v.get("HELD", 0) for v in stock_counts.values()),
            "stock_sold": sum(v.get("SOLD", 0) for v in stock_counts.values()),
        },
        "products": product_rows,
        "orders": orders[:limit],
        "users": user_rows[:limit],
        "pool": pool[:pool_limit],
        "reservations": reservations[:limit],
        "fulfillments": fulfillments[:limit],
        "deliveries": delivery_rows[:limit],
    }
    if include_materials:
        result["materials"] = materials[:pool_limit]
    return result


def save_product(data: Dict[str, Any]) -> Dict[str, Any]:
    shop.init_sheets()
    headers = _headers(shop._ws_products)
    if not headers:
        raise RuntimeError("PRODUCTS thieu header")

    product_id = (data.get("product_id") or "").strip()
    stock_code = (data.get("stock_code") or "").strip()
    name = (data.get("name") or "").strip()
    if not product_id:
        product_id = stock_code or f"P{shop.now_dt().strftime('%Y%m%d%H%M%S')}"
    if not stock_code or not name:
        raise ValueError("Can co name va stock_code")

    payload = {
        "product_id": product_id,
        "name": name,
        "stock_code": stock_code,
        "price": shop.normalize_int(data.get("price"), 0),
        "description": data.get("description", ""),
    }

    values = shop._ws_products.get_all_values()
    id_col = headers.get("product_id")
    target_row = None
    if id_col:
        for idx, row in enumerate(values[1:], start=2):
            if id_col - 1 < len(row) and row[id_col - 1].strip() == product_id:
                target_row = idx
                break

    if target_row:
        cells = []
        for key, value in payload.items():
            col = headers.get(key.lower())
            if col:
                cells.append(Cell(target_row, col, str(value)))
        if cells:
            shop._ws_products.update_cells(cells, value_input_option="USER_ENTERED")
    else:
        shop._ws_products.append_row(_row_from_headers(headers, payload), value_input_option="USER_ENTERED")

    shop._CACHE["products"]["ts"] = 0.0
    return {"ok": True, "product_id": product_id}


def add_stock(data: Dict[str, Any]) -> Dict[str, Any]:
    shop.init_sheets()
    headers = _headers(shop._ws_pool)
    if not headers:
        raise RuntimeError("POOL thieu header")

    stock_code = (data.get("stock_code") or "").strip()
    raw_items = (data.get("items") or data.get("secret") or "").strip()
    if not stock_code or not raw_items:
        raise ValueError("Can co stock_code va items")

    secrets = [line.strip() for line in raw_items.splitlines() if line.strip()]
    existing_keys = {_secret_key(row.get("secret")) for row in _records(shop._ws_pool)}
    existing_keys.discard("")
    seen_keys = set()
    clean_secrets = []
    duplicate_secrets = []
    for secret in secrets:
        key = _secret_key(secret)
        if key in existing_keys or key in seen_keys:
            duplicate_secrets.append(secret)
            continue
        seen_keys.add(key)
        clean_secrets.append(secret)

    rows = []
    for secret in clean_secrets:
        rows.append(_row_from_headers(headers, {
            "item_id": _make_item_id(stock_code),
            "stock_code": stock_code,
            "secret": secret,
            "status": "READY",
            "hold_order_id": "",
            "hold_at": "",
            "hold_expires_at": "",
            "sold_order_id": "",
            "sold_at": "",
        }))
    if rows:
        shop._ws_pool.append_rows(rows, value_input_option="USER_ENTERED")
        shop.invalidate_stock_cache()
    return {"ok": True, "added": len(rows), "skipped_duplicates": duplicate_secrets}


def release_order(order_id: str, status: str = "EXPIRED") -> Dict[str, Any]:
    if not order_id:
        raise ValueError("Missing order_id")
    released = shop.release_hold_by_order(order_id, status or "EXPIRED")
    return {"ok": True, "released": released}


def update_stock_item(data: Dict[str, Any]) -> Dict[str, Any]:
    shop.init_sheets()
    headers = _headers(shop._ws_pool)
    if not headers:
        raise RuntimeError("POOL thieu header")

    item_id = str(data.get("item_id") or "").strip()
    status = str(data.get("status") or "").strip().upper()
    if not item_id:
        raise ValueError("Missing item_id")
    if status not in {"READY", "SOLD"}:
        raise ValueError("Chi ho tro status READY hoac SOLD")

    c_item = headers.get("item_id")
    c_status = headers.get("status")
    if not c_item or not c_status:
        raise RuntimeError("POOL thieu cot item_id/status")

    values = shop._ws_pool.get_all_values()
    target_row = 0
    for rownum, row in enumerate(values[1:], start=2):
        current_item_id = row[c_item - 1].strip() if c_item - 1 < len(row) else ""
        if current_item_id == item_id:
            target_row = rownum
            break
    if not target_row:
        raise ValueError("Khong tim thay item trong kho")

    cells = [Cell(target_row, c_status, status)]
    if status == "READY":
        for key in ("hold_order_id", "hold_at", "hold_expires_at", "sold_order_id", "sold_at"):
            col = headers.get(key)
            if col:
                cells.append(Cell(target_row, col, ""))
    else:
        now = shop.now_str()
        for key in ("hold_order_id", "hold_at", "hold_expires_at"):
            col = headers.get(key)
            if col:
                cells.append(Cell(target_row, col, ""))
        sold_order_col = headers.get("sold_order_id")
        sold_at_col = headers.get("sold_at")
        if sold_order_col:
            cells.append(Cell(target_row, sold_order_col, str(data.get("sold_order_id") or "MANUAL")))
        if sold_at_col:
            cells.append(Cell(target_row, sold_at_col, now))

    shop._ws_pool.update_cells(cells, value_input_option="USER_ENTERED")
    shop.invalidate_stock_cache()
    return {"ok": True, "item_id": item_id, "status": status}


def _is_expired_hold(value: str) -> bool:
    dt = shop.parse_dt(value)
    return bool(dt and dt <= shop.now_dt())


def release_holds(expired_only: bool = True, status: str = "EXPIRED") -> Dict[str, Any]:
    shop.init_sheets()
    headers = _headers(shop._ws_pool)
    if not headers:
        raise RuntimeError("POOL thieu header")

    c_status = headers.get("status")
    c_hold_oid = headers.get("hold_order_id")
    c_hold_exp = headers.get("hold_expires_at")
    if not c_status:
        raise RuntimeError("POOL thieu cot status")
    if expired_only and not c_hold_exp:
        raise RuntimeError("POOL thieu cot hold_expires_at")

    values = shop._ws_pool.get_all_values()
    order_ids: set[str] = set()
    orphan_cells: List[Cell] = []
    orphan_released = 0

    for idx, row in enumerate(values[1:], start=2):
        current_status = row[c_status - 1].strip().upper() if c_status - 1 < len(row) else ""
        if current_status != "HELD":
            continue

        expires_at = row[c_hold_exp - 1].strip() if c_hold_exp and c_hold_exp - 1 < len(row) else ""
        if expired_only and not _is_expired_hold(expires_at):
            continue

        order_id = row[c_hold_oid - 1].strip() if c_hold_oid and c_hold_oid - 1 < len(row) else ""
        if order_id:
            order_ids.add(order_id)
            continue

        orphan_cells.append(Cell(idx, c_status, "READY"))
        for key in ("hold_order_id", "hold_at", "hold_expires_at"):
            col = headers.get(key)
            if col:
                orphan_cells.append(Cell(idx, col, ""))
        orphan_released += 1

    released = orphan_released
    for order_id in sorted(order_ids):
        released += shop.release_hold_by_order(order_id, status or "EXPIRED")

    if orphan_cells:
        shop._ws_pool.update_cells(orphan_cells, value_input_option="USER_ENTERED")

    if released:
        shop.invalidate_stock_cache()

    return {
        "ok": True,
        "expired_only": expired_only,
        "orders": len(order_ids),
        "released": released,
        "orphan_released": orphan_released,
    }


def update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    if not order_id:
        raise ValueError("Missing order_id")
    allowed = {"status", "tx_id", "paid_at", "delivered_at", "deliver_text"}
    payload = {k: v for k, v in updates.items() if k in allowed}
    if not payload:
        raise ValueError("No allowed updates")
    shop.set_order_fields(order_id, payload)
    return {"ok": True, "order_id": order_id, "updates": payload}
