# 마지막 수정 : 2026.05.10
# 깃헙 저장소 주소 : https://github.com/NeighborfoodCapstone/Neighborfood.git
from fastapi import Request
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs
import sqlite3
import hashlib
import secrets
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sqlite3
import random
from datetime import datetime, timedelta

app = FastAPI(title="NeighborFood Auth API")

# ── CORS ──────────────────────────────────────────────────────────────────
# [수정] allow_credentials=True 와 allow_origins=["*"] 동시 사용 불가 → 제거
# 배포 시 여기 부분 바꿔야 함
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 배포 시 실제 도메인으로 교체
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB 초기화 ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_codes (
            phone_number TEXT PRIMARY KEY,
            code         TEXT NOT NULL,
            expiry_time  TEXT NOT NULL   -- [수정] ISO 8601 문자열로 저장 (Python 3.12+ 호환)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── 요청/응답 모델 ─────────────────────────────────────────────────────────
class AuthRequest(BaseModel):
    # [추가] 서버 측 전화번호 형식 검증
    phone_number: str = Field(..., pattern=r'^010-\d{4}-\d{4}$',
                              description="010-XXXX-XXXX 형식")

class VerifyRequest(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)

# ── 인증번호 발송 ──────────────────────────────────────────────────────────
@app.post("/request-auth")
async def request_auth(request: AuthRequest):
    auth_code = str(random.randint(100000, 999999))
    # [수정] datetime 객체 → ISO 8601 문자열로 저장
    expiry = (datetime.now() + timedelta(minutes=5)).isoformat() # 만료시간 설정

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO auth_codes (phone_number, code, expiry_time)
        VALUES (?, ?, ?)
    """, (request.phone_number, auth_code, expiry))
    conn.commit()
    conn.close()

    # [시연용] 실제 SMS API 연동 전에 터미널에서 확인
    print(f"\n[SMS 발송] {request.phone_number} → 인증번호: [{auth_code}]  (만료: 5분)\n") # 만료시간 터미널에 출력

    # 수정: auth_code를 응답에 포함 (실제 배포 시에는 SMS로만 발송하고 응답에서 제거)
    return {
        "message": "인증번호가 발송되었습니다.",
        "auth_code": auth_code
    }


# ── 인증번호 검증 ──────────────────────────────────────────────────────────
@app.post("/verify-auth")
async def verify_auth(req: VerifyRequest):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT code, expiry_time FROM auth_codes WHERE phone_number = ?",
        (req.phone_number,)
    )
    row = cursor.fetchone()
    conn.close()

    # 1) 인증 요청 기록 없음
    if not row:
        raise HTTPException(
            status_code=404,
            detail="인증 요청 기록이 없습니다. 인증요청을 먼저 눌러 주세요."
        )

    saved_code, expiry_str = row

    # 2) 만료 확인
    if datetime.fromisoformat(expiry_str) < datetime.now():
        raise HTTPException(
            status_code=410,
            detail="인증번호가 만료되었습니다. 재전송 후 다시 시도해 주세요."
        )

    # 3) 코드 불일치
    if saved_code != req.code:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 일치하지 않습니다. 다시 확인해 주세요."
        )

    # 4) 인증 성공 → 재사용 방지를 위해 코드 삭제
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_codes WHERE phone_number = ?", (req.phone_number,))
    conn.commit()
    conn.close()

    print(f"\n[인증 완료] {req.phone_number}\n")
    return {"message": "인증이 완료되었습니다.", "verified": True}


# ── 로컬 실행 진입점 ──────────────────────────────────────────────────────
# python main.py 로 바로 실행 가능
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

# =========================================================
# QR 거래 인증 API
# =========================================================

QR_DB_PATH = os.path.join(os.path.dirname(__file__), "qr_auth.db")


def qr_get_conn():
    conn = sqlite3.connect(QR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def qr_now_utc():
    return datetime.now(timezone.utc)


def qr_to_iso(dt: datetime):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def qr_from_iso(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def qr_hash_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def qr_parse_token(raw_value: str):
    if not raw_value:
        return ""

    value = raw_value.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)

        query = parse_qs(parsed.query)
        if "token" in query:
            return query["token"][0]

        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[-1]

    return value


def qr_row_to_dict(row):
    return {
        "id": row["id"],
        "subjectId": row["subject_id"],
        "purpose": row["purpose"],
        "status": row["status"],
        "issuedAt": row["issued_at"],
        "expiresAt": row["expires_at"],
        "usedAt": row["used_at"],
        "lastScannedAt": row["last_scanned_at"],
    }


def qr_init_db():
    with qr_get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_sessions (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'ISSUED'
                    CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                last_scanned_at TEXT,
                scanner_ip TEXT,
                scanner_user_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued
            ON qr_sessions (subject_id, issued_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires
            ON qr_sessions (status, expires_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash
            ON qr_sessions (token_hash)
            """
        )

        conn.commit()


def qr_expire_old_sessions():
    current_time = qr_to_iso(qr_now_utc())

    with qr_get_conn() as conn:
        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'EXPIRED',
                updated_at = ?
            WHERE status = 'ISSUED'
              AND expires_at < ?
            """,
            (current_time, current_time),
        )
        conn.commit()


class QrIssueRequest(BaseModel):
    subjectId: str
    purpose: str = "pickup_confirm"
    ttlSeconds: int = 300


class QrVerifyRequest(BaseModel):
    token: str | None = None
    rawValue: str | None = None


@app.post("/api/qr/request")
def issue_qr(body: QrIssueRequest):
    qr_init_db()

    subject_id = body.subjectId.strip()

    if not subject_id:
        return {
            "ok": False,
            "message": "subjectId가 비어 있습니다."
        }

    ttl = max(60, min(body.ttlSeconds, 900))

    session_id = f"qrs_{secrets.token_hex(8)}"
    raw_token = secrets.token_urlsafe(32)
    token_hash = qr_hash_token(raw_token)

    issued_at = qr_now_utc()
    expires_at = issued_at + timedelta(seconds=ttl)

    issued_at_text = qr_to_iso(issued_at)
    expires_at_text = qr_to_iso(expires_at)

    with qr_get_conn() as conn:
        conn.execute(
            """
            INSERT INTO qr_sessions (
                id,
                subject_id,
                purpose,
                token_hash,
                status,
                issued_at,
                expires_at,
                used_at,
                last_scanned_at,
                scanner_ip,
                scanner_user_agent,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                session_id,
                subject_id,
                body.purpose,
                token_hash,
                issued_at_text,
                expires_at_text,
                issued_at_text,
                issued_at_text,
            ),
        )
        conn.commit()

    verify_url = f"http://127.0.0.1:8000/api/qr/verify/{raw_token}"

    return {
        "ok": True,
        "session": {
            "id": session_id,
            "subjectId": subject_id,
            "purpose": body.purpose,
            "status": "ISSUED",
            "issuedAt": issued_at_text,
            "expiresAt": expires_at_text,
            "usedAt": None,
            "lastScannedAt": None,
            "token": raw_token,
            "verifyUrl": verify_url,
        },
    }


@app.post("/api/qr/verify")
def verify_qr(body: QrVerifyRequest, request: Request):
    qr_init_db()
    qr_expire_old_sessions()

    raw_value = body.token or body.rawValue or ""
    token = qr_parse_token(raw_value)

    if not token:
        return {
            "ok": False,
            "result": "invalid_input",
            "message": "QR 토큰이 비어 있습니다.",
        }

    token_hash = qr_hash_token(token)
    scanned_at = qr_to_iso(qr_now_utc())

    scanner_ip = request.client.host if request.client else None
    scanner_user_agent = request.headers.get("user-agent")

    with qr_get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "저장된 인증 세션을 찾을 수 없습니다.",
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET last_scanned_at = ?,
                scanner_ip = ?,
                scanner_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_at,
                scanner_ip,
                scanner_user_agent,
                scanned_at,
                row["id"],
            ),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE id = ?
            """,
            (row["id"],),
        ).fetchone()

        if row["status"] == "EXPIRED":
            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if row["status"] == "VERIFIED":
            return {
                "ok": False,
                "result": "already_used",
                "message": "이미 사용된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if qr_from_iso(row["expires_at"]) < qr_now_utc():
            conn.execute(
                """
                UPDATE qr_sessions
                SET status = 'EXPIRED',
                    updated_at = ?
                WHERE id = ?
                """,
                (scanned_at, row["id"]),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT *
                FROM qr_sessions
                WHERE id = ?
                """,
                (row["id"],),
            ).fetchone()

            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'VERIFIED',
                used_at = ?,
                last_scanned_at = ?,
                scanner_ip = ?,
                scanner_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_at,
                scanned_at,
                scanner_ip,
                scanner_user_agent,
                scanned_at,
                row["id"],
            ),
        )
        conn.commit()

        updated = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            WHERE id = ?
            """,
            (row["id"],),
        ).fetchone()

    return {
        "ok": True,
        "result": "verified",
        "message": "QR 인증이 완료되었습니다.",
        "session": qr_row_to_dict(updated),
    }


@app.get("/api/qr/verify/{token}")
def verify_qr_by_url(token: str, request: Request):
    body = QrVerifyRequest(token=token)
    return verify_qr(body, request)


@app.get("/api/qr/history")
def get_qr_history(limit: int = 20):
    qr_init_db()
    qr_expire_old_sessions()

    limit = max(1, min(limit, 50))

    with qr_get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            ORDER BY issued_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "ok": True,
        "items": [qr_row_to_dict(row) for row in rows],
    }