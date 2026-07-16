import json
from fastapi          import APIRouter, HTTPException, Depends
from app.core.deps    import get_current_user
from app.core.utils   import now_utc, to_iso
from app.db.member_db import get_conn

router = APIRouter()


@router.get("")
async def my_wishlist(user: dict = Depends(get_current_user)):
    """내가 찜한 게시글 목록 (삭제된 글 제외)."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.type, p.title, p.category, p.images, p.address,
                   p.status, p.gb_target, p.gb_current, p.gb_price,
                   w.created_at AS wished_at,
                   COALESCE(u.nickname, '이웃' || u.id) AS author_nickname
            FROM   wishlists w
            JOIN   posts p ON p.id = w.post_id
            LEFT JOIN users u ON u.id = p.author_id
            WHERE  w.user_id = ? AND p.status != 'deleted'
            ORDER BY w.created_at DESC
        """, (user["id"],)).fetchall()

    items = []
    for r in rows:
        item = dict(r)
        try:
            item["images"] = json.loads(item["images"] or "[]")
        except json.JSONDecodeError:
            item["images"] = []
        items.append(item)
    return {"count": len(items), "items": items}


@router.put("/{post_id}")
async def add_wish(post_id: int, user: dict = Depends(get_current_user)):
    """게시글을 찜 목록에 추가합니다 (이미 있으면 무시 — 멱등)."""
    with get_conn() as conn:
        post = conn.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post or post["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        conn.execute(
            "INSERT OR IGNORE INTO wishlists (user_id, post_id, created_at) VALUES (?, ?, ?)",
            (user["id"], post_id, to_iso(now_utc())),
        )
        conn.commit()
    return {"postId": post_id, "wished": True}


@router.delete("/{post_id}")
async def remove_wish(post_id: int, user: dict = Depends(get_current_user)):
    """찜을 해제합니다 (없어도 성공 — 멱등)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM wishlists WHERE user_id = ? AND post_id = ?",
                     (user["id"], post_id))
        conn.commit()
    return {"postId": post_id, "wished": False}
