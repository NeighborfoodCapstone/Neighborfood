"""관리자 체험 모드 테스트 — 권한, 유형별 생성, 호천관 고정, 가상 참여자 QR → 체험자 스캔 → 완료/평가, 초기화."""
import sqlite3

import pytest

from app.core.demo_spot import SPOT_ADDRESS, SPOT_LAT, SPOT_LNG

EXP = "booth_guest"
WHEN = "2026-11-05T18:30:00Z"


def _db(client):
    conn = sqlite3.connect(client.db_path)
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture
def world(client, make_user):
    admin, guest, other = make_user("admin_user"), make_user(EXP), make_user("other_user")
    with _db(client) as conn:
        conn.execute("UPDATE users SET role='admin' WHERE id = ?", (admin.id,))
        conn.commit()
    return admin, guest, other


def _create(admin, kind):
    r = admin.post("/api/admin/demo/trades", {"loginId": EXP, "type": kind})
    assert r.status_code == 200, r.text
    return r.json()["trade"]


def _scan(guest, token, **scope):
    return guest.post("/api/qr/verify", {"rawValue": token, **scope})


# ── 권한 ──────────────────────────────────────────────────────
def test_admin_only(client, world):
    admin, guest, other = world
    assert client.get("/api/admin/demo/users").status_code == 401
    for path in ("/api/admin/demo/users", f"/api/admin/demo/trades?loginId={EXP}"):
        assert guest.get(path).status_code == 403
    assert guest.post("/api/admin/demo/trades", {"loginId": EXP, "type": "share"}).status_code == 403
    assert guest.delete(f"/api/admin/demo/trades?loginId={EXP}").status_code == 403
    assert admin.get("/api/admin/demo/users?q=booth").json()["items"][0]["loginId"] == EXP


def test_target_validation(client, world):
    admin, _, _ = world
    assert admin.post("/api/admin/demo/trades", {"loginId": "nobody", "type": "share"}).status_code == 404
    assert admin.post("/api/admin/demo/trades", {"loginId": "admin_user", "type": "share"}).status_code == 400
    assert admin.post("/api/admin/demo/trades", {"loginId": EXP, "type": "bogus"}).status_code == 422
    _create(admin, "share")
    assert admin.post("/api/admin/demo/trades", {"loginId": "demo_nb_1", "type": "share"}).status_code == 400


def test_trade_limit(client, world):
    admin, _, _ = world
    for _ in range(5):
        _create(admin, "random")
    assert admin.post("/api/admin/demo/trades", {"loginId": EXP, "type": "random"}).status_code == 409


# ── 생성: 유형별 ──────────────────────────────────────────────
@pytest.mark.parametrize("kind", ["groupbuy", "share", "exchange"])
def test_create_each_type(client, world, kind):
    admin, guest, _ = world
    t = _create(admin, kind)
    assert t["type"] == kind and t["title"].startswith("[체험] ")
    items = admin.get(f"/api/admin/demo/trades?loginId={EXP}").json()["items"]
    assert len(items) == 1 and items[0]["type"] == kind and items[0]["place"] == SPOT_ADDRESS
    # 체험자는 주최자로 채팅방에 들어와 가상 이웃의 메시지를 본다
    path = f"/api/chats/{'group/' if kind == 'groupbuy' else ''}{t['conversationId']}/messages"
    assert guest.get(path).json()["count"] >= 2
    post = guest.get(f"/posts/{t['postId']}").json()
    assert post["author_id"] == guest.id


def test_random_type_is_valid(client, world):
    admin, _, _ = world
    assert _create(admin, "random")["type"] in ("groupbuy", "share", "exchange")


# ── 장소 고정 ────────────────────────────────────────────────
def test_place_is_locked_to_spot(client, world):
    admin, guest, _ = world
    t = _create(admin, "groupbuy")
    r = guest.post(f"/posts/{t['postId']}/appointment",
                   {"place": "엉뚱한 곳", "appointment_at": WHEN, "lat": 37.0, "lng": 127.0})
    assert r.status_code == 200
    assert r.json()["appointment"]["place"] == SPOT_ADDRESS
    sid = guest.post("/api/settlements", {"post_id": t["postId"], "total_amount": 10000}).json()["settlement"]["id"]
    s = guest.post(f"/api/settlements/{sid}/appointment",
                   {"place": "또 엉뚱한 곳", "appointment_at": WHEN, "lat": 1.0, "lng": 2.0}).json()["settlement"]
    assert (s["appointmentPlace"], s["appointmentLat"], s["appointmentLng"]) == (SPOT_ADDRESS, SPOT_LAT, SPOT_LNG)


def test_normal_posts_not_locked(client, world):
    _, guest, _ = world
    pid = guest.post("/posts", {"type": "share", "title": "일반 나눔"}).json()["id"]
    r = guest.post(f"/posts/{pid}/appointment", {"place": "내가 정한 곳", "appointment_at": WHEN, "lat": 37.5, "lng": 127.0})
    assert r.json()["appointment"]["place"] == "내가 정한 곳"


# ── 전체 흐름: 공동구매 ───────────────────────────────────────
def test_groupbuy_full_flow_and_reset(client, world):
    admin, guest, other = world
    t = _create(admin, "groupbuy")
    pid = t["postId"]
    item = lambda: admin.get(f"/api/admin/demo/trades?loginId={EXP}").json()["items"][0]
    nbs = [p["userId"] for p in item()["participants"]]
    assert len(nbs) == 2

    # 정산 전/일시 전에는 QR 발급 불가
    assert admin.post(f"/api/admin/demo/trades/{pid}/participants/{nbs[0]}/qr").status_code == 409
    sid = guest.post("/api/settlements", {"post_id": pid, "total_amount": t["suggestedTotal"]}).json()["settlement"]["id"]
    assert admin.post(f"/api/admin/demo/trades/{pid}/participants/{nbs[0]}/qr").status_code == 409  # 일시 미정
    assert guest.post(f"/posts/{pid}/appointment", {"place": "x", "appointment_at": WHEN}).status_code == 200

    # 가상 참여자만 대상: 실제 회원/주최자는 거부
    assert admin.post(f"/api/admin/demo/trades/{pid}/participants/{guest.id}/qr").status_code == 403
    assert admin.post(f"/api/admin/demo/trades/{pid}/participants/{other.id}/qr").status_code == 403

    # 노트북에서 QR 발급 → 체험자 폰이 스캔
    for nb in nbs:
        q = admin.post(f"/api/admin/demo/trades/{pid}/participants/{nb}/qr")
        assert q.status_code == 200, q.text
        s = q.json()["session"]
        assert s["settlementId"] == sid
        assert admin.get(f"/api/admin/demo/qr/{s['id']}").json()["status"] == "ISSUED"
        # 인증 전 납부 처리는 거부(실제 검증 조건 유지)
        assert admin.post(f"/api/admin/demo/settlements/{sid}/participants/{nb}/pay").status_code == 400
        # 참여자 본인이 아닌 제3자는 스캔 불가, 주최자(체험자)는 가능
        assert _scan(other, s["token"], settlementId=sid).status_code == 403
        v = _scan(guest, s["token"], settlementId=sid)
        assert v.status_code == 200 and v.json()["ok"], v.text
        assert admin.get(f"/api/admin/demo/qr/{s['id']}").json()["status"] == "VERIFIED"
        assert admin.post(f"/api/admin/demo/settlements/{sid}/participants/{nb}/pay").status_code == 200
    assert all(p["gps"] and p["qr"] and p["paid"] for p in item()["participants"])

    # 일반 정산 완료 API → 후기
    assert guest.post(f"/api/settlements/{sid}/complete").status_code == 200
    tx = guest.get("/api/transactions?status=completed").json()["items"]
    assert len(tx) == 2
    assert guest.post("/api/ratings", {"transaction_id": tx[0]["id"], "score": 1}).status_code in (200, 201)

    # 초기화
    rm = admin.delete(f"/api/admin/demo/trades?loginId={EXP}")
    assert rm.status_code == 200 and rm.json()["removed"] == 1
    with _db(client) as conn:
        for table in ("posts", "settlements", "transactions", "settlement_shares", "conversations",
                      "messages", "qr_sessions", "manner_ratings", "location_verify_sessions"):
            assert conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()[0] == 0, table
        assert conn.execute("SELECT trust_score FROM users WHERE id=?", (guest.id,)).fetchone()[0] == 36.5


# ── 전체 흐름: 나눔/교환 ──────────────────────────────────────
@pytest.mark.parametrize("kind", ["share", "exchange"])
def test_direct_trade_flow(client, world, kind):
    admin, guest, other = world
    t = _create(admin, kind)
    pid = t["postId"]
    it = admin.get(f"/api/admin/demo/trades?loginId={EXP}").json()["items"][0]
    nb, txid = it["participants"][0]["userId"], it["transaction"]["id"]
    assert it["transaction"]["status"] == "confirmed" and it["conversationKind"] == "direct"

    assert admin.post(f"/api/admin/demo/trades/{pid}/participants/{nb}/qr").status_code == 409  # 일시 미정
    assert guest.post(f"/posts/{pid}/appointment", {"place": "x", "appointment_at": WHEN}).status_code == 200
    q = admin.post(f"/api/admin/demo/trades/{pid}/participants/{nb}/qr")
    assert q.status_code == 200, q.text
    s = q.json()["session"]
    assert s["transactionId"] == txid
    v = _scan(guest, s["token"], transactionId=txid)
    assert v.status_code == 200 and v.json()["ok"], v.text
    assert guest.get("/api/transactions?status=completed").json()["count"] == 1
    again = admin.post(f"/api/admin/demo/trades/{pid}/participants/{nb}/qr")
    assert again.status_code == 409           # 이미 완료
    rated = guest.post("/api/ratings", {"transaction_id": txid, "score": 1})
    assert rated.status_code in (200, 201), rated.text


def test_expired_qr_rejected(client, world):
    admin, guest, _ = world
    t = _create(admin, "share")
    it = admin.get(f"/api/admin/demo/trades?loginId={EXP}").json()["items"][0]
    nb, txid = it["participants"][0]["userId"], it["transaction"]["id"]
    guest.post(f"/posts/{t['postId']}/appointment", {"place": "x", "appointment_at": WHEN})
    s = admin.post(f"/api/admin/demo/trades/{t['postId']}/participants/{nb}/qr").json()["session"]
    with _db(client) as conn:
        conn.execute("UPDATE qr_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (s["id"],))
        conn.commit()
    r = _scan(guest, s["token"], transactionId=txid)
    assert r.json()["ok"] is False
