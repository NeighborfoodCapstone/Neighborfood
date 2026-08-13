-- ============================================================================
--  NeighborFood — 단일 SQLite 스키마 (Source of Truth)
--  파일      : sql/neighborfood_schema.sql
--  대상 DB   : data/neighborfood.db   (3개 분리 DB → 1개 파일로 통합 완료)
--  생성 기준 : app/db/*.py 코드 기준 재동기화 (2026-07-11)
--  엔진      : SQLite 3 (단일 FastAPI 백엔드)
--
--  주의:
--   - 이 파일은 app/db/*.py 의 CREATE TABLE IF NOT EXISTS 와 항상 일치해야 합니다.
--   - 부모 테이블(users → posts → transactions) 순서로 정의합니다.
--   - 애플리케이션은 모든 연결을 make_conn(DB_PATH, foreign_keys=True)로 생성하므로
--     세션당 외래키 제약이 활성화됩니다. (아래 PRAGMA는 수동 적용 시 참고용)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. users — 회원
--    login_id + password_hash 기반 자체 인증.
--    posts·transactions·sessions 가 id를 참조한다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    login_id                 TEXT    UNIQUE NOT NULL,                -- 로그인 아이디
    password_hash            TEXT    NOT NULL,                       -- PBKDF2-SHA256 'salt$hash'
    phone_number             TEXT    UNIQUE,                         -- 선택적 연락처
    nickname                 TEXT,                                   -- 표시 닉네임
    profile_image            TEXT,                                   -- 프로필 이미지 경로/URL
    trust_score              REAL    NOT NULL DEFAULT 36.5,          -- 신뢰 온도(°)
    role                     TEXT    NOT NULL DEFAULT 'user'
                             CHECK (role IN ('user', 'admin')),
    status                   TEXT    NOT NULL DEFAULT 'active'
                             CHECK (status IN ('active', 'suspended', 'withdrawn')),
    neighborhood             TEXT,                                   -- 인증된 동네 이름
    neighborhood_verified_at TEXT,                                   -- 동네 인증 일시(ISO-8601)
    email                    TEXT,                                   -- 이메일(선택)
    bio                      TEXT,                                   -- 자기소개
    interests                TEXT,                                   -- 관심 카테고리 JSON 배열
    dietary                  TEXT,                                   -- 식이 제한 JSON 배열
    created_at               TEXT    NOT NULL,
    updated_at               TEXT    NOT NULL
);

-- ----------------------------------------------------------------------------
-- 2. sessions — 로그인 세션 (Bearer 토큰)
--    /auth/login 성공 시 발급. Authorization: Bearer <token> 로 회원을 식별.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT    PRIMARY KEY,                        -- secrets.token_urlsafe(32)
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT    NOT NULL,                           -- 만료 시각(ISO-8601). 경과 시 401
    created_at TEXT    NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. auth_codes — OTP 인증코드 (단명 데이터, 선택적 사용)
--    SMS 인증이 필요한 경우 사용. 인증 성공 시 즉시 삭제.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_codes (
    phone_number TEXT PRIMARY KEY,
    code         TEXT NOT NULL,
    expiry_time  TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 4. posts — 게시글 (나눔/공동구매/교환 통합)
--    type 값에 따라 gb_* / exchange_want 전용 필드가 사용된다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT    NOT NULL,                        -- 'share' | 'groupbuy' | 'exchange'
    title         TEXT    NOT NULL,
    description   TEXT,
    category      TEXT,
    images        TEXT    DEFAULT '[]',                    -- 이미지 경로 JSON 배열
    address       TEXT,
    lat           REAL,
    lng           REAL,
    author_id     INTEGER NOT NULL REFERENCES users(id),
    status        TEXT    DEFAULT 'active',                -- 'active' | 'completed' | 'expired' | 'deleted'
    created_at    TEXT    NOT NULL,
    expires_at    TEXT,
    gb_target     INTEGER,
    gb_current    INTEGER DEFAULT 0,
    gb_price      INTEGER,
    exchange_want TEXT,
    appointment_place TEXT,  -- posts 거래 약속 장소(정산이 승계)
    appointment_at    TEXT,  -- posts 거래 약속 일시
    appointment_lat   REAL,  -- posts 약속 좌표 위도
    appointment_lng   REAL   -- posts 약속 좌표 경도
);
CREATE INDEX IF NOT EXISTS idx_posts_type_created ON posts (type, created_at);
CREATE INDEX IF NOT EXISTS idx_posts_author       ON posts (author_id);

-- ----------------------------------------------------------------------------
-- 5. transactions — 거래 앵커 테이블
--    정산·매너평가·신고·거래내역이 공통으로 참조하는 테이블.
--    게시글은 소프트삭제(status='deleted')이므로 CASCADE를 두지 않는다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id        INTEGER NOT NULL REFERENCES posts(id),
    provider_id    INTEGER NOT NULL REFERENCES users(id),
    receiver_id    INTEGER          REFERENCES users(id),
    status         TEXT    NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'confirmed', 'completed', 'canceled')),
    qr_session_id  TEXT,
    receipt_id     TEXT,
    appointment_at TEXT,                                   -- 거래 약속 일시(ISO-8601, 선택)
    created_at     TEXT    NOT NULL,
    completed_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_provider ON transactions (provider_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions (receiver_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tx_post     ON transactions (post_id);

-- ----------------------------------------------------------------------------
-- 5-1. groupbuy_participants — 공동구매 참여자
--    (post_id, user_id) 복합 PK로 중복 참여 차단.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS groupbuy_participants (
    post_id   INTEGER NOT NULL REFERENCES posts(id),
    user_id   INTEGER NOT NULL REFERENCES users(id),
    joined_at TEXT    NOT NULL,
    PRIMARY KEY (post_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_gbp_user ON groupbuy_participants (user_id);

-- ----------------------------------------------------------------------------
-- 5-2. manner_ratings — 상호 매너 평가
--    완료된 거래(transactions.status='completed')에 대해 당사자가 상대를 평가.
--    (transaction_id, rater_id) UNIQUE 로 거래당 평가자 1회만 허용.
--    score: +1(좋았어요) | -1(아쉬웠어요). users.trust_score에 소폭 반영.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manner_ratings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    rater_id       INTEGER NOT NULL REFERENCES users(id),   -- 평가하는 사람
    ratee_id       INTEGER NOT NULL REFERENCES users(id),   -- 평가받는 사람
    score          INTEGER NOT NULL CHECK (score IN (-1, 1)),
    comment        TEXT,
    created_at     TEXT    NOT NULL,
    UNIQUE (transaction_id, rater_id)
);
CREATE INDEX IF NOT EXISTS idx_mr_ratee ON manner_ratings (ratee_id, created_at);

-- ----------------------------------------------------------------------------
-- 5-3. settlements — 공동구매 정산 헤더
--    주최자(글 작성자)가 총 금액을 입력해 생성. 참여자별 분담은 shares에 기록.
--    앱은 자금을 보관/이동하지 않고 납부 상태만 추적(신뢰 기반).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settlements (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id           INTEGER NOT NULL REFERENCES posts(id),
    requester_id      INTEGER NOT NULL REFERENCES users(id),   -- 주최자(글 작성자)
    total_amount      INTEGER NOT NULL,
    account_info      TEXT,                                    -- 주최자 계좌(평문, 선택)
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','completed','canceled')),
    appointment_place TEXT,                                    -- 주최자 확정 거래 장소
    appointment_at    TEXT,                                    -- 주최자 확정 거래 일시(ISO-8601)
    appointment_lat   REAL,                                    -- 약속 장소 위도 (GPS 100m 검증 기준)
    appointment_lng   REAL,                                    -- 약속 장소 경도 (GPS 100m 검증 기준)
    created_at        TEXT NOT NULL,
    completed_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_stl_post      ON settlements (post_id);
CREATE INDEX IF NOT EXISTS idx_stl_requester ON settlements (requester_id, created_at);

-- ----------------------------------------------------------------------------
-- 5-4. settlement_shares — 참여자별 분담
--    순차 2단계 인증: gps_verified(Step 1) → quality_agreed(Step 2) 모두 1이어야 납부 가능
--    gps_verified  : 거래 지점 GPS 인증(LOCATION_VERIFIED) 완료 시 1
--    quality_agreed: 대면 QR 인증 완료(품질 동의) 시 1
--    auto_confirmed: (레거시) 과거 GPS+24h 자동확인 플래그 — 현재 미사용, 하위호환 유지
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settlement_shares (
    settlement_id  INTEGER NOT NULL REFERENCES settlements(id),
    user_id        INTEGER NOT NULL REFERENCES users(id),
    amount         INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'unpaid'
                   CHECK (status IN ('unpaid','paid','noshow')),
    gps_verified   INTEGER NOT NULL DEFAULT 0,               -- Step 1: GPS 인증 완료
    quality_agreed INTEGER NOT NULL DEFAULT 0,               -- Step 2: QR 인증 완료
    auto_confirmed INTEGER NOT NULL DEFAULT 0,               -- (레거시, 미사용)
    paid_at        TEXT,
    created_at     TEXT NOT NULL,
    PRIMARY KEY (settlement_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_shares_user ON settlement_shares (user_id, status);

-- ----------------------------------------------------------------------------
-- 6. qr_sessions — QR 거래 인증 세션
-- ----------------------------------------------------------------------------
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
);
CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued ON qr_sessions (subject_id, issued_at);
CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires ON qr_sessions (status, expires_at);
CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash     ON qr_sessions (token_hash);

-- ----------------------------------------------------------------------------
-- 7. receipts — 영수증 OCR 인증
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS receipts (
    id                    TEXT PRIMARY KEY,
    subject_id            TEXT,
    store_name            TEXT,
    purchased_at          TEXT,
    items                 TEXT NOT NULL DEFAULT '[]',
    selected_items        TEXT NOT NULL DEFAULT '[]',
    total                 INTEGER,
    status                TEXT NOT NULL DEFAULT 'SCANNED'
                          CHECK (status IN ('SCANNED', 'VERIFIED', 'FAILED')),
    trust_delta           REAL NOT NULL DEFAULT 0,
    ocr_engine            TEXT,
    image_path            TEXT,
    raw_ocr_json          TEXT,
    shopping_matches_json TEXT NOT NULL DEFAULT '[]',
    shopping_match_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED',
    shopping_matched_at   TEXT,
    fridge_added_at       TEXT,
    scanned_at            TEXT NOT NULL,
    verified_at           TEXT,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_receipts_subject_scanned ON receipts (subject_id, scanned_at);
CREATE INDEX IF NOT EXISTS idx_receipts_status_scanned  ON receipts (status, scanned_at);

-- ----------------------------------------------------------------------------
-- 8. fridge_items — 내 냉장고 관리
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fridge_items (
    id          TEXT PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    receipt_id  TEXT,
    source      TEXT NOT NULL DEFAULT 'receipt',
    item_name   TEXT NOT NULL,
    qty         INTEGER NOT NULL DEFAULT 1,
    unit        TEXT,
    price       INTEGER DEFAULT 0,
    category    TEXT,
    store_name  TEXT,
    purchased_at TEXT,
    status      TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'CONSUMED', 'EXPIRED', 'DISCARDED')),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE(receipt_id, item_name, purchased_at)
);
CREATE INDEX IF NOT EXISTS idx_fridge_items_user_status ON fridge_items (user_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_fridge_items_receipt     ON fridge_items (receipt_id);

-- ----------------------------------------------------------------------------
-- 9. location_verify_sessions — GPS 위치 인증 세션
-- ----------------------------------------------------------------------------
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
);

-- ----------------------------------------------------------------------------
-- 10. wishlists — 찜 목록
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wishlists (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id    INTEGER NOT NULL REFERENCES posts(id),
    created_at TEXT    NOT NULL,
    PRIMARY KEY (user_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_wishlists_post ON wishlists (post_id);

-- ----------------------------------------------------------------------------
-- 11. conversations — 채팅방 (1:1·그룹 공용)
--     kind: 'direct' = 1:1, 'group' = 공동구매 그룹 채팅
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL REFERENCES posts(id),
    host_id    INTEGER NOT NULL REFERENCES users(id),
    guest_id   INTEGER NOT NULL REFERENCES users(id),
    kind       TEXT    NOT NULL DEFAULT 'direct',
    created_at TEXT    NOT NULL,
    UNIQUE (post_id, guest_id)
);
CREATE INDEX IF NOT EXISTS idx_conv_host      ON conversations (host_id);
CREATE INDEX IF NOT EXISTS idx_conv_guest     ON conversations (guest_id);
CREATE INDEX IF NOT EXISTS idx_conv_post_kind ON conversations (post_id, kind);

-- ----------------------------------------------------------------------------
-- 12. messages — 채팅 메시지
--     read_at:   1:1 읽음 처리용 (그룹은 conversation_members.last_read_id 사용)
--     is_system: 1이면 시스템 알림 메시지 (예: "OOO님이 참여를 취소하셨습니다.")
--                posts.py cancel_join_groupbuy 에서 멱등 ALTER 후 삽입 (2026-08-12)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id       INTEGER NOT NULL REFERENCES users(id),
    content         TEXT    NOT NULL,
    created_at      TEXT    NOT NULL,
    read_at         TEXT,
    is_system       INTEGER NOT NULL DEFAULT 0  -- 0: 일반 메시지, 1: 시스템 알림
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages (conversation_id, id);

-- ----------------------------------------------------------------------------
-- 13. conversation_members — 그룹 채팅 멤버십·읽음 포인터
--     last_read_id: 해당 멤버가 마지막으로 읽은 message.id
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_members (
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    last_read_id    INTEGER NOT NULL DEFAULT 0,
    joined_at       TEXT    NOT NULL,
    PRIMARY KEY (conversation_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_convmem_user ON conversation_members (user_id);

-- ----------------------------------------------------------------------------
-- 14. notices — 공지사항
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER REFERENCES users(id),
    title      TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notices_created ON notices (created_at);

-- ----------------------------------------------------------------------------
-- 15. reports — 신고 (게시글/회원 대상)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    target_type TEXT    NOT NULL CHECK (target_type IN ('post','user')),
    target_id   INTEGER NOT NULL,
    reason      TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','resolved','dismissed')),
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status, created_at);