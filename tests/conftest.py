"""공용 pytest 픽스처 — 테스트마다 임시 SQLite DB 로 전체 앱(main.app)을 띄웁니다.

실제 data/neighborfood.db 는 건드리지 않습니다. (DB_PATH 를 가져다 쓰는 모든 app.* 모듈을 임시 경로로 교체)
실행: pip install pytest httpx  →  python -m pytest tests -q
"""
import sys
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import main                                   # app.* 모듈을 모두 import 시킴
    path = str(tmp_path / "test.db")
    for name, mod in list(sys.modules.items()):
        if name.startswith("app.") and hasattr(mod, "DB_PATH"):
            monkeypatch.setattr(mod, "DB_PATH", path)

    from app.db.base import init_all_databases
    from app.db import settlement_db
    from app.routers import portone
    init_all_databases()
    portone.init_db()
    settlement_db.init_settlement_extension()
    with TestClient(main.app) as c:               # lifespan 이 한 번 더 init(멱등)
        c.db_path = path
        yield c


class Api:
    """테스트 편의용 래퍼: 회원 가입/로그인 후 Bearer 헤더를 붙여 요청합니다."""
    def __init__(self, client, name, phone):
        self.c, self.name = client, name
        r = client.post("/api/auth/register", json={
            "login_id": name, "password": "pass1234",
            "phone_number": phone, "nickname": name})
        assert r.status_code in (200, 201), r.text
        r = client.post("/api/auth/login", json={"login_id": name, "password": "pass1234"})
        assert r.status_code == 200, r.text
        self.token, self.id = r.json()["token"], r.json()["userId"]

    @property
    def h(self):
        return {"Authorization": "Bearer " + self.token}

    def get(self, p, **k):    return self.c.get(p, headers=self.h, **k)
    def post(self, p, j=None): return self.c.post(p, headers=self.h, json=j if j is not None else {})
    def patch(self, p, j):    return self.c.patch(p, headers=self.h, json=j)
    def delete(self, p):      return self.c.delete(p, headers=self.h)


@pytest.fixture
def make_user(client):
    seq = iter(range(1, 100))
    def _make(name):
        n = next(seq)
        return Api(client, name, f"010-{n:04d}-{n:04d}")
    return _make
