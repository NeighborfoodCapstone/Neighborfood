import sqlite3
from app.config  import DB_PATH
from app.db.base import make_conn


def get_conn() -> sqlite3.Connection:
    """통합 DB(neighborfood.db) 연결을 반환합니다."""
    return make_conn(DB_PATH, foreign_keys=True)


def init_transaction_db() -> None:
    """
    transactions(거래) + groupbuy_participants(공동구매 참여자) 테이블 초기화.
    정산·매너평가·신고·내 활동이 공통으로 참조하는 기반 테이블입니다.
    init_all_databases()에서 init_auth_db(users·posts) 이후에 호출됩니다.
    """
    with get_conn() as conn:
        # ── 거래 앵커 ──────────────────────────────────────────────────────
        #   post_id 는 CASCADE를 두지 않습니다(기본 NO ACTION).
        #   → 게시글이 삭제돼도 거래 이력은 보존됩니다(정산/분쟁/감사 대비).
        #   → 게시글 삭제는 하드 DELETE 대신 소프트삭제(status='deleted')를 사용합니다.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id       INTEGER NOT NULL REFERENCES posts(id),  -- 이력 보존(CASCADE 제거)
                provider_id   INTEGER NOT NULL REFERENCES users(id),  -- 나눔/판매자
                receiver_id   INTEGER          REFERENCES users(id),  -- 수령자
                status        TEXT    NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'confirmed', 'completed', 'canceled')),
                qr_session_id TEXT,    -- 연계된 qr_sessions.id (선택)
                receipt_id    TEXT,    -- 연계된 receipts.id    (선택)
                created_at    TEXT    NOT NULL,
                completed_at  TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_provider ON transactions (provider_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions (receiver_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_post     ON transactions (post_id)")

        # ── 공동구매 참여자 ────────────────────────────────────────────────
        #   '누가 참여했는가'를 기록 → 정산(N명 분담)·내 활동의 기반.
        #   (post_id, user_id) 복합 PK 로 중복 참여를 원천 차단합니다.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groupbuy_participants (
                post_id   INTEGER NOT NULL REFERENCES posts(id),
                user_id   INTEGER NOT NULL REFERENCES users(id),
                joined_at TEXT    NOT NULL,
                PRIMARY KEY (post_id, user_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gbp_user ON groupbuy_participants (user_id)")
        conn.commit()


def row_to_dict(row) -> dict:
    """transactions Row → API 응답용 dict 변환."""
    return {
        "id":          row["id"],
        "postId":      row["post_id"],
        "providerId":  row["provider_id"],
        "receiverId":  row["receiver_id"],
        "status":      row["status"],
        "qrSessionId": row["qr_session_id"],
        "receiptId":   row["receipt_id"],
        "createdAt":   row["created_at"],
        "completedAt": row["completed_at"],
    }
