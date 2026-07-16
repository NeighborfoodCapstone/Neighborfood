from app.config  import DB_PATH
from app.db.base import make_conn


def get_conn():
    return make_conn(DB_PATH, foreign_keys=True)


def init_admin_db() -> None:
    """관리자 기능 테이블(notices · reports) 초기화 (idempotent).
    users·posts(부모) 생성 이후 호출."""
    with get_conn() as conn:
        # 공지사항
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id  INTEGER REFERENCES users(id),
                title      TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            )
        """)
        # 신고 (게시글/회원 대상)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL REFERENCES users(id),
                target_type TEXT    NOT NULL CHECK (target_type IN ('post','user')),
                target_id   INTEGER NOT NULL,
                reason      TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','resolved','dismissed')),
                created_at  TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notices_created ON notices (created_at)")
        conn.commit()
