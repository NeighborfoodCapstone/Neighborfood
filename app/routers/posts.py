import json
import os
import sqlite3
import uuid
from typing          import Optional, List
from fastapi         import APIRouter, HTTPException, UploadFile, File, Query, Depends
from app.config      import UPLOAD_DIR
from app.core.deps   import get_current_user
from app.core.utils  import now_utc, to_iso
from app.db.auth_db  import get_conn
from app.db          import settlement_db
from app.models.post import PostCreate
from pydantic import BaseModel, Field


class PostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    exchange_want: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    gb_max: Optional[int] = None          # (미사용, 구버전 호환)
    # ── 2026-10 확장 ─────────────────────────────────────────────
    images: Optional[List[str]] = None    # 사진 URL 목록 전체 교체
    type: Optional[str] = Field(None, pattern=r"^(share|exchange|groupbuy)$")
    gb_target: Optional[int] = None       # 공동구매 목표 인원
    gb_price: Optional[int] = None        # 공동구매 1인 가격


class PostAppointment(BaseModel):
    place:          Optional[str]   = None
    appointment_at: Optional[str]   = None
    lat:            Optional[float] = None
    lng:            Optional[float] = None

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
        # 만료 시각이 지난 active 게시글을 expired로 자동 전환 (멱등, 목록 조회 시점 정리)
        conn.execute("""
            UPDATE posts SET status = 'expired'
             WHERE status = 'active'
               AND expires_at IS NOT NULL
               AND datetime(expires_at) < datetime('now')
        """)
        conn.commit()
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


@router.post("/posts/{post_id}/appointment")
async def set_post_appointment(post_id: int, body: PostAppointment,
                               user: dict = Depends(get_current_user)):
    """게시글에 거래 약속(장소·시간·좌표)을 저장합니다 — 작성자 전용.

    정산 레코드가 없어도 채팅 단계에서 약속을 확정할 수 있게 합니다.
    이후 정산이 생성되면 settlements가 이 값을 승계합니다.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT author_id, status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(404, "해당 게시글을 찾을 수 없습니다.")
        if row["author_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(403, "게시글 작성자만 약속을 정할 수 있습니다.")
        if not (body.place or body.appointment_at):
            raise HTTPException(400, "약속 장소 또는 시간을 입력해 주세요.")

        conn.execute("""
            UPDATE posts
               SET appointment_place = ?, appointment_at = ?,
                   appointment_lat   = ?, appointment_lng = ?
             WHERE id = ?
        """, ((body.place or "").strip() or None,
              (body.appointment_at or "").strip() or None,
              body.lat, body.lng, post_id))
        conn.commit()

        # 이미 정산이 있으면 정산에도 동기화(승계)
        stl = conn.execute(
            "SELECT id FROM settlements WHERE post_id = ? AND status = 'pending'",
            (post_id,),
        ).fetchone()
        if stl:
            conn.execute("""
                UPDATE settlements
                   SET appointment_place = ?, appointment_at = ?,
                       appointment_lat   = ?, appointment_lng = ?
                 WHERE id = ?
            """, ((body.place or "").strip() or None,
                  (body.appointment_at or "").strip() or None,
                  body.lat, body.lng, stl["id"]))
            conn.commit()

    return {
        "ok": True,
        "appointment": {
            "place":         body.place,
            "appointmentAt": body.appointment_at,
            "lat":           body.lat,
            "lng":           body.lng,
        },
        "settlementSynced": bool(stl),
    }


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


@router.patch("/posts/{post_id}")
async def update_post(post_id: int, body: PostUpdate, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT author_id, status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")
        if row["author_id"] != user["id"] and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="본인 게시글만 수정할 수 있습니다.")

        sets: list[str] = []
        vals: list = []
        field_map = {
            "title": body.title, "description": body.description,
            "category": body.category, "status": body.status,
            "exchange_want": body.exchange_want, "address": body.address,
            "lat": body.lat, "lng": body.lng,
        }
        for col, val in field_map.items():
            if val is not None:
                sets.append(f"{col} = ?"); vals.append(val)

        # 사진은 거래 진행과 무관하게 수정 가능 (목록 전체 교체)
        if body.images is not None:
            if len(body.images) > 10:
                raise HTTPException(status_code=400, detail="사진은 최대 10장까지 등록할 수 있습니다.")
            sets.append("images = ?"); vals.append(json.dumps(body.images, ensure_ascii=False))

        # 거래 유형·공동구매 인원/가격은 참여자나 정산이 생기면 잠급니다.
        if any(v is not None for v in (body.type, body.gb_target, body.gb_price)):
            cur = conn.execute(
                "SELECT type, gb_target, gb_current, gb_price FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
            participants = (cur["gb_current"] or 0) > 0 or conn.execute(
                "SELECT 1 FROM groupbuy_participants WHERE post_id = ? LIMIT 1", (post_id,)
            ).fetchone()
            settled = conn.execute(
                "SELECT 1 FROM settlements WHERE post_id = ? AND status != 'canceled' LIMIT 1", (post_id,)
            ).fetchone()
            if participants or settled:
                raise HTTPException(
                    status_code=409,
                    detail="참여자나 정산이 있는 게시글은 거래 유형·인원·가격을 변경할 수 없습니다.",
                )
            new_type = body.type or cur["type"]
            if new_type == "groupbuy":
                target = body.gb_target if body.gb_target is not None else cur["gb_target"]
                price  = body.gb_price  if body.gb_price  is not None else cur["gb_price"]
                if target is None or target < 2:
                    raise HTTPException(status_code=400, detail="공동구매 목표 인원은 2명 이상이어야 합니다.")
                if price is None or price <= 0:
                    raise HTTPException(status_code=400, detail="공동구매 가격은 1원 이상이어야 합니다.")
                sets += ["type = ?", "gb_target = ?", "gb_price = ?", "gb_current = ?"]
                vals += [new_type, target, price, 0]
            else:
                if body.gb_target is not None or body.gb_price is not None:
                    raise HTTPException(status_code=400, detail="공동구매 게시글만 인원·가격을 설정할 수 있습니다.")
                if new_type != cur["type"]:
                    sets += ["type = ?", "gb_target = NULL", "gb_price = NULL", "gb_current = NULL"]
                    vals += [new_type]
        if not sets:
            raise HTTPException(status_code=400, detail="수정할 내용이 없습니다.")
        vals.append(post_id)
        conn.execute(f"UPDATE posts SET {', '.join(sets)} WHERE id = ?", tuple(vals))
        conn.commit()
        updated = conn.execute(_AUTHOR_SELECT + "WHERE p.id = ?", (post_id,)).fetchone()

    return _row_to_item(updated)


@router.get("/posts/{post_id}/my-status")
async def my_post_status(post_id: int, user: dict = Depends(get_current_user)):
    """현재 사용자의 해당 게시글에 대한 역할 조회 (작성자 여부 + 참여자 여부).
    공동구매 상세 화면에서 "참여 취소" 버튼 노출 여부를 결정하는 데 사용합니다."""
    uid = user["id"]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT author_id FROM posts WHERE id = ? AND status != 'deleted'", (post_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        is_author      = (row["author_id"] == uid)
        is_participant = bool(conn.execute(
            "SELECT 1 FROM groupbuy_participants WHERE post_id = ? AND user_id = ?",
            (post_id, uid),
        ).fetchone())
    return {"isAuthor": is_author, "isParticipant": is_participant}


@router.delete("/posts/{post_id}/join")
async def cancel_join_groupbuy(post_id: int, user: dict = Depends(get_current_user)):
    """공동구매 참여 취소 — 정산이 생성(pending/completed)된 이후에는 취소 불가.
    gb_current를 MAX(0, gb_current-1)로 원자적 감소하고,
    그룹 채팅방에서 해당 회원을 퇴장 처리 + 시스템 메시지를 삽입합니다."""
    uid = user["id"]
    with get_conn() as conn:
        # ── messages 테이블에 is_system 컬럼이 없으면 추가 (멱등 마이그레이션) ──
        msg_cols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)")}
        if "is_system" not in msg_cols:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0"
            )

        row = conn.execute(
            "SELECT type, status FROM posts WHERE id = ? AND status != 'deleted'", (post_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if row["type"] != "groupbuy":
            raise HTTPException(status_code=400, detail="공동구매 게시글만 취소할 수 있습니다.")

        # 참여 여부 확인
        if not conn.execute(
            "SELECT 1 FROM groupbuy_participants WHERE post_id = ? AND user_id = ?",
            (post_id, uid),
        ).fetchone():
            raise HTTPException(status_code=404, detail="참여 기록을 찾을 수 없습니다.")

        # 정산이 이미 시작된 경우 취소 불가 (미납 신뢰 보호)
        settlement = conn.execute("""
            SELECT s.id FROM settlements s
            JOIN settlement_shares ss ON ss.settlement_id = s.id
            WHERE s.post_id = ? AND ss.user_id = ?
              AND s.status IN ('pending', 'completed')
            LIMIT 1
        """, (post_id, uid)).fetchone()
        if settlement:
            raise HTTPException(
                status_code=400,
                detail="정산이 진행 중이거나 완료되어 참여를 취소할 수 없습니다.",
            )

        # 취소 회원 닉네임 조회 (시스템 메시지용)
        user_row = conn.execute(
            "SELECT nickname FROM users WHERE id = ?", (uid,)
        ).fetchone()
        nickname = (user_row["nickname"] if user_row and user_row["nickname"]
                    else f"이웃{uid}")

        # ① groupbuy_participants 삭제
        conn.execute(
            "DELETE FROM groupbuy_participants WHERE post_id = ? AND user_id = ?",
            (post_id, uid),
        )

        # ② gb_current 원자적 감소
        conn.execute(
            "UPDATE posts SET gb_current = MAX(0, gb_current - 1) WHERE id = ?",
            (post_id,),
        )
        new_row = conn.execute(
            "SELECT gb_current, gb_target FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

        # ③ 그룹 채팅 퇴장: conversation_members 삭제 + 시스템 메시지 삽입
        conv = conn.execute(
            "SELECT id FROM conversations WHERE post_id = ? AND kind = 'group'",
            (post_id,),
        ).fetchone()
        if conv:
            conv_id = conv["id"]
            # conversation_members 에서 해당 사용자 제거
            conn.execute(
                "DELETE FROM conversation_members "
                "WHERE conversation_id = ? AND user_id = ?",
                (conv_id, uid),
            )
            # 시스템 메시지 삽입 — 나머지 참여자가 Group_Chat.html 폴링 시 확인 가능
            conn.execute(
                "INSERT INTO messages "
                "(conversation_id, sender_id, content, is_system, created_at) "
                "VALUES (?, ?, ?, 1, ?)",
                (conv_id, uid, f"{nickname}님이 참여를 취소하셨습니다.", to_iso(now_utc())),
            )

        conn.commit()

    return {
        "id":         post_id,
        "message":    "참여가 취소되었습니다.",
        "gb_current": new_row["gb_current"],
        "gb_target":  new_row["gb_target"],
    }


@router.post("/posts/{post_id}/join")
async def join_groupbuy(post_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT type, status, gb_target FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if not row or row["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if row["type"] != "groupbuy":
            raise HTTPException(status_code=400, detail="공동구매 게시글만 참여할 수 있습니다.")

        # 미완료된 정산(미납)이 있으면 새 공동구매 참여를 차단 (신뢰 보완)
        if settlement_db.has_unpaid_settlement(user["id"]):
            raise HTTPException(status_code=400,
                                detail="미완료된 정산이 있어 공동구매에 참여할 수 없습니다.")

        # 참여자 기록: (post_id, user_id) 복합 PK가 DB 레벨에서 중복 참여를 차단
        try:
            conn.execute(
                "INSERT INTO groupbuy_participants (post_id, user_id, joined_at) VALUES (?, ?, ?)",
                (post_id, user["id"], to_iso(now_utc())),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="이미 참여한 공동구매입니다.")

        # 원자적 UPDATE: "읽고 계산해서 쓰기" 대신 SQL 한 줄로 조건부 증가
        # (gb_target이 없으면 무제한, 있으면 정원 남았을 때만 증가)
        cur = conn.execute(
            """
            UPDATE posts
               SET gb_current = gb_current + 1
             WHERE id = ?
               AND (gb_target IS NULL OR gb_current < gb_target)
            """,
            (post_id,),
        )
        if cur.rowcount == 0:
            # 정원 초과 → 예외를 던지면 이 with 블록이 방금의 INSERT까지 통째로 롤백함
            raise HTTPException(status_code=409, detail="이미 모집이 완료되었습니다.")

        new_row = conn.execute(
            "SELECT gb_current, gb_target FROM posts WHERE id = ?", (post_id,)
        ).fetchone()

    return {"id": post_id, "gb_current": new_row["gb_current"], "gb_target": new_row["gb_target"]}