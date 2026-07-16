import json
import re
from fastapi          import APIRouter, HTTPException, Depends
from app.core.deps     import get_current_user
from app.core.utils    import now_utc, to_iso, verify_password
from app.db.auth_db    import get_conn
from app.models.user   import ProfileUpdate, WithdrawRequest
from app.models.member import NeighborhoodVerify

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _mask_phone(phone: str) -> str:
    """010-1234-5678 → 010-****-5678 (응답에 원본 전화번호를 노출하지 않기 위함)."""
    parts = (phone or "").split("-")
    if len(parts) == 3:
        return f"{parts[0]}-****-{parts[2]}"
    return phone or ""


def _json_list(raw):
    """interests/dietary 의 JSON 문자열을 리스트로 복원 (없으면 빈 리스트)."""
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _profile(user: dict) -> dict:
    return {
        "id":           user["id"],
        "loginId":      user.get("login_id"),
        "phoneMasked":  _mask_phone(user["phone_number"]),
        "nickname":     user["nickname"],
        "profileImage": user["profile_image"],
        "trustScore":   user["trust_score"],
        "role":         user["role"],
        "status":       user["status"],
        "neighborhood":           user.get("neighborhood"),
        "neighborhoodVerifiedAt": user.get("neighborhood_verified_at"),
        "email":        user.get("email"),
        "bio":          user.get("bio"),
        "interests":    _json_list(user.get("interests")),
        "dietary":      _json_list(user.get("dietary")),
        "createdAt":    user["created_at"],
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return _profile(user)


@router.patch("/me")
async def update_me(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    fields, params = [], []

    nickname = body.nickname.strip() if body.nickname is not None else None
    if nickname is not None:
        fields.append("nickname = ?")
        params.append(nickname)
    if body.profile_image is not None:
        fields.append("profile_image = ?")
        params.append(body.profile_image)
    if body.bio is not None:
        fields.append("bio = ?")
        params.append(body.bio.strip())
    if body.email is not None:
        email = body.email.strip()
        if email and not EMAIL_RE.match(email):
            raise HTTPException(status_code=400, detail="이메일 형식이 올바르지 않습니다.")
        fields.append("email = ?")
        params.append(email or None)
    if body.interests is not None:
        fields.append("interests = ?")
        params.append(json.dumps([s.strip() for s in body.interests if s.strip()],
                                  ensure_ascii=False))
    if body.dietary is not None:
        fields.append("dietary = ?")
        params.append(json.dumps([s.strip() for s in body.dietary if s.strip()],
                                  ensure_ascii=False))

    if not fields:
        raise HTTPException(status_code=400, detail="변경할 항목이 없습니다.")

    fields.append("updated_at = ?")
    params.append(to_iso(now_utc()))
    params.append(user["id"])

    with get_conn() as conn:
        if nickname is not None:
            dup = conn.execute(
                "SELECT 1 FROM users WHERE nickname = ? AND id != ?",
                (nickname, user["id"]),
            ).fetchone()
            if dup:
                raise HTTPException(status_code=409, detail="이미 사용 중인 닉네임입니다.")

        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        conn.commit()

    return _profile(dict(row))


@router.post("/withdraw")
async def withdraw(body: WithdrawRequest, user: dict = Depends(get_current_user)):
    """회원 탈퇴: 현재 비밀번호 확인 → 소프트삭제(status='withdrawn') + 개인정보 익명화.
    거래/게시글/채팅 이력은 '탈퇴한 사용자'로 보존됩니다(하드삭제 시 FK·타인 이력 손상)."""
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

    now = to_iso(now_utc())
    uid = user["id"]
    # UNIQUE/NOT NULL 제약을 지키면서 식별정보를 placeholder 로 치환 (개인정보 파기)
    anon_phone = f"withdrawn_{uid}"
    anon_nick  = f"탈퇴한 사용자#{uid}"
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET
                status        = 'withdrawn',
                phone_number  = ?,
                nickname      = ?,
                email         = NULL,
                bio           = NULL,
                interests     = NULL,
                dietary       = NULL,
                profile_image = NULL,
                neighborhood  = NULL,
                neighborhood_verified_at = NULL,
                updated_at    = ?
            WHERE id = ?
        """, (anon_phone, anon_nick, now, uid))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        conn.commit()
    return {"message": "회원 탈퇴가 완료되었습니다."}


@router.post("/neighborhood")
async def verify_neighborhood(body: NeighborhoodVerify,
                              user: dict = Depends(get_current_user)):
    """동네(위치) 인증: 프런트가 GPS 좌표 + 행정동 이름을 보내면 회원에 기록합니다."""
    # 좌표 유효성만 검사 (대한민국 대략 범위). 정밀 역지오코딩은 프런트 Kakao SDK 담당.
    if not (33.0 <= body.lat <= 39.5 and 124.0 <= body.lng <= 132.0):
        raise HTTPException(status_code=400, detail="국내 좌표가 아닙니다. 위치를 다시 확인해 주세요.")

    now = to_iso(now_utc())
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET neighborhood = ?, neighborhood_verified_at = ?, updated_at = ?
            WHERE id = ?
        """, (body.neighborhood, now, now, user["id"]))
        conn.commit()

    return {"neighborhood": body.neighborhood, "verifiedAt": now,
            "message": f"'{body.neighborhood}' 동네 인증이 완료되었습니다."}
