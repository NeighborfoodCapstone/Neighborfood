import random
import secrets
from datetime        import timedelta
from fastapi         import APIRouter, HTTPException, Depends
from app.config      import SESSION_TTL_DAYS
from app.core.utils  import now_utc, to_iso, from_iso, hash_password, verify_password
from app.core.deps   import get_bearer_token
from app.db.auth_db  import get_conn
from app.models.auth import RegisterRequest, LoginRequest, AuthRequest, PasswordResetRequest

router = APIRouter()

CODE_TTL_MIN        = 5    # 인증번호 유효 시간(분)
RESEND_COOLDOWN_SEC = 30   # 같은 번호 재요청 최소 간격(초)


def _issue_session(conn, user_id: int) -> str:
    """세션 토큰을 발급하고 만료 세션을 정리합니다."""
    now = to_iso(now_utc())
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    token   = secrets.token_urlsafe(32)
    expires = to_iso(now_utc() + timedelta(days=SESSION_TTL_DAYS))
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (token, user_id, expires, now),
    )
    return token


# ── 회원가입 / 로그인 (ID·비밀번호) ─────────────────────────────────────────

@router.post("/api/auth/register")
async def register(req: RegisterRequest):
    """ID·비밀번호·휴대폰 번호로 가입합니다. 휴대폰 OTP 검증은 하지 않으며,
    번호는 비밀번호 재설정(OTP) 용도로만 보관합니다. 가입 즉시 로그인됩니다."""
    now = to_iso(now_utc())
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE login_id = ?",
                        (req.login_id,)).fetchone():
            raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")
        if conn.execute("SELECT 1 FROM users WHERE phone_number = ?",
                        (req.phone_number,)).fetchone():
            raise HTTPException(status_code=409, detail="이미 가입된 휴대폰 번호입니다.")
        if req.nickname and conn.execute("SELECT 1 FROM users WHERE nickname = ?",
                                         (req.nickname,)).fetchone():
            raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.")

        cur = conn.execute("""
            INSERT INTO users (login_id, password_hash, phone_number, nickname,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.login_id, hash_password(req.password), req.phone_number,
              req.nickname, now, now))
        user_id = cur.lastrowid
        token   = _issue_session(conn, user_id)
        conn.commit()

    print(f"\n[회원가입] {req.login_id} (userId={user_id})\n")
    return {"message": "가입이 완료되었습니다.", "userId": user_id, "token": token}


@router.post("/api/auth/login")
async def login(req: LoginRequest):
    """ID·비밀번호로 로그인하고 Bearer 세션 토큰을 발급합니다."""
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id, password_hash, status FROM users WHERE login_id = ?",
            (req.login_id,),
        ).fetchone()

        # 아이디 존재 여부를 노출하지 않도록 동일 메시지로 응답
        if user is None or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401,
                detail="아이디 또는 비밀번호가 일치하지 않습니다.")
        if user["status"] == "withdrawn":
            raise HTTPException(status_code=403, detail="탈퇴한 계정입니다.")
        if user["status"] == "suspended":
            raise HTTPException(status_code=403, detail="이용이 정지된 계정입니다.")

        token = _issue_session(conn, user["id"])
        conn.commit()

    print(f"\n[로그인] {req.login_id} (userId={user['id']})\n")
    return {"message": "로그인되었습니다.", "userId": user["id"], "token": token}


@router.post("/logout")
async def logout(token: str = Depends(get_bearer_token)):
    """현재 세션 토큰을 폐기합니다."""
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    return {"message": "로그아웃되었습니다."}


# ── 비밀번호 재설정 (OTP는 이 용도로만 사용) ───────────────────────────────

@router.post("/request-auth")
async def request_auth(request: AuthRequest):
    """가입된 휴대폰 번호로 비밀번호 재설정 OTP를 발송합니다."""
    with get_conn() as conn:
        # 가입된 번호에만 발송 (단, 존재 여부는 응답으로 노출하지 않음)
        owner = conn.execute(
            "SELECT id, status FROM users WHERE phone_number = ?",
            (request.phone_number,),
        ).fetchone()

        if owner and owner["status"] == "active":
            existing = conn.execute(
                "SELECT expiry_time FROM auth_codes WHERE phone_number = ?",
                (request.phone_number,),
            ).fetchone()
            # 재요청 쿨다운: 발급 직후 RESEND_COOLDOWN_SEC 이내면 거부 (문자 폭탄 방지)
            if existing:
                remaining = (from_iso(existing["expiry_time"]) - now_utc()).total_seconds()
                if remaining > (CODE_TTL_MIN * 60 - RESEND_COOLDOWN_SEC):
                    raise HTTPException(status_code=429, detail="잠시 후 다시 시도해 주세요.")

            auth_code = str(random.randint(100000, 999999))
            expiry    = to_iso(now_utc() + timedelta(minutes=CODE_TTL_MIN))
            conn.execute(
                "INSERT OR REPLACE INTO auth_codes (phone_number, code, expiry_time) VALUES (?, ?, ?)",
                (request.phone_number, auth_code, expiry),
            )
            conn.commit()
            # 보안: 인증번호는 응답으로 노출하지 않고 서버 콘솔 로그로만 확인합니다.
            print(f"\n[SMS 발송] {request.phone_number} → [{auth_code}] (만료: {CODE_TTL_MIN}분)\n")

    return {"message": "가입된 번호라면 인증번호가 발송됩니다."}


@router.post("/reset-password")
async def reset_password(req: PasswordResetRequest):
    """OTP 코드를 검증하고 새 비밀번호로 변경합니다. 성공 시 전 세션을 폐기합니다."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT code, expiry_time FROM auth_codes WHERE phone_number = ?",
            (req.phone_number,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404,
                detail="인증 요청 기록이 없습니다. 인증요청을 먼저 눌러 주세요.")
        if from_iso(row["expiry_time"]) < now_utc():
            raise HTTPException(status_code=410,
                detail="인증번호가 만료되었습니다. 재전송 후 다시 시도해 주세요.")
        if row["code"] != req.code:
            raise HTTPException(status_code=400,
                detail="인증번호가 일치하지 않습니다. 다시 확인해 주세요.")

        user = conn.execute(
            "SELECT id FROM users WHERE phone_number = ? AND status = 'active'",
            (req.phone_number,),
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="가입 정보를 찾을 수 없습니다.")

        now = to_iso(now_utc())
        conn.execute("DELETE FROM auth_codes WHERE phone_number = ?", (req.phone_number,))
        conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                     (hash_password(req.new_password), now, user["id"]))
        # 비밀번호가 바뀌었으므로 기존 로그인 전부 무효화 (탈취 세션 차단)
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        conn.commit()

    print(f"\n[비밀번호 재설정] {req.phone_number} (userId={user['id']})\n")
    return {"message": "비밀번호가 변경되었습니다. 새 비밀번호로 로그인해 주세요."}
