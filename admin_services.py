import random
import string
from typing import Any, Dict, List

from gspread.cell import Cell

import bot_shop as shop


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


def snapshot(limit: int = 100) -> Dict[str, Any]:
    shop.init_sheets()
    products = shop.load_products()
    pool = _records(shop._ws_pool)
    orders = _records(shop._ws_orders)
    users = _records(shop._ws_users)
    reservations = _records(shop._ws_res)
    fulfillments = _records(shop._ws_ful)

    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    limit = max(1, min(int(limit or 100), 300))

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

    return {
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
        "pool": pool[:limit],
        "reservations": reservations[:limit],
        "fulfillments": fulfillments[:limit],
    }


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
    rows = []
    for secret in secrets:
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
    return {"ok": True, "added": len(rows)}


def release_order(order_id: str, status: str = "EXPIRED") -> Dict[str, Any]:
    if not order_id:
        raise ValueError("Missing order_id")
    released = shop.release_hold_by_order(order_id, status or "EXPIRED")
    return {"ok": True, "released": released}


def update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    if not order_id:
        raise ValueError("Missing order_id")
    allowed = {"status", "tx_id", "paid_at", "delivered_at", "deliver_text"}
    payload = {k: v for k, v in updates.items() if k in allowed}
    if not payload:
        raise ValueError("No allowed updates")
    shop.set_order_fields(order_id, payload)
    return {"ok": True, "order_id": order_id, "updates": payload}
