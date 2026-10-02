"""PostgreSQL-backed worksheet compatibility layer.

The application historically talks to Google Sheets through a small subset of
the gspread Worksheet API.  This module implements that subset on PostgreSQL so
the storage backend can be switched safely with STORAGE_BACKEND=postgres.
All business columns remain visible as normal PostgreSQL columns; `_row_id` is
the internal stable ordering key that replaces a spreadsheet row number.
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_HEADERS: Dict[str, List[str]] = {
    "PRODUCTS": [
        "product_id", "name", "price", "stock_code", "description",
        "duration_days", "expires_at", "pricing_enabled", "slot_limit",
    ],
    "POOL": [
        "item_id", "stock_code", "secret", "status", "hold_order_id",
        "hold_at", "hold_expires_at", "sold_order_id", "sold_at",
        "base_price", "duration_days", "expires_at",
    ],
    "ORDERS": [
        "order_id", "user_id", "stock_code", "qty", "total", "status",
        "qr_msg_id", "paid_at", "tx_id", "delivered_at", "deliver_text",
        "created_at", "subtotal", "promo_code", "promo_discount",
    ],
    "USERS": ["chat_id", "username", "full_name", "created_at", "updated_at"],
    "RESERVATIONS": [
        "order_id", "item_id", "stock_code", "reserved_at", "expires_at",
        "released_at", "sold_at",
    ],
    "FULFILLMENTS": ["order_id", "item_id", "stock_code", "secret", "delivered_at"],
    "PROMOTIONS": [
        "id", "code", "promo_type", "discount_amount", "min_order_total",
        "stock_code", "threshold_amount", "required_orders", "threshold_qty",
        "max_claims", "target_user_id", "count_from_created", "expires_days",
        "status", "note", "created_at", "updated_at",
    ],
    "PROMO_AWARDS": [
        "user_id", "username", "full_name", "promo_id", "cycle", "code",
        "discount_amount", "min_order_total", "stock_code", "status",
        "awarded_at", "expires_at", "used_order_id", "used_at",
    ],
    "PROMO_SETTINGS": ["key", "value", "updated_at"],
    "SLOTS": ["slot_id", "title", "price", "total_slots", "status", "note", "created_at", "updated_at"],
    "SLOT_PARTICIPANTS": [
        "slot_id", "user_id", "username", "full_name", "email", "order_id",
        "status", "paid_at", "joined_at", "done_at", "note",
    ],
    "EXPENSES": ["id", "name", "amount", "date", "note", "created_at", "updated_at"],
    "GPT_MARKS": ["key", "value", "status", "note", "subject", "updated_at"],
    "MATERIALS": ["id", "value", "status", "note", "created_at", "updated_at"],
}


def postgres_enabled() -> bool:
    return os.getenv("STORAGE_BACKEND", "sheets").strip().lower() in {"postgres", "postgresql", "supabase"}


def _database_url() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("STORAGE_BACKEND=postgres nhưng DATABASE_URL đang trống")
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg://" + raw[len("postgres://"):]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


def _safe_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
    if not cleaned:
        raise ValueError("Tên bảng/cột không hợp lệ")
    return cleaned[:55]


def _quoted(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class PostgresWorksheet:
    def __init__(self, spreadsheet: "PostgresSpreadsheet", title: str, headers: Optional[List[str]] = None):
        self.spreadsheet = spreadsheet
        self.engine = spreadsheet.engine
        self.title = str(title).strip()
        self.table_name = "bot_" + _safe_identifier(self.title)
        defaults = headers or DEFAULT_HEADERS.get(self.title.upper()) or ["value"]
        self._ensure_table([_safe_identifier(h) for h in defaults if str(h).strip()])

    @property
    def col_count(self) -> int:
        return len(self._headers())

    def _ensure_table(self, headers: List[str]) -> None:
        from sqlalchemy import text

        normalized = list(dict.fromkeys(_safe_identifier(h) for h in headers))
        with self.engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS bot_sheet_meta ("
                "title TEXT PRIMARY KEY, table_name TEXT NOT NULL UNIQUE, headers JSONB NOT NULL)"
            ))
            columns = ", ".join(f"{_quoted(h)} TEXT NOT NULL DEFAULT ''" for h in normalized)
            suffix = f", {columns}" if columns else ""
            conn.execute(text(
                f"CREATE TABLE IF NOT EXISTS {_quoted(self.table_name)} "
                f"(_row_id BIGSERIAL PRIMARY KEY{suffix})"
            ))
            row = conn.execute(
                text("SELECT headers FROM bot_sheet_meta WHERE title=:title"),
                {"title": self.title},
            ).scalar_one_or_none()
            current = list(row or [])
            merged = list(dict.fromkeys(current + normalized))
            for header in merged:
                conn.execute(text(
                    f"ALTER TABLE {_quoted(self.table_name)} "
                    f"ADD COLUMN IF NOT EXISTS {_quoted(header)} TEXT NOT NULL DEFAULT ''"
                ))
            conn.execute(text(
                "INSERT INTO bot_sheet_meta(title, table_name, headers) "
                "VALUES (:title, :table_name, CAST(:headers AS JSONB)) "
                "ON CONFLICT(title) DO UPDATE SET table_name=EXCLUDED.table_name, headers=EXCLUDED.headers"
            ), {
                "title": self.title,
                "table_name": self.table_name,
                "headers": json.dumps(merged),
            })

    def _headers(self) -> List[str]:
        from sqlalchemy import text

        with self.engine.connect() as conn:
            value = conn.execute(
                text("SELECT headers FROM bot_sheet_meta WHERE title=:title"),
                {"title": self.title},
            ).scalar_one()
        return list(value or [])

    def _add_headers(self, headers: Iterable[str]) -> None:
        self._ensure_table(self._headers() + [_safe_identifier(h) for h in headers])

    def _row_ids(self) -> List[int]:
        from sqlalchemy import text

        with self.engine.connect() as conn:
            return list(conn.execute(text(
                f"SELECT _row_id FROM {_quoted(self.table_name)} ORDER BY _row_id"
            )).scalars())

    def row_values(self, row: int) -> List[str]:
        if int(row) == 1:
            return self._headers()
        values = self.get_all_values()
        index = int(row) - 1
        return values[index] if 0 <= index < len(values) else []

    def get_all_values(self) -> List[List[str]]:
        from sqlalchemy import text

        headers = self._headers()
        if not headers:
            return []
        cols = ", ".join(_quoted(h) for h in headers)
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                f"SELECT {cols} FROM {_quoted(self.table_name)} ORDER BY _row_id"
            )).all()
        return [headers] + [["" if value is None else str(value) for value in row] for row in rows]

    def get_all_records(self) -> List[Dict[str, str]]:
        values = self.get_all_values()
        if len(values) < 2:
            return []
        headers = values[0]
        return [dict(zip(headers, row)) for row in values[1:]]

    def col_values(self, col: int) -> List[str]:
        values = self.get_all_values()
        index = int(col) - 1
        return [row[index] if index < len(row) else "" for row in values]

    def append_row(self, values: List[Any], value_input_option: str = "RAW") -> None:
        self.append_rows([values], value_input_option=value_input_option)

    def append_rows(self, rows: List[List[Any]], value_input_option: str = "RAW") -> None:
        if not rows:
            return
        with self.engine.begin() as conn:
            self._insert_rows(conn, rows)

    def _insert_rows(self, conn: Any, rows: List[List[Any]]) -> None:
        from sqlalchemy import text

        if not rows:
            return
        headers = self._headers()
        cols = ", ".join(_quoted(h) for h in headers)
        binds = ", ".join(f":v{i}" for i in range(len(headers)))
        statement = text(f"INSERT INTO {_quoted(self.table_name)} ({cols}) VALUES ({binds})")
        payload = []
        for row in rows:
            payload.append({f"v{i}": "" if i >= len(row) or row[i] is None else str(row[i]) for i in range(len(headers))})
        conn.execute(statement, payload)

    def add_cols(self, cols: int) -> None:
        # Column names are added when header cells are written.
        return None

    def update_cell(self, row: int, col: int, value: Any) -> None:
        class CellValue:
            def __init__(self, r: int, c: int, v: Any):
                self.row, self.col, self.value = r, c, v

        self.update_cells([CellValue(row, col, value)])

    def update_cells(self, cells: List[Any], value_input_option: str = "RAW") -> None:
        from sqlalchemy import text

        if not cells:
            return
        header_cells = [cell for cell in cells if int(cell.row) == 1]
        if header_cells:
            names = [str(cell.value).strip() for cell in sorted(header_cells, key=lambda c: c.col) if str(cell.value).strip()]
            self._add_headers(names)

        headers = self._headers()
        row_ids = self._row_ids()
        grouped: Dict[int, List[Any]] = {}
        for cell in cells:
            if int(cell.row) > 1:
                grouped.setdefault(int(cell.row), []).append(cell)
        with self.engine.begin() as conn:
            for rownum, row_cells in grouped.items():
                offset = rownum - 2
                while offset >= len(row_ids):
                    result = conn.execute(text(f"INSERT INTO {_quoted(self.table_name)} DEFAULT VALUES RETURNING _row_id"))
                    row_ids.append(int(result.scalar_one()))
                assignments = []
                params: Dict[str, Any] = {"row_id": row_ids[offset]}
                for index, cell in enumerate(row_cells):
                    col_index = int(cell.col) - 1
                    if not (0 <= col_index < len(headers)):
                        continue
                    key = f"v{index}"
                    assignments.append(f"{_quoted(headers[col_index])}=:{key}")
                    params[key] = "" if cell.value is None else str(cell.value)
                if assignments:
                    conn.execute(text(
                        f"UPDATE {_quoted(self.table_name)} SET {', '.join(assignments)} WHERE _row_id=:row_id"
                    ), params)

    def delete_rows(self, start_index: int, end_index: Optional[int] = None) -> None:
        from sqlalchemy import text

        start = max(2, int(start_index))
        end = max(start, int(end_index or start))
        row_ids = self._row_ids()[start - 2:end - 1]
        if not row_ids:
            return
        placeholders = ", ".join(f":row_id_{index}" for index in range(len(row_ids)))
        params = {f"row_id_{index}": row_id for index, row_id in enumerate(row_ids)}
        with self.engine.begin() as conn:
            conn.execute(text(
                f"DELETE FROM {_quoted(self.table_name)} WHERE _row_id IN ({placeholders})"
            ), params)

    def clear(self) -> None:
        from sqlalchemy import text

        with self.engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {_quoted(self.table_name)} RESTART IDENTITY"))

    def update(self, range_name: Any, values: Optional[List[List[Any]]] = None, value_input_option: str = "RAW") -> None:
        # gspread also accepts update(values) without a range.
        if values is None and isinstance(range_name, list):
            values = range_name
            range_name = "A1"
        values = values or []
        match = re.match(r"([A-Z]+)(\d+)", str(range_name).upper())
        start_row = int(match.group(2)) if match else 1
        start_col_letters = match.group(1) if match else "A"
        start_col = 0
        for char in start_col_letters:
            start_col = start_col * 26 + (ord(char) - 64)
        if start_row == 1 and values:
            self._add_headers([str(v) for v in values[0] if str(v).strip()])
        cells = []
        for r_index, row in enumerate(values):
            for c_index, value in enumerate(row):
                cell = type("CellValue", (), {})()
                cell.row = start_row + r_index
                cell.col = start_col + c_index
                cell.value = value
                cells.append(cell)
        self.update_cells(cells, value_input_option=value_input_option)

    def batch_update(self, data: List[Dict[str, Any]], value_input_option: str = "RAW") -> None:
        for entry in data:
            self.update(entry.get("range", "A1"), entry.get("values") or [], value_input_option=value_input_option)

    def replace_all(self, values: List[List[Any]]) -> None:
        from sqlalchemy import text

        if not values:
            return
        source_headers = [_safe_identifier(v) for v in values[0] if str(v).strip()]
        self._ensure_table(source_headers)
        target_headers = self._headers()
        source_indexes = {header: index for index, header in enumerate(source_headers)}
        normalized_rows: List[List[Any]] = []
        for source_row in values[1:]:
            normalized_rows.append([
                source_row[source_indexes[header]]
                if header in source_indexes and source_indexes[header] < len(source_row)
                else ""
                for header in target_headers
            ])
        with self.engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {_quoted(self.table_name)} RESTART IDENTITY"))
            self._insert_rows(conn, normalized_rows)


class PostgresSpreadsheet:
    def __init__(self):
        from sqlalchemy import create_engine

        self.engine = create_engine(_database_url(), pool_pre_ping=True, pool_recycle=300)
        self._worksheets: Dict[str, PostgresWorksheet] = {}
        self._lock = threading.Lock()

    def worksheet(self, title: str) -> PostgresWorksheet:
        key = str(title).strip()
        with self._lock:
            if key not in self._worksheets:
                self._worksheets[key] = PostgresWorksheet(self, key)
            return self._worksheets[key]

    def add_worksheet(self, title: str, rows: int = 1000, cols: int = 20) -> PostgresWorksheet:
        return self.worksheet(title)

    def worksheets(self) -> List[PostgresWorksheet]:
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        if "bot_sheet_meta" not in inspector.get_table_names():
            return list(self._worksheets.values())
        with self.engine.connect() as conn:
            titles = list(conn.execute(text("SELECT title FROM bot_sheet_meta ORDER BY title")).scalars())
        return [self.worksheet(title) for title in titles]


_SPREADSHEET: Optional[PostgresSpreadsheet] = None
_SPREADSHEET_LOCK = threading.Lock()


def get_postgres_spreadsheet() -> PostgresSpreadsheet:
    global _SPREADSHEET
    with _SPREADSHEET_LOCK:
        if _SPREADSHEET is None:
            _SPREADSHEET = PostgresSpreadsheet()
        return _SPREADSHEET
