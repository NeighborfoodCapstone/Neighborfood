import json
import os
import uuid
from datetime        import datetime
from typing          import Optional, List
from fastapi         import APIRouter, HTTPException, UploadFile, File, Query
from app.config      import UPLOAD_DIR
from app.db.auth_db  import get_conn
from app.models.post import PostCreate

router = APIRouter()


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
async def create_post(post: PostCreate):
    if post.type == "groupbuy":
        if not post.gb_target or not post.gb_price:
            raise HTTPException(
                status_code=400,
                detail="공동구매는 목표 인원(gb_target)과 1인당 가격(gb_price)이 필요합니다.",
            )

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
            post.author_id, "active",
            datetime.now().isoformat(),
            post.expires_at,
            post.gb_target, 0 if post.type == "groupbuy" else None,
            post.gb_price, post.exchange_want,
        ))
        new_id = cursor.lastrowid
        conn.commit()

    print(f"\n[게시글 등록] #{new_id} ({post.type}) {post.title} by {post.author_id}\n")
    return {"id": new_id, "message": "게시글이 등록되었습니다."}


@router.get("/posts")
async def list_posts(
    keyword:  Optional[str] = Query(None, description="제목·설명·카테고리 검색어"),
    type:     Optional[str] = Query(None, description="share|exchange|groupbuy"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    limit:    int           = 100,
):
    sql    = "SELECT * FROM posts WHERE 1=1"
    params = []

    if type:
        sql += " AND type = ?"
        params.append(type)
    if category:
        sql += " AND category LIKE ?"
        params.append(f"%{category}%")
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = []
    for r in rows:
        item = dict(r)
        try:
            item["images"] = json.loads(item["images"] or "[]")
        except json.JSONDecodeError:
            item["images"] = []
        results.append(item)

    return {"count": len(results), "items": results}


@router.get("/posts/{post_id}")
async def get_post(post_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")

    item = dict(row)
    try:
        item["images"] = json.loads(item["images"] or "[]")
    except json.JSONDecodeError:
        item["images"] = []

    return item


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT title FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")

        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()

    print(f"\n[게시글 삭제] #{post_id} '{row['title']}' 삭제됨\n")
    return {"id": post_id, "message": "게시글이 성공적으로 삭제되었습니다."}


@router.post("/posts/{post_id}/join")
async def join_groupbuy(post_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT type, gb_target, gb_current FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        if row["type"] != "groupbuy":
            raise HTTPException(status_code=400, detail="공동구매 게시글만 참여할 수 있습니다.")
        if row["gb_current"] >= row["gb_target"]:
            raise HTTPException(status_code=409, detail="이미 모집이 완료되었습니다.")

        new_current = row["gb_current"] + 1
        conn.execute(
            "UPDATE posts SET gb_current = ? WHERE id = ?",
            (new_current, post_id),
        )
        conn.commit()

    return {"id": post_id, "gb_current": new_current, "gb_target": row["gb_target"]}
