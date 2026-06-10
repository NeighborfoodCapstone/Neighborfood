-- ============================================================================
--  NeighborFood — 단일 SQLite 스키마 (Source of Truth)
--  파일      : sql/neighborfood_schema.sql
--  대상 DB   : data/neighborfood.db   (3개 분리 DB → 1개 파일로 통합 완료)
--  생성 기준 : 실제 neighborfood.db 추출 결과 (2026-06-07)
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
--    휴대폰 인증(auth_codes)을 통과한 번호로 자동 가입되는 기준 테이블.
--    posts·transactions·sessions 가 id를 참조한다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number  TEXT    UNIQUE NOT NULL,                 -- OTP 인증 연계 키 (중복 불가)
    nickname      TEXT,                                    -- 표시 닉네임 (가입 직후 NULL 허용)
    profile_image TEXT,                                    -- 프로필 이미지 경로/URL
    trust_score   REAL    NOT NULL DEFAULT 36.5,           -- 신뢰 온도(°). 영수증·매너로 가감
    role          TEXT    NOT NULL DEFAULT 'user'
                  CHECK (role   IN ('user', 'admin')),     -- 권한 구분
    status        TEXT    NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'suspended', 'withdrawn')),  -- 계정 상태(탈퇴=소프트삭제)
    created_at    TEXT    NOT NULL,                        -- ISO-8601 문자열
    updated_at    TEXT    NOT NULL
);

-- ----------------------------------------------------------------------------
-- 2. sessions — 로그인 세션 (Bearer 토큰)
--    /verify-auth 성공 시 발급. Authorization: Bearer <token> 로 회원을 식별.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT    PRIMARY KEY,                        -- secrets.token_urlsafe(32)
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT    NOT NULL,                           -- 만료 시각(ISO-8601). 경과 시 401
    created_at TEXT    NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. auth_codes — OTP 인증코드 (단명 데이터)
--    SMS로 발송되는 일회성 인증번호. 인증 성공 시 즉시 삭제된다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_codes (
    phone_number TEXT PRIMARY KEY,                         -- 재요청 시 INSERT OR REPLACE
    code         TEXT NOT NULL,                            -- 6자리 인증번호
    expiry_time  TEXT NOT NULL                             -- 만료 시각(ISO-8601 문자열)
);

-- ----------------------------------------------------------------------------
-- 4. posts — 게시글 (나눔/공동구매/교환 통합)
--    type 값에 따라 gb_* / exchange_want 전용 필드가 사용된다.
--    author_id 는 users.id 에 대한 물리 FK (회원 기능 도입으로 적용 완료).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT    NOT NULL,                        -- 'share' | 'groupbuy' | 'exchange'
    title         TEXT    NOT NULL,
    description   TEXT,
    category      TEXT,                                    -- 식재료 카테고리
    images        TEXT    DEFAULT '[]',                    -- 이미지 경로 JSON 배열(텍스트)
    address       TEXT,                                    -- 거래 장소명
    lat           REAL,                                    -- 위도
    lng           REAL,                                    -- 경도
    author_id     INTEGER NOT NULL REFERENCES users(id),   -- 작성자 (FK)
    status        TEXT    DEFAULT 'active',                -- 'active' | 'completed' | 'expired'
    created_at    TEXT    NOT NULL,
    expires_at    TEXT,                                    -- 마감 일시. NULL이면 무기한
    gb_target     INTEGER,                                 -- [공구] 목표 인원/수량
    gb_current    INTEGER DEFAULT 0,                       -- [공구] 현재 참여 인원
    gb_price      INTEGER,                                 -- [공구] 1인 분담금(원)
    exchange_want TEXT                                     -- [교환] 희망 물품 설명
);
CREATE INDEX IF NOT EXISTS idx_posts_type_created ON posts (type, created_at);
CREATE INDEX IF NOT EXISTS idx_posts_author       ON posts (author_id);

-- ----------------------------------------------------------------------------
-- 5. transactions — 거래 (앵커 테이블)
--    정산·매너평가·신고·거래내역이 공통으로 참조할 '하나의 거래' 단위.
--    qr_session_id / receipt_id 로 인증 세션과 느슨하게 연결한다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id       INTEGER NOT NULL REFERENCES posts(id),   -- 이력 보존(CASCADE 제거): 게시글은 소프트삭제
    provider_id   INTEGER NOT NULL REFERENCES users(id),   -- 나눔/판매자
    receiver_id   INTEGER          REFERENCES users(id),   -- 수령자
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'confirmed', 'completed', 'canceled')),
    qr_session_id TEXT,                                    -- 연계된 qr_sessions.id (선택)
    receipt_id    TEXT,                                    -- 연계된 receipts.id    (선택)
    created_at    TEXT    NOT NULL,
    completed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_provider ON transactions (provider_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tx_receiver ON transactions (receiver_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tx_post     ON transactions (post_id);

-- ----------------------------------------------------------------------------
-- 5-1. groupbuy_participants — 공동구매 참여자
--    '누가 참여했는가'를 기록 → 정산(N명 분담)·내 활동의 기반.
--    (post_id, user_id) 복합 PK로 중복 참여를 차단한다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS groupbuy_participants (
    post_id   INTEGER NOT NULL REFERENCES posts(id),
    user_id   INTEGER NOT NULL REFERENCES users(id),
    joined_at TEXT    NOT NULL,
    PRIMARY KEY (post_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_gbp_user ON groupbuy_participants (user_id);

-- ----------------------------------------------------------------------------
-- 6. qr_sessions — QR 거래 인증 세션
--    대면 거래 수령 확인용 일회용 토큰. 원본은 저장하지 않고 SHA-256 해시만 보관.
--    subject_id 는 현재 자유 문자열(논리적 참조) — 거래 연동은 transactions 경유.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS qr_sessions (
    id                 TEXT PRIMARY KEY,                   -- 'qrs_' + 랜덤 hex
    subject_id         TEXT NOT NULL,                      -- 대상 식별자(논리적)
    purpose            TEXT NOT NULL,                      -- 발행 목적(예: pickup_confirm)
    token_hash         TEXT NOT NULL UNIQUE,               -- 원본 토큰의 SHA-256 해시
    status             TEXT NOT NULL DEFAULT 'ISSUED'
                       CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
    issued_at          TEXT NOT NULL,
    expires_at         TEXT NOT NULL,                      -- 경과 시 자동 EXPIRED 처리
    used_at            TEXT,                               -- 검증 완료 시각
    last_scanned_at    TEXT,                               -- 마지막 스캔 시각(실패 포함)
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
--    이미지 OCR로 품목을 추출하고 사용자가 선택한 품목으로 인증해 신뢰 온도를 올린다.
--    image_path 는 PII(카드번호 등) 마스킹 후 경로만 저장.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS receipts (
    id             TEXT PRIMARY KEY,                       -- 'rcpt_' + 랜덤 hex
    subject_id     TEXT,                                   -- 인증 수행 식별자(논리적)
    store_name     TEXT,                                   -- OCR 인식 점포명
    purchased_at   TEXT,                                   -- 결제 일시(OCR 파싱)
    items          TEXT NOT NULL DEFAULT '[]',             -- OCR 전체 품목 JSON 배열
    selected_items TEXT NOT NULL DEFAULT '[]',             -- 사용자 선택 품목 JSON 배열
    total          INTEGER,                                -- 결제 총액(원)
    status         TEXT NOT NULL DEFAULT 'SCANNED'
                   CHECK (status IN ('SCANNED', 'VERIFIED', 'FAILED')),
    trust_delta    REAL NOT NULL DEFAULT 0,                -- 인증 성공 시 가산 점수(기본 0.3)
    ocr_engine     TEXT,                                   -- 'tesseract' | 'demo' 등
    image_path     TEXT,                                   -- PII 마스킹 후 저장 경로
    scanned_at     TEXT NOT NULL,
    verified_at    TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_receipts_subject_scanned ON receipts (subject_id, scanned_at);
CREATE INDEX IF NOT EXISTS idx_receipts_status_scanned  ON receipts (status, scanned_at);

-- ============================================================================
--  향후 확장(미생성) — transactions.id 를 FK로 참조해 추가 예정
--    settlements    (정산 요청)
--    manner_ratings (상호 매너 평가)
--    reports        (신고)
--    fridge_items   (내 냉장고 관리, users.id 참조)
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 7-1. receipts compatibility columns — 영수증 후속 흐름 확장
-- 기존 receipts.status CHECK(SCANNED/VERIFIED/FAILED)는 유지하고,
-- 쇼핑 검증/냉장고 추가 상태는 별도 컬럼으로 관리한다.
-- SQLite ALTER 참고용. 실제 앱은 app/db/fridge_db.py에서 안전하게 ADD COLUMN 처리한다.
-- ----------------------------------------------------------------------------
-- ALTER TABLE receipts ADD COLUMN raw_ocr_json TEXT;
-- ALTER TABLE receipts ADD COLUMN shopping_matches_json TEXT NOT NULL DEFAULT '[]';
-- ALTER TABLE receipts ADD COLUMN shopping_match_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED';
-- ALTER TABLE receipts ADD COLUMN shopping_matched_at TEXT;
-- ALTER TABLE receipts ADD COLUMN fridge_added_at TEXT;

-- ----------------------------------------------------------------------------
-- 8. fridge_items — 내 냉장고 관리
-- VERIFIED 된 receipts.selected_items를 사용자의 냉장고 항목으로 전환한다.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fridge_items (
  id TEXT PRIMARY KEY,
  user_id INTEGER,
  receipt_id TEXT,
  source TEXT NOT NULL DEFAULT 'receipt',
  item_name TEXT NOT NULL,
  qty INTEGER NOT NULL DEFAULT 1,
  unit TEXT,
  price INTEGER DEFAULT 0,
  category TEXT,
  store_name TEXT,
  purchased_at TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('ACTIVE', 'CONSUMED', 'EXPIRED', 'DISCARDED')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(receipt_id, item_name, purchased_at)
);
CREATE INDEX IF NOT EXISTS idx_fridge_items_user_status
ON fridge_items (user_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_fridge_items_receipt
ON fridge_items (receipt_id);
