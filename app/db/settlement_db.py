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
        # 게시글에 이미 확정된 약속(장소·시간·좌표)이 있으면 정산이 승계
        post_appt = conn.execute("""
            SELECT appointment_place, appointment_at, appointment_lat, appointment_lng
              FROM posts WHERE id = ?
        """, (post_id,)).fetchone()
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


# ── 상태 변경 ────────────────────────────────────────────────────────────────

def mark_paid(settlement_id: int, user_id: int) -> None:
    """참여자 본인이 납부했음을 표시합니다."""
    now = to_iso(now_utc())
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares
               SET status = 'paid', paid_at = ?
             WHERE settlement_id = ? AND user_id = ? AND status = 'unpaid'
        """, (now, settlement_id, user_id))
        conn.commit()


def mark_noshow(settlement_id: int, user_id: int) -> None:
    """참여자를 노쇼 처리합니다(주최자만 호출)."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares
               SET status = 'noshow'
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, user_id))
        conn.commit()


def revert_noshow(settlement_id: int, user_id: int) -> None:
    """노쇼 처리를 취소해 unpaid(납부 대기)로 되돌립니다(주최자만 호출).
    trust_score 복원 및 연결된 pending 노쇼 신고 삭제는 라우터에서 같은 트랜잭션으로 처리합니다."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares
               SET status = 'unpaid'
             WHERE settlement_id = ? AND user_id = ? AND status = 'noshow'
        """, (settlement_id, user_id))
        conn.commit()


def set_quality_agreed(settlement_id: int, user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares SET quality_agreed = 1
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, user_id))
        conn.commit()


def complete_settlement(settlement_id: int) -> None:
    now = to_iso(now_utc())
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlements SET status = 'completed', completed_at = ?
             WHERE id = ? AND status = 'pending'
        """, (now, settlement_id))
        conn.commit()


def cancel_settlement(settlement_id: int) -> None:
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlements SET status = 'canceled'
             WHERE id = ? AND status = 'pending'
        """, (settlement_id,))
        conn.commit()


# ── QR 연동 (품질 동의) ──────────────────────────────────────────────────────

def apply_quality_agreed_for_user(post_id: int, user_id: int) -> None:
    """해당 게시글의 진행 중 정산에서 user의 share에 quality_agreed=1을 세팅.
    QR 인증 성공 시 qr.py에서 호출. 정산이 없으면 no-op."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares
               SET quality_agreed = 1
             WHERE user_id = ?
               AND settlement_id IN (
                   SELECT id FROM settlements
                    WHERE post_id = ? AND status = 'pending'
               )
        """, (user_id, post_id))
        conn.commit()


# ── GPS 자동 확인 ────────────────────────────────────────────────────────────

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
        conn.execute("""
            UPDATE settlements
               SET appointment_place = ?,
                   appointment_at    = ?,
                   appointment_lat   = ?,
                   appointment_lng   = ?
             WHERE id = ? AND status = 'pending'
        """, ((place or "").strip() or None, (at_iso or "").strip() or None,
               lat, lng, settlement_id))
        conn.commit()


# ── Step 1: GPS 인증 확인 ────────────────────────────────────────────────────

def has_verified_gps_session(user_id: int) -> bool:
    """해당 사용자가 소유한 GPS 세션 중 LOCATION_VERIFIED 이상 상태가 있으면 True.
    location_verify_sessions.subject_id 는 문자열(user_id)로 바인딩된다고 가정한다.
    QR_ISSUED / QR_VERIFIED 도 GPS 통과 이후 단계이므로 인정한다."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 1 FROM location_verify_sessions
             WHERE subject_id = ?
               AND status IN ('LOCATION_VERIFIED','QR_ISSUED','QR_VERIFIED')
               AND verified_at IS NOT NULL
             LIMIT 1
        """, (str(user_id),)).fetchone()
        return row is not None


def set_gps_verified(settlement_id: int, user_id: int) -> None:
    """참여자의 GPS 인증 완료를 기록한다(Step 1)."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares SET gps_verified = 1
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, user_id))
        conn.commit()


def verify_participant_gps(user_id: int, appt_lat: float, appt_lng: float,
                           threshold_m: float = 100.0) -> dict:
    """참여자의 최근 LOCATION_VERIFIED 세션 좌표와 약속 좌표 간 거리를 서버에서 재검증한다.

    - subject_id = str(user_id) 인 세션 중 가장 최근 인증 성공 기록을 사용한다.
    - Haversine 거리가 threshold_m(기본 100m) 이내이면 ok=True.
    - 프론트가 보낸 값을 신뢰하지 않고 DB에 저장된 current_lat/lng으로 재계산한다.
    """
    from app.db.location_verify_db import distance_meters
    with get_conn() as conn:
        sess = conn.execute("""
            SELECT current_lat, current_lng, verified_at
              FROM location_verify_sessions
             WHERE subject_id = ?
               AND current_lat  IS NOT NULL
               AND current_lng  IS NOT NULL
               AND verified_at  IS NOT NULL
               AND status IN ('LOCATION_VERIFIED', 'QR_ISSUED', 'QR_VERIFIED')
             ORDER BY datetime(verified_at) DESC
             LIMIT 1
        """, (str(user_id),)).fetchone()

    if not sess:
        return {
            "ok": False,
            "distanceM": None,
            "reason": (
                "GPS 인증 기록을 찾을 수 없어요. "
                "약속 장소 근처에서 GPS 인증을 먼저 완료해 주세요."
            ),
        }

    dist = distance_meters(
        float(sess["current_lat"]), float(sess["current_lng"]),
        appt_lat, appt_lng,
    )
    ok = dist <= threshold_m
    return {
        "ok":         ok,
        "distanceM":  round(dist, 1),
        "verifiedAt": sess["verified_at"],
        "reason":     None if ok else (
            f"약속 장소에서 {round(dist)}m 떨어진 위치에서 인증했어요. "
            f"허용 반경 {round(threshold_m)}m 이내에서 다시 인증해 주세요."
        ),
    }


# ── Step 2: QR 인증 확인 ─────────────────────────────────────────────────────

def has_verified_qr_session(user_id: int) -> bool:
    """해당 사용자를 subject 로 하는 qr_sessions 중 VERIFIED 상태가 있으면 True.
    subject_id 포맷은 'user_<id>' 또는 순수 '<id>' 를 모두 허용한다."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT 1 FROM qr_sessions
             WHERE status = 'VERIFIED'
               AND (subject_id = ? OR subject_id = ?)
             LIMIT 1
        """, (str(user_id), f"user_{user_id}")).fetchone()
        return row is not None


def set_qr_verified(settlement_id: int, user_id: int) -> None:
    """참여자의 QR 인증 완료(품질 동의)를 기록한다(Step 2)."""
    with get_conn() as conn:
        conn.execute("""
            UPDATE settlement_shares SET quality_agreed = 1
             WHERE settlement_id = ? AND user_id = ?
        """, (settlement_id, user_id))
        conn.commit()


# ── 정산 완료 → transactions 연동 ────────────────────────────────────────────

def create_transactions_for_settlement(settlement_id: int) -> List[int]:
    """정산 완료 시 paid 상태인 참여자마다 transactions 행을 생성합니다.

    - provider_id = 정산 주최자(requester_id)
    - receiver_id = paid 상태 참여자(settlement_shares.user_id)
    - status      = 'completed' (즉시 완료 처리 → ratings 평가 가능)

    멱등성: 이미 같은 (post_id, provider_id, receiver_id) 조합이 있으면 생성하지 않고
    기존 id를 반환합니다.

    noshow 참여자는 제외합니다 (실제 수령이 없으므로 거래 내역 불포함).
    """
    now = to_iso(now_utc())
    tx_ids: List[int] = []

    with get_conn() as conn:
        stl = conn.execute(
            "SELECT id, post_id, requester_id, appointment_at FROM settlements WHERE id = ?",
            (settlement_id,),
        ).fetchone()
        if not stl:
            return []

        paid_shares = conn.execute(
            "SELECT user_id FROM settlement_shares WHERE settlement_id = ? AND status = 'paid'",
            (settlement_id,),
        ).fetchall()

        for share in paid_shares:
            participant_id = share["user_id"]
            # 멱등 체크: 동일 조합 행이 이미 있으면 기존 id 반환
            existing = conn.execute(
                """SELECT id FROM transactions
                    WHERE post_id = ? AND provider_id = ? AND receiver_id = ?""",
                (stl["post_id"], stl["requester_id"], participant_id),
            ).fetchone()
            if existing:
                tx_ids.append(existing["id"])
                continue

            cur = conn.execute(
                """INSERT INTO transactions
                       (post_id, provider_id, receiver_id, status,
                        appointment_at, completed_at, created_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?)""",
                (stl["post_id"], stl["requester_id"], participant_id,
                 stl["appointment_at"], now, now),
            )
            tx_ids.append(cur.lastrowid)

        conn.commit()

    return tx_ids


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
                 WHERE subject_id = ?
                   AND status IN ('LOCATION_VERIFIED','QR_ISSUED','QR_VERIFIED')
                   AND verified_at IS NOT NULL
                 ORDER BY datetime(verified_at) DESC
                 LIMIT 1
            """, (str(uid),)).fetchone()

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