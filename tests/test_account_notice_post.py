"""비밀번호 변경 · 공개 공지 · 게시글 수정 확장 API 테스트."""
import sqlite3


# ── 비밀번호 변경 ─────────────────────────────────────────────
def test_password_change_flow(client, make_user):
    u = make_user("pwuser")
    other = client.post("/api/auth/login", json={"login_id": "pwuser", "password": "pass1234"}).json()["token"]

    # 현재 비밀번호 오답 → 401
    assert u.patch("/api/users/me/password",
                   {"current_password": "wrong!!", "new_password": "newpass99"}).status_code == 401
    # 새 비밀번호 6자 미만 → 422, 동일 비밀번호 → 400
    assert u.patch("/api/users/me/password",
                   {"current_password": "pass1234", "new_password": "123"}).status_code == 422
    assert u.patch("/api/users/me/password",
                   {"current_password": "pass1234", "new_password": "pass1234"}).status_code == 400
    # 성공
    assert u.patch("/api/users/me/password",
                   {"current_password": "pass1234", "new_password": "newpass99"}).status_code == 200

    # 현재 세션은 유지, 다른 기기 세션은 만료
    assert u.get("/api/users/me").status_code == 200
    assert client.get("/api/users/me", headers={"Authorization": "Bearer " + other}).status_code == 401

    # 옛 비밀번호 로그인 실패 / 새 비밀번호 로그인 성공
    assert client.post("/api/auth/login", json={"login_id": "pwuser", "password": "pass1234"}).status_code != 200
    assert client.post("/api/auth/login", json={"login_id": "pwuser", "password": "newpass99"}).status_code == 200


def test_password_change_requires_login(client):
    r = client.patch("/api/users/me/password", json={"current_password": "a", "new_password": "bbbbbb"})
    assert r.status_code == 401


# ── 공개 공지 ─────────────────────────────────────────────────
def test_public_notices(client):
    assert client.get("/api/notices").json() == {"count": 0, "items": []}
    with sqlite3.connect(client.db_path) as db:
        for i in range(3):
            db.execute("INSERT INTO notices (author_id, title, content, created_at) VALUES (NULL, ?, ?, ?)",
                       (f"공지{i}", f"내용{i}", f"2026-10-0{i+1}T00:00:00Z"))
    body = client.get("/api/notices?limit=2").json()          # 로그인 없이 조회, 최신순
    assert body["count"] == 2
    assert [n["title"] for n in body["items"]] == ["공지2", "공지1"]
    assert set(body["items"][0]) == {"id", "title", "content", "created_at"}   # 작성자 정보 비노출
    assert client.get("/api/notices?limit=0").status_code == 422


# ── 게시글 수정 확장 ──────────────────────────────────────────
def _gb(u, **k):
    body = {"type": "groupbuy", "title": "공구", "gb_target": 3, "gb_price": 3000}
    body.update(k)
    r = u.post("/posts", body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_post_edit_images_and_type(client, make_user):
    host = make_user("host")
    pid = _gb(host)
    # 사진 교체 / 인원·가격 변경 (참여자 없음)
    r = host.patch(f"/posts/{pid}", {"images": ["a.jpg", "b.jpg"], "gb_target": 5, "gb_price": 4500})
    assert r.status_code == 200, r.text
    assert r.json()["images"] == ["a.jpg", "b.jpg"] and r.json()["gb_target"] == 5 and r.json()["gb_price"] == 4500
    assert host.patch(f"/posts/{pid}", {"images": []}).json()["images"] == []
    assert host.patch(f"/posts/{pid}", {"images": ["x"] * 11}).status_code == 400
    # 검증: 목표 인원 2 미만, 가격 0 이하
    assert host.patch(f"/posts/{pid}", {"gb_target": 1}).status_code == 400
    assert host.patch(f"/posts/{pid}", {"gb_price": 0}).status_code == 400
    # 유형 변경 groupbuy → share: gb 필드 정리
    r = host.patch(f"/posts/{pid}", {"type": "share"})
    assert r.status_code == 200 and r.json()["type"] == "share" and r.json()["gb_target"] is None
    # share → groupbuy 는 인원·가격 필수
    assert host.patch(f"/posts/{pid}", {"type": "groupbuy"}).status_code == 400
    r = host.patch(f"/posts/{pid}", {"type": "groupbuy", "gb_target": 4, "gb_price": 1000})
    assert r.status_code == 200 and r.json()["gb_current"] == 0
    # share 게시글에 인원/가격만 지정 → 400
    share = host.post("/posts", {"type": "share", "title": "나눔"}).json()["id"]
    assert host.patch(f"/posts/{share}", {"gb_target": 3}).status_code == 400


def test_post_edit_locked_after_join(client, make_user):
    host, guest = make_user("host"), make_user("guest")
    pid = _gb(host)
    assert guest.post(f"/posts/{pid}/join").status_code == 200
    for body in ({"gb_target": 4}, {"gb_price": 100}, {"type": "share"}):
        assert host.patch(f"/posts/{pid}", body).status_code == 409
    # 제목·사진은 계속 수정 가능
    assert host.patch(f"/posts/{pid}", {"title": "새 제목", "images": ["z.jpg"]}).status_code == 200
    # 타인은 수정 불가
    assert guest.patch(f"/posts/{pid}", {"title": "hack"}).status_code == 403
