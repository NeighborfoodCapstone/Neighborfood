# 마지막 수정 : 2026.05.10
# 깃헙 저장소 주소 : https://github.com/NeighborfoodCapstone/Neighborfood.git

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