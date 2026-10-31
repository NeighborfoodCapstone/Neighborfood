# -*- coding: utf-8 -*-
"""
demo.py — 전시 부스 '관리자 체험 모드' API  (prefix: /api/admin/demo, 관리자 전용)

흐름
  1) 관리자가 체험자(부스 방문자가 직접 가입한 계정)의 로그인 ID와 거래 유형을 골라 더미 거래를 만든다.
     체험자는 그 거래의 '주최자(글 작성자)'가 되고, 가상 이웃(demo_nb_*)이 참여자로 들어온다.
  2) 체험자가 자기 폰에서 채팅방에 들어가 만남 '일시'를 정한다. (장소는 서일대 호천관으로 서버가 고정)
  3) 관리자 노트북에서 가상 참여자의 '위치 인증 + QR'을 발급(위치는 호천관 고정 좌표) → 체험자 폰이 QR을 스캔한다.
  4) 공동구매는 가상 참여자 납부 처리 → 체험자가 정산 완료 → 후기. 나눔/교환은 QR 스캔으로 거래 완료 → 후기.

안전장치
  - 모든 엔드포인트는 관리자(get_current_admin)만 호출할 수 있다.
  - 대상은 일반 회원(role=user, 활성, 가상 이웃 아님)이며, 건드리는 데이터는 제목이 '[체험] '으로 시작하는
    그 회원의 게시글과 여기에 연결된 가상 이웃의 기록뿐이다.
  - 기존 GPS·QR·정산 검증 로직은 수정하지 않는다. 가상 참여자의 위치 증거와 QR 세션만 서버에서 직접 만든다.
    (QR 스캔 검증은 실제 /api/qr/verify 가 체험자 폰에서 그대로 수행한다.)
"""
import random
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.deps import get_current_admin
from app.core.demo_spot import DEMO_PREFIX, SPOT_ADDRESS, SPOT_LAT, SPOT_LNG
from app.core.utils import now_utc, to_iso, hash_token
from app.db import trade_verification as tv
from app.db.transaction_db import get_conn

router = APIRouter()

NEIGHBOR_PREFIX = "demo_nb_"
MAX_ACTIVE_TRADES = 5
TRUST_DEFAULT = 36.5
QR_TTL_SECONDS = 300          # GPS 증거 유효 시간(5분)과 맞춘다.
TYPES = ("groupbuy", "share", "exchange")
TYPE_LABEL = {"groupbuy": "공동구매", "share": "나눔", "exchange": "교환"}

# 가상 이웃 (로그인 불가: 비밀번호 해시가 형식에 맞지 않아 어떤 입력도 통과하지 못함)
NEIGHBORS = [
    (NEIGHBOR_PREFIX + "1", "체험이웃 하나", "demo-neighbor-1"),
    (NEIGHBOR_PREFIX + "2", "체험이웃 두리", "demo-neighbor-2"),
]

# 공동구매: (제목, 카테고리, 설명, 1인 가격, 이웃 인사말)
GROUPBUY = [
    ("대파 5단 공동구매",       "채소",     "시장에서 대파를 크게 묶어 사면 저렴해요. 이웃과 나눠요.",       4000, "대파 신선해 보여요! 참여할게요."),
    ("양파 10kg 같이 사요",     "채소",     "도매로 10kg 사서 나눠 담아요. 혼자 사기엔 너무 많아요.",       5000, "양파 필요했는데 잘됐네요!"),
    ("제철 사과 한 박스 공구",  "과일",     "농장 직거래 박스를 나눠 담아요. 이웃분들 환영!",               7000, "사과 좋아해요. 저도 참여합니다."),
    ("삼겹살 공구 (1근씩)",     "정육",     "동네 정육점 대량 주문입니다. 근당 가격으로 가져가요.",           9000, "고기 공구 반가워요. 신청했어요!"),
    ("우유 24팩 공동구매",      "유제품",   "대형마트 묶음을 나눠요. 유통기한이 길어서 쟁여두기 좋아요.",     6000, "우유 묶음 필요했어요. 참여해요."),
    ("쌀 20kg 같이 나눠요",     "곡물",     "햅쌀 한 포대를 소분해서 N분의 1로 나눠요.",                     8000, "쌀 소분 감사해요. 신청합니다!"),
    ("커피 원두 1kg 공구",      "음료",     "로스터리 원두 1kg을 250g씩 소분해요. 고소한 맛!",               6000, "원두 향 좋겠어요. 저도 할게요."),
    ("닭가슴살 10팩 묶음 공구", "냉동식품", "운동하시는 분들 같이 사요. 묶음으로 사면 훨씬 저렴해요.",       5000, "닭가슴살 찾고 있었어요. 참여!"),
    ("식빵 6봉지 공동구매",     "베이커리", "빵집 도매가로 6봉지를 나눠요. 냉동 보관하면 오래가요.",         4500, "아침마다 먹어서 딱이에요. 신청했어요."),
]
# 나눔/교환용 식재료: (이름, 카테고리)
ITEMS = [("대파", "채소"), ("양파", "채소"), ("사과", "과일"), ("우유", "유제품"), ("쌀", "곡물"),
         ("커피 원두", "음료"), ("식빵", "베이커리"), ("계란", "유제품"), ("감자", "채소")]
SWAP_WITH = ["고구마", "귤", "두부", "김", "라면", "토마토"]


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────
def _ensure_neighbors(conn):
    """가상 이웃 계정을 보장하고 [(id, nickname), ...]를 반환합니다."""
    now = to_iso(now_utc())
    result = []
    for login_id, nickname, phone in NEIGHBORS:
        row = conn.execute("SELECT id FROM users WHERE login_id = ?", (login_id,)).fetchone()
        if not row:
            conn.execute("""
                INSERT INTO users (login_id, password_hash, phone_number, nickname,
                                   trust_score, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'user', 'active', ?, ?)
            """, (login_id, "!demo-neighbor-login-disabled", phone, nickname, TRUST_DEFAULT, now, now))
            row = conn.execute("SELECT id FROM users WHERE login_id = ?", (login_id,)).fetchone()
        result.append((row["id"], nickname))
    return result


def _target_user(conn, login_id: str):
    login_id = (login_id or "").strip()
    if not login_id:
        raise HTTPException(400, "체험자 로그인 ID를 입력해 주세요.")
    u = conn.execute("SELECT * FROM users WHERE login_id = ?", (login_id,)).fetchone()
    if not u:
        raise HTTPException(404, "해당 로그인 ID의 회원이 없습니다.")
    if u["role"] == "admin":
        raise HTTPException(400, "관리자 계정에는 체험 거래를 만들 수 없습니다.")
    if str(u["login_id"]).startswith(NEIGHBOR_PREFIX):
        raise HTTPException(400, "가상 이웃 계정은 대상이 될 수 없습니다.")
    if u["status"] != "active":
        raise HTTPException(400, "활성 상태의 회원만 대상이 될 수 있습니다.")
    return u


def _demo_posts(conn, user_id: int):
    return conn.execute(
        "SELECT * FROM posts WHERE author_id = ? AND title LIKE ? AND status != 'deleted' ORDER BY id DESC",
        (user_id, DEMO_PREFIX + "%"),
    ).fetchall()


def _demo_post(conn, post_id: int):
    post = tv.lock_row(conn, "posts", post_id)
    if not post or post["status"] == "deleted" or not str(post["title"]).startswith(DEMO_PREFIX):
        raise HTTPException(404, "체험 거래를 찾을 수 없습니다.")
    return post


def _neighbor(conn, user_id: int):
    u = conn.execute("SELECT id, login_id, nickname FROM users WHERE id = ?", (user_id,)).fetchone()
    if not u or not str(u["login_id"]).startswith(NEIGHBOR_PREFIX):
        raise HTTPException(403, "가상 이웃에게만 사용할 수 있습니다.")
    return u


def _say(conn, conv_id: int, script, base):
    for i, (sender, text) in enumerate(script):
        conn.execute("INSERT INTO messages (conversation_id, sender_id, content, created_at) VALUES (?, ?, ?, ?)",
                     (conv_id, sender, text, to_iso(base + timedelta(seconds=i))))


def _insert_post(conn, kind, title, desc, category, user_id, now, **gb):
    cur = conn.execute("""
        INSERT INTO posts (type, title, description, category, images, address, lat, lng,
                           author_id, status, created_at, expires_at,
                           gb_target, gb_current, gb_price,
                           appointment_place, appointment_lat, appointment_lng)
        VALUES (?, ?, ?, ?, '[]', ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?)
    """, (kind, DEMO_PREFIX + title, desc, category, SPOT_ADDRESS, SPOT_LAT, SPOT_LNG, user_id,
          to_iso(now), to_iso(now + timedelta(hours=72)),
          gb.get("target"), gb.get("current"), gb.get("price"),
          SPOT_ADDRESS, SPOT_LAT, SPOT_LNG))
    return cur.lastrowid


# ── 조회 ─────────────────────────────────────────────────────────────────────
@router.get("/users")
async def search_users(q: str = Query("", max_length=50), admin: dict = Depends(get_current_admin)):
    """체험자 후보 검색(일반 회원, 최신 가입 순). q 가 없으면 최근 가입자."""
    like = f"%{q.strip()}%"
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, login_id, nickname, created_at FROM users
             WHERE role = 'user' AND status = 'active' AND login_id NOT LIKE ?
               AND (login_id LIKE ? OR nickname LIKE ?)
             ORDER BY id DESC LIMIT 20
        """, (NEIGHBOR_PREFIX + "%", like, like)).fetchall()
        items = []
        for r in rows:
            n = conn.execute("SELECT COUNT(*) c FROM posts WHERE author_id = ? AND title LIKE ? AND status != 'deleted'",
                             (r["id"], DEMO_PREFIX + "%")).fetchone()["c"]
            items.append({"id": r["id"], "loginId": r["login_id"], "nickname": r["nickname"],
                          "createdAt": r["created_at"], "demoTrades": n})
    return {"ok": True, "items": items}


@router.get("/trades")
async def list_trades(loginId: str = Query(...), admin: dict = Depends(get_current_admin)):
    """대상 체험자의 체험 거래와 가상 참여자별 진행 상태."""
    items = []
    with get_conn() as conn:
        user = _target_user(conn, loginId)
        for post in _demo_posts(conn, user["id"]):
            kind = post["type"]
            conv = conn.execute(
                "SELECT id, kind FROM conversations WHERE post_id = ? ORDER BY id LIMIT 1", (post["id"],)).fetchone()
            item = {
                "postId": post["id"], "type": kind, "typeLabel": TYPE_LABEL.get(kind, kind),
                "title": post["title"], "conversationId": conv["id"] if conv else None,
                "conversationKind": conv["kind"] if conv else None,
                "appointmentAt": post["appointment_at"], "place": post["appointment_place"],
                "settlement": None, "transaction": None, "participants": [],
            }
            if kind == "groupbuy":
                stl = conn.execute("SELECT * FROM settlements WHERE post_id = ? AND status IN ('pending','completed') "
                                   "ORDER BY id DESC LIMIT 1", (post["id"],)).fetchone()
                if stl:
                    item["settlement"] = {"id": stl["id"], "status": stl["status"],
                                          "appointmentAt": stl["appointment_at"]}
                    item["appointmentAt"] = stl["appointment_at"] or item["appointmentAt"]
                    shares = conn.execute("""SELECT ss.*, u.nickname FROM settlement_shares ss
                        JOIN users u ON u.id = ss.user_id WHERE ss.settlement_id = ? ORDER BY ss.user_id""",
                        (stl["id"],)).fetchall()
                    for s in shares:
                        item["participants"].append({
                            "userId": s["user_id"], "nickname": s["nickname"],
                            "gps": bool(s["gps_verified"]), "qr": bool(s["quality_agreed"]),
                            "paid": s["status"] == "paid"})
                else:
                    for p in conn.execute("""SELECT u.id, u.nickname FROM groupbuy_participants gp
                        JOIN users u ON u.id = gp.user_id WHERE gp.post_id = ? AND u.id != ?""",
                        (post["id"], user["id"])).fetchall():
                        item["participants"].append({"userId": p["id"], "nickname": p["nickname"],
                                                     "gps": False, "qr": False, "paid": False})
                if not stl:
                    item["next"] = "체험자: 채팅방에서 일시를 정하고 '정산 시작하기'를 누르게 안내하세요."
                elif stl["status"] == "completed":
                    item["next"] = "정산 완료. 체험자가 참여자 후기를 남기면 끝입니다."
                elif not stl["appointment_at"]:
                    item["next"] = "체험자가 '약속 변경'에서 일시를 정해야 합니다."
                elif all(p["paid"] for p in item["participants"]):
                    item["next"] = "모두 납부됨. 체험자가 '정산 완료'를 누르면 됩니다."
                else:
                    item["next"] = "참여자별로 '위치 인증 + QR 발급' → 체험자 폰이 스캔 → '납부 처리' 순서로 진행하세요."
            else:
                tx = conn.execute("SELECT * FROM transactions WHERE post_id = ? ORDER BY id DESC LIMIT 1",
                                  (post["id"],)).fetchone()
                if tx:
                    nick = conn.execute("SELECT nickname FROM users WHERE id = ?", (tx["receiver_id"],)).fetchone()
                    gps = conn.execute("""SELECT 1 FROM location_verify_sessions WHERE transaction_id = ?
                        AND subject_id = ? AND verified_at IS NOT NULL LIMIT 1""",
                        (tx["id"], str(tx["receiver_id"]))).fetchone()
                    item["transaction"] = {"id": tx["id"], "status": tx["status"]}
                    item["participants"].append({
                        "userId": tx["receiver_id"], "nickname": nick["nickname"] if nick else "",
                        "gps": bool(gps) or tx["status"] == "completed",
                        "qr": tx["status"] == "completed", "paid": False})
                    if tx["status"] == "completed":
                        item["next"] = "거래 완료. 체험자가 상대 후기를 남기면 끝입니다."
                    elif not post["appointment_at"]:
                        item["next"] = "체험자가 채팅방 상단/내 거래에서 약속 일시를 정해야 합니다."
                    else:
                        item["next"] = "'위치 인증 + QR 발급' → 체험자 폰이 'QR 스캔'으로 인증하면 거래가 완료됩니다."
            items.append(item)
    return {"ok": True, "user": {"id": user["id"], "loginId": user["login_id"], "nickname": user["nickname"]},
            "spot": {"address": SPOT_ADDRESS, "lat": SPOT_LAT, "lng": SPOT_LNG},
            "count": len(items), "items": items}


# ── 거래 생성 ────────────────────────────────────────────────────────────────
class TradeCreate(BaseModel):
    loginId: str = Field(..., min_length=1, max_length=60)
    type: str = Field("random", pattern=r"^(random|groupbuy|share|exchange)$")


@router.post("/trades")
async def create_trade(body: TradeCreate, admin: dict = Depends(get_current_admin)):
    kind = random.choice(TYPES) if body.type == "random" else body.type
    now = now_utc()
    now_text = to_iso(now)
    with get_conn() as conn:
        tv.begin(conn)
        user = _target_user(conn, body.loginId)
        if len(_demo_posts(conn, user["id"])) >= MAX_ACTIVE_TRADES:
            raise HTTPException(409, f"이 체험자에게 체험 거래가 이미 {MAX_ACTIVE_TRADES}건 있습니다. 초기화 후 다시 만들어 주세요.")
        neighbors = _ensure_neighbors(conn)
        me = user["id"]

        if kind == "groupbuy":
            title, category, desc, price, greeting = random.choice(GROUPBUY)
            post_id = _insert_post(conn, "groupbuy", title, desc, category, me, now,
                                   target=len(neighbors) + 2, current=len(neighbors), price=price)
            for uid, _ in neighbors:
                conn.execute("INSERT INTO groupbuy_participants (post_id, user_id, joined_at) VALUES (?, ?, ?)",
                             (post_id, uid, now_text))
            cur = conn.execute("INSERT INTO conversations (post_id, host_id, guest_id, created_at, kind) "
                               "VALUES (?, ?, ?, ?, 'group')", (post_id, me, me, now_text))
            conv_id = cur.lastrowid
            for uid in [me] + [n[0] for n in neighbors]:
                conn.execute("INSERT OR IGNORE INTO conversation_members (conversation_id, user_id, last_read_id, joined_at) "
                             "VALUES (?, ?, 0, ?)", (conv_id, uid, now_text))
            _say(conn, conv_id, [
                (neighbors[0][0], greeting),
                (neighbors[1][0], "저도 참여 신청했어요. 만나는 시간만 정해주세요!"),
                (neighbors[0][0], "주최자님, 일시 정해지면 알려주세요. 모임 날 인증하고 정산할게요."),
            ], now)
            shown = price * len(neighbors)
        else:
            nb_id, nb_name = neighbors[0]
            name, category = random.choice(ITEMS)
            if kind == "share":
                title, desc = f"남는 {name} 나눠요", f"{name}이(가) 많이 남아서 필요한 이웃께 무료로 드려요."
                greeting = f"{name} 나눔 신청했어요. 시간 정해주시면 맞출게요!"
            else:
                other = random.choice(SWAP_WITH)
                title, desc = f"{name} ↔ {other} 교환해요", f"{name}과(와) {other}을(를) 바꾸실 분 찾아요."
                greeting = f"{other}(으)로 교환하고 싶어요. 가능한 시간 알려주세요!"
            post_id = _insert_post(conn, kind, title, desc, category, me, now)
            cur = conn.execute("INSERT INTO conversations (post_id, host_id, guest_id, created_at, kind) "
                               "VALUES (?, ?, ?, ?, 'direct')", (post_id, me, nb_id, now_text))
            conv_id = cur.lastrowid
            # 신청이 수락된 상태(confirmed)로 시작 — 체험자는 일시 확정과 QR 스캔에 집중한다.
            conn.execute("""INSERT INTO transactions (post_id, provider_id, receiver_id, status, created_at)
                            VALUES (?, ?, ?, 'confirmed', ?)""", (post_id, me, nb_id, now_text))
            _say(conn, conv_id, [(nb_id, greeting), (nb_id, "만나는 날짜와 시간만 정해주세요 :)")], now)
            shown = None
        conn.commit()
    return {"ok": True, "trade": {"postId": post_id, "conversationId": conv_id, "type": kind,
                                  "typeLabel": TYPE_LABEL[kind], "title": DEMO_PREFIX + title,
                                  "suggestedTotal": shown, "neighbors": [n[1] for n in neighbors]}}


# ── 가상 참여자: 위치 인증(호천관 고정) + QR 발급 ────────────────────────────
@router.post("/trades/{post_id}/participants/{user_id}/qr")
async def issue_participant_qr(post_id: int, user_id: int, admin: dict = Depends(get_current_admin)):
    """가상 참여자의 위치 증거를 호천관 고정 좌표로 만들고, 체험자가 스캔할 QR 을 발급합니다."""
    now = now_utc()
    now_text = to_iso(now)
    expires_text = to_iso(now + timedelta(seconds=QR_TTL_SECONDS))
    with get_conn() as conn:
        tv.begin(conn)
        post = _demo_post(conn, post_id)
        neighbor = _neighbor(conn, user_id)
        sid = tid = None
        if post["type"] == "groupbuy":
            row = conn.execute("SELECT id FROM settlements WHERE post_id = ? AND status = 'pending' "
                               "ORDER BY id DESC LIMIT 1", (post_id,)).fetchone()
            if not row:
                raise HTTPException(409, "아직 정산이 시작되지 않았습니다. 체험자가 '정산 시작하기'를 먼저 눌러야 합니다.")
            stl = tv.lock_row(conn, "settlements", row["id"])
            share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                                 (stl["id"], user_id)).fetchone()
            if not share or share["status"] not in ("unpaid", "paid"):
                raise HTTPException(409, "이 정산의 진행 중인 참여자가 아닙니다.")
            if not stl["appointment_at"]:
                raise HTTPException(409, "체험자가 만남 일시를 먼저 정해야 합니다.")
            sid, target_lat, target_lng = stl["id"], stl["appointment_lat"], stl["appointment_lng"]
            purpose = "groupbuy_receive"
        else:
            tx = conn.execute("SELECT * FROM transactions WHERE post_id = ? AND receiver_id = ? AND status = 'confirmed' "
                              "ORDER BY id DESC LIMIT 1", (post_id, user_id)).fetchone()
            if not tx:
                raise HTTPException(409, "인증할 수 있는 진행 중 거래가 없습니다. (이미 완료되었을 수 있어요)")
            tv.lock_row(conn, "transactions", tx["id"])
            if not post["appointment_at"]:
                raise HTTPException(409, "체험자가 만남 일시를 먼저 정해야 합니다.")
            tid, target_lat, target_lng = tx["id"], post["appointment_lat"], post["appointment_lng"]
            purpose = "pickup_confirm"
        if not tv.valid_coordinate(target_lat, target_lng):
            raise HTTPException(409, "약속 좌표가 없습니다. 체험자가 약속을 다시 저장해야 합니다.")

        # 1) 위치 증거: 약속 좌표(=호천관)에 있는 것으로 기록
        loc_id = "locv_" + secrets.token_hex(8)
        conn.execute("""INSERT INTO location_verify_sessions
            (id, subject_id, transaction_id, settlement_id, target_lat, target_lng, target_address, radius_m,
             status, current_lat, current_lng, current_accuracy, distance_m, verified_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 100, 'LOCATION_VERIFIED', ?, ?, 10, 0, ?, ?, ?)""",
            (loc_id, str(user_id), tid, sid, target_lat, target_lng, SPOT_ADDRESS,
             target_lat, target_lng, now_text, now_text, now_text))
        if sid:
            conn.execute("UPDATE settlement_shares SET gps_verified = 1 WHERE settlement_id = ? AND user_id = ?",
                         (sid, user_id))
        # 2) QR: 이전 미사용 QR 은 만료시키고 새로 발급
        if sid:
            conn.execute("UPDATE qr_sessions SET status = 'EXPIRED', updated_at = ? WHERE subject_id = ? "
                         "AND settlement_id = ? AND status = 'ISSUED'", (now_text, str(user_id), sid))
        else:
            conn.execute("UPDATE qr_sessions SET status = 'EXPIRED', updated_at = ? WHERE subject_id = ? "
                         "AND transaction_id = ? AND status = 'ISSUED'", (now_text, str(user_id), tid))
        qr_id = "qrs_" + secrets.token_hex(8)
        token = secrets.token_urlsafe(32)
        conn.execute("""INSERT INTO qr_sessions
            (id, subject_id, purpose, token_hash, status, issued_at, expires_at, created_at, updated_at,
             transaction_id, settlement_id, location_session_id)
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, ?, ?, ?, ?, ?)""",
            (qr_id, str(user_id), purpose, hash_token(token), now_text, expires_text, now_text, now_text,
             tid, sid, loc_id))
        conn.commit()
    return {"ok": True, "session": {"id": qr_id, "token": token, "expiresAt": expires_text,
                                    "transactionId": tid, "settlementId": sid,
                                    "ttlSeconds": QR_TTL_SECONDS},
            "neighbor": neighbor["nickname"]}


@router.get("/qr/{session_id}")
async def qr_status(session_id: str, admin: dict = Depends(get_current_admin)):
    """노트북에 띄운 QR 이 스캔(VERIFIED)되었는지 확인하는 폴링용."""
    with get_conn() as conn:
        row = conn.execute("SELECT status, expires_at, used_at, purpose FROM qr_sessions WHERE id = ?",
                           (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, "QR 세션을 찾을 수 없습니다.")
    return {"ok": True, "status": row["status"], "expiresAt": row["expires_at"], "usedAt": row["used_at"]}


@router.post("/settlements/{settlement_id}/participants/{user_id}/pay")
async def pay_participant(settlement_id: int, user_id: int, admin: dict = Depends(get_current_admin)):
    """QR 인증이 끝난 가상 참여자의 납부를 처리합니다(실제 납부 API 의 조건과 동일하게 확인)."""
    with get_conn() as conn:
        tv.begin(conn)
        stl = tv.lock_row(conn, "settlements", settlement_id)
        if not stl:
            raise HTTPException(404, "정산을 찾을 수 없습니다.")
        _demo_post(conn, stl["post_id"])
        _neighbor(conn, user_id)
        if stl["status"] != "pending":
            raise HTTPException(400, "진행 중인 정산이 아닙니다.")
        share = conn.execute("SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?",
                             (settlement_id, user_id)).fetchone()
        if not share:
            raise HTTPException(404, "분담 대상이 아닙니다.")
        if share["status"] == "paid":
            raise HTTPException(409, "이미 납부 처리되었습니다.")
        ev = conn.execute("""SELECT id FROM qr_sessions WHERE settlement_id = ? AND subject_id = ?
            AND scanner_id = ? AND status = 'VERIFIED' AND used_at IS NOT NULL LIMIT 1""",
            (settlement_id, str(user_id), stl["requester_id"])).fetchone()
        if not share["gps_verified"] or not share["quality_agreed"] or not ev:
            raise HTTPException(400, "체험자 폰의 QR 스캔 인증이 먼저 필요합니다.")
        conn.execute("UPDATE settlement_shares SET status = 'paid', paid_at = ? "
                     "WHERE settlement_id = ? AND user_id = ? AND status = 'unpaid'",
                     (to_iso(now_utc()), settlement_id, user_id))
        conn.commit()
    return {"ok": True}


# ── 초기화 ───────────────────────────────────────────────────────────────────
@router.delete("/trades")
async def reset_trades(loginId: str = Query(...), admin: dict = Depends(get_current_admin)):
    """대상 체험자의 체험 거래·정산·채팅·평가를 지우고 신뢰 온도를 기본값으로 되돌립니다."""
    removed = 0
    with get_conn() as conn:
        tv.begin(conn)
        user = _target_user(conn, loginId)
        for p in conn.execute("SELECT id FROM posts WHERE author_id = ? AND title LIKE ?",
                              (user["id"], DEMO_PREFIX + "%")).fetchall():
            pid = p["id"]
            tx_ids = [r["id"] for r in conn.execute("SELECT id FROM transactions WHERE post_id = ?", (pid,)).fetchall()]
            st_ids = [r["id"] for r in conn.execute("SELECT id FROM settlements WHERE post_id = ?", (pid,)).fetchall()]
            for tid in tx_ids:
                conn.execute("DELETE FROM manner_ratings WHERE transaction_id = ?", (tid,))
                conn.execute("DELETE FROM qr_verification_events WHERE qr_session_id IN "
                             "(SELECT id FROM qr_sessions WHERE transaction_id = ?)", (tid,))
                conn.execute("DELETE FROM qr_sessions WHERE transaction_id = ?", (tid,))
                conn.execute("DELETE FROM location_verify_sessions WHERE transaction_id = ?", (tid,))
            for sid in st_ids:
                conn.execute("DELETE FROM qr_verification_events WHERE qr_session_id IN "
                             "(SELECT id FROM qr_sessions WHERE settlement_id = ?)", (sid,))
                conn.execute("DELETE FROM qr_sessions WHERE settlement_id = ?", (sid,))
                conn.execute("DELETE FROM location_verify_sessions WHERE settlement_id = ?", (sid,))
            conn.execute("DELETE FROM transactions WHERE post_id = ?", (pid,))
            for sid in st_ids:
                conn.execute("DELETE FROM settlement_shares WHERE settlement_id = ?", (sid,))
                conn.execute("DELETE FROM settlements WHERE id = ?", (sid,))
            for c in conn.execute("SELECT id FROM conversations WHERE post_id = ?", (pid,)).fetchall():
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (c["id"],))
                conn.execute("DELETE FROM conversation_members WHERE conversation_id = ?", (c["id"],))
            conn.execute("DELETE FROM conversations WHERE post_id = ?", (pid,))
            conn.execute("DELETE FROM groupbuy_participants WHERE post_id = ?", (pid,))
            conn.execute("DELETE FROM wishlists WHERE post_id = ?", (pid,))
            conn.execute("DELETE FROM posts WHERE id = ?", (pid,))
            removed += 1
        # 후기로 변한 신뢰 온도를 기본값으로 복원 (체험자 + 가상 이웃)
        conn.execute("UPDATE users SET trust_score = ? WHERE id = ?", (TRUST_DEFAULT, user["id"]))
        conn.execute("UPDATE users SET trust_score = ? WHERE login_id LIKE ?", (TRUST_DEFAULT, NEIGHBOR_PREFIX + "%"))
        conn.commit()
    return {"ok": True, "removed": removed}
