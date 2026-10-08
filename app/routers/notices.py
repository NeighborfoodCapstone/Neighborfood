from fastapi         import APIRouter, Query
from app.db.admin_db import get_conn

router = APIRouter()


@router.get("")
async def public_notices(limit: int = Query(10, ge=1, le=50)):
    """공개 공지 목록(로그인 불필요, 최신순). 관리자가 등록한 notices 를 도움말 화면에서 읽습니다.
    작성자 정보는 노출하지 않습니다."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM notices ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"count": len(rows), "items": [dict(r) for r in rows]}
