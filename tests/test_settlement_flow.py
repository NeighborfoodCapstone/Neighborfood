"""정산 흐름 자동화 테스트: 약속 → GPS(100m, 서버 재검증) → QR → 납부 → 완료 → 매너 평가.

GPS/QR '증거' 행(location_verify_sessions, qr_sessions)은 DB 에 직접 심고,
정산 API 가 그 증거로 단계를 올바르게 통과/차단하는지를 검증합니다.
(실제 GPS·QR 발급 라우터 자체는 별도 기능이며 여기서는 대상이 아닙니다.)
"""
import sqlite3
import pytest

APPT_LAT, APPT_LNG = 37.5665, 126.9780        # 약속 좌표(서울시청)
NEAR = (37.5666, 126.9781)                    # 약 15m
FAR  = (37.5800, 126.9780)                    # 약 1.5km


_tick = iter(range(1, 10_000))


def _seed_gps(db_path, user_id, lat, lng):
    """가장 최근(verified_at 이 더 큰) 기록이 검증에 쓰이므로 호출 순서대로 시각을 증가시킨다."""
    with sqlite3.connect(db_path) as db:
        n = next(_tick)
        db.execute("""INSERT INTO location_verify_sessions
            (id, subject_id, target_lat, target_lng, status, current_lat, current_lng, verified_at)
            VALUES (?, ?, ?, ?, 'LOCATION_VERIFIED', ?, ?, ?)""",
            (f"gps-{n}", str(user_id), APPT_LAT, APPT_LNG, lat, lng,
             f"2026-10-08T00:{n // 60:02d}:{n % 60:02d}Z"))


def _seed_qr(db_path, user_id):
    with sqlite3.connect(db_path) as db:
        db.execute("""INSERT INTO qr_sessions
            (id, subject_id, purpose, token_hash, status, issued_at, expires_at, created_at, updated_at)
            VALUES (?, ?, 'trade', ?, 'VERIFIED', 't', 't', 't', 't')""",
            (f"qr-{user_id}", str(user_id), f"hash-{user_id}"))


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
    _seed_gps(t["db"], user.id, *lat_lng)
    assert user.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 200
    _seed_qr(t["db"], user.id)
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


# ── 약속 / GPS / QR 게이트 ────────────────────────────────────
def test_gps_requires_appointment_then_distance(trade):
    sid, a, h = trade["sid"], trade["a"], trade["host"]
    assert a.post(f"/api/settlements/{sid}/appointment", {"place": "x"}).status_code == 403          # 주최자만
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 400                    # 약속 없음
    _appoint(trade)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 400                    # GPS 기록 없음
    _seed_gps(trade["db"], a.id, *FAR)
    r = a.post(f"/api/settlements/{sid}/shares/me/gps-done")
    assert r.status_code == 400 and "m" in r.json()["detail"]                                         # 100m 초과
    _seed_gps(trade["db"], a.id, *NEAR)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 200                    # 100m 이내
    # 주최자는 분담 대상이 아님
    assert h.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 403


def test_qr_requires_gps_first_and_pay_requires_both(trade):
    sid, a = trade["sid"], trade["a"]
    _appoint(trade)
    _seed_qr(trade["db"], a.id)
    assert a.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 400                     # GPS 선행
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400                         # GPS 없이 납부
    _seed_gps(trade["db"], a.id, *NEAR)
    assert a.post(f"/api/settlements/{sid}/shares/me/gps-done").status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 400                         # QR 없이 납부
    assert a.post(f"/api/settlements/{sid}/shares/me/qr-done").status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 200
    assert a.post(f"/api/settlements/{sid}/shares/me/pay").status_code == 409                         # 중복 납부


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
