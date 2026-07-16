import hashlib
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

# ── 시간 헬퍼 ──────────────────────────────────────────────────────────────
def now_utc() -> datetime:
    """현재 UTC 시각을 반환합니다."""
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> str:
    """datetime → 'Z' 접미사 ISO-8601 문자열 변환."""
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def from_iso(value: str) -> datetime:
    """ISO-8601 문자열 → timezone-aware datetime 변환."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

# ── 보안 헬퍼 ──────────────────────────────────────────────────────────────
def hash_token(token: str) -> str:
    """토큰을 SHA-256 해시로 변환합니다. DB에는 원본 대신 해시만 저장합니다."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def new_token() -> str:
    """URL-safe 32바이트 원본 일회용 토큰을 생성합니다."""
    return secrets.token_urlsafe(32)

def new_id(prefix: str) -> str:
    """고유 ID를 생성합니다. 예: new_id('qrs') → 'qrs_a3f9c2b1'"""
    return f"{prefix}_{secrets.token_hex(8)}"

# ── 비밀번호 해시 (표준 라이브러리 PBKDF2 — 외부 의존성 없음) ──────────────
_PBKDF2_ITER = 200_000

def hash_password(password: str) -> str:
    """비밀번호를 'salt$hash' 형식의 PBKDF2-SHA256 문자열로 변환합니다."""
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               salt.encode("utf-8"), _PBKDF2_ITER)
    return f"{salt}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    """입력 비밀번호가 저장된 'salt$hash'와 일치하는지 상수 시간 비교합니다."""
    try:
        salt, expected = (stored or "").split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt.encode("utf-8"), _PBKDF2_ITER)
    return secrets.compare_digest(dk.hex(), expected)

# ── URL 파싱 ───────────────────────────────────────────────────────────────
def parse_token(raw_value: str) -> str:
    """
    QR / 영수증 검증 URL 또는 raw 토큰에서 토큰 문자열을 추출합니다.
    - URL 형식:  http://127.0.0.1:8000/api/qr/verify/<token>
    - Query 형식: ?token=<token>
    - Raw 형식:  <token>
    """
    if not raw_value:
        return ""

    value = raw_value.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        query  = parse_qs(parsed.query)
        if "token" in query and query["token"]:
            return query["token"][0]
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[-1]

    return value
