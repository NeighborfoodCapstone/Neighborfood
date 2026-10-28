"""실제 API를 이용한 정산 GPS·QR·납부·평가 흐름 테스트."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest

APPT_LAT, APPT_LNG = 37.5665, 126.9780        # 약속 좌표(서울시청)
NEAR = (37.5666, 126.9781)                    # 약 15m
FAR  = (37.5800, 126.9780)                    # 약 1.5km


def _gps_session(user, lat, lng):
    created = user.post("/api/location-verify/dummy-target", {"lat": lat, "lng": lng})
    assert created.status_code == 200, created.text
    session_id = created.json()["session"]["id"]
    checked = user.post(f"/api/location-verify/{session_id}/gps-check",
                        {"lat": lat, "lng": lng, "accuracy": 10})
    assert checked.status_code == 200, checked.text
    return session_id


def _scan_settlement_qr(t, user):
    sid = t["sid"]
    issued = user.post("/api/qr/request", {"subjectId": str(user.id), "settlementId": sid})
    assert issued.status_code == 200, issued.text
    token = issued.json()["session"]["token"]
    scanned = t["host"].post("/api/qr/verify", {"token": token, "settlementId": sid})
    assert scanned.status_code == 200 and scanned.json()["ok"], scanned.text
    return token


@pytest.fixture
def trade(client, make_user):
    """주최자 + 참여자 2명이 있는 공동구매와 생성된 정산."""
    host, a, b = make_user("host"), make_user("alice"), make_user("bob")
    pid = host.post("/posts", {"type": "groupbuy", "title": "공구", "gb_target": 3, "gb_price": 3000}).json()["id"]
    assert a.post(f"/posts/{pid}/join").status_code == 200
    assert b.post(f"/posts/{pid}/join").status_code == 200
    r = host.post("/api/settlements", {"post_id": pid, "total_amount": 9000})
    assert r.status_code == 200, r.text
    sid = r.json()["settlement"]["id"]
    return dict(client=client, host=host, a=a, b=b, pid=pid, sid=sid, db=client.db_path)


def _appoint(t, lat=APPT_LAT, lng=APPT_LNG):
    r = t["host"].post(f"/api/settlements/{t['sid']}/appointment",
                       {"place": "시청 앞", "appointment_at": "2026-10-20T09:00:00Z", "lat": lat, "lng": lng})
    assert r.status_code == 200, r.text


def _complete_steps(t, user, lat_lng=NEAR):
    sid = t["sid"]
    location_id = _gps_session(user, *lat_lng)
    assert user.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 200
    _scan_settlement_qr(t, user)
    assert user.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 200


# ── 생성 ──────────────────────────────────────────────────────
def test_create_rules(trade, make_user):
    h, a, pid = trade["host"], trade["a"], trade["pid"]
    assert h.post("/api/settlements", {"post_id": pid, "total_amount": 9000}).status_code == 409   # 중복
    assert a.post("/api/settlements", {"post_id": pid, "total_amount": 9000}).status_code == 403   # 작성자만
    empty = h.post("/posts", {"type": "groupbuy", "title": "빈공구", "gb_target": 3, "gb_price": 1}).json()["id"]
    assert h.post("/api/settlements", {"post_id": empty, "total_amount": 100}).status_code == 400  # 참여자 없음
    assert h.post("/api/settlements", {"post_id": pid, "total_amount": 0}).status_code == 422
    s = h.get(f"/api/settlements/{trade['sid']}").json()["settlement"]
    assert len(s["shares"]) == 2 and sum(x["amount"] for x in s["shares"]) == 9000
    # 관련 없는 사람은 접근 불가
    outsider = make_user("eve")
    assert outsider.get(f"/api/settlements/{trade['sid']}").status_code == 403


def test_concurrent_settlement_creation_only_creates_one(client, make_user):
    host, participant = make_user("create_host"), make_user("create_participant")
    pid = host.post("/posts", {"type": "groupbuy", "title": "공구", "gb_target": 2, "gb_price": 1000}).json()["id"]
    assert participant.post(f"/posts/{pid}/join").status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: host.post("/api/settlements", {"post_id": pid, "total_amount": 1000}), range(2)))
    assert sum(response.status_code == 200 for response in responses) == 1
    assert all(response.status_code in (200, 400, 409) for response in responses)
    with sqlite3.connect(client.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM settlements WHERE post_id = ?", (pid,)).fetchone()[0] == 1


def test_post_appointment_and_settlement_rollback_together(trade):
    host, pid, sid = trade["host"], trade["pid"], trade["sid"]
    with sqlite3.connect(trade["db"]) as db:
        db.execute(f"""CREATE TRIGGER reject_appointment BEFORE UPDATE ON settlement_shares
            WHEN NEW.settlement_id = {sid}
            BEGIN SELECT RAISE(ABORT, 'injected failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        host.post(f"/posts/{pid}/appointment", {"place": "새 장소", "lat": APPT_LAT, "lng": APPT_LNG})
    with sqlite3.connect(trade["db"]) as db:
        assert db.execute("SELECT appointment_place FROM posts WHERE id = ?", (pid,)).fetchone()[0] is None
        assert db.execute("SELECT appointment_place FROM settlements WHERE id = ?", (sid,)).fetchone()[0] is None


# ── 약속 / GPS / QR 게이트 ────────────────────────────────────
def test_gps_requires_appointment_then_distance(trade):
    sid, a, h = trade["sid"], trade["a"], trade["host"]
    assert a.post(f"/api/settlements/{sid}/appointment", {"place": "x"}).status_code == 403          # 주최자만
    location_id = _gps_session(a, *NEAR)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 400
    _appoint(trade)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": "missing"}).status_code == 403
    far_id = _gps_session(a, *FAR)
    r = a.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": far_id})
    assert r.status_code == 400 and "m" in r.json()["detail"]
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 200
    assert h.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 403


def test_qr_requires_gps_first_and_pay_requires_both(trade):
    sid, a = trade["sid"], trade["a"]
    _appoint(trade)
    assert a.post("/api/qr/request", {"subjectId": str(a.id), "settlementId": sid}).status_code == 400
    assert a.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 400
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400
    location_id = _gps_session(a, *NEAR)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400
    _scan_settlement_qr(trade, a)
    assert a.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 409                         # 중복 납부


def test_settlement_qr_is_scoped_to_organizer_and_settlement(trade, make_user):
    sid, participant, host = trade["sid"], trade["a"], trade["host"]
    outsider = make_user("outsider")
    _appoint(trade)
    location_id = _gps_session(participant, *NEAR)
    assert participant.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 200
    token = participant.post("/api/qr/request", {"subjectId": str(participant.id), "settlementId": sid}).json()["session"]["token"]
    assert outsider.post("/api/qr/verify", {"token": token, "settlementId": sid}).status_code == 403
    assert host.post("/api/qr/verify", {"token": token, "settlementId": sid + 1}).status_code == 403
    assert host.post("/api/qr/verify", {"token": token, "settlementId": sid}).json()["ok"] is True
    assert host.post("/api/qr/verify", {"token": token, "settlementId": sid}).json()["ok"] is False


def test_settlement_completion_is_atomic_on_insert_failure(trade):
    sid, host = trade["sid"], trade["host"]
    _appoint(trade)
    for user in (trade["a"], trade["b"]):
        _complete_steps(trade, user)
        assert user.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    with sqlite3.connect(trade["db"]) as db:
        db.execute(f"""CREATE TRIGGER reject_second_trade BEFORE INSERT ON transactions
            WHEN NEW.settlement_id = {sid} AND NEW.receiver_id = {trade["b"].id}
            BEGIN SELECT RAISE(ABORT, 'injected failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        host.post(f"/api/settlements/{sid}/complete")
    with sqlite3.connect(trade["db"]) as db:
        assert db.execute("SELECT status FROM settlements WHERE id = ?", (sid,)).fetchone()[0] == "pending"
        assert db.execute("SELECT COUNT(*) FROM transactions WHERE settlement_id = ?", (sid,)).fetchone()[0] == 0


def test_legacy_paid_share_can_reverify_without_changing_payment(trade):
    sid, host, participant = trade["sid"], trade["host"], trade["a"]
    _appoint(trade)
    with sqlite3.connect(trade["db"]) as db:
        db.execute("UPDATE settlement_shares SET status='paid', gps_verified=1, quality_agreed=1 WHERE settlement_id=? AND user_id=?",
                   (sid, participant.id))
    assert host.post(f"/api/settlements/{sid}/shares/{trade['b'].id}/noshow").status_code == 200
    assert host.post(f"/api/settlements/{sid}/complete").status_code == 409
    location_id = _gps_session(participant, *NEAR)
    assert participant.post(f"/api/settlements/{sid}/shares/me/gps-done", {"locationSessionId": location_id}).status_code == 200
    _scan_settlement_qr(trade, participant)
    assert participant.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 200
    assert host.post(f"/api/settlements/{sid}/complete").status_code == 200
    with sqlite3.connect(trade["db"]) as db:
        assert db.execute("SELECT status FROM settlement_shares WHERE settlement_id=? AND user_id=?", (sid, participant.id)).fetchone()[0] == 'paid'


def test_changed_appointment_requires_paid_users_to_reverify(trade):
    sid, host = trade["sid"], trade["host"]
    _appoint(trade)
    for user in (trade["a"], trade["b"]):
        _complete_steps(trade, user)
        assert user.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    _appoint(trade, lat=APPT_LAT + .001, lng=APPT_LNG)
    assert host.post(f"/api/settlements/{sid}/complete").status_code == 409
    for user in (trade["a"], trade["b"]):
        _complete_steps(trade, user, (APPT_LAT + .001, APPT_LNG))
    assert host.post(f"/api/settlements/{sid}/complete").status_code == 200


# ── 전체 흐름: 약속 → GPS → QR → 납부 → 완료 → 평가 ────────────
def test_full_flow_to_rating(trade):
    sid, h, a, b = trade["sid"], trade["host"], trade["a"], trade["b"]
    _appoint(trade)
    assert h.post(f"/api/settlements/{sid}/complete").status_code == 400          # 미납자 있음
    for u in (a, b):
        _complete_steps(trade, u)
        assert u.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    st = h.get(f"/api/settlements/{sid}/participants/gps-status").json()
    assert st["verifiedCount"] == 2 and st["participantCount"] == 2
    assert a.post(f"/api/settlements/{sid}/complete").status_code == 403           # 주최자만 완료
    r = h.post(f"/api/settlements/{sid}/complete")
    assert r.status_code == 200 and r.json()["settlement"]["status"] == "completed"
    assert h.post(f"/api/settlements/{sid}/cancel").status_code == 400             # 완료 후 취소 불가
    assert h.post(f"/api/settlements/{sid}/complete").status_code == 400           # 재완료 불가

    # 거래 행 생성 → 매너 평가
    with sqlite3.connect(trade["db"]) as db:
        txs = db.execute("SELECT id, provider_id, receiver_id FROM transactions WHERE status='completed'").fetchall()
    assert len(txs) == 2 and all(t[1] == h.id for t in txs)
    tx_id = next(t[0] for t in txs if t[2] == a.id)
    assert a.post("/api/ratings", {"transaction_id": tx_id, "score": 1}).status_code == 200
    assert h.get("/api/ratings/received").status_code == 200


# ── 노쇼 / 취소 ───────────────────────────────────────────────
def test_noshow_penalty_and_restore(trade):
    sid, h, a, b = trade["sid"], trade["host"], trade["a"], trade["b"]
    _appoint(trade)
    base = a.get("/api/users/me").json()
    trust0 = base.get("trust_score", base.get("trustScore"))
    assert a.post(f"/api/settlements/{sid}/shares/{b.id}/noshow").status_code == 403    # 주최자만
    assert h.post(f"/api/settlements/{sid}/shares/{b.id}/noshow").status_code == 200
    assert h.post(f"/api/settlements/{sid}/shares/{b.id}/noshow").status_code == 409
    assert b.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400            # 노쇼자 납부 불가
    with sqlite3.connect(trade["db"]) as db:
        assert db.execute("SELECT trust_score FROM users WHERE id=?", (b.id,)).fetchone()[0] == 35.5
        assert db.execute("SELECT COUNT(*) FROM reports WHERE target_id=?", (b.id,)).fetchone()[0] == 1
    # 노쇼 처리된 b 는 완료 조건에서 제외 → a 만 납부하면 완료 가능
    _complete_steps(trade, a)
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    # 노쇼 철회: 점수·신고 복원
    assert h.delete(f"/api/settlements/{sid}/shares/{b.id}/noshow").status_code == 200
    with sqlite3.connect(trade["db"]) as db:
        assert db.execute("SELECT trust_score FROM users WHERE id=?", (b.id,)).fetchone()[0] == 36.5
        assert db.execute("SELECT COUNT(*) FROM reports WHERE target_id=?", (b.id,)).fetchone()[0] == 0
    assert h.post(f"/api/settlements/{sid}/complete").status_code == 400   # b 다시 미납


def test_cancel_and_unpaid_join_block(trade):
    sid, h, a = trade["sid"], trade["host"], trade["a"]
    # 미납 정산이 있는 참여자는 다른 공동구매 참여 차단
    other = h.post("/posts", {"type": "groupbuy", "title": "다른공구", "gb_target": 3, "gb_price": 100}).json()["id"]
    assert a.post(f"/posts/{other}/join").status_code == 400
    assert a.post(f"/api/settlements/{sid}/cancel").status_code == 403           # 주최자만 취소
    assert h.post(f"/api/settlements/{sid}/cancel").status_code == 200
    assert h.post(f"/api/settlements/{sid}/cancel").status_code == 400           # 이미 취소
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400    # 취소된 정산에서 납부 불가
    assert a.post(f"/posts/{other}/join").status_code == 200                     # 취소 후 참여 가능
    # 취소 후 재생성 가능(중복 차단은 pending/completed 만)
    assert h.post("/api/settlements", {"post_id": trade["pid"], "total_amount": 6000}).status_code == 200


def test_post_appointment_inherited_by_settlement(client, make_user):
    h, a = make_user("host"), make_user("alice")
    pid = h.post("/posts", {"type": "groupbuy", "title": "공구", "gb_target": 2, "gb_price": 1000}).json()["id"]
    a.post(f"/posts/{pid}/join")
    r = h.post(f"/posts/{pid}/appointment", {"place": "정문", "appointment_at": "2026-10-20T09:00:00Z",
                                              "lat": APPT_LAT, "lng": APPT_LNG})
    assert r.status_code == 200 and r.json()["settlementSynced"] is False
    s = h.post("/api/settlements", {"post_id": pid, "total_amount": 1000}).json()["settlement"]
    assert "정문" in str(s) and s["id"]          # 채팅 단계 약속을 정산이 승계
