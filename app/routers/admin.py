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


# ── 대시보드 통계 (차트/분포/처리율) ─────────────────────────────────────
@router.get("/stats")
async def stats(admin: dict = Depends(get_current_admin)):
    """대시보드 시각화용 집계.
    - weekly: 최근 7일(오늘 포함) 날짜별 접수(received)/처리(handled) 수
    - reasons: 신고 사유별 건수 상위 5개 + 백분율
    - resolveRate: 최근 7일 접수분 기준 처리율(%)
    """
    with get_conn() as conn:
        # 최근 7일 날짜 축 (오래된 날 → 오늘)
        day_rows = conn.execute(
            "SELECT date('now', '-' || d || ' days') AS day "
            "FROM (SELECT 0 AS d UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 "
            "      UNION SELECT 4 UNION SELECT 5 UNION SELECT 6) ORDER BY day"
        ).fetchall()
        days = [r["day"] for r in day_rows]

        # 날짜별 접수 수 (created_at 기준)
        recv_rows = conn.execute("""
            SELECT substr(created_at,1,10) AS day, COUNT(*) AS c
            FROM reports
            WHERE substr(created_at,1,10) >= date('now','-6 days')
            GROUP BY day
        """).fetchall()
        recv = {r["day"]: r["c"] for r in recv_rows}

        # 날짜별 처리 수 (처리된 신고를 접수일 기준으로 — 별도 처리일 컬럼이 없어 접수일에 귀속)
        hand_rows = conn.execute("""
            SELECT substr(created_at,1,10) AS day, COUNT(*) AS c
            FROM reports
            WHERE status != 'pending'
              AND substr(created_at,1,10) >= date('now','-6 days')
            GROUP BY day
        """).fetchall()
        hand = {r["day"]: r["c"] for r in hand_rows}

        weekly = [
            {"day": d, "received": recv.get(d, 0), "handled": hand.get(d, 0)}
            for d in days
        ]

        # 사유 분포 (전체 기간, 상위 5)
        reason_rows = conn.execute("""
            SELECT reason, COUNT(*) AS c
            FROM reports
            GROUP BY reason
            ORDER BY c DESC
            LIMIT 5
        """).fetchall()
        reason_total = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        reasons = [
            {
                "reason": r["reason"],
                "count": r["c"],
                "percent": round(r["c"] * 100 / reason_total) if reason_total else 0,
            }
            for r in reason_rows
        ]

        # 이번 주(최근 7일) 신고 처리율
        week_total = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE substr(created_at,1,10) >= date('now','-6 days')"
        ).fetchone()[0]
        week_handled = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE status != 'pending' "
            "AND substr(created_at,1,10) >= date('now','-6 days')"
        ).fetchone()[0]
        resolve_rate = round(week_handled * 100 / week_total) if week_total else 0

    return {
        "weekly": weekly,
        "reasons": reasons,
        "resolveRate": resolve_rate,
        "weekTotal": week_total,
        "weekHandled": week_handled,
    }


# ── 회원 관리 ────────────────────────────────────────────────────────────
@router.get("/users")
async def list_users(
    q:      Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern=r"^(active|suspended)$"),
    admin:  dict = Depends(get_current_admin),
):
    """회원 목록. q로 닉네임·아이디 검색, status로 상태 필터. 각 회원의 누적 거래 수
    (tx_count: provider/receiver로 참여한 거래)와 미처리 신고 피신고 수(report_count)를
    함께 반환합니다. 필터칩 표시용 상태별 합계(counts)도 포함합니다."""
    sql = """
        SELECT u.id, u.login_id, u.nickname, u.trust_score, u.role, u.status,
               u.neighborhood, u.created_at,
               (SELECT COUNT(*) FROM transactions t
                 WHERE t.provider_id = u.id OR t.receiver_id = u.id) AS tx_count,
               (SELECT COUNT(*) FROM reports r
                 WHERE r.target_type = 'user' AND r.target_id = u.id
                   AND r.status = 'pending') AS report_count
        FROM users u
        WHERE u.status != 'withdrawn'
    """
    params = []
    if q:
        sql += " AND (u.nickname LIKE ? OR u.login_id LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if status:
        sql += " AND u.status = ?"
        params.append(status)
    sql += " ORDER BY u.id DESC LIMIT 200"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        # 필터칩용 상태별 합계 (검색어 q는 반영, 상태 필터는 제외한 전체 기준)
        cnt_sql = "SELECT status, COUNT(*) AS c FROM users WHERE status != 'withdrawn'"
        cnt_params = []
        if q:
            cnt_sql += " AND (nickname LIKE ? OR login_id LIKE ?)"
            cnt_params += [f"%{q}%", f"%{q}%"]
        cnt_sql += " GROUP BY status"
        cnt_rows = conn.execute(cnt_sql, cnt_params).fetchall()

    counts = {"active": 0, "suspended": 0}
    for r in cnt_rows:
        counts[r["status"]] = r["c"]
    counts["all"] = counts["active"] + counts["suspended"]

    return {"count": len(rows), "counts": counts, "items": [dict(r) for r in rows]}


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


@router.get("/reports/{report_id}")
async def get_report(report_id: int, admin: dict = Depends(get_current_admin)):
    """신고 단건 상세. 신고 메타 + 신고자 + 피신고 대상(회원/게시글) 정보 + 대상 누적
    신고수를 반환합니다. (증빙 이미지·처리 로그·관리자 메모는 현재 스키마 미지원으로 제외)"""
    with get_conn() as conn:
        r = conn.execute("""
            SELECT rp.*,
                   ru.nickname     AS reporter_nickname,
                   ru.trust_score  AS reporter_trust,
                   ru.neighborhood AS reporter_neighborhood
            FROM reports rp
            LEFT JOIN users ru ON ru.id = rp.reporter_id
            WHERE rp.id = ?
        """, (report_id,)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")

        report = dict(r)

        # 대상 누적 신고 수(같은 대상 전체) + 미처리 수
        report["target_report_total"] = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE target_type = ? AND target_id = ?",
            (report["target_type"], report["target_id"]),
        ).fetchone()[0]

        target = None
        if report["target_type"] == "user":
            tu = conn.execute("""
                SELECT id, nickname, login_id, trust_score, neighborhood, status, role, created_at
                FROM users WHERE id = ?
            """, (report["target_id"],)).fetchone()
            if tu:
                target = dict(tu)
        else:  # 'post'
            tp = conn.execute("""
                SELECT p.id, p.type, p.title, p.description, p.category, p.images,
                       p.status, p.created_at, p.author_id,
                       au.nickname AS author_nickname
                FROM posts p LEFT JOIN users au ON au.id = p.author_id
                WHERE p.id = ?
            """, (report["target_id"],)).fetchone()
            if tp:
                target = dict(tp)

        report["target"] = target
    return report


@router.patch("/reports/{report_id}")
async def patch_report(report_id: int, body: ReportPatch, admin: dict = Depends(get_current_admin)):
    """신고 상태를 resolved / dismissed 로 전환합니다.

    페널티 규칙 (Settlement_Implementation_Plan.md §6):
    - 기존 상태가 pending → resolved 로 확정되고
    - 신고 대상이 회원(target_type='user')인 경우에만
    - 해당 회원의 trust_score에 -2.0 페널티를 원자적으로 적용합니다.
    (dismissed 처리, 게시글 신고 처리, 이미 처리된 신고 재전환은 페널티 미적용)
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status, target_type, target_id FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")

        prev_status = row["status"]
        conn.execute("UPDATE reports SET status = ? WHERE id = ?", (body.status, report_id))

        # 주최자 귀책/먹튀 페널티: pending → resolved + 대상이 회원인 경우에만 -2.0 적용
        # (이미 resolved/dismissed → resolved 재전환 시에는 중복 적용하지 않음)
        if (prev_status == "pending"
                and body.status == "resolved"
                and row["target_type"] == "user"):
            conn.execute("""
                UPDATE users
                   SET trust_score = MAX(0.0, MIN(99.0, trust_score - 2.0))
                 WHERE id = ?
            """, (row["target_id"],))

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