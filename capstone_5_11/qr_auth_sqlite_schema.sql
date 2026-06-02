-- NeighborFood QR Auth SQLite prototype schema
-- qr-auth-app의 MySQL/Prisma QrSession 모델을 SQLite용으로 단순 변환한 버전입니다.

CREATE TABLE IF NOT EXISTS qr_sessions (
  id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  purpose TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'ISSUED'
    CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
  issued_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL,
  used_at TEXT,
  last_scanned_at TEXT,
  scanner_ip TEXT,
  scanner_user_agent TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued
ON qr_sessions (subject_id, issued_at);

CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires
ON qr_sessions (status, expires_at);

-- API 대응
-- POST /api/qr/request : subject_id, purpose, ttl_seconds -> raw token + QR image 반환, DB에는 token_hash 저장
-- POST /api/qr/verify  : raw token 또는 verify URL -> hash 후 상태 검증/사용 처리
-- GET  /api/qr/history : 최근 발급/검증 이력 조회
