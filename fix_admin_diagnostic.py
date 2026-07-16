#!/usr/bin/env python3

# Admin 로그인 401 진단 스크립트
# 실행: python fix_admin_diagnostic.py
# 위치: C:\Projects\Neighborfood_Merged\ (프로젝트 루트)

import sqlite3, sys

DB_PATH = "data/neighborfood.db"

print("=" * 60)
print("  Admin 로그인 401 원인 진단")
print("=" * 60)

# 1) DB에서 Admin 계정 확인
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, login_id, status, password_hash FROM users WHERE login_id = 'Admin'"
    ).fetchone()
    conn.close()
except Exception as e:
    print(f"\n✘ DB 연결 실패: {e}")
    sys.exit(1)

if not row:
    print("\n✘ Admin 계정이 DB에 없습니다. reset_db.py --yes --pw admin0000 을 다시 실행하세요.")
    sys.exit(1)

print(f"\n✔ Admin 계정 발견 (id={row['id']}, status={row['status']})")
stored_hash = row["password_hash"]
print(f"  저장된 해시 앞 50자: {stored_hash[:50]}")

# 해시 형식 판별
if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
    fmt = "bcrypt"
elif stored_hash.startswith("pbkdf2:"):
    fmt = "werkzeug PBKDF2"
elif "$" in stored_hash and stored_hash.count("$") == 1:
    fmt = "custom salt$hash (app.core.utils)"
else:
    fmt = f"알 수 없음 (prefix={stored_hash[:10]!r})"
print(f"  해시 형식: {fmt}")

# 2) verify_password 시도
pw_to_test = "admin0000"
print(f"\n[verify_password 테스트] 비밀번호: {pw_to_test!r}")

try:
    from app.core.utils import verify_password
    result = verify_password(pw_to_test, stored_hash)
    if result:
        print(f"  ✔ app.core.utils.verify_password → True  (로그인이 성공해야 함)")
        print("\n  원인이 다른 곳에 있습니다. 가능성:")
        print("  1) 테스트 실행 전 서버를 재시작했는지 확인")
        print("  2) ADMIN_PW 환경변수 확인: python -c \"import os; print(os.environ.get('ADMIN_PW', '미설정'))\"")
    else:
        print(f"  ✘ app.core.utils.verify_password → False")
        print(f"\n  원인: reset_db.py가 다른 hash_password 함수를 사용했을 가능성")
        print(f"  해결: reset_db.py를 아래 명령으로 다시 실행하세요:")
        print(f"        python reset_db.py --yes --pw admin0000")
        print(f"  그 후 바로 테스트: set ADMIN_PW=admin0000 && python nf_functional_test.py")
except ImportError as e:
    print(f"  ✘ app.core.utils import 실패: {e}")
    print("  앱 소스가 다른 hash 함수를 사용 중일 수 있습니다.")

# 3) 수동 검증 (custom format)
if "$" in stored_hash and stored_hash.count("$") == 1:
    import hashlib, secrets
    try:
        salt, expected = stored_hash.split("$", 1)
        for iters in [200_000, 260_000, 310_000, 100_000]:
            dk = hashlib.pbkdf2_hmac("sha256", pw_to_test.encode("utf-8"),
                                     salt.encode("utf-8"), iters)
            if secrets.compare_digest(dk.hex(), expected):
                print(f"\n  ✔ 수동 PBKDF2 검증 성공 (iterations={iters})")
                break
        else:
            print(f"\n  ✘ 수동 PBKDF2 검증 실패 (salt$hash 형식이지만 password가 일치하지 않음)")
    except Exception as e2:
        print(f"  수동 검증 오류: {e2}")

print("\n" + "=" * 60)