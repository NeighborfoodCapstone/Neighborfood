from typing            import Optional
from fastapi           import APIRouter, HTTPException, Depends, Query
from app.core.deps     import get_current_user
from app.core.utils    import now_utc, to_iso
from app.db.member_db  import get_conn
from app.models.member import ChatOpen, MessageSend

router = APIRouter()


# ════════════════════════════════════════════════════════════════════════
#  공통 헬퍼
# ════════════════════════════════════════════════════════════════════════
def _get_conv_for(conn, conv_id: int, user_id: int):
    """1:1 대화방 조회 + 참여자 본인 검증."""
    conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if conv is None:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
    if user_id not in (conv["host_id"], conv["guest_id"]):
        raise HTTPException(status_code=403, detail="참여 중인 채팅방이 아닙니다.")
    return conv


def _is_group_eligible(conn, post_id: int, user_id: int) -> bool:
    """공동구매 그룹 채팅 참여 자격: 글 작성자이거나 참여자(groupbuy_participants)."""
    post = conn.execute("SELECT author_id FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post and post["author_id"] == user_id:
        return True
    row = conn.execute(
        "SELECT 1 FROM groupbuy_participants WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()
    return row is not None


def _ensure_member(conn, conv_id: int, user_id: int):
    """그룹 멤버십을 보장합니다 (없으면 추가 — lazy join)."""
    conn.execute(
        "INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, last_read_id, joined_at) "
        "VALUES (?, ?, 0, ?)",
        (conv_id, user_id, to_iso(now_utc())),
    )


def _get_group_conv_for(conn, conv_id: int, user_id: int):
    """그룹 대화방 조회 + 멤버 검증(자격 있으면 자동 가입). 그룹이 아니면 404."""
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id = ? AND kind = 'group'", (conv_id,)
    ).fetchone()
    if conv is None:
        raise HTTPException(status_code=404, detail="그룹 채팅방을 찾을 수 없습니다.")
    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id = ? AND user_id = ?",
        (conv_id, user_id),
    ).fetchone()
    if not member:
        if not _is_group_eligible(conn, conv["post_id"], user_id):
            raise HTTPException(status_code=403, detail="참여 중인 공동구매가 아닙니다.")
        _ensure_member(conn, conv_id, user_id)   # 자격이 있으면 자동 합류
    return conv


# ════════════════════════════════════════════════════════════════════════
#  1:1 채팅 (기존 동작 그대로 — kind='direct')
# ════════════════════════════════════════════════════════════════════════
@router.post("")
async def open_chat(body: ChatOpen, user: dict = Depends(get_current_user)):
    """게시글 작성자와의 1:1 채팅방을 만들거나, 이미 있으면 기존 방을 반환합니다."""
    with get_conn() as conn:
        post = conn.execute(
            "SELECT author_id, status FROM posts WHERE id = ?", (body.post_id,)
        ).fetchone()
        if not post or post["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if post["author_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="본인 게시글에는 채팅을 시작할 수 없습니다.")

        existing = conn.execute(
            "SELECT id FROM conversations WHERE post_id = ? AND guest_id = ? AND COALESCE(kind,'direct') = 'direct'",
            (body.post_id, user["id"]),
        ).fetchone()
        if existing:
            return {"conversationId": existing["id"], "created": False}

        cur = conn.execute("""
            INSERT INTO conversations (post_id, host_id, guest_id, created_at, kind)
            VALUES (?, ?, ?, ?, 'direct')
        """, (body.post_id, post["author_id"], user["id"], to_iso(now_utc())))
        conn.commit()
        return {"conversationId": cur.lastrowid, "created": True}


@router.get("")
async def my_chats(user: dict = Depends(get_current_user)):
    """내 채팅방 목록(1:1 + 그룹) + 마지막 메시지 + 안 읽은 수."""
    uid = user["id"]
    with get_conn() as conn:
        # ── 1:1 방 (기존 쿼리 + kind 필터) ──
        direct = conn.execute("""
            SELECT c.id, c.post_id, c.host_id, c.guest_id, c.created_at,
                   p.title AS post_title,
                   COALESCE(hu.nickname, '이웃' || hu.id) AS host_nickname,
                   COALESCE(gu.nickname, '이웃' || gu.id) AS guest_nickname,
                   (SELECT content    FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1)                          AS last_message,
                   (SELECT created_at FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1)                          AS last_message_at,
                   (SELECT COUNT(*)   FROM messages m WHERE m.conversation_id = c.id
                    AND m.sender_id != ? AND m.read_at IS NULL)          AS unread_count
            FROM   conversations c
            JOIN   posts p  ON p.id  = c.post_id
            LEFT JOIN users hu ON hu.id = c.host_id
            LEFT JOIN users gu ON gu.id = c.guest_id
            WHERE  COALESCE(c.kind,'direct') = 'direct' AND (c.host_id = ? OR c.guest_id = ?)
        """, (uid, uid, uid)).fetchall()

        # ── 그룹 방 (내가 멤버인 것) ──
        group = conn.execute("""
            SELECT c.id, c.post_id, c.created_at,
                   p.title AS post_title,
                   (SELECT content    FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1)                          AS last_message,
                   (SELECT created_at FROM messages m WHERE m.conversation_id = c.id
                    ORDER BY m.id DESC LIMIT 1)                          AS last_message_at,
                   (SELECT COUNT(*)   FROM messages m WHERE m.conversation_id = c.id
                    AND m.id > cm.last_read_id AND m.sender_id != ?)     AS unread_count,
                   (SELECT COUNT(*)   FROM conversation_members x
                    WHERE x.conversation_id = c.id)                      AS member_count
            FROM   conversation_members cm
            JOIN   conversations c ON c.id = cm.conversation_id AND c.kind = 'group'
            JOIN   posts p ON p.id = c.post_id
            WHERE  cm.user_id = ?
        """, (uid, uid)).fetchall()

    items = []
    for r in direct:
        it = dict(r)
        it["kind"] = "direct"
        it["partnerNickname"] = (it["guest_nickname"] if it["host_id"] == uid else it["host_nickname"])
        items.append(it)
    for r in group:
        it = dict(r)
        it["kind"] = "group"
        it["partnerNickname"] = "공동구매 · " + (it.get("post_title") or "")
        items.append(it)

    # 최근 메시지(없으면 생성시각) 기준 내림차순 정렬
    items.sort(key=lambda x: (x.get("last_message_at") or x.get("created_at") or ""), reverse=True)
    return {"count": len(items), "items": items}


@router.get("/{conv_id}/messages")
async def get_messages(
    conv_id: int,
    after_id: Optional[int] = Query(None, description="이 메시지 ID 이후만 조회(폴링용)"),
    user: dict = Depends(get_current_user),
):
    """1:1 메시지 조회. 상대가 보낸 메시지는 읽음 처리됩니다."""
    with get_conn() as conn:
        _get_conv_for(conn, conv_id, user["id"])
        sql, params = "SELECT * FROM messages WHERE conversation_id = ?", [conv_id]
        if after_id is not None:
            sql += " AND id > ?"; params.append(after_id)
        sql += " ORDER BY id ASC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        conn.execute("""
            UPDATE messages SET read_at = ?
            WHERE conversation_id = ? AND sender_id != ? AND read_at IS NULL
        """, (to_iso(now_utc()), conv_id, user["id"]))
        conn.commit()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.post("/{conv_id}/messages")
async def send_message(conv_id: int, body: MessageSend,
                       user: dict = Depends(get_current_user)):
    """1:1 메시지 전송."""
    with get_conn() as conn:
        _get_conv_for(conn, conv_id, user["id"])
        cur = conn.execute("""
            INSERT INTO messages (conversation_id, sender_id, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (conv_id, user["id"], body.content, to_iso(now_utc())))
        conn.commit()
    return {"messageId": cur.lastrowid, "message": "전송되었습니다."}


# ════════════════════════════════════════════════════════════════════════
#  그룹(공동구매) 채팅 — 신규
# ════════════════════════════════════════════════════════════════════════
@router.post("/group/{post_id}")
async def open_group_chat(post_id: int, user: dict = Depends(get_current_user)):
    """공동구매 게시글의 그룹 채팅방을 만들거나(글당 1개) 기존 방을 반환하고, 나를 멤버로 추가합니다."""
    with get_conn() as conn:
        post = conn.execute(
            "SELECT author_id, type, status FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        if not post or post["status"] == "deleted":
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if post["type"] != "groupbuy":
            raise HTTPException(status_code=400, detail="공동구매 게시글만 그룹 채팅을 사용할 수 있습니다.")
        if not _is_group_eligible(conn, post_id, user["id"]):
            raise HTTPException(status_code=403, detail="공동구매에 참여한 뒤 이용할 수 있습니다.")

        conv = conn.execute(
            "SELECT id FROM conversations WHERE post_id = ? AND kind = 'group'", (post_id,)
        ).fetchone()
        created = False
        if conv:
            conv_id = conv["id"]
        else:
            # 그룹 방은 host_id=guest_id=작성자 (guest_id NOT NULL 제약 우회), 멤버십은 별도 테이블로 관리
            cur = conn.execute("""
                INSERT INTO conversations (post_id, host_id, guest_id, created_at, kind)
                VALUES (?, ?, ?, ?, 'group')
            """, (post_id, post["author_id"], post["author_id"], to_iso(now_utc())))
            conv_id = cur.lastrowid
            created = True
            _ensure_member(conn, conv_id, post["author_id"])  # 작성자 자동 멤버
        _ensure_member(conn, conv_id, user["id"])
        conn.commit()
    return {"conversationId": conv_id, "created": created}


@router.get("/group/{conv_id}/messages")
async def get_group_messages(
    conv_id: int,
    after_id: Optional[int] = Query(None),
    user: dict = Depends(get_current_user),
):
    """그룹 메시지 조회(발신자 닉네임 포함). 내 last_read_id를 최신으로 갱신."""
    with get_conn() as conn:
        _get_group_conv_for(conn, conv_id, user["id"])
        sql = """
            SELECT m.*, COALESCE(u.nickname, '이웃' || u.id) AS sender_nickname
            FROM messages m LEFT JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_id = ?
        """
        params = [conv_id]
        if after_id is not None:
            sql += " AND m.id > ?"; params.append(after_id)
        sql += " ORDER BY m.id ASC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        # 내 읽음 포인터를 방의 최신 메시지로 이동
        conn.execute("""
            UPDATE conversation_members
            SET last_read_id = (SELECT COALESCE(MAX(id),0) FROM messages WHERE conversation_id = ?)
            WHERE conversation_id = ? AND user_id = ?
        """, (conv_id, conv_id, user["id"]))
        conn.commit()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.post("/group/{conv_id}/messages")
async def send_group_message(conv_id: int, body: MessageSend,
                             user: dict = Depends(get_current_user)):
    """그룹 메시지 전송."""
    with get_conn() as conn:
        _get_group_conv_for(conn, conv_id, user["id"])
        cur = conn.execute("""
            INSERT INTO messages (conversation_id, sender_id, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (conv_id, user["id"], body.content, to_iso(now_utc())))
        conn.commit()
    return {"messageId": cur.lastrowid, "message": "전송되었습니다."}


@router.get("/group/{conv_id}/members")
async def get_group_members(conv_id: int, user: dict = Depends(get_current_user)):
    """그룹 참여자 목록(헤더의 '참여자 N명' 표시용)."""
    with get_conn() as conn:
        conv = _get_group_conv_for(conn, conv_id, user["id"])
        rows = conn.execute("""
            SELECT cm.user_id, COALESCE(u.nickname, '이웃' || u.id) AS nickname,
                   (cm.user_id = ?) AS is_host
            FROM conversation_members cm
            LEFT JOIN users u ON u.id = cm.user_id
            WHERE cm.conversation_id = ?
            ORDER BY cm.joined_at ASC
        """, (conv["host_id"], conv_id)).fetchall()
        post = conn.execute("SELECT title FROM posts WHERE id = ?", (conv["post_id"],)).fetchone()
    members = [dict(r) for r in rows]
    return {"count": len(members), "title": (post["title"] if post else ""), "members": members}
