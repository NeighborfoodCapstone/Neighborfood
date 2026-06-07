import json
import os
import uuid
from typing          import Optional, List
from fastapi         import APIRouter, HTTPException, UploadFile, File, Query, Depends
from app.config      import UPLOAD_DIR
from app.core.deps   import get_current_user
from app.core.utils  import now_utc, to_iso
from app.db.auth_db  import get_conn
from app.models.post import PostCreate

router = APIRouter()

# 작성자 표시용: 닉네임이 없으면 '이웃<id>'로 폴백 (프런트에서 숫자만 노출되는 문제 방지)
_AUTHOR_SELECT = (
    "SELECT p.*, "
    "COALESCE(u.nickname, '이웃' || u.id) AS author_nickname, "
    "u.trust_score AS author_trust "
    "FROM posts p LEFT JOIN users u ON u.id = p.author_id "
)


def _row_to_item(row) -> dict:
    item = dict(row)
    try:
        item["images"] = json.loads(item["images"] or "[]")
    except json.JSONDecodeError:
        item["images"] = []
    return item


@router.post("/upload-images")
async def upload_images(files: List[UploadFile] = File(...)):
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    saved = []

    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in allowed_ext:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 확장자: {ext}")

        new_name = f"{uuid.uuid4().hex}{ext}"
        path     = os.path.join(UPLOAD_DIR, new_name)

        with open(path, "wb") as out:
            out.write(await f.read())

        saved.append(new_name)
        print(f"[이미지 저장] {f.filename} → {new_name}")

    return {"files": saved}


@router.post("/posts")
async def create_post(post: PostCreate, user: dict = Depends(get_current_user)):
    if post.type == "groupbuy":
        if not post.gb_target or not post.gb_price:
            raise HTTPException(
                status_code=400,
                detail="공동구매는 목표 인원(gb_target)과 1인당 가격(gb_price)이 필요합니다.",
            )

    # author_id는 클라이언트 값이 아니라 인증된 세션의 회원 id를 사용합니다 (위변조 방지)
    author_id = user["id"]

    with get_conn() as conn:
        cursor = conn.execute("""
            INSERT INTO posts (
                type, title, description, category, images,
                address, lat, lng, author_id, status,
                created_at, expires_at,
                gb_target, gb_current, gb_price, exchange_want
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post.type, post.title, post.description, post.category,
            json.dumps(post.images, ensure_ascii=False),
            post.address, post.lat, post.lng,
            author_id, "active",
            to_iso(now_utc()),
            post.expires_at,
            post.gb_target, 0 if post.type == "groupbuy" else None,
            post.gb_price, post.exchange_want,
        ))
        new_id = cursor.lastrowid
        conn.commit()

    print(f"\n[게시글 등록] #{new_id} ({post.type}) {post.title} by user#{author_id}\n")
    return {"id": new_id, "message": "게시글이 등록되었습니다."}


@router.get("/posts")
async def list_posts(
    keyword:  Optional[str] = Query(None, description="제목·설명·카테고리 검색어"),
    type:     Optional[str] = Query(None, description="share|exchange|groupbuy"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    limit:    int           = 100,
):
    sql    = _AUTHOR_SELECT + "WHERE p.status != 'deleted'"
    params = []

    if type:
        sql += " AND p.type = ?"
        params.append(type)
    if category:
        sql += " AND p.category LIKE ?"
        params.append(f"%{category}%")
    if keyword:
        sql += " AND (p.title LIKE ? OR p.description LIKE ? OR p.category LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

    sql += " ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = [_row_to_item(r) for r in rows]
    return {"count": len(results), "items": results}


@router.get("/posts/{post_id}")
async def get_post(post_id: int):
    with get_conn() as conn:
        row = conn.execute(_AUTHOR_SELECT + "WHERE p.id = ?", (post_id,)).fetchone()

    if not row or row["status"] == "deleted":
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")

    return _row_to_item(row)


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT title, author_id, status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")

        # 작성자 본인 또는 관리자만 삭제 가능
        if row["author_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="본인 게시글만 삭제할 수 있습니다.")

        # 하드 DELETE 대신 소프트삭제 → 연결된 거래 이력 보존
        conn.execute("UPDATE posts SET status = 'deleted' WHERE id = ?", (post_id,))
        conn.commit()

    print(f"\n[게시글 삭제] #{post_id} '{row['title']}' (soft-delete)\n")
    return {"id": post_id, "message": "게시글이 삭제되었습니다."}


@router.post("/posts/{post_id}/join")
async def join_groupbuy(post_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT type, status, gb_target, gb_current FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if row["type"] != "groupbuy":
            raise HTTPException(status_code=400, detail="공동구매 게시글만 참여할 수 있습니다.")

        # 중복 참여 방지
        dup = conn.execute(
            "SELECT 1 FROM groupbuy_participants WHERE post_id = ? AND user_id = ?",
            (post_id, user["id"]),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail="이미 참여한 공동구매입니다.")

        if row["gb_current"] is not None and row["gb_target"] is not None \
                and row["gb_current"] >= row["gb_target"]:
            raise HTTPException(status_code=409, detail="이미 모집이 완료되었습니다.")

        # 누가 참여했는지 기록(정산/내 활동 기반) + 카운트 증가
        conn.execute(
            "INSERT INTO groupbuy_participants (post_id, user_id, joined_at) VALUES (?, ?, ?)",
            (post_id, user["id"], to_iso(now_utc())),
        )
        new_current = (row["gb_current"] or 0) + 1
        conn.execute("UPDATE posts SET gb_current = ? WHERE id = ?", (new_current, post_id))
        conn.commit()

    return {"id": post_id, "gb_current": new_current, "gb_target": row["gb_target"]}
