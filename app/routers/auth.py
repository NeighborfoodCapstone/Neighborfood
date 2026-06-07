import random
from datetime        import datetime, timedelta
from fastapi         import APIRouter, HTTPException
from app.db.auth_db  import get_conn
from app.models.auth import AuthRequest, VerifyRequest

router = APIRouter()


@router.post("/request-auth")
async def request_auth(request: AuthRequest):
    auth_code = str(random.randint(100000, 999999))
    expiry    = (datetime.now() + timedelta(minutes=5)).isoformat()

    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO auth_codes (phone_number, code, expiry_time)
            VALUES (?, ?, ?)
        """, (request.phone_number, auth_code, expiry))
        conn.commit()

    print(f"\n[SMS 발송] {request.phone_number} → [{auth_code}] (만료: 5분)\n")
    return {"message": "인증번호가 발송되었습니다.", "auth_code": auth_code}


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

    if datetime.fromisoformat(row["expiry_time"]) < datetime.now():
        raise HTTPException(status_code=410,
            detail="인증번호가 만료되었습니다. 재전송 후 다시 시도해 주세요.")

    if row["code"] != req.code:
        raise HTTPException(status_code=400,
            detail="인증번호가 일치하지 않습니다. 다시 확인해 주세요.")

    with get_conn() as conn:
        conn.execute("DELETE FROM auth_codes WHERE phone_number = ?", (req.phone_number,))
        conn.commit()

    print(f"\n[인증 완료] {req.phone_number}\n")
    return {"message": "인증이 완료되었습니다.", "verified": True}