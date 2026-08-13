from fastapi          import APIRouter, HTTPException, Depends
from pydantic         import BaseModel, Field
from app.core.deps    import get_current_user
from app.core.utils   import now_utc, to_iso
from app.db.admin_db  import get_conn

router = APIRouter()


class ReportCreate(BaseModel):
    target_type: str = Field(..., pattern=r"^(post|user)$")
    target_id:   int
    reason:      str = Field(..., min_length=1, max_length=500)


@router.post("")
async def submit_report(body: ReportCreate, user: dict = Depends(get_current_user)):
    """게시글/회원 신고 제출 (로그인 회원). 관리자가 Admin_Report_Detail 에서 처리."""
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO reports (reporter_id, target_type, target_id, reason, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (user["id"], body.target_type, body.target_id, body.reason, to_iso(now_utc())))
        conn.commit()
    return {"reportId": cur.lastrowid, "message": "신고가 접수되었습니다."}


@router.get("/my")
async def my_reports(user: dict = Depends(get_current_user)):
    """내가 제출한 신고 목록 (최근 50건)."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, target_type, target_id, reason, status, created_at
              FROM reports
             WHERE reporter_id = ?
             ORDER BY datetime(created_at) DESC
             LIMIT 50
        """, (user["id"],)).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.delete("/{report_id}")
async def cancel_report(report_id: int, user: dict = Depends(get_current_user)):
    """내 신고 취소 — 본인이 제출했고 아직 pending 상태인 것만 가능.
    관리자가 처리 중(resolved/rejected)인 신고는 취소 불가."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT reporter_id, status FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")
        if row["reporter_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="본인이 제출한 신고만 취소할 수 있습니다.")
        if row["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="이미 처리된 신고는 취소할 수 없습니다."
            )
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
    return {"ok": True, "reportId": report_id, "deleted": True}