"""Shared, fail-closed OCR budget. All reservation decisions serialize on one DB row."""
import math
import re
import secrets
import sqlite3
from datetime import timedelta

from fastapi import HTTPException

from app.config import DB_PATH
from app.core.utils import from_iso, now_utc, to_iso
from app.db.base import make_conn


def get_conn():
    return make_conn(DB_PATH, foreign_keys=True)


def init_ocr_guard():
    """SQLite development setup; PostgreSQL changes require the reviewed migration."""
    with get_conn() as conn:
        if not isinstance(conn, sqlite3.Connection):
            return
        conn.execute("""CREATE TABLE IF NOT EXISTS ocr_guard_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
            user_daily_limit INTEGER NOT NULL CHECK (user_daily_limit > 0),
            user_monthly_limit INTEGER NOT NULL CHECK (user_monthly_limit > 0),
            global_monthly_limit INTEGER NOT NULL CHECK (global_monthly_limit > 0),
            updated_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ocr_requests (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            idempotency_key TEXT NOT NULL,
            image_hash TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('reserved', 'sent', 'completed', 'failed', 'canceled')),
            scan_id TEXT UNIQUE REFERENCES receipts(id),
            object_name TEXT,
            storage_kind TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (user_id, idempotency_key)
        )""")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(ocr_requests)").fetchall()}
        for column in ("object_name", "storage_kind"):
            if column not in columns:
                conn.execute(f"ALTER TABLE ocr_requests ADD COLUMN {column} TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_created ON ocr_requests (created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ocr_user_created ON ocr_requests (user_id, created_at)")
        conn.execute("""CREATE TABLE IF NOT EXISTS ocr_guard_audit (
            id TEXT PRIMARY KEY, actor_id INTEGER NOT NULL REFERENCES users(id),
            enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)), created_at TEXT NOT NULL
        )""")
        conn.execute("""INSERT OR IGNORE INTO ocr_guard_settings
            (id, enabled, user_daily_limit, user_monthly_limit, global_monthly_limit, updated_at)
            VALUES (1, 0, 3, 30, 300, ?)""", (to_iso(now_utc()),))
        conn.commit()


def _lock_settings(conn):
    if isinstance(conn, sqlite3.Connection):
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM ocr_guard_settings WHERE id = 1").fetchone()
    else:
        row = conn.execute("SELECT * FROM ocr_guard_settings WHERE id = 1 FOR UPDATE").fetchone()
    if row is None:
        raise HTTPException(503, "OCR 안전 설정이 없어 분석을 중단했습니다. 수동 입력을 이용해 주세요.")
    return row


def _reset_time(now, daily):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if daily:
        return start + timedelta(days=1)
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def _database_now(conn):
    # PostgreSQL clock is shared by all serverless instances, even after lock waits.
    if isinstance(conn, sqlite3.Connection):
        return now_utc()
    return conn.execute("SELECT clock_timestamp() AS current_time").fetchone()["current_time"]


def reserve(user_id, key, image_hash):
    if not key or not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
        raise HTTPException(400, "유효한 Idempotency-Key가 필요합니다.")
    with get_conn() as conn:
        settings = _lock_settings(conn)
        now = _database_now(conn)
        day = to_iso(now.replace(hour=0, minute=0, second=0, microsecond=0))
        next_day = to_iso(_reset_time(now, True))
        next_month = to_iso(_reset_time(now, False))
        month = to_iso(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
        prior = conn.execute("SELECT * FROM ocr_requests WHERE user_id = ? AND idempotency_key = ?", (user_id, key)).fetchone()
        if prior:
            if prior['image_hash'] != image_hash:
                raise HTTPException(409, "같은 요청 키를 다른 이미지에 사용할 수 없습니다.")
            if prior['status'] == 'completed' and prior['scan_id']:
                return {'replay': prior['scan_id']}
            raise HTTPException(409, "이미 처리 중이거나 결과를 확인할 수 없는 요청입니다. 중복 호출하지 않았습니다.")
        if not settings['enabled']:
            raise HTTPException(503, "영수증 자동 분석이 중단되었습니다. 수동 입력을 이용해 주세요.")
        duplicate = conn.execute("""SELECT id FROM ocr_requests
            WHERE user_id = ? AND image_hash = ? AND created_at >= ? AND created_at < ? LIMIT 1""", (user_id, image_hash, month, next_month)).fetchone()
        if duplicate:
            raise HTTPException(409, "이번 달에 이미 요청한 영수증 이미지입니다. 중복 호출하지 않았습니다.")
        counts = conn.execute("""SELECT
            COUNT(*) AS global_month,
            SUM(CASE WHEN user_id = ? THEN 1 ELSE 0 END) AS user_month,
            SUM(CASE WHEN user_id = ? AND created_at >= ? AND created_at < ? THEN 1 ELSE 0 END) AS user_day
            FROM ocr_requests WHERE created_at >= ? AND created_at < ?""",
            (user_id, user_id, day, next_day, month, next_month)).fetchone()
        for value, limit, daily in ((counts['global_month'], settings['global_monthly_limit'], False),
                                    (counts['user_month'] or 0, settings['user_monthly_limit'], False),
                                    (counts['user_day'] or 0, settings['user_daily_limit'], True)):
            if value >= limit:
                reset = _reset_time(now, daily)
                retry = max(1, math.ceil((reset - now).total_seconds()))
                raise HTTPException(429, f"OCR 사용 한도에 도달했습니다. {to_iso(reset)} 이후 다시 시도하거나 수동 입력을 이용해 주세요.", headers={'Retry-After': str(retry)})
        recent = conn.execute("""SELECT created_at FROM ocr_requests WHERE user_id = ?
            AND created_at >= ? AND created_at <= ? ORDER BY created_at DESC LIMIT 1""",
            (user_id, to_iso(now - timedelta(seconds=5)), to_iso(now))).fetchone()
        if recent:
            remaining = (from_iso(recent["created_at"]) + timedelta(seconds=5) - now).total_seconds()
            if remaining > 0:
                retry = max(1, math.ceil(remaining))
                raise HTTPException(429, f"요청이 너무 빠릅니다. {retry}초 후 다시 시도해 주세요.",
                                    headers={"Retry-After": str(retry)})
        request_id = 'ocr_' + secrets.token_hex(16)
        timestamp = to_iso(now)
        conn.execute("""INSERT INTO ocr_requests
            (id, user_id, idempotency_key, image_hash, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'reserved', ?, ?)""", (request_id, user_id, key, image_hash, timestamp, timestamp))
        conn.commit()
        return {'id': request_id}


def mark_sent(request_id, object_name, storage_kind):
    with get_conn() as conn:
        settings = _lock_settings(conn)
        if not settings['enabled']:
            conn.execute("UPDATE ocr_requests SET status = 'canceled', updated_at = ? WHERE id = ? AND status = 'reserved'", (to_iso(now_utc()), request_id))
            conn.commit()
            raise HTTPException(503, "OCR이 중단되어 요청을 전송하지 않았습니다. 수동 입력을 이용해 주세요.")
        cur = conn.execute("""UPDATE ocr_requests SET status = 'sent', object_name = ?, storage_kind = ?,
            updated_at = ? WHERE id = ? AND status = 'reserved'""",
            (object_name, storage_kind, to_iso(now_utc()), request_id))
        if cur.rowcount != 1:
            raise HTTPException(503, "OCR 예약 상태를 확인할 수 없습니다.")
        conn.commit()


def mark_failed(request_id):
    with get_conn() as conn:
        conn.execute("UPDATE ocr_requests SET status = 'failed', updated_at = ? WHERE id = ? AND status IN ('reserved', 'sent')", (to_iso(now_utc()), request_id))
        conn.commit()


def usage():
    with get_conn() as conn:
        now = _database_now(conn)
        month = to_iso(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0))
        next_month = to_iso(_reset_time(now, False))
        settings = conn.execute("SELECT * FROM ocr_guard_settings WHERE id = 1").fetchone()
        if settings is None:
            raise HTTPException(503, "OCR 안전 설정이 없습니다.")
        count = conn.execute("SELECT COUNT(*) AS n FROM ocr_requests WHERE created_at >= ? AND created_at < ?", (month, next_month)).fetchone()['n']
    return {'enabled': bool(settings['enabled']), 'globalMonthlyUsed': count,
            'globalMonthlyLimit': settings['global_monthly_limit'],
            'userDailyLimit': settings['user_daily_limit'], 'userMonthlyLimit': settings['user_monthly_limit'],
            'period': month, 'timezone': 'UTC'}


def set_enabled(actor_id, enabled):
    with get_conn() as conn:
        _lock_settings(conn)
        now = to_iso(now_utc())
        conn.execute("UPDATE ocr_guard_settings SET enabled = ?, updated_at = ? WHERE id = 1", (int(enabled), now))
        conn.execute("INSERT INTO ocr_guard_audit (id, actor_id, enabled, created_at) VALUES (?, ?, ?, ?)",
                     ('ocra_' + secrets.token_hex(16), actor_id, int(enabled), now))
        conn.commit()
