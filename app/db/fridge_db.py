import json
import secrets
import sqlite3
from datetime import date as _date
from typing import Optional

from app.config import DB_PATH
from app.core.utils import now_utc, to_iso
from app.db.base import make_conn


VALID_FRIDGE_STATUSES = {"ACTIVE", "CONSUMED", "EXPIRED", "DISCARDED"}


def get_conn() -> sqlite3.Connection:
    return make_conn(DB_PATH, foreign_keys=True)


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def ensure_receipt_compat_columns(conn: sqlite3.Connection) -> None:
    # Existing receipts.status CHECK stays unchanged for backward compatibility.
    # Extra workflow states are stored in separate nullable/default columns.
    _add_column_if_missing(conn, "receipts", "raw_ocr_json", "raw_ocr_json TEXT")
    _add_column_if_missing(conn, "receipts", "shopping_matches_json", "shopping_matches_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "receipts", "shopping_match_status", "shopping_match_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED'")
    _add_column_if_missing(conn, "receipts", "shopping_matched_at", "shopping_matched_at TEXT")
    _add_column_if_missing(conn, "receipts", "fridge_added_at", "fridge_added_at TEXT")


def init_fridge_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS fridge_items (
          id TEXT PRIMARY KEY,
          user_id INTEGER,
          receipt_id TEXT,
          source TEXT NOT NULL DEFAULT 'receipt',
          item_name TEXT NOT NULL,
          qty INTEGER NOT NULL DEFAULT 1,
          unit TEXT,
          price INTEGER DEFAULT 0,
          category TEXT,
          store_name TEXT,
          purchased_at TEXT,
          status TEXT NOT NULL DEFAULT 'ACTIVE'
            CHECK (status IN ('ACTIVE', 'CONSUMED', 'EXPIRED', 'DISCARDED')),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(receipt_id, item_name, purchased_at)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fridge_items_user_status
        ON fridge_items (user_id, status, created_at)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fridge_items_receipt
        ON fridge_items (receipt_id)
        """)
        # Add new nullable columns for manual fridge items (safe on existing DBs)
        _add_column_if_missing(conn, "fridge_items", "expiry_date",   "expiry_date TEXT")
        _add_column_if_missing(conn, "fridge_items", "memo",          "memo TEXT")
        _add_column_if_missing(conn, "fridge_items", "quantity_text", "quantity_text TEXT")
        # If receipts table exists, add compatibility columns safely.
        exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='receipts'").fetchone()
        if exists:
            ensure_receipt_compat_columns(conn)
        conn.commit()


def _loads_items(value: str):
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "receiptId": row["receipt_id"],
        "source": row["source"],
        "name": row["item_name"],
        "qty": row["qty"],
        "unit": row["unit"],
        "price": row["price"],
        "category": row["category"],
        "store": row["store_name"],
        "purchasedAt": row["purchased_at"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _calc_d_day(expiry_date_str: Optional[str]) -> Optional[int]:
    """유통기한 문자열 (YYYY-MM-DD) → 오늘 기준 D-day 정수 (양수=남은 일, 0=당일, 음수=초과)"""
    if not expiry_date_str:
        return None
    try:
        expiry = _date.fromisoformat(expiry_date_str[:10])
        return (expiry - _date.today()).days
    except (ValueError, TypeError):
        return None


def row_to_dict_v2(row) -> dict:
    """Fridge.html 프론트엔드가 기대하는 필드를 포함한 확장 dict"""
    expiry = row["expiry_date"] if "expiry_date" in row.keys() else None
    qty_text = row["quantity_text"] if "quantity_text" in row.keys() else None
    memo = row["memo"] if "memo" in row.keys() else None
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "receiptId": row["receipt_id"],
        "source": row["source"],
        "name": row["item_name"],
        "qty": row["qty"],
        "quantity": qty_text or (str(row["qty"]) if row["qty"] else "1"),
        "unit": row["unit"],
        "price": row["price"],
        "category": row["category"],
        "store": row["store_name"],
        "purchasedAt": row["purchased_at"],
        "expiry_date": expiry,
        "d_day": _calc_d_day(expiry),
        "memo": memo,
        "status": row["status"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def add_from_receipt(receipt_id: str, user_id: Optional[int] = None) -> dict:
    init_fridge_db()
    receipt_id = (receipt_id or "").strip()
    if not receipt_id:
        raise ValueError("receiptId가 필요합니다.")

    now = to_iso(now_utc())
    inserted = []
    skipped = []

    with get_conn() as conn:
        ensure_receipt_compat_columns(conn)
        receipt = conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()
        if receipt is None:
            raise LookupError("영수증 인증 기록을 찾을 수 없습니다.")
        if receipt["status"] != "VERIFIED":
            raise PermissionError("VERIFIED 상태의 영수증만 냉장고에 추가할 수 있습니다.")

        items = _loads_items(receipt["selected_items"])
        if not items:
            raise ValueError("선택 인증된 품목이 없습니다.")

        for item in items:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            qty = int(item.get("qty") or 1)
            price = int(item.get("price") or 0)
            category = item.get("category")
            unit = item.get("unit")
            fridge_id = "frg_" + secrets.token_hex(8)
            try:
                conn.execute("""
                INSERT INTO fridge_items (
                  id, user_id, receipt_id, source,
                  item_name, qty, unit, price, category,
                  store_name, purchased_at, status,
                  created_at, updated_at
                ) VALUES (?, ?, ?, 'receipt', ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """, (
                    fridge_id,
                    user_id,
                    receipt_id,
                    name,
                    max(1, qty),
                    unit,
                    max(0, price),
                    category,
                    receipt["store_name"],
                    receipt["purchased_at"],
                    now,
                    now,
                ))
                inserted.append(fridge_id)
            except sqlite3.IntegrityError:
                skipped.append(name)

        conn.execute(
            "UPDATE receipts SET fridge_added_at = COALESCE(fridge_added_at, ?), updated_at = ? WHERE id = ?",
            (now, now, receipt_id),
        )
        conn.commit()

        rows = conn.execute(
            "SELECT * FROM fridge_items WHERE receipt_id = ? ORDER BY created_at DESC",
            (receipt_id,),
        ).fetchall()

    return {
        "receiptId": receipt_id,
        "insertedCount": len(inserted),
        "skippedCount": len(skipped),
        "skippedNames": skipped,
        "items": [row_to_dict(r) for r in rows],
    }


def list_items(user_id: Optional[int] = None, status: str = "ACTIVE", limit: int = 50) -> list[dict]:
    init_fridge_db()
    status = (status or "ACTIVE").upper()
    if status not in VALID_FRIDGE_STATUSES and status != "ALL":
        status = "ACTIVE"
    limit = max(1, min(int(limit or 50), 100))

    where = []
    params = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if status != "ALL":
        where.append("status = ?")
        params.append(status)

    sql = "SELECT * FROM fridge_items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [row_to_dict(r) for r in rows]


def list_items_v2(user_id: Optional[int] = None, status: str = "ACTIVE", limit: int = 50) -> list[dict]:
    """row_to_dict_v2를 사용하는 확장 목록 조회"""
    init_fridge_db()
    status = (status or "ACTIVE").upper()
    if status not in VALID_FRIDGE_STATUSES and status != "ALL":
        status = "ACTIVE"
    limit = max(1, min(int(limit or 50), 100))

    where: list[str] = []
    params: list = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if status != "ALL":
        where.append("status = ?")
        params.append(status)

    sql = "SELECT * FROM fridge_items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [row_to_dict_v2(r) for r in rows]


def add_manual_item(
    user_id: int,
    name: str,
    category: Optional[str] = None,
    quantity: Optional[str] = None,
    expiry_date: Optional[str] = None,
    memo: Optional[str] = None,
) -> dict:
    """사용자가 직접 냉장고 항목을 추가합니다."""
    init_fridge_db()
    if not name or not name.strip():
        raise ValueError("품목명이 필요합니다.")
    now = to_iso(now_utc())
    item_id = "frg_" + secrets.token_hex(8)
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO fridge_items
          (id, user_id, receipt_id, source, item_name, qty, unit, price,
           category, store_name, purchased_at, status,
           expiry_date, memo, quantity_text,
           created_at, updated_at)
        VALUES (?, ?, NULL, 'manual', ?, 1, NULL, 0,
                ?, NULL, NULL, 'ACTIVE',
                ?, ?, ?,
                ?, ?)
        """, (
            item_id, user_id, name.strip(),
            category, expiry_date, memo, quantity,
            now, now,
        ))
        conn.commit()
        row = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict_v2(row)


def update_manual_item(
    item_id: str,
    user_id: int,
    name: Optional[str] = None,
    category: Optional[str] = None,
    quantity: Optional[str] = None,
    expiry_date: Optional[str] = None,
    memo: Optional[str] = None,
) -> dict:
    """냉장고 항목을 수정합니다. user_id로 소유권 확인."""
    init_fridge_db()
    now = to_iso(now_utc())
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if row is None or row["user_id"] != user_id:
            raise LookupError("냉장고 항목을 찾을 수 없습니다.")

        sets: list[str] = ["updated_at = ?"]
        vals: list = [now]
        if name is not None:
            sets.append("item_name = ?"); vals.append(name.strip())
        if category is not None:
            sets.append("category = ?"); vals.append(category)
        if quantity is not None:
            sets.append("quantity_text = ?"); vals.append(quantity)
        if expiry_date is not None:
            sets.append("expiry_date = ?"); vals.append(expiry_date)
        if memo is not None:
            sets.append("memo = ?"); vals.append(memo)
        vals.append(item_id)

        conn.execute(f"UPDATE fridge_items SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        conn.commit()
        updated = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict_v2(updated)


def delete_manual_item(item_id: str, user_id: int) -> None:
    """냉장고 항목을 삭제합니다. user_id로 소유권 확인."""
    init_fridge_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if row is None or row["user_id"] != user_id:
            raise LookupError("냉장고 항목을 찾을 수 없습니다.")
        conn.execute("DELETE FROM fridge_items WHERE id = ?", (item_id,))
        conn.commit()


def update_status(item_id: str, status: str, user_id: Optional[int] = None) -> dict:
    """냉장고 항목 상태를 변경합니다.

    Args:
        item_id: 변경할 항목 ID
        status: 새 상태값 (ACTIVE | CONSUMED | EXPIRED | DISCARDED)
        user_id: 요청자 user ID. None이 아니면 소유권 검증을 수행합니다.

    Raises:
        ValueError: 허용되지 않은 상태값
        LookupError: 항목을 찾을 수 없거나 소유권 불일치
    """
    init_fridge_db()
    item_id = (item_id or "").strip()
    status = (status or "").upper()
    if status not in VALID_FRIDGE_STATUSES:
        raise ValueError("허용되지 않은 상태값입니다.")
    now = to_iso(now_utc())
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise LookupError("냉장고 항목을 찾을 수 없습니다.")
        if user_id is not None and row["user_id"] != user_id:
            raise LookupError("냉장고 항목을 찾을 수 없습니다.")  # 소유권 불일치 — 404로 통일(열거 방지)
        conn.execute("UPDATE fridge_items SET status = ?, updated_at = ? WHERE id = ?", (status, now, item_id))
        conn.commit()
        updated = conn.execute("SELECT * FROM fridge_items WHERE id = ?", (item_id,)).fetchone()
        return row_to_dict(updated)