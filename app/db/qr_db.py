import sqlite3
from app.config     import QR_DB_PATH
from app.db.base    import make_conn
from app.core.utils import to_iso, now_utc


def get_conn() -> sqlite3.Connection:
    """qr_auth.db 연결을 반환합니다."""
    return make_conn(QR_DB_PATH)


def init_qr_db() -> None:
    """qr_sessions 테이블과 인덱스를 초기화합니다."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qr_sessions (
                id                 TEXT PRIMARY KEY,
                subject_id         TEXT NOT NULL,
                purpose            TEXT NOT NULL,
                token_hash         TEXT NOT NULL UNIQUE,
                status             TEXT NOT NULL DEFAULT 'ISSUED'
                                   CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
                issued_at          TEXT NOT NULL,
                expires_at         TEXT NOT NULL,
                used_at            TEXT,
                last_scanned_at    TEXT,
                scanner_ip         TEXT,
                scanner_user_agent TEXT,
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued
            ON qr_sessions (subject_id, issued_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires
            ON qr_sessions (status, expires_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash
            ON qr_sessions (token_hash)
        """)
        conn.commit()


def expire_old_sessions() -> None:
    """만료 시각이 지난 ISSUED 세션을 EXPIRED로 일괄 업데이트합니다."""
    current_time = to_iso(now_utc())
    with get_conn() as conn:
        conn.execute("""
            UPDATE qr_sessions
            SET    status     = 'EXPIRED',
                   updated_at = ?
            WHERE  status     = 'ISSUED'
              AND  expires_at < ?
        """, (current_time, current_time))
        conn.commit()


def row_to_dict(row) -> dict:
    """qr_sessions Row → API 응답용 dict 변환."""
    return {
        "id":            row["id"],
        "subjectId":     row["subject_id"],
        "purpose":       row["purpose"],
        "status":        row["status"],
        "issuedAt":      row["issued_at"],
        "expiresAt":     row["expires_at"],
        "usedAt":        row["used_at"],
        "lastScannedAt": row["last_scanned_at"],
    }
