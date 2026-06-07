import os

# ── 경로 상수 ──────────────────────────────────────────────────────────────
# app/config.py 기준으로 두 단계 위가 프로젝트 루트(BASE_DIR)
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PAGE_DIR   = os.path.join(BASE_DIR, "frontend")

DB_PATH          = os.path.join(DATA_DIR, "neighborfood.db")
SESSION_TTL_DAYS = 30

# 폴더가 없으면 자동 생성
os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── DB 파일 경로 ───────────────────────────────────────────────────────────
AUTH_DB_PATH    = os.path.join(DATA_DIR, "auth.db")
QR_DB_PATH      = os.path.join(DATA_DIR, "qr_auth.db")
RECEIPT_DB_PATH = os.path.join(DATA_DIR, "receipt_auth.db")

# ── 비즈니스 상수 ──────────────────────────────────────────────────────────
RECEIPT_TRUST_DELTA = 0.3   # 영수증 인증 1건당 신뢰 온도 +0.3°

# ── HTTP 헤더 ──────────────────────────────────────────────────────────────
# 개발 중 브라우저 캐시로 인한 stale HTML 방지
NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma":        "no-cache",
    "Expires":       "0",
}
