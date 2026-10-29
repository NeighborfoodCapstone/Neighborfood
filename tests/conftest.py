"""공용 pytest 픽스처 — 테스트마다 임시 SQLite DB로 전체 앱을 띄웁니다.

설치: python -m pip install -r requirements-test.txt
실행: python -m pytest -q
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# 테스트 수집 중 app.config와 main이 환경파일을 읽지 않도록 앱 import 전에 격리합니다.
for name in (
    "DATABASE_URL", "VERCEL", "SUPABASE_URL", "SUPABASE_SECRET_KEY",
    "CLOVA_OCR_INVOKE_URL", "CLOVA_OCR_SECRET", "PORTONE_TEST_ENABLED",
    "PORTONE_STORE_ID", "PORTONE_CHANNEL_KEY", "PORTONE_API_SECRET", "KAKAO_JS_KEY",
):
    os.environ[name] = ""

_env_file = Path(__file__).resolve().parents[1] / ".env"
_path_exists = Path.exists
with patch("dotenv.load_dotenv", return_value=False), patch.object(
    Path, "exists", lambda path: path != _env_file and _path_exists(path)
):
    import main
    from app.db import receipt_db

# 영수증 OCR의 별도 수동 환경파일 로더도 테스트 중에는 사용하지 않습니다.
receipt_db._DOTENV_LOADED = True


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("VERCEL", "")
    path = str(tmp_path / "test.db")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    for name, mod in list(sys.modules.items()):
        if name.startswith("app."):
            for attr, value in (("DB_PATH", path), ("DATA_DIR", str(tmp_path)), ("UPLOAD_DIR", str(upload_dir))):
                if hasattr(mod, attr):
                    monkeypatch.setattr(mod, attr, value)
    monkeypatch.setattr(main, "UPLOAD_DIR", str(upload_dir))

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
