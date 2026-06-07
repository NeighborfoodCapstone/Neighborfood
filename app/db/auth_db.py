import sqlite3
from app.config  import AUTH_DB_PATH
from app.db.base import make_conn


def get_conn() -> sqlite3.Connection:
    """auth.db 연결을 반환합니다."""
    return make_conn(AUTH_DB_PATH)


def init_auth_db() -> None:
    """auth_codes 및 posts 테이블을 초기화합니다 (서버 시작 시 1회 실행)."""
    with get_conn() as conn:
        # ── 인증코드 테이블 ────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_codes (
                phone_number TEXT PRIMARY KEY,
                code         TEXT NOT NULL,
                expiry_time  TEXT NOT NULL
            )
        """)

        # ── 게시글 통합 테이블 ─────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                type          TEXT    NOT NULL,
                title         TEXT    NOT NULL,
                description   TEXT,
                category      TEXT,
                images        TEXT    DEFAULT '[]',
                address       TEXT,
                lat           REAL,
                lng           REAL,
                author_id     TEXT    NOT NULL,
                status        TEXT    DEFAULT 'active',
                created_at    TEXT    NOT NULL,
                expires_at    TEXT,
                gb_target     INTEGER,
                gb_current    INTEGER DEFAULT 0,
                gb_price      INTEGER,
                exchange_want TEXT
            )
        """)
        conn.commit()
