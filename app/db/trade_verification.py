"""Lock trade rows and validate trade-bound, recent GPS evidence."""
import math
import sqlite3
from datetime import timedelta

from fastapi import HTTPException

from app.core.utils import now_utc, to_iso
from app.db.location_verify_db import distance_meters

GPS_RADIUS_M = 100.0
GPS_ACCURACY_LIMIT_M = 100.0  # Accuracy is a signal, not proof against GPS spoofing.
GPS_MAX_AGE = timedelta(minutes=5)


def begin(conn):
    if isinstance(conn, sqlite3.Connection):
        conn.execute('BEGIN IMMEDIATE')


def lock_row(conn, table, row_id):
    if table not in {'transactions', 'settlements', 'posts', 'qr_sessions', 'location_verify_sessions', 'manner_ratings'}:
        raise ValueError('Unsupported trade lock')
    suffix = '' if isinstance(conn, sqlite3.Connection) else (' FOR NO KEY UPDATE' if table == 'posts' else ' FOR UPDATE')
    return conn.execute(f'SELECT * FROM {table} WHERE id = ?{suffix}', (row_id,)).fetchone()


def valid_coordinate(lat, lng):
    return (lat is not None and lng is not None and math.isfinite(float(lat))
            and math.isfinite(float(lng)) and -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180)


def assert_location(lat, lng, accuracy, target_lat, target_lng):
    if not valid_coordinate(target_lat, target_lng):
        raise HTTPException(400, '거래 약속 좌표를 먼저 설정해 주세요.')
    if not valid_coordinate(lat, lng) or accuracy is None or not math.isfinite(float(accuracy)) or not 0 <= float(accuracy) <= GPS_ACCURACY_LIMIT_M:
        raise HTTPException(400, '위치 또는 GPS 정확도를 확인할 수 없습니다. 다시 측정해 주세요.')
    distance = distance_meters(float(target_lat), float(target_lng), float(lat), float(lng))
    if distance > GPS_RADIUS_M:
        raise HTTPException(400, f'약속 장소에서 {round(distance)}m 떨어져 있습니다. 100m 이내에서 다시 인증해 주세요.')
    return distance


def require_gps(conn, kind, trade_id, user_id, target_lat, target_lng, session_id=None):
    if kind not in ('transaction', 'settlement'):
        raise ValueError('Invalid trade kind')
    if not valid_coordinate(target_lat, target_lng):
        raise HTTPException(400, '거래 약속 좌표를 먼저 설정해 주세요.')
    cutoff = to_iso(now_utc() - GPS_MAX_AGE)
    session_filter = " AND id = ?" if session_id is not None else ""
    params = (trade_id, str(user_id), cutoff, target_lat, target_lng)
    if session_id is not None:
        params += (session_id,)
    row = conn.execute(f"""SELECT * FROM location_verify_sessions
        WHERE {kind}_id = ? AND subject_id = ? AND verified_at >= ?
          AND target_lat = ? AND target_lng = ?
          AND status IN ('LOCATION_VERIFIED', 'QR_ISSUED', 'QR_VERIFIED')
          {session_filter}
        ORDER BY verified_at DESC LIMIT 1""", params).fetchone()
    if not row:
        raise HTTPException(400, '이 거래의 최근 GPS 인증이 필요합니다. 약속 장소에서 다시 인증해 주세요.')
    assert_location(row['current_lat'], row['current_lng'], row['current_accuracy'], target_lat, target_lng)
    return row
