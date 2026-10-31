"""
settlements.py — 공동구매 정산 API

신뢰 기반 납부 추적 + 자동화 보완(GPS/QR):
  - 주최자(글 작성자)가 총 금액 입력 → 참여자별 분담 자동 생성
  - 참여자는 외부(카카오페이 등)로 송금 후 '납부했어요' 표시
  - QR 인증(품질 동의) 완료 시 납부 가능
  - GPS 인증 + 24h 경과 시 자동 납부 확인
  - 노쇼 신고 시 trust_score 페널티 + reports 자동 기록
  - 노쇼 취소(철회) 시 share→unpaid 복원 + trust_score +1.0 복원 + 신고 삭제
"""
from typing import Optional, List, Dict

from fastapi   import APIRouter, HTTPException, Depends
from pydantic  import BaseModel, Field

from app.core.deps  import get_current_user
from app.core.utils import now_utc, to_iso, from_iso
from app.core.demo_spot import is_demo_title, SPOT_ADDRESS, SPOT_LAT, SPOT_LNG
from app.db.transaction_db import get_conn
from app.db import settlement_db as sdb, trade_verification as tv

router = APIRouter()

# trust_score 변동폭
_NOSHOW_PENALTY  = 1.0   # 노쇼 신고 시 감소
_NOSHOW_RESTORE  = 1.0   # 노쇼 취소(철회) 시 복원
_TRUST_MIN = 0.0
_TRUST_MAX = 99.0

# 노쇼 신고 자동 생성 reason 포맷 (취소 시 삭제 기준으로도 사용)
def _noshow_reason(settlement_id: int) -> str:
    return f"공동구매 정산 노쇼 신고 (settlement #{settlement_id})"


class SettlementCreate(BaseModel):
    post_id:      int
    total_amount: int = Field(..., gt=0, description="정산 총 금액(원)")
    account_info: Optional[str] = Field(None, description="주최자 계좌 정보(표시용)")


def _nickname_map(conn, user_ids: List[int]) -> Dict[int, str]:
    if not user_ids:
        return {}
    q = ",".join("?" * len(user_ids))
    rows = conn.execute(
        f"SELECT id, nickname FROM users WHERE id IN ({q})", user_ids
    ).fetchall()
    return {r["id"]: r["nickname"] for r in rows}


def _load_and_authorize(settlement_id: int, user: dict, *, require_requester=False):
    """정산을 로드하고 접근 권한을 확인합니다.
    관련자(주최자 또는 분담 참여자)만 접근 가능.
    require_requester=True 이면 주최자 본인만."""
    s = sdb.get_settlement(settlement_id)
    if not s:
        raise HTTPException(404, "정산을 찾을 수 없습니다.")

    uid = user["id"]
    is_requester = (s["requester_id"] == uid)
    share = sdb.get_share(settlement_id, uid)

    if require_requester:
        if not is_requester and user.get("role") != "admin":
            raise HTTPException(403, "정산 주최자만 할 수 있습니다.")
    else:
        if not is_requester and share is None and user.get("role") != "admin":
            raise HTTPException(403, "이 정산에 접근할 권한이 없습니다.")
    return s, is_requester, share


def _serialize_full(s: dict) -> dict:
    shares = sdb.list_shares(s["id"])
    with get_conn() as conn:
        nmap = _nickname_map(conn, [sh["user_id"] for sh in shares])
    return sdb.serialize(s, shares, nmap)


@router.post("")
async def create_settlement(body: SettlementCreate, user: dict = Depends(get_current_user)):
    """정산 생성 — 주최자(글 작성자)만. 참여자별 분담 자동 생성."""
    uid = user["id"]
    with get_conn() as conn:
        post = conn.execute(
            "SELECT author_id, type, status FROM posts WHERE id = ?", (body.post_id,)
        ).fetchone()
        if not post or post["status"] == "deleted":
            raise HTTPException(404, "게시글을 찾을 수 없습니다.")
        if post["author_id"] != uid:
            raise HTTPException(403, "게시글 작성자만 정산을 시작할 수 있습니다.")

        # 이미 진행 중/완료된 정산이 있으면 중복 생성 차단
        dup = conn.execute(
            "SELECT id FROM settlements WHERE post_id = ? AND status IN ('pending','completed')",
            (body.post_id,),
        ).fetchone()
        if dup:
            raise HTTPException(409, "이미 이 게시글에 정산이 있습니다.")

        # 참여자 목록 (주최자 제외)
        parts = conn.execute(
            "SELECT user_id FROM groupbuy_participants WHERE post_id = ? AND user_id != ?",
            (body.post_id, uid),
        ).fetchall()
        participant_ids = [p["user_id"] for p in parts]

    if not participant_ids:
        raise HTTPException(400, "정산할 참여자가 없습니다.")

    try:
        s = sdb.create_settlement(body.post_id, uid, body.total_amount,
                                  body.account_info, participant_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"ok": True, "settlement": _serialize_full(s)}


@router.get("/my")
async def my_settlements(user: dict = Depends(get_current_user)):
    """내가 주최했거나 분담이 있는 정산 목록."""
    uid = user["id"]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT s.* FROM settlements s
            LEFT JOIN settlement_shares ss ON ss.settlement_id = s.id
            WHERE s.requester_id = ? OR ss.user_id = ?
            ORDER BY s.id DESC
        """, (uid, uid)).fetchall()
        items = []
        for row in rows:
            s = dict(row)
            shares = sdb.list_shares(s["id"])
            nmap = _nickname_map(conn, [sh["user_id"] for sh in shares])
            items.append(sdb.serialize(s, shares, nmap))
    return {"ok": True, "items": items}


@router.get("/post/{post_id}")
async def get_by_post(post_id: int, user: dict = Depends(get_current_user)):
    """게시글 기준 정산 조회. 없으면 404."""
    s = sdb.get_settlement_by_post(post_id)
    if not s:
        raise HTTPException(404, "이 게시글에는 정산이 없습니다.")
    _load_and_authorize(s["id"], user)  # 권한 확인
    return {"ok": True, "settlement": _serialize_full(s)}


@router.get("/{settlement_id}")
async def get_detail(settlement_id: int, user: dict = Depends(get_current_user)):
    """정산 상세."""
    s = sdb.get_settlement(settlement_id)
    if not s:
        raise HTTPException(404, "정산을 찾을 수 없습니다.")
    _load_and_authorize(settlement_id, user)
    return {"ok": True, "settlement": _serialize_full(s)}


@router.get("/{settlement_id}/participants/gps-status")
async def participants_gps_status(settlement_id: int,
                                  user: dict = Depends(get_current_user)):
    """참여자별 GPS 인증 현황 — 주최자 전용.

    각 참여자의 GPS 인증 여부·거리·인증시각을 반환합니다(5초 폴링용).
    개인 좌표는 노출하지 않고 거리(distanceM)만 제공합니다.
    """
    _load_and_authorize(settlement_id, user, require_requester=True)
    details = sdb.get_participant_gps_details(settlement_id)
    verified = sum(1 for d in details if d["gpsVerified"])
    return {
        "ok": True,
        "settlementId": settlement_id,
        "verifiedCount": verified,
        "participantCount": len(details),
        "participants": details,
    }


@router.post("/{settlement_id}/shares/me/pay")
async def pay_my_share(settlement_id: int, user: dict = Depends(get_current_user)):
    """Record payment only for this settlement's verified participant."""
    with get_conn() as conn:
        tv.begin(conn)
        settlement = tv.lock_row(conn, "settlements", settlement_id)
        if not settlement:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, user["id"])).fetchone()
        if not share:
            raise HTTPException(403, "이 정산의 분담 대상이 아닙니다.")
        if settlement["status"] != "pending":
            raise HTTPException(400, "진행 중인 정산이 아닙니다.")
        if share["status"] == "paid":
            raise HTTPException(409, "이미 납부 처리되었습니다.")
        if share["status"] != "unpaid":
            raise HTTPException(400, "노쇼 처리된 분담은 납부할 수 없습니다.")
        evidence = conn.execute("""SELECT id FROM qr_sessions WHERE settlement_id = ? AND subject_id = ?
            AND scanner_id = ? AND status = 'VERIFIED' AND used_at IS NOT NULL LIMIT 1""",
            (settlement_id, str(user["id"]), settlement["requester_id"])).fetchone()
        if not share["gps_verified"] or not share["quality_agreed"] or not evidence:
            raise HTTPException(400, "이 정산의 GPS와 주최자 QR 인증을 먼저 완료해 주세요.")
        conn.execute("""UPDATE settlement_shares SET status = 'paid', paid_at = ?
                        WHERE settlement_id = ? AND user_id = ? AND status = 'unpaid'""",
                     (to_iso(now_utc()), settlement_id, user["id"]))
        conn.commit()
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.post("/{settlement_id}/complete")
async def complete(settlement_id: int, user: dict = Depends(get_current_user)):
    """Complete settlement and create its transaction records in one DB transaction."""
    with get_conn() as conn:
        tv.begin(conn)
        settlement = tv.lock_row(conn, "settlements", settlement_id)
        if not settlement:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        if settlement["requester_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(403, "정산 주최자만 할 수 있습니다.")
        if settlement["status"] != "pending":
            raise HTTPException(400, "이미 완료되었거나 취소된 정산입니다.")
        shares = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ?", (settlement_id,)).fetchall()
        if not shares:
            raise HTTPException(400, "분담 대상이 없습니다.")
        if any(share["status"] == "unpaid" for share in shares):
            raise HTTPException(400, "아직 미납 참여자가 있어요.")
        now = to_iso(now_utc())
        for share in shares:
            if share["status"] != "paid":
                continue
            qr = conn.execute("""SELECT id FROM qr_sessions WHERE settlement_id = ? AND subject_id = ?
                AND scanner_id = ? AND status = 'VERIFIED' AND used_at IS NOT NULL
                ORDER BY used_at DESC LIMIT 1""",
                (settlement_id, str(share["user_id"]), settlement["requester_id"])).fetchone()
            if not qr or not share["gps_verified"] or not share["quality_agreed"]:
                raise HTTPException(409, "정산에 연결된 인증 기록이 없습니다. 해당 참여자가 GPS와 QR을 다시 인증해 주세요.")
            conn.execute("""INSERT INTO transactions
                (post_id, provider_id, receiver_id, status, settlement_id, qr_session_id,
                 appointment_at, completed_at, created_at)
                VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?)""",
                (settlement["post_id"], settlement["requester_id"], share["user_id"], settlement_id,
                 qr["id"], settlement["appointment_at"], now, now))
        conn.execute("UPDATE settlements SET status = 'completed', completed_at = ? WHERE id = ? AND status = 'pending'",
                     (now, settlement_id))
        conn.commit()
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.post("/{settlement_id}/cancel")
async def cancel(settlement_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        tv.begin(conn)
        settlement = tv.lock_row(conn, "settlements", settlement_id)
        if not settlement:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        if settlement["requester_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(403, "정산 주최자만 할 수 있습니다.")
        if settlement["status"] != "pending":
            raise HTTPException(400, "이미 완료되었거나 취소된 정산입니다.")
        conn.execute("UPDATE settlements SET status = 'canceled' WHERE id = ? AND status = 'pending'", (settlement_id,))
        conn.commit()
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.post("/{settlement_id}/shares/{target_user_id}/noshow")
async def report_noshow(settlement_id: int, target_user_id: int,
                        user: dict = Depends(get_current_user)):
    """참여자 노쇼 신고 — 주최자만. trust_score 페널티 + reports 자동 기록."""

    now = to_iso(now_utc())
    with get_conn() as conn:
        tv.begin(conn)
        s = tv.lock_row(conn, "settlements", settlement_id)
        if not s:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        if s["requester_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(403, "정산 주최자만 할 수 있습니다.")
        if s["status"] != "pending":
            raise HTTPException(400, "진행 중인 정산이 아닙니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, target_user_id)).fetchone()
        if not share:
            raise HTTPException(404, "해당 참여자의 분담을 찾을 수 없습니다.")
        if share["status"] == "noshow":
            raise HTTPException(409, "이미 노쇼 처리된 참여자입니다.")
        if share["status"] != "unpaid":
            raise HTTPException(400, "납부된 분담은 노쇼 처리할 수 없습니다.")
        # 노쇼 처리 + trust_score 페널티 + 신고 자동 기록 (같은 트랜잭션)
        conn.execute("""
            UPDATE settlement_shares SET status = 'noshow'
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, target_user_id))
        conn.execute("""
            UPDATE users
               SET trust_score = MAX(?, MIN(?, trust_score - ?))
             WHERE id = ?
        """, (_TRUST_MIN, _TRUST_MAX, _NOSHOW_PENALTY, target_user_id))
        conn.execute("""
            INSERT INTO reports (reporter_id, target_type, target_id, reason, status, created_at)
            VALUES (?, 'user', ?, ?, 'pending', ?)
        """, (user["id"], target_user_id, _noshow_reason(settlement_id), now))
        conn.commit()

    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.delete("/{settlement_id}/shares/{target_user_id}/noshow")
async def cancel_noshow(settlement_id: int, target_user_id: int,
                        user: dict = Depends(get_current_user)):
    """노쇼 취소(철회) — 주최자만.

    share.status → unpaid 복원 / trust_score +1.0 복원 / 자동 기록된 신고 삭제.
    이미 완료·취소된 정산이거나 share가 noshow 상태가 아니면 거부.
    """

    with get_conn() as conn:
        tv.begin(conn)
        s = tv.lock_row(conn, "settlements", settlement_id)
        if not s:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        if s["requester_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(403, "정산 주최자만 할 수 있습니다.")
        if s["status"] != "pending":
            raise HTTPException(400, "진행 중인 정산에서만 노쇼 취소가 가능합니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, target_user_id)).fetchone()
        if not share:
            raise HTTPException(404, "해당 참여자의 분담을 찾을 수 없습니다.")
        if share["status"] != "noshow":
            raise HTTPException(400, "노쇼 상태인 분담만 취소할 수 있습니다.")
        # 1) share → unpaid 복원 (paid_at 초기화)
        conn.execute("""
            UPDATE settlement_shares
               SET status = 'unpaid', paid_at = NULL
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, target_user_id))

        # 2) trust_score +1.0 복원 (원자적, 클램프 0~99)
        conn.execute("""
            UPDATE users
               SET trust_score = MAX(?, MIN(?, trust_score + ?))
             WHERE id = ?
        """, (_TRUST_MIN, _TRUST_MAX, _NOSHOW_RESTORE, target_user_id))

        # 3) 자동 생성된 노쇼 신고 삭제 (pending 상태인 것만 — 관리자가 이미 처리한 경우 보존)
        conn.execute("""
            DELETE FROM reports
             WHERE target_type = 'user'
               AND target_id   = ?
               AND reporter_id = ?
               AND reason      = ?
               AND status      = 'pending'
        """, (target_user_id, s["requester_id"], _noshow_reason(settlement_id)))

        conn.commit()

    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}

# ════════════════════════════════════════════════════════════════════════════
#  거래 확정(약속) → GPS 인증 → QR 인증  (채팅→GPS→QR→납부 흐름)
# ════════════════════════════════════════════════════════════════════════════

class AppointmentBody(BaseModel):
    place:          Optional[str]   = Field(None, description="거래 약속 장소 (텍스트)")
    appointment_at: Optional[str]   = Field(None, description="거래 약속 일시(ISO-8601)")
    lat:            Optional[float] = Field(None, description="약속 장소 위도 — 참여자 GPS 100m 검증 기준")
    lng:            Optional[float] = Field(None, description="약속 장소 경도 — 참여자 GPS 100m 검증 기준")

class SettlementGpsBody(BaseModel):
    locationSessionId: str


@router.post("/{settlement_id}/appointment")
async def set_appointment(settlement_id: int, body: AppointmentBody,
                          user: dict = Depends(get_current_user)):
    """거래 약속 장소·시간·좌표 확정 — 주최자만.

    lat/lng 를 함께 전송하면 참여자 GPS 인증 시 이 좌표를 기준으로
    100m 이내 여부를 서버에서 실제 검증합니다.
    """
    s, _, _ = _load_and_authorize(settlement_id, user, require_requester=True)
    if s["status"] != "pending":
        raise HTTPException(400, "진행 중인 정산에서만 약속을 정할 수 있습니다.")
    if not (body.place or body.appointment_at):
        raise HTTPException(400, "약속 장소 또는 시간을 입력해 주세요.")
    with get_conn() as conn:
        _post = conn.execute("SELECT title FROM posts WHERE id = ?", (s["post_id"],)).fetchone()
    if _post and is_demo_title(_post["title"]):
        # 체험 거래는 만남 장소가 호천관으로 고정되어 있고 일시만 정할 수 있습니다.
        body.place, body.lat, body.lng = SPOT_ADDRESS, SPOT_LAT, SPOT_LNG
    try:
        sdb.set_appointment(settlement_id, body.place, body.appointment_at, body.lat, body.lng)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.post("/{settlement_id}/shares/me/gps-done")
async def gps_done(settlement_id: int, body: SettlementGpsBody, user: dict = Depends(get_current_user)):
    """Bind this participant's recent GPS reading to this settlement."""
    with get_conn() as conn:
        tv.begin(conn)
        settlement = tv.lock_row(conn, "settlements", settlement_id)
        if not settlement:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, user["id"])).fetchone()
        if not share:
            raise HTTPException(403, "이 정산의 분담 대상이 아닙니다.")
        if settlement["status"] != "pending" or share["status"] not in ("unpaid", "paid"):
            raise HTTPException(409, "진행 중인 정산의 참여자만 인증할 수 있습니다.")
        session = tv.lock_row(conn, "location_verify_sessions", body.locationSessionId)
        if not session or session["subject_id"] != str(user["id"]):
            raise HTTPException(403, "본인의 GPS 인증 기록이 필요합니다.")
        if session["transaction_id"] is not None or session["settlement_id"] not in (None, settlement_id):
            raise HTTPException(409, "다른 거래에 사용한 위치 인증입니다.")
        if (session["status"] not in ("LOCATION_VERIFIED", "QR_ISSUED", "QR_VERIFIED")
                or not session["verified_at"] or from_iso(session["verified_at"]) < now_utc() - tv.GPS_MAX_AGE):
            raise HTTPException(400, "최근 GPS 인증을 다시 진행해 주세요.")
        distance = tv.assert_location(session["current_lat"], session["current_lng"], session["current_accuracy"],
                                      settlement["appointment_lat"], settlement["appointment_lng"])
        conn.execute("""UPDATE location_verify_sessions
                        SET settlement_id = ?, target_lat = ?, target_lng = ?, distance_m = ?, radius_m = ?
                        WHERE id = ?""", (settlement_id, settlement["appointment_lat"], settlement["appointment_lng"],
                                         distance, tv.GPS_RADIUS_M, body.locationSessionId))
        conn.execute("UPDATE settlement_shares SET gps_verified = 1 WHERE settlement_id = ? AND user_id = ?",
                     (settlement_id, user["id"]))
        conn.commit()
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}


@router.post("/{settlement_id}/shares/me/qr-done")
async def qr_done(settlement_id: int, user: dict = Depends(get_current_user)):
    """Confirm the organizer scanned this participant's QR for this settlement."""
    with get_conn() as conn:
        settlement = conn.execute("SELECT * FROM settlements WHERE id = ?", (settlement_id,)).fetchone()
        if not settlement:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, user["id"])).fetchone()
        if not share:
            raise HTTPException(403, "이 정산의 분담 대상이 아닙니다.")
        if settlement["status"] != "pending" or share["status"] not in ("unpaid", "paid"):
            raise HTTPException(409, "진행 중인 정산이 아닙니다.")
        evidence = conn.execute("""SELECT id FROM qr_sessions WHERE settlement_id = ? AND subject_id = ?
            AND scanner_id = ? AND status = 'VERIFIED' AND used_at IS NOT NULL LIMIT 1""",
            (settlement_id, str(user["id"]), settlement["requester_id"])).fetchone()
        if not share["gps_verified"] or not share["quality_agreed"] or not evidence:
            raise HTTPException(400, "주최자가 이 정산의 QR을 스캔해야 합니다.")
    return {"ok": True, "settlement": _serialize_full(sdb.get_settlement(settlement_id))}