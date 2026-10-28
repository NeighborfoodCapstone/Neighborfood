"""
settlement_db.py — 정산(Settlements) DB 레이어

정산 헤더(settlements) + 참여자별 분담(settlement_shares) CRUD.
transactions와 같은 DB 파일(neighborfood.db)을 사용합니다.

신뢰 모델 (순차 2단계 인증):
  - 앱은 자금을 보관/이동하지 않고 납부 상태만 추적한다.
  - Step 1) gps_verified : 거래 지점 GPS 인증(LOCATION_VERIFIED) 완료 시 1
  - Step 2) quality_agreed : 대면 QR 인증 완료 시 1
  - 두 단계가 모두 1이어야 참여자의 '납부했어요' 버튼이 활성화된다.
  - 주최자는 약속 장소·시간(appointment_place / appointment_at)을 확정한다.
"""
from typing import Any, Dict, List, Optional

from app.core.utils import now_utc, to_iso
from app.db.transaction_db import get_conn
from app.db import trade_verification as tv


# ── 스키마 마이그레이션 (멱등, 안전망) ────────────────────────────────────────
#   컬럼 추가는 transaction_db.init_transaction_db() 에서 주로 처리하지만,
#   임포트 시점에 한 번 더 보정해 구버전 DB에서도 함수가 안전하게 동작하도록 한다.

def init_settlement_extension() -> None:
    """정산 흐름 확장 컬럼을 멱등적으로 추가한다."""
    with get_conn() as conn:
        s_cols = [r[1] for r in conn.execute("PRAGMA table_info(settlements)").fetchall()]
        if "appointment_at" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_at TEXT")
        if "appointment_place" not in s_cols:
            conn.execute("ALTER TABLE settlements ADD COLUMN appointment_place TEXT")

        sh_cols = [r[1] for r in conn.execute("PRAGMA table_info(settlement_shares)").fetchall()]
        if "gps_verified" not in sh_cols:
            conn.execute("ALTER TABLE settlement_shares ADD COLUMN gps_verified INTEGER NOT NULL DEFAULT 0")
        conn.commit()


try:
    init_settlement_extension()
except Exception:
    # 테이블이 아직 없으면(최초 부팅 순서) 조용히 넘어가고, 이후 호출 시 재시도된다.
    pass


# ── 조회 헬퍼 ────────────────────────────────────────────────────────────────

def get_settlement(settlement_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM settlements WHERE id = ?", (settlement_id,)
        ).fetchone()
        return dict(row) if row else None


def get_settlement_by_post(post_id: int) -> Optional[Dict[str, Any]]:
    """게시글 기준 활성(pending/completed) 정산 1건을 반환합니다."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM settlements WHERE post_id = ? "
            "AND status IN ('pending','completed') ORDER BY id DESC LIMIT 1",
            (post_id,),
        ).fetchone()
        return dict(row) if row else None


def list_shares(settlement_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM settlement_shares WHERE settlement_id = ? "
            "ORDER BY user_id",
            (settlement_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_share(settlement_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
            (settlement_id, user_id),
        ).fetchone()
        return dict(row) if row else None


# ── 생성 ─────────────────────────────────────────────────────────────────────

def create_settlement(post_id: int, requester_id: int, total_amount: int,
                       account_info: Optional[str],
                       participant_ids: List[int]) -> Dict[str, Any]:
    """정산 헤더 + 참여자별 분담을 한 트랜잭션으로 생성합니다.

    분담 = total_amount // N (나머지는 주최자 흡수, shares에는 미포함).
    참여자가 없으면 ValueError.
    """
    n = len(participant_ids)
    if n <= 0:
        raise ValueError("참여자가 없어 정산을 생성할 수 없습니다.")

    per = total_amount // n
    now = to_iso(now_utc())

    with get_conn() as conn:
        tv.begin(conn)
        # Serialize creation with post-appointment changes and other creations.
        post_appt = tv.lock_row(conn, "posts", post_id)
        if conn.execute("SELECT id FROM settlements WHERE post_id = ? AND status IN ('pending', 'completed')",
                        (post_id,)).fetchone():
            raise ValueError("이미 이 게시글에 정산이 있습니다.")
        appt_place = post_appt["appointment_place"] if post_appt else None
        appt_at    = post_appt["appointment_at"]    if post_appt else None
        appt_lat   = post_appt["appointment_lat"]   if post_appt else None
        appt_lng   = post_appt["appointment_lng"]   if post_appt else None

        cur = conn.execute("""
            INSERT INTO settlements
                (post_id, requester_id, total_amount, account_info, status,
                 appointment_place, appointment_at, appointment_lat, appointment_lng,
                 created_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
        """, (post_id, requester_id, total_amount, (account_info or "").strip() or None,
              appt_place, appt_at, appt_lat, appt_lng, now))
        sid = cur.lastrowid

        for uid in participant_ids:
            conn.execute("""
                INSERT INTO settlement_shares
                    (settlement_id, user_id, amount, status, created_at)
                VALUES (?, ?, ?, 'unpaid', ?)
            """, (sid, uid, per, now))
        conn.commit()

    return get_settlement(sid)



# ── 약속 장소·시간 (주최자 확정) ─────────────────────────────────────────────

def set_appointment(settlement_id: int,
                    place: Optional[str], at_iso: Optional[str],
                    lat: Optional[float] = None,
                    lng: Optional[float] = None) -> None:
    """주최자가 거래 약속 장소/시간/좌표를 확정한다(pending 정산만).

    lat/lng 를 함께 저장하면 참여자 GPS 인증 시 해당 좌표를 target으로 삼아
    실제 100m 이내 여부를 서버에서 검증할 수 있다.
    """
    with get_conn() as conn:
        updated = conn.execute("""
            UPDATE settlements
               SET appointment_place = ?,
                   appointment_at    = ?,
                   appointment_lat   = ?,
                   appointment_lng   = ?
             WHERE id = ? AND status = 'pending'
        """, ((place or "").strip() or None, (at_iso or "").strip() or None,
               lat, lng, settlement_id))
        if updated.rowcount != 1:
            raise ValueError("진행 중인 정산에서만 약속을 변경할 수 있습니다.")
        conn.execute("""UPDATE settlement_shares SET gps_verified = 0, quality_agreed = 0
                        WHERE settlement_id = ? AND status IN ('unpaid', 'paid')""", (settlement_id,))
        conn.commit()




# ── 참여 차단 체크 ───────────────────────────────────────────────────────────

def has_unpaid_settlement(user_id: int) -> bool:
    """진행 중 정산에서 미납(unpaid) share가 있으면 True."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 1 FROM settlement_shares ss
            JOIN settlements s ON s.id = ss.settlement_id
            WHERE ss.user_id = ? AND ss.status = 'unpaid'
              AND s.status = 'pending'
            LIMIT 1
        """, (user_id,)).fetchone()
        return row is not None


# ── 주최자용: 참여자 GPS 인증 현황 상세 ──────────────────────────────────────

def get_participant_gps_details(settlement_id: int) -> List[Dict[str, Any]]:
    """정산 참여자별 GPS 인증 현황을 상세 조회합니다(주최자 대시보드용).

    settlement_shares(gps_verified) + location_verify_sessions(거리·시각)를 결합.
    각 참여자의 가장 최근 '인증 성공' 세션(LOCATION_VERIFIED 이상)을 기준으로,
    거리(distanceM)·인증시각(verifiedAt)·반경(radiusM)을 반환합니다.

    반환 항목:
      userId, nickname, status, gpsVerified,
      distanceM(float|None), verifiedAt(str|None), radiusM(float|None),
      withinThreshold(bool) — distance <= radius 이면 True
    """
    with get_conn() as conn:
        shares = conn.execute("""
            SELECT ss.user_id, ss.status, ss.gps_verified,
                   u.nickname
              FROM settlement_shares ss
              LEFT JOIN users u ON u.id = ss.user_id
             WHERE ss.settlement_id = ?
             ORDER BY ss.user_id
        """, (settlement_id,)).fetchall()

        out: List[Dict[str, Any]] = []
        for sh in shares:
            uid = sh["user_id"]
            # 해당 참여자의 최근 인증 성공 세션(거리·시각 보유)
            sess = conn.execute("""
                SELECT distance_m, radius_m, verified_at, status
                  FROM location_verify_sessions
                 WHERE subject_id = ? AND settlement_id = ?
                   AND status IN ('LOCATION_VERIFIED','QR_ISSUED','QR_VERIFIED')
                   AND verified_at IS NOT NULL
                 ORDER BY datetime(verified_at) DESC
                 LIMIT 1
            """, (str(uid), settlement_id)).fetchone()

            dist   = float(sess["distance_m"]) if sess and sess["distance_m"] is not None else None
            radius = float(sess["radius_m"])   if sess and sess["radius_m"]   is not None else None
            within = (dist is not None and radius is not None and dist <= radius)

            out.append({
                "userId":         uid,
                "nickname":       sh["nickname"] or f"이웃{uid}",
                "status":         sh["status"],
                "gpsVerified":    bool(sh["gps_verified"]),
                "distanceM":      round(dist, 1) if dist is not None else None,
                "radiusM":        round(radius, 1) if radius is not None else None,
                "verifiedAt":     sess["verified_at"] if sess else None,
                "withinThreshold": within,
            })
        return out


# ── 응답 직렬화 ──────────────────────────────────────────────────────────────

def serialize(settlement: Dict[str, Any], shares: List[Dict[str, Any]],
              nickname_map: Dict[int, str]) -> Dict[str, Any]:
    paid = sum(1 for s in shares if s["status"] == "paid")
    # 미납(unpaid)이 하나도 없으면(=모두 paid/noshow) 정산 완료 가능
    unpaid = sum(1 for s in shares if s["status"] == "unpaid")

    def _share_out(s: Dict[str, Any]) -> Dict[str, Any]:
        gps = bool(s["gps_verified"]) if "gps_verified" in s.keys() else False
        qr  = bool(s["quality_agreed"])
        return {
            "userId":        s["user_id"],
            "nickname":      nickname_map.get(s["user_id"], f"이웃{s['user_id']}"),
            "amount":        s["amount"],
            "status":        s["status"],
            "gpsVerified":   gps,
            "qualityAgreed": qr,
            "autoConfirmed": bool(s["auto_confirmed"]),
            # 두 단계(GPS→QR) 모두 통과 + 아직 미납이면 납부 버튼 활성 가능
            "payable":       gps and qr and s["status"] == "unpaid",
            "paidAt":        s["paid_at"],
        }

    return {
        "id":           settlement["id"],
        "postId":       settlement["post_id"],
        "requesterId":  settlement["requester_id"],
        "totalAmount":  settlement["total_amount"],
        "accountInfo":  settlement["account_info"],
        "status":       settlement["status"],
        "appointmentAt":    (settlement["appointment_at"]
                             if "appointment_at" in settlement.keys() else None),
        "appointmentPlace": (settlement["appointment_place"]
                             if "appointment_place" in settlement.keys() else None),
        "appointmentLat":   (settlement["appointment_lat"]
                             if "appointment_lat" in settlement.keys() else None),
        "appointmentLng":   (settlement["appointment_lng"]
                             if "appointment_lng" in settlement.keys() else None),
        "createdAt":    settlement["created_at"],
        "completedAt":  settlement["completed_at"],
        "participantCount": len(shares),
        "paidCount":    paid,
        "allPaid":      len(shares) > 0 and paid == len(shares),
        # 미납자가 없으면(전원 paid 또는 noshow) 주최자가 완료 처리 가능
        "canComplete":  len(shares) > 0 and unpaid == 0,
        "shares": [_share_out(s) for s in shares],
    }