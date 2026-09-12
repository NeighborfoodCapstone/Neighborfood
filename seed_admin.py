#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_admin.py — 관리자 계정 부트스트랩 / 승격 스크립트

README.md · NeighborFood_Architecture_Plan.md 에 문서화되어 있었으나 저장소에는
존재하지 않던 스크립트를 동일한 사용법으로 복원한 것입니다.

배치 위치: 프로젝트 루트 (main.py 와 같은 위치)

사용법:
    python seed_admin.py                 # 신규 관리자 계정 생성 (login_id=Admin, pw=admin0000)
    python seed_admin.py <login_id>      # 이미 가입된 계정을 admin 역할로 승격

주의사항:
- 서버(main.py)를 한 번도 실행하지 않아 data/neighborfood.db 및 users 테이블이
  아직 생성되지 않았다면, 먼저 `python main.py`로 서버를 한 번 띄웠다가 종료한 뒤
  이 스크립트를 실행하세요. (서버 시작 시 app/db/base.py의 init_all_databases()가
  테이블을 만듭니다.)
- 비밀번호 해시는 app/core/utils.py의 hash_password()와 동일한 방식
  (PBKDF2-HMAC-SHA256, salt$hash, 200,000회 반복)을 그대로 사용하므로,
  이 스크립트로 만든 계정은 기존 로그인 API(POST /api/auth/login 등)로 바로
  로그인할 수 있습니다.
- 이 스크립트는 users 테이블만 다루며 idempotent 합니다(여러 번 실행해도 안전).
"""

import os
import sys
import sqlite3
import secrets
import hashlib
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "neighborfood.db")

DEFAULT_LOGIN_ID = "Admin"
DEFAULT_PASSWORD = "admin0000"
DEFAULT_PHONE    = "010-0000-0000"   # UNIQUE NOT NULL 컬럼용 자리표시 번호
DEFAULT_NICKNAME = "관리자"

PBKDF2_ITER = 200_000


def hash_password(password: str) -> str:
    """app/core/utils.py의 hash_password()와 동일한 알고리즘."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITER
    )
    return f"{salt}${dk.hex()}"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect():
    if not os.path.exists(DB_PATH):
        print(f"[오류] DB 파일이 없습니다: {DB_PATH}")
        print("       먼저 `python main.py`로 서버를 한 번 실행해 DB를 초기화한 뒤 다시 시도하세요.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("SELECT 1 FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("[오류] users 테이블이 없습니다. 먼저 서버를 한 번 실행해 DB를 초기화하세요.")
        sys.exit(1)
    return conn


def promote(conn, login_id: str) -> None:
    row = conn.execute(
        "SELECT id, role FROM users WHERE login_id = ?", (login_id,)
    ).fetchone()
    if not row:
        print(f"[오류] login_id='{login_id}' 계정을 찾을 수 없습니다. 먼저 Signup.html로 가입하세요.")
        sys.exit(1)
    if row["role"] == "admin":
        print(f"[안내] '{login_id}' 계정은 이미 admin입니다. 변경 사항 없음.")
        return
    conn.execute(
        "UPDATE users SET role = 'admin', updated_at = ? WHERE id = ?",
        (now_iso(), row["id"]),
    )
    conn.commit()
    print(f"[완료] '{login_id}' 계정을 admin으로 승격했습니다.")


def create_default(conn) -> None:
    row = conn.execute(
        "SELECT id, role FROM users WHERE login_id = ?", (DEFAULT_LOGIN_ID,)
    ).fetchone()
    if row:
        if row["role"] != "admin":
            conn.execute(
                "UPDATE users SET role = 'admin', updated_at = ? WHERE id = ?",
                (now_iso(), row["id"]),
            )
            conn.commit()
        print(f"[안내] '{DEFAULT_LOGIN_ID}' 계정이 이미 존재합니다 (role=admin 보장됨).")
        print(f"       로그인: {DEFAULT_LOGIN_ID} / (최초 생성 시 설정한 비밀번호)")
        return

    now = now_iso()
    try:
        conn.execute(
            """
            INSERT INTO users (login_id, password_hash, phone_number, nickname,
                                trust_score, role, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 36.5, 'admin', 'active', ?, ?)
            """,
            (
                DEFAULT_LOGIN_ID,
                hash_password(DEFAULT_PASSWORD),
                DEFAULT_PHONE,
                DEFAULT_NICKNAME,
                now,
                now,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"[오류] 계정 생성 실패({e}). phone_number='{DEFAULT_PHONE}'가 이미 다른 계정에 "
              f"사용 중일 수 있습니다. 이미 가입된 계정이 있다면 `python seed_admin.py <login_id>`로 승격하세요.")
        sys.exit(1)

    print(f"[완료] 관리자 계정 생성됨 → login_id={DEFAULT_LOGIN_ID} / password={DEFAULT_PASSWORD}")


def main() -> None:
    conn = connect()
    args = sys.argv[1:]
    if args:
        promote(conn, args[0])
    else:
        create_default(conn)
    conn.close()


if __name__ == "__main__":
    main()
