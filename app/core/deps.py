from fastapi         import Header, HTTPException, Depends
from app.core.utils  import now_utc, from_iso
from app.db.auth_db  import get_conn


def get_bearer_token(authorization: str = Header(None)) -> str:
    """'Authorization: Bearer <token>' 헤더에서 토큰 문자열만 추출합니다."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(token: str = Depends(get_bearer_token)) -> dict:
    """
    세션 토큰을 검증해 회원 dict를 반환합니다.
    보호가 필요한 엔드포인트에 Depends(get_current_user)로 주입합니다.
    """
    with get_conn() as conn:
        row = conn.execute("""
            SELECT u.*, s.expires_at AS _exp
            FROM   sessions s
            JOIN   users    u ON u.id = s.user_id
            WHERE  s.token = ?
        """, (token,)).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.")
    if from_iso(row["_exp"]) < now_utc():
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해 주세요.")
    if row["status"] != "active":
        raise HTTPException(status_code=403, detail="이용이 제한된 계정입니다.")

    user = dict(row)
    user.pop("_exp", None)
    return user


def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    """관리자 전용 엔드포인트 가드. role='admin'이 아니면 403."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return user
