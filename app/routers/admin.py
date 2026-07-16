from typing            import Optional
from fastapi           import APIRouter, HTTPException, Depends, Query
from pydantic          import BaseModel, Field
from app.core.deps     import get_current_admin
from app.core.utils    import now_utc, to_iso
from app.db.admin_db   import get_conn

router = APIRouter()


class NoticeCreate(BaseModel):
    title:   str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=4000)

class UserPatch(BaseModel):
    role:   Optional[str] = Field(None, pattern=r"^(user|admin)$")
    status: Optional[str] = Field(None, pattern=r"^(active|suspended)$")

class ReportPatch(BaseModel):
    status: str = Field(..., pattern=r"^(resolved|dismissed)$")


# ── 대시보드 요약 ────────────────────────────────────────────────────────
@router.get("/dashboard")
async def dashboard(admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        q = lambda sql: conn.execute(sql).fetchone()[0]
        return {
            "users":         q("SELECT COUNT(*) FROM users WHERE status != 'withdrawn'"),
            "posts":         q("SELECT COUNT(*) FROM posts WHERE status != 'deleted'"),
            "transactions":  q("SELECT COUNT(*) FROM transactions"),
            "reportsPending":q("SELECT COUNT(*) FROM reports WHERE status = 'pending'"),
            "todaySignups":  q("SELECT COUNT(*) FROM users WHERE status != 'withdrawn' AND substr(created_at,1,10) = date('now')"),
            "ongoingTransactions": q("SELECT COUNT(*) FROM transactions WHERE status IN ('pending','confirmed')"),
        }


# ── 회원 관리 ────────────────────────────────────────────────────────────
@router.get("/users")
async def list_users(q: Optional[str] = Query(None), admin: dict = Depends(get_current_admin)):
    sql = ("SELECT id, login_id, nickname, trust_score, role, status, created_at "
           "FROM users WHERE status != 'withdrawn'")
    params = []
    if q:
        sql += " AND (nickname LIKE ? OR login_id LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY id DESC LIMIT 200"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.patch("/users/{user_id}")
async def patch_user(user_id: int, body: UserPatch, admin: dict = Depends(get_current_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="본인 계정의 권한·상태는 변경할 수 없습니다.")
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="변경할 항목이 없습니다.")
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
        sets = ", ".join(f"{k} = ?" for k in fields)            # 키는 화이트리스트(role/status)
        conn.execute(f"UPDATE users SET {sets}, updated_at = ? WHERE id = ?",
                     list(fields.values()) + [to_iso(now_utc()), user_id])
        conn.commit()
        row = conn.execute("SELECT id, login_id, nickname, role, status FROM users WHERE id = ?",
                           (user_id,)).fetchone()
    return dict(row)


# ── 공지 ────────────────────────────────────────────────────────────────
@router.get("/notices")
async def list_notices(admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT n.*, COALESCE(u.nickname, '관리자') AS author_nickname
            FROM notices n LEFT JOIN users u ON u.id = n.author_id
            ORDER BY n.id DESC LIMIT 200
        """).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.post("/notices")
async def create_notice(body: NoticeCreate, admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO notices (author_id, title, content, created_at) VALUES (?, ?, ?, ?)",
                           (admin["id"], body.title, body.content, to_iso(now_utc())))
        conn.commit()
    return {"noticeId": cur.lastrowid}


@router.delete("/notices/{notice_id}")
async def delete_notice(notice_id: int, admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        conn.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
        conn.commit()
    return {"noticeId": notice_id, "deleted": True}


# ── 신고 처리 ────────────────────────────────────────────────────────────
@router.get("/reports")
async def list_reports(status: Optional[str] = Query(None), admin: dict = Depends(get_current_admin)):
    sql = """
        SELECT r.*, COALESCE(u.nickname, '이웃' || u.id) AS reporter_nickname,
               CASE r.target_type
                    WHEN 'post' THEN (SELECT title FROM posts WHERE id = r.target_id)
                    WHEN 'user' THEN (SELECT nickname FROM users WHERE id = r.target_id)
               END AS target_label
        FROM reports r LEFT JOIN users u ON u.id = r.reporter_id
    """
    params = []
    if status:
        sql += " WHERE r.status = ?"; params.append(status)
    sql += " ORDER BY (r.status='pending') DESC, r.id DESC LIMIT 200"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.patch("/reports/{report_id}")
async def patch_report(report_id: int, body: ReportPatch, admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM reports WHERE id = ?", (report_id,)).fetchone():
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")
        conn.execute("UPDATE reports SET status = ? WHERE id = ?", (body.status, report_id))
        conn.commit()
    return {"reportId": report_id, "status": body.status}


# ── 채팅 모니터링 (신고 처리용) ──────────────────────────────────────────
@router.get("/chats")
async def list_chats(admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT c.id, c.kind, c.post_id, p.title AS post_title,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
                   (SELECT created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_at
            FROM conversations c LEFT JOIN posts p ON p.id = c.post_id
            ORDER BY c.id DESC LIMIT 200
        """).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.get("/chats/{conv_id}/messages")
async def chat_messages(conv_id: int, admin: dict = Depends(get_current_admin)):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT m.*, COALESCE(u.nickname, '이웃' || u.id) AS sender_nickname
            FROM messages m LEFT JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_id = ? ORDER BY m.id ASC LIMIT 500
        """, (conv_id,)).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}