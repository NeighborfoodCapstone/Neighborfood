#!/usr/bin/env python3

# Admin 비밀번호를 app.core.utils.hash_password로 재설정합니다.
# 실행: python fix_admin_password.py
# 위치: C:\Projects\Neighborfood_Merged\ (프로젝트 루트)

import sqlite3, sys

DB_PATH  = "data/neighborfood.db"
NEW_PW   = "admin0000"

print("=" * 60)
print("  Admin 비밀번호 재설정 (app.core.utils 기반)")
print("=" * 60)

# 1) 정규 hash_password 임포트
try:
    from app.core.utils import hash_password, verify_password
    print("\n✔ app.core.utils.hash_password 로드 성공")
except ImportError as e:
    print(f"\n✘ 임포트 실패: {e}")
    sys.exit(1)

# 2) 해시 생성 및 즉시 검증
new_hash = hash_password(NEW_PW)
if not verify_password(NEW_PW, new_hash):
    print("✘ 해시 생성 직후 verify 실패 — utils.py 로직 오류")
    sys.exit(1)
print(f"✔ 새 해시 생성 성공 (앞 40자: {new_hash[:40]}…)")
print(f"✔ verify_password('{NEW_PW}', new_hash) → True")

# 3) DB 업데이트
try:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE login_id = 'Admin'",
        (new_hash, now)
    )
    conn.commit()
    if cur.rowcount == 0:
        print("\n✘ Admin 계정을 찾을 수 없습니다. reset_db.py --yes --pw admin0000 을 먼저 실행하세요.")
        conn.close()
        sys.exit(1)
    conn.close()
    print(f"\n✔ DB 업데이트 완료 (영향 행: {cur.rowcount})")
except Exception as e:
    print(f"\n✘ DB 업데이트 실패: {e}")
    sys.exit(1)

# 4) 최종 검증
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT password_hash FROM users WHERE login_id = 'Admin'").fetchone()
conn.close()
ok = verify_password(NEW_PW, row["password_hash"])
print(f"✔ 최종 검증 — verify_password('{NEW_PW}', 저장값) → {ok}")

if ok:
    print("\n  Admin 비밀번호가 성공적으로 재설정되었습니다.")
    print(f"  login_id : Admin")
    print(f"  password : {NEW_PW}")
    print("\n  다음 단계:")
    print("    set ADMIN_PW=admin0000 && python nf_functional_test.py")
else:
    print("\n✘ 최종 검증 실패 — 다른 원인 조사 필요")

print("=" * 60)