-- ====================================================================
-- DATABASE: qr_auth.db
-- DESCRIPTION: 대면 거래 시 안전한 물품 수령/픽업 확인을 위한 QR 일회용 토큰 세션 관리
-- ====================================================================

-- 1. QR 인증 세션 테이블
-- 물품 양도자와 수령자가 만나 QR 코드를 스캔하여 거래 완료를 확정 짓는 보안 도메인
CREATE TABLE IF NOT EXISTS qr_sessions (
    id                 TEXT PRIMARY KEY,        -- QR 세션 고유 ID
    subject_id         TEXT NOT NULL,           -- 논리적 외래키 (연동된 posts.id 또는 거래 대상 매칭 ID)
    purpose            TEXT NOT NULL,           -- QR 발행 목적 (ex: "pickup_confirm", "user_verify")
    token_hash         TEXT NOT NULL UNIQUE,    -- 보안을 위해 원본 일회용 토큰을 일방향 해싱(SHA-256)하여 저장한 값
    status             TEXT NOT NULL DEFAULT 'ISSUED'
                       CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
                                                -- 상태 정의:
                                                -- 'ISSUED': QR 코드가 화면에 노출되어 스캔 대기 중인 상태
                                                -- 'VERIFIED': 상대방이 스캔하여 정상 거래 완료 처리된 상태
                                                -- 'EXPIRED': 제한 시간이 초과되어 사용할 수 없는 상태
    issued_at          TEXT NOT NULL,           -- QR 토큰 발급 시점 (ISO 8601)
    expires_at         TEXT NOT NULL,           -- QR 토큰 만료 시점 (보안 유효 기간 TTL 처리용, ISO 8601)
    used_at            TEXT,                    -- 실제 상대방이 스캔하여 승인 처리된 시점 (ISO 8601)
    last_scanned_at    TEXT,                    -- 마지막으로 QR이 리더기에 찍힌 시점 (실패 이력 포함)
    scanner_ip         TEXT,                    -- 어뷰징/부정 거래 추적 목적의 스캐너 기기 IP 주소
    scanner_user_agent TEXT,                    -- 스캐너 기기의 브라우저/앱 OS 정보 (User-Agent 문자열)
    created_at         TEXT NOT NULL,           -- 레코드 생성 일시
    updated_at         TEXT NOT NULL            -- 레코드 수정 일시
);

-- 실시간 검증 및 이력 조회를 위한 인덱스 설정
CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued 
ON qr_sessions (subject_id, issued_at);

CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires 
ON qr_sessions (status, expires_at);

-- 가장 핵심이 되는 QR 보안 검증용 해시 단일 인덱스
CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash 
ON qr_sessions (token_hash);