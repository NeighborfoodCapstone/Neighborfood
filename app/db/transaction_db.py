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
                appointment_at TEXT,   -- 거래 약속 일시(ISO, 선택)
                created_at    TEXT    NOT NULL,
                completed_at  TEXT
            )
        """)
        # 구버전 DB 파일 보호용 멱등 마이그레이션 (신규 생성 시에는 no-op)
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
        if "appointment_at" not in existing:
            conn.execute("ALTER TABLE transactions ADD COLUMN appointment_at TEXT")
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

        # ── 상호 매너 평가 ─────────────────────────────────────────────────
        #   완료된 거래에 대해 당사자가 상대를 평가(+1/-1).
        #   (transaction_id, rater_id) UNIQUE 로 거래당 평가자 1회만 허용.
        #   users.trust_score 반영은 rating.py에서 같은 트랜잭션으로 원자적 처리.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manner_ratings (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                rater_id       INTEGER NOT NULL REFERENCES users(id),
                ratee_id       INTEGER NOT NULL REFERENCES users(id),
                score          INTEGER NOT NULL CHECK (score IN (-1, 1)),
                comment        TEXT,
                created_at     TEXT    NOT NULL,
                UNIQUE (transaction_id, rater_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mr_ratee ON manner_ratings (ratee_id, created_at)")

        # ── 정산 헤더 ─────────────────────────────────────────────────────
        #   공동구매 주최자가 총 금액을 입력해 생성. 앱은 자금을 보관/이동하지
        #   않고 참여자별 납부 상태만 추적(신뢰 기반).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id           INTEGER NOT NULL REFERENCES posts(id),
                requester_id      INTEGER NOT NULL REFERENCES users(id),
                total_amount      INTEGER NOT NULL,
                account_info      TEXT,
                status            TEXT NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending','completed','canceled')),
                appointment_place TEXT,
                appointment_at    TEXT,
                appointment_lat   REAL,
                appointment_lng   REAL,
                created_at        TEXT NOT NULL,
                completed_at      TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stl_post      ON settlements (post_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stl_requester ON settlements (requester_id, created_at)")

        # ── 참여자별 분담 ──────────────────────────────────────────────────
        #   순차 2단계: gps_verified(Step 1) → quality_agreed(Step 2) 모두 1이어야 납부 가능
        #   auto_confirmed: (레거시) 미사용, 하위호환 컬럼
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settlement_shares (
                settlement_id  INTEGER NOT NULL REFERENCES settlements(id),
                user_id        INTEGER NOT NULL REFERENCES users(id),
                amount         INTEGER NOT NULL,
                status         TEXT NOT NULL DEFAULT 'unpaid'
                               CHECK (status IN ('unpaid','paid','noshow')),
                gps_verified   INTEGER NOT NULL DEFAULT 0,
                quality_agreed INTEGER NOT NULL DEFAULT 0,
                auto_confirmed INTEGER NOT NULL DEFAULT 0,
                paid_at        TEXT,
                created_at     TEXT NOT NULL,
                PRIMARY KEY (settlement_id, user_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_user ON settlement_shares (user_id, status)")

        # ── 멱등 마이그레이션 (구버전 DB 보정) ──────────────────────────────
        s_cols = [r[1] for r in conn.execute("PRAGMA table_info(settlements)").fetchall()]
        if "appointment_place" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_place TEXT")
        if "appointment_at" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_at TEXT")
        if "appointment_lat" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_lat REAL")
        if "appointment_lng" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_lng REAL")
        sh_cols = [r[1] for r in conn.execute("PRAGMA table_info(settlement_shares)").fetchall()]
        if "gps_verified" not in sh_cols:
            conn.execute("ALTER TABLE settlement_shares ADD COLUMN gps_verified INTEGER NOT NULL DEFAULT 0")
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
        "appointmentAt": row["appointment_at"] if "appointment_at" in row.keys() else None,
        "createdAt":   row["created_at"],
        "completedAt": row["completed_at"],
    }