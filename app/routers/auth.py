import random
import secrets
from datetime        import timedelta
from fastapi         import APIRouter, HTTPException, Depends
from app.config      import SESSION_TTL_DAYS
from app.core.utils  import now_utc, to_iso, from_iso
from app.core.deps   import get_bearer_token
from app.db.auth_db  import get_conn
from app.models.auth import AuthRequest, VerifyRequest

router = APIRouter()

CODE_TTL_MIN        = 5    # 인증번호 유효 시간(분)
RESEND_COOLDOWN_SEC = 30   # 같은 번호 재요청 최소 간격(초)


@router.post("/request-auth")
async def request_auth(request: AuthRequest):
    with get_conn() as conn:
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
    return {"message": "인증번호가 발송되었습니다."}


@router.post("/verify-auth")
async def verify_auth(req: VerifyRequest):
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

        now = to_iso(now_utc())

        # 사용한 코드 폐기 + 만료된 세션 청소(테이블 비대화 방지)
        conn.execute("DELETE FROM auth_codes WHERE phone_number = ?", (req.phone_number,))
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))

        # 회원 조회 / 자동 가입 (휴대폰 인증 = 가입·로그인 일원화)
        user = conn.execute(
            "SELECT id, status FROM users WHERE phone_number = ?",
            (req.phone_number,),
        ).fetchone()

        if user is None:
            cur = conn.execute(
                "INSERT INTO users (phone_number, created_at, updated_at) VALUES (?, ?, ?)",
                (req.phone_number, now, now),
            )
            user_id = cur.lastrowid
            is_new  = True
        else:
            if user["status"] == "withdrawn":
                raise HTTPException(status_code=403, detail="탈퇴한 계정입니다.")
            if user["status"] == "suspended":
                raise HTTPException(status_code=403, detail="이용이 정지된 계정입니다.")
            user_id = user["id"]
            is_new  = False

        # 세션 토큰 발급
        token   = secrets.token_urlsafe(32)
        expires = to_iso(now_utc() + timedelta(days=SESSION_TTL_DAYS))
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, expires, now),
        )
        conn.commit()

    print(f"\n[인증 완료] {req.phone_number} (userId={user_id}, 신규={is_new})\n")
    return {
        "message":  "인증이 완료되었습니다.",
        "verified": True,
        "isNew":    is_new,
        "userId":   user_id,
        "token":    token,
    }


@router.post("/logout")
async def logout(token: str = Depends(get_bearer_token)):
    """현재 세션 토큰을 폐기합니다."""
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    return {"message": "로그아웃되었습니다."}
