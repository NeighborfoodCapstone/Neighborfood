import sqlite3
from app.config import DB_PATH
from app.db.base import make_conn


def get_conn():
    return make_conn(DB_PATH, foreign_keys=True) 

def init_auth_db() -> None:
    """users · sessions · auth_codes · posts 테이블을 초기화합니다 (서버 시작 시 1회)."""
    with get_conn() as conn:
        # ── 회원 ───────────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number  TEXT    UNIQUE NOT NULL,
                nickname      TEXT,
                profile_image TEXT,
                trust_score   REAL    NOT NULL DEFAULT 36.5,
                role          TEXT    NOT NULL DEFAULT 'user'
                              CHECK (role   IN ('user', 'admin')),
                status        TEXT    NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'suspended', 'withdrawn')),
                created_at    TEXT    NOT NULL,
                updated_at    TEXT    NOT NULL
            )
        """)

        # ── 로그인 세션 (휴대폰 인증 성공 시 발급되는 Bearer 토큰) ──────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)

        # ── OTP 인증코드 ───────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_codes (
                phone_number TEXT PRIMARY KEY,
                code         TEXT NOT NULL,
                expiry_time  TEXT NOT NULL
            )
        """)

        # ── 게시글 통합 테이블 (author_id → users.id FK) ───────────────────
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
                author_id     INTEGER NOT NULL REFERENCES users(id),
                status        TEXT    DEFAULT 'active',
                created_at    TEXT    NOT NULL,
                expires_at    TEXT,
                gb_target     INTEGER,
                gb_current    INTEGER DEFAULT 0,
                gb_price      INTEGER,
                exchange_want TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_type_created ON posts (type, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_author       ON posts (author_id)")
        conn.commit()