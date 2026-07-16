from app.config import DB_PATH
from app.db.base import make_conn


def get_conn():
    return make_conn(DB_PATH, foreign_keys=True)


def init_member_db() -> None:
    """회원 전용 기능 테이블(wishlists · conversations · messages · conversation_members)을
    초기화합니다. users · posts(부모 테이블) 생성 이후에 호출되어야 합니다."""
    with get_conn() as conn:
        # ── 찜(관심) 목록 ───────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wishlists (
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                post_id    INTEGER NOT NULL REFERENCES posts(id),
                created_at TEXT    NOT NULL,
                PRIMARY KEY (user_id, post_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wishlists_post ON wishlists (post_id)")

        # ── 채팅방 (1:1 = 게시글×문의자, 그룹 = 공동구매 게시글 1개) ──────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id    INTEGER NOT NULL REFERENCES posts(id),
                host_id    INTEGER NOT NULL REFERENCES users(id),
                guest_id   INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT    NOT NULL,
                UNIQUE (post_id, guest_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_host  ON conversations (host_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_guest ON conversations (guest_id)")

        # 그룹 채팅 도입: kind 컬럼 (멱등 ALTER — 기존 행은 자동으로 'direct')
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "kind" not in cols:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN kind TEXT NOT NULL DEFAULT 'direct'"
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_post_kind ON conversations (post_id, kind)")

        # ── 채팅 메시지 (1:1·그룹 공용) ─────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                sender_id       INTEGER NOT NULL REFERENCES users(id),
                content         TEXT    NOT NULL,
                created_at      TEXT    NOT NULL,
                read_at         TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages (conversation_id, id)")

        # ── 그룹 채팅 멤버십 + 멤버별 읽음 포인터 ───────────────────────────
        # (1:1은 messages.read_at 으로, 그룹은 last_read_id 로 안 읽은 수 계산)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                last_read_id    INTEGER NOT NULL DEFAULT 0,
                joined_at       TEXT    NOT NULL,
                PRIMARY KEY (conversation_id, user_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_convmem_user ON conversation_members (user_id)")
        conn.commit()
