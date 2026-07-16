import sqlite3
from app.config import DB_PATH
from app.db.base import make_conn


def get_conn():
    return make_conn(DB_PATH, foreign_keys=True)


def _ensure_columns(conn, table: str, columns: dict) -> None:
    """기존 DB 파일에 컬럼이 없으면 ALTER TABLE로 추가합니다 (멱등).
    DB를 초기화하지 않고 서버만 재시작해도 스키마가 맞춰지도록 보호합니다."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_auth_db() -> None:
    """users · sessions · auth_codes · posts 테이블을 초기화합니다 (서버 시작 시 1회)."""
    with get_conn() as conn:
        # ── 회원 ───────────────────────────────────────────────────────────
        # 인증 정책(2026-06): 가입/로그인 = ID·비밀번호. 휴대폰 번호는 가입 시
        # 입력만 받고(OTP 검증 없음), OTP는 비밀번호 재설정 시에만 사용합니다.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                login_id        TEXT    UNIQUE NOT NULL,
                password_hash   TEXT    NOT NULL,
                phone_number    TEXT    UNIQUE NOT NULL,
                nickname        TEXT,
                profile_image   TEXT,
                trust_score     REAL    NOT NULL DEFAULT 36.5,
                role            TEXT    NOT NULL DEFAULT 'user'
                                CHECK (role   IN ('user', 'admin')),
                status          TEXT    NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active', 'suspended', 'withdrawn')),
                neighborhood    TEXT,
                neighborhood_verified_at TEXT,
                email           TEXT,
                bio             TEXT,
                interests       TEXT,
                dietary         TEXT,
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            )
        """)
        # 구버전 DB 파일 보호용 멱등 마이그레이션 (신규 생성 시에는 no-op)
        # interests·dietary 는 JSON 문자열(예: '["채소","과일"]')로 보관해 확장 여지를 둠.
        _ensure_columns(conn, "users", {
            "login_id":                 "TEXT",
            "password_hash":            "TEXT",
            "neighborhood":             "TEXT",
            "neighborhood_verified_at": "TEXT",
            "email":                    "TEXT",
            "bio":                      "TEXT",
            "interests":                "TEXT",
            "dietary":                  "TEXT",
        })

        # ── 로그인 세션 (로그인/가입 성공 시 발급되는 Bearer 토큰) ──────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT    PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)

        # ── OTP 인증코드 (용도: 비밀번호 재설정 전용) ──────────────────────
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_login        ON users (login_id)")
        conn.commit()
