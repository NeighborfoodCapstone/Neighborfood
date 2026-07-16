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
