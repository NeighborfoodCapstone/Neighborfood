import json
from fastapi              import APIRouter, HTTPException, Depends, Query
from typing               import Optional
from app.core.deps        import get_current_user
from app.core.utils       import now_utc, to_iso
from app.db.transaction_db import get_conn, row_to_dict
from app.models.member    import TransactionCreate, TransactionUpdate

router = APIRouter()

# 상태 전환 허용 규칙 (단방향 진행 + 취소)
_ALLOWED = {
    "pending":   {"confirmed", "canceled"},
    "confirmed": {"completed", "canceled"},
    "completed": set(),
    "canceled":  set(),
}


def _enrich(conn, row) -> dict:
    """거래 행에 게시글 제목·이미지·유형, 상대방 닉네임을 붙여 응답용으로 가공."""
    d = row_to_dict(row)
    post = conn.execute(
        "SELECT title, type, images, status FROM posts WHERE id = ?", (row["post_id"],)
    ).fetchone()
    if post:
        d["postTitle"]  = post["title"]
        d["postType"]   = post["type"]
        d["postStatus"] = post["status"]
        try:
            imgs = json.loads(post["images"] or "[]")
        except json.JSONDecodeError:
            imgs = []
        d["postImage"] = imgs[0] if imgs else None
    else:
        d["postTitle"] = "(삭제된 게시글)"
        d["postType"] = d["postStatus"] = d["postImage"] = None

    def _nick(uid):
        if not uid:
            return None
        u = conn.execute("SELECT nickname, id FROM users WHERE id = ?", (uid,)).fetchone()
        return (u["nickname"] or f"이웃{u['id']}") if u else None

    d["providerNickname"] = _nick(row["provider_id"])
    d["receiverNickname"] = _nick(row["receiver_id"])
    return d


@router.get("")
async def my_transactions(
    status: Optional[str] = Query(None, pattern=r"^(pending|confirmed|completed|canceled)$"),
    user: dict = Depends(get_current_user),
):
    """내가 provider 또는 receiver 인 거래 목록 + 요약 통계."""
    uid = user["id"]
    with get_conn() as conn:
        sql = """SELECT * FROM transactions
                 WHERE (provider_id = ? OR receiver_id = ?)"""
        params = [uid, uid]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY datetime(created_at) DESC"
        rows = conn.execute(sql, params).fetchall()
        items = [_enrich(conn, r) for r in rows]

        # 요약 통계 (전체 기준)
        shared   = conn.execute("SELECT COUNT(*) c FROM transactions WHERE provider_id = ? AND status = 'completed'", (uid,)).fetchone()["c"]
        received = conn.execute("SELECT COUNT(*) c FROM transactions WHERE receiver_id = ? AND status = 'completed'", (uid,)).fetchone()["c"]
        ongoing  = conn.execute("SELECT COUNT(*) c FROM transactions WHERE (provider_id = ? OR receiver_id = ?) AND status IN ('pending','confirmed')", (uid, uid)).fetchone()["c"]

    # 각 거래에서 '내 역할'과 '상대방'을 정리해 프런트가 쓰기 쉽게
    for d in items:
        d["myRole"]  = "provider" if d["providerId"] == uid else "receiver"
        d["partner"] = d["receiverNickname"] if d["myRole"] == "provider" else d["providerNickname"]

    return {"count": len(items), "items": items,
            "stats": {"shared": shared, "received": received, "ongoing": ongoing}}


@router.post("")
async def create_transaction(body: TransactionCreate, user: dict = Depends(get_current_user)):
    """게시글에 대해 거래를 생성합니다. provider = 글 작성자, receiver = 신청자(나)."""
    now = to_iso(now_utc())
    with get_conn() as conn:
        post = conn.execute(
            "SELECT author_id, status FROM posts WHERE id = ?", (body.post_id,)
        ).fetchone()
        if not post or post["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if post["author_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="본인 게시글에는 거래를 신청할 수 없습니다.")

        # 같은 글에 같은 신청자의 진행 중 거래가 있으면 그것을 반환 (중복 방지)
        dup = conn.execute("""
            SELECT * FROM transactions
            WHERE post_id = ? AND receiver_id = ? AND status IN ('pending','confirmed')
            ORDER BY id DESC LIMIT 1
        """, (body.post_id, user["id"])).fetchone()
        if dup:
            return {"transactionId": dup["id"], "created": False,
                    "transaction": _enrich(conn, dup)}

        cur = conn.execute("""
            INSERT INTO transactions (post_id, provider_id, receiver_id, status,
                                      appointment_at, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (body.post_id, post["author_id"], user["id"], body.appointment_at, now))
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.commit()
        return {"transactionId": cur.lastrowid, "created": True,
                "transaction": _enrich(conn, row)}


@router.patch("/{tx_id}")
async def update_transaction(tx_id: int, body: TransactionUpdate,
                             user: dict = Depends(get_current_user)):
    """거래 상태를 전환합니다. 거래 당사자만 가능하며 허용된 전이만 적용됩니다."""
    with get_conn() as conn:
        tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if tx is None:
            raise HTTPException(status_code=404, detail="거래를 찾을 수 없습니다.")
        if user["id"] not in (tx["provider_id"], tx["receiver_id"]):
            raise HTTPException(status_code=403, detail="해당 거래의 당사자가 아닙니다.")

        cur_status, new_status = tx["status"], body.status
        if new_status != cur_status and new_status not in _ALLOWED.get(cur_status, set()):
            raise HTTPException(status_code=400,
                detail=f"'{cur_status}'에서 '{new_status}'(으)로 변경할 수 없습니다.")

        fields = ["status = ?"]
        params = [new_status]
        if body.appointment_at is not None:
            fields.append("appointment_at = ?")
            params.append(body.appointment_at)
        if new_status == "completed":
            fields.append("completed_at = ?")
            params.append(to_iso(now_utc()))
        params.append(tx_id)

        conn.execute(f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        conn.commit()
        return {"transactionId": tx_id, "transaction": _enrich(conn, row)}
