from fastapi              import APIRouter, HTTPException, Depends
from pydantic             import BaseModel, Field
from typing               import Optional
from app.core.deps        import get_current_user
from app.core.utils       import now_utc, to_iso
from app.db.transaction_db import get_conn

router = APIRouter()

# trust_score 반영 폭 및 허용 범위
_TRUST_DELTA        = 0.5   # 받는 사람: +1 → +0.5, -1 → -0.5
_RATER_REWARD       = 0.1   # 평가를 남긴 사람(작성자) 본인에게 주는 보상
_TRUST_MIN          = 0.0
_TRUST_MAX          = 99.0


def _clamp_update(conn, user_id: int, delta: float) -> None:
    """trust_score를 원자적으로 delta만큼 조정하고 0~99로 클램프합니다."""
    conn.execute("""
        UPDATE users
           SET trust_score = MAX(?, MIN(?, trust_score + ?))
         WHERE id = ?
    """, (_TRUST_MIN, _TRUST_MAX, delta, user_id))


def _score_delta(score: int) -> float:
    return _TRUST_DELTA if score > 0 else -_TRUST_DELTA


class RatingCreate(BaseModel):
    transaction_id: int
    score:          int = Field(..., description="+1(좋았어요) 또는 -1(아쉬웠어요)")
    comment:        Optional[str] = None


class RatingUpdate(BaseModel):
    score:   Optional[int] = Field(None, description="+1 또는 -1")
    comment: Optional[str] = None


@router.post("")
async def create_rating(body: RatingCreate, user: dict = Depends(get_current_user)):
    """완료된 거래에 대해 상대방을 평가하고 trust_score에 반영합니다.

    규칙:
    - 완료(completed)된 거래만 평가 가능
    - 거래 당사자(provider/receiver)만 가능, 상대방을 평가 (자기 평가 불가)
    - 거래당 평가자 1회만 (UNIQUE 위반 시 409)
    - 받는 사람 trust_score ±0.5, 평가를 남긴 본인 +0.1 (같은 트랜잭션에서 원자적 처리)
    """
    if body.score not in (-1, 1):
        raise HTTPException(status_code=400, detail="score는 +1 또는 -1이어야 합니다.")

    uid = user["id"]
    now = to_iso(now_utc())

    with get_conn() as conn:
        tx = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (body.transaction_id,)
        ).fetchone()
        if tx is None:
            raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")

        if uid not in (tx["provider_id"], tx["receiver_id"]):
            raise HTTPException(status_code=403, detail="해당 거래의 당사자가 아닙니다.")

        if tx["status"] != "completed":
            raise HTTPException(status_code=400, detail="완료된 거래만 평가할 수 있습니다.")

        ratee_id = tx["receiver_id"] if uid == tx["provider_id"] else tx["provider_id"]
        if not ratee_id or ratee_id == uid:
            raise HTTPException(status_code=400, detail="평가할 상대방이 없습니다.")

        dup = conn.execute(
            "SELECT id FROM manner_ratings WHERE transaction_id = ? AND rater_id = ?",
            (body.transaction_id, uid),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail="이미 이 거래를 평가했습니다.")

        # ── 평가 기록 + trust_score 원자적 반영 (같은 트랜잭션) ──
        try:
            cur = conn.execute("""
                INSERT INTO manner_ratings
                    (transaction_id, rater_id, ratee_id, score, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (body.transaction_id, uid, ratee_id, body.score,
                  (body.comment or "").strip() or None, now))
            new_rating_id = cur.lastrowid

            # 받는 사람: 점수에 따라 ±0.5
            _clamp_update(conn, ratee_id, _score_delta(body.score))
            # 평가를 남긴 본인: 참여 보상 +0.1
            _clamp_update(conn, uid, _RATER_REWARD)
            conn.commit()
        except Exception:
            conn.rollback()
            raise HTTPException(status_code=409, detail="이미 이 거래를 평가했습니다.")

        ratee_ts = conn.execute(
            "SELECT trust_score FROM users WHERE id = ?", (ratee_id,)
        ).fetchone()
        rater_ts = conn.execute(
            "SELECT trust_score FROM users WHERE id = ?", (uid,)
        ).fetchone()

    return {
        "ok": True,
        "ratingId": new_rating_id,
        "transactionId": body.transaction_id,
        "rateeId": ratee_id,
        "score": body.score,
        "rateeTrustScore": round(ratee_ts["trust_score"], 1) if ratee_ts else None,
        "myTrustScore": round(rater_ts["trust_score"], 1) if rater_ts else None,
    }


@router.patch("/{rating_id}")
async def update_rating(rating_id: int, body: RatingUpdate,
                        user: dict = Depends(get_current_user)):
    """내가 남긴 평가의 점수·코멘트를 수정합니다.

    - 본인이 작성한 평가만 수정 가능
    - 점수가 바뀌면 받는 사람 trust_score를 재계산(기존 효과 취소 후 새 효과 적용)
    - 작성 보상(+0.1)은 이미 지급되었으므로 수정 시 다시 지급하지 않음
    """
    uid = user["id"]

    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM manner_ratings WHERE id = ?", (rating_id,)
        ).fetchone()
        if r is None:
            raise HTTPException(status_code=404, detail="평가를 찾을 수 없습니다.")
        if r["rater_id"] != uid:
            raise HTTPException(status_code=403, detail="본인이 작성한 평가만 수정할 수 있습니다.")

        new_score   = r["score"] if body.score is None else body.score
        if new_score not in (-1, 1):
            raise HTTPException(status_code=400, detail="score는 +1 또는 -1이어야 합니다.")

        # comment: 명시적으로 전달된 경우에만 갱신
        new_comment = r["comment"]
        if body.comment is not None:
            new_comment = body.comment.strip() or None

        now = to_iso(now_utc())
        try:
            # 점수가 바뀌면 받는 사람 trust_score 재계산
            if new_score != r["score"]:
                # 기존 효과 취소 + 새 효과 적용 = (new_delta - old_delta)
                diff = _score_delta(new_score) - _score_delta(r["score"])
                _clamp_update(conn, r["ratee_id"], diff)

            conn.execute("""
                UPDATE manner_ratings
                   SET score = ?, comment = ?
                 WHERE id = ?
            """, (new_score, new_comment, rating_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"평가 수정에 실패했습니다: {e}")

        ratee_ts = conn.execute(
            "SELECT trust_score FROM users WHERE id = ?", (r["ratee_id"],)
        ).fetchone()

    return {
        "ok": True,
        "ratingId": rating_id,
        "score": new_score,
        "comment": new_comment,
        "rateeTrustScore": round(ratee_ts["trust_score"], 1) if ratee_ts else None,
    }


@router.delete("/{rating_id}")
async def delete_rating(rating_id: int, user: dict = Depends(get_current_user)):
    """내가 남긴 평가를 삭제합니다.

    - 본인이 작성한 평가만 삭제 가능
    - 받는 사람에게 줬던 점수 효과(±0.5)를 되돌림
    - 작성 보상(+0.1)도 함께 회수 (같은 트랜잭션에서 원자적 처리)
    """
    uid = user["id"]

    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM manner_ratings WHERE id = ?", (rating_id,)
        ).fetchone()
        if r is None:
            raise HTTPException(status_code=404, detail="평가를 찾을 수 없습니다.")
        if r["rater_id"] != uid:
            raise HTTPException(status_code=403, detail="본인이 작성한 평가만 삭제할 수 있습니다.")

        try:
            # 받는 사람: 줬던 효과 취소
            _clamp_update(conn, r["ratee_id"], -_score_delta(r["score"]))
            # 작성자: 작성 보상 회수
            _clamp_update(conn, uid, -_RATER_REWARD)
            conn.execute("DELETE FROM manner_ratings WHERE id = ?", (rating_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"평가 삭제에 실패했습니다: {e}")

    return {"ok": True, "ratingId": rating_id, "deleted": True}


@router.get("/received")
async def received_ratings(user_id: Optional[int] = None,
                           user: dict = Depends(get_current_user)):
    """받은 매너 평가 요약. user_id 미지정 시 본인 기준."""
    target = user_id or user["id"]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT score, comment, created_at
              FROM manner_ratings
             WHERE ratee_id = ?
             ORDER BY datetime(created_at) DESC
        """, (target,)).fetchall()

        u = conn.execute("SELECT trust_score FROM users WHERE id = ?", (target,)).fetchone()

    total = len(rows)
    positive = sum(1 for r in rows if r["score"] > 0)
    negative = total - positive
    comments = [r["comment"] for r in rows if r["comment"]]

    return {
        "userId": target,
        "trustScore": round(u["trust_score"], 1) if u else None,
        "total": total,
        "positive": positive,
        "negative": negative,
        "comments": comments[:20],
    }


@router.get("/transaction/{tx_id}/me")
async def my_rating_for_transaction(tx_id: int, user: dict = Depends(get_current_user)):
    """특정 거래에 대해 내가 남긴 평가(수정·삭제용 id 포함)를 반환합니다."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, score, comment, created_at FROM manner_ratings "
            "WHERE transaction_id = ? AND rater_id = ?",
            (tx_id, user["id"]),
        ).fetchone()
    if not row:
        return {"rated": False}
    return {"rated": True, "ratingId": row["id"], "score": row["score"],
            "comment": row["comment"], "createdAt": row["created_at"]}