-- ====================================================================
-- DATABASE: auth.db
-- DESCRIPTION: 사용자 휴대폰 인증 및 메인 비즈니스 데이터(게시글/거래) 관리
-- ====================================================================

-- 1. 사용자 휴대폰 인증 번호 관리 테이블
-- 유저가 회원가입/로그인 시 발급받는 일회성 SMS 인증 코드 세션
CREATE TABLE IF NOT EXISTS auth_codes (
    phone_number TEXT PRIMARY KEY,        -- 사용자 휴대폰 번호 (국가코드 포함 또는 대시 없는 형태)
    code         TEXT NOT NULL,           -- 발급된 4~6자리 인증 번호 문자열
    expiry_time  TEXT NOT NULL            -- 인증 만료 일시 (ISO 8601 포맷: YYYY-MM-DDTHH:mm:ssZ)
);

-- 2. 게시글 통합 관리 테이블 (나눔, 공동구매, 교환)
-- NeighborFood 서비스의 핵심 게시글 데이터를 저장하며, type에 따라 활성화되는 필드가 다름
CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,              -- 게시글 도메인 타입 ('share': 나눔, 'groupbuy': 공동구매, 'exchange': 교환)
    title           TEXT NOT NULL,              -- 게시글 제목
    description     TEXT,                       -- 본문 상세 내용
    category        TEXT,                       -- 식재료 카테고리 (예: 채소, 과일, 냉동식품, 베이커리 등)
    images          TEXT DEFAULT '[]',          -- 이미지 저장 경로의 JSON 배열 문자열 (ex: '["uploads/img1.png", "..."]')
    address         TEXT,                       -- 거래를 희망하는 대면 장소/주소 명칭
    lat             REAL,                       -- 거래 장소의 위도 (Latitude)
    lng             REAL,                       -- 거래 장소의 경도 (Longitude)
    author_id       TEXT NOT NULL,              -- 게시글 작성자 고유 식별자 (User ID)
    status          TEXT DEFAULT 'active',      -- 게시글 상태값 ('active': 거래중, 'completed': 거래완료, 'expired': 만료)
    created_at      TEXT NOT NULL,              -- 게시글 생성 일시 (ISO 8601)
    expires_at      TEXT,                       -- 게시글 마감/만료 일시 (ISO 8601, 나눔/공구 마감 시점)
    
    -- [공동구매(groupbuy) 전용 필드] *type이 'groupbuy'일 때만 유효함
    gb_target       INTEGER,                    -- 목표 모집 인원수 또는 목표 수량
    gb_current      INTEGER DEFAULT 0,          -- 현재까지 참여 확정된 인원수/수량
    gb_price        INTEGER,                    -- 공구 참여자 1인당 분담해야 하는 가격
    
    -- [교환(exchange) 전용 필드] *type이 'exchange'일 때만 유효함
    exchange_want   TEXT                        -- 작성자가 본인 물품과 바꾸고 싶어하는 희망 물품 상세 설명
);