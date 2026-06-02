-- ====================================================================
-- DATABASE: receipt_auth.db
-- DESCRIPTION: 영수증 이미지 OCR 처리 결과 및 유저 신뢰 온도(가산치) 관리
-- ====================================================================

-- 1. 영수증 검증 데이터 테이블
CREATE TABLE IF NOT EXISTS receipts (
    id             TEXT PRIMARY KEY,            -- 영수증 인증 세션 고유 ID (UUID 등)
    subject_id     TEXT,                        -- 논리적 외래키 (연동된 posts.id 또는 작성자 user_id)
    store_name     TEXT,                        -- 마트/가게 점포명 (ex: "이마트 구의점") [수정 완료]
    purchased_at   TEXT,                        -- 영수증 결제 시점 (결제지 기준 일시 문자열) [수정 완료]
    items          TEXT NOT NULL DEFAULT '[]',  -- OCR 엔진이 영수증에서 추출한 전체 품목 리스트 (JSON Array 텍스트)
    selected_items TEXT NOT NULL DEFAULT '[]',  -- 전체 품목 중 유저가 실제 인증/판매용으로 선택한 품목 리스트 (JSON Array)
    total          INTEGER,                     -- 영수증 결제 총 금액
    status         TEXT NOT NULL DEFAULT 'SCANNED'
                   CHECK (status IN ('SCANNED', 'VERIFIED', 'FAILED')), 
                                                -- 상태 정의:
                                                -- 'SCANNED': 영수증 이미지 텍스트 분석 직후 단계
                                                -- 'VERIFIED': 사용자가 품목 선택 후 최종 검증 완료된 단계
                                                -- 'FAILED': 유효하지 않거나 중복된 영수증으로 판명 시
    trust_delta    REAL NOT NULL DEFAULT 0,     -- 영수증 인증 성공 시 해당 유저에게 부여할 신뢰 온도 보너스 점수 (ex: 0.5)
    ocr_engine     TEXT,                        -- 사용된 OCR 기술 프레임워크 (ex: 'tesseract', 'clova', 'google_vision')
    image_path     TEXT,                        -- 민감정보(카드번호 등) 마스킹 처리 후 서버 스토리지에 보관된 영수증 이미지 경로
    scanned_at     TEXT NOT NULL,               -- 영수증 최초 스캔/업로드 일시 (ISO 8601)
    verified_at    TEXT,                        -- 최종 검증 완료/승인 일시 (ISO 8601)
    created_at     TEXT NOT NULL,               -- 레코드 생성 일시 (ISO 8601)
    updated_at     TEXT NOT NULL                -- 레코드 수정 일시 (ISO 8601)
);

-- 대용량 데이터 환경에서의 빠른 논리 검색 조회를 위한 성능 최적화 인덱스
CREATE INDEX IF NOT EXISTS idx_receipts_subject_scanned 
ON receipts (subject_id, scanned_at);

CREATE INDEX IF NOT EXISTS idx_receipts_status_scanned 
ON receipts (status, scanned_at);