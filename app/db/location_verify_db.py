# -*- coding: utf-8 -*-
"""GPS 위치 인증 세션 DB 모듈 (main 브랜치 신규 기능)
_conn() → make_conn(DB_PATH) 으로 통합 연결 방식으로 수정."""
from __future__ import annotations

import math
import sqlite3
import uuid
from typing import Any, Dict, Optional

from app.config      import DB_PATH
from app.core.utils  import now_utc, to_iso
from app.db.base     import make_conn

DEFAULT_RADIUS_M        = 300.0
DEFAULT_ACCURACY_LIMIT_M = 1500.0


def _now() -> str:
    """현재 UTC 시각을 ISO-8601 'Z' 형식으로 반환합니다."""
    return to_iso(now_utc())


def get_conn() -> sqlite3.Connection:
    """통합 DB(neighborfood.db) 연결을 반환합니다."""
    return make_conn(DB_PATH, foreign_keys=True)


def _row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _pick(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def distance_meters(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    """Haversine 공식으로 두 GPS 좌표 간 거리(미터)를 계산합니다."""
    radius = 6371000.0
    lat1   = math.radians(a_lat)
    lat2   = math.radians(b_lat)
    dlat   = math.radians(b_lat - a_lat)
    dlng   = math.radians(b_lng - a_lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def init_location_verify_db() -> None:
    """location_verify_sessions 테이블을 초기화합니다 (idempotent)."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS location_verify_sessions (
                id               TEXT PRIMARY KEY,
                subject_id       TEXT,
                target_lat       REAL NOT NULL,
                target_lng       REAL NOT NULL,
                target_address   TEXT,
                radius_m         REAL DEFAULT 300,
                status           TEXT DEFAULT 'TARGET_CREATED',
                current_lat      REAL,
                current_lng      REAL,
                current_accuracy REAL,
                distance_m       REAL,
                qr_session_id    TEXT,
                verified_at      TEXT,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 멱등 마이그레이션: 구버전 DB에 컬럼이 없으면 추가
        existing = [r[1] for r in conn.execute(
            "PRAGMA table_info(location_verify_sessions)").fetchall()]
        migrations = {
            "target_address":   "ALTER TABLE location_verify_sessions ADD COLUMN target_address TEXT",
            "radius_m":         "ALTER TABLE location_verify_sessions ADD COLUMN radius_m REAL DEFAULT 300",
            "current_lat":      "ALTER TABLE location_verify_sessions ADD COLUMN current_lat REAL",
            "current_lng":      "ALTER TABLE location_verify_sessions ADD COLUMN current_lng REAL",
            "current_accuracy": "ALTER TABLE location_verify_sessions ADD COLUMN current_accuracy REAL",
            "distance_m":       "ALTER TABLE location_verify_sessions ADD COLUMN distance_m REAL",
            "qr_session_id":    "ALTER TABLE location_verify_sessions ADD COLUMN qr_session_id TEXT",
            "verified_at":      "ALTER TABLE location_verify_sessions ADD COLUMN verified_at TEXT",
            "updated_at":       "ALTER TABLE location_verify_sessions ADD COLUMN updated_at TEXT",
        }
        for col, ddl in migrations.items():
            if col not in existing:
                conn.execute(ddl)
        conn.commit()


def create_dummy_target(payload: Dict[str, Any]) -> Dict[str, Any]:
    """위치 인증 세션을 생성합니다. lat/lng 필수."""
    lat = _float(_pick(payload, "lat", "targetLat", "target_lat"))
    lng = _float(_pick(payload, "lng", "targetLng", "target_lng"))
    if lat is None or lng is None:
        raise ValueError("lat/lng 값이 필요합니다.")

    radius_m   = _float(_pick(payload, "radiusM", "radius_m"), DEFAULT_RADIUS_M) or DEFAULT_RADIUS_M
    address    = _str(_pick(payload, "address", "targetAddress", "target_address"), "")
    subject_id = _str(_pick(payload, "subjectId", "subject_id"), "")
    session_id = "locv_" + uuid.uuid4().hex[:16]
    if not subject_id:
        subject_id = "demo_pickup_" + session_id[-8:]
    now = _now()

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO location_verify_sessions
            (id, subject_id, target_lat, target_lng, target_address, radius_m, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'TARGET_CREATED', ?, ?)
        """, (session_id, subject_id, lat, lng, address, radius_m, now, now))
        conn.commit()
    return get_session(session_id) or {}


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM location_verify_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_dict(row)


def gps_check(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """현재 GPS 좌표를 검증해 거리를 계산하고 세션 상태를 갱신합니다."""
    session = get_session(session_id)
    if not session:
        raise LookupError("location verify session not found")

    lat      = _float(_pick(payload, "lat", "currentLat", "current_lat"))
    lng      = _float(_pick(payload, "lng", "currentLng", "current_lng"))
    accuracy = _float(_pick(payload, "accuracy", "currentAccuracy", "current_accuracy"), 9999.0) or 9999.0
    if lat is None or lng is None:
        raise ValueError("현재 lat/lng 값이 필요합니다.")

    target_lat       = float(session["target_lat"])
    target_lng       = float(session["target_lng"])
    radius_m         = _float(_pick(payload, "radiusM", "radius_m"),
                              _float(session.get("radius_m"), DEFAULT_RADIUS_M)) or DEFAULT_RADIUS_M
    accuracy_limit_m = _float(_pick(payload, "accuracyLimitM", "accuracy_limit_m"),
                              DEFAULT_ACCURACY_LIMIT_M) or DEFAULT_ACCURACY_LIMIT_M
    dist = distance_meters(target_lat, target_lng, lat, lng)

    if accuracy > accuracy_limit_m:
        status  = "LOW_ACCURACY"
        ok      = False
        message = f"GPS 정확도가 낮습니다. 현재 정확도 ±{round(accuracy)}m / 허용 ±{round(accuracy_limit_m)}m"
    elif dist <= radius_m:
        status  = "LOCATION_VERIFIED"
        ok      = True
        message = f"1차 GPS 인증 완료. 거래 지점에서 {round(dist)}m"
    else:
        status  = "TOO_FAR"
        ok      = False
        message = f"거래 지점에서 {round(dist)}m 떨어져 있습니다. 허용 반경 {round(radius_m)}m"

    now         = _now()
    verified_at = now if ok else session.get("verified_at")
    with get_conn() as conn:
        conn.execute("""
            UPDATE location_verify_sessions
               SET current_lat = ?, current_lng = ?, current_accuracy = ?, distance_m = ?,
                   radius_m = ?, status = ?, verified_at = ?, updated_at = ?
             WHERE id = ?
        """, (lat, lng, accuracy, dist, radius_m, status, verified_at, now, session_id))
        conn.commit()

    updated = get_session(session_id) or {}
    return {"ok": ok, "status": status, "message": message, "session": updated}


def mark_qr_issued(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """GPS 인증 세션에 QR 세션 ID를 연결하고 상태를 QR_ISSUED로 변경합니다."""
    session = get_session(session_id)
    if not session:
        raise LookupError("location verify session not found")
    qr_session_id = _str(_pick(payload, "qrSessionId", "qr_session_id", "id", "sessionId", "session_id"), "")
    now = _now()
    with get_conn() as conn:
        conn.execute("""
            UPDATE location_verify_sessions
               SET qr_session_id = ?, status = 'QR_ISSUED', updated_at = ?
             WHERE id = ?
        """, (qr_session_id, now, session_id))
        conn.commit()
    return get_session(session_id) or {}


def mark_qr_verified_by_qr_session(qr_session_id: str) -> int:
    """QR 세션 ID로 연결된 위치 인증 세션 상태를 QR_VERIFIED로 변경합니다.
    qr.py에서 QR 검증 성공 시 호출합니다. 갱신된 행 수를 반환합니다."""
    if not qr_session_id:
        return 0
    now = _now()
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE location_verify_sessions
               SET status = 'QR_VERIFIED', updated_at = ?
             WHERE qr_session_id = ?
        """, (now, qr_session_id))
        conn.commit()
        return int(cur.rowcount or 0)


def list_sessions(limit: int = 20) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit or 20), 100))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM location_verify_sessions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) or {} for r in rows]
