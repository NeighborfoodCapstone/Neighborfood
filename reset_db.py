#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeighborFood DB 초기화 스크립트
- 모든 회원·게시글 및 연관 데이터를 삭제합니다.
- Admin 계정을 지정한 비밀번호로 새로 생성합니다.

실행:  python reset_db.py
       python reset_db.py --yes          (확인 프롬프트 생략)
       python reset_db.py --pw MyPass1!  (비밀번호 직접 지정)
"""

import sqlite3, hashlib, secrets, sys, importlib, argparse
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────
DB_PATH        = Path("data/neighborfood.db")
ADMIN_LOGIN_ID = "Admin"
ADMIN_PASSWORD = "Admin1234!"   # --pw 옵션으로 덮어쓸 수 있음
ADMIN_PHONE    = "01000000000"
ADMIN_NICKNAME = "관리자"

GREEN  = "\033[92m"; RED  = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD = "\033[1m";  RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✔{RESET} {msg}")
def err(msg):  print(f"  {RED}✘{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}△{RESET} {msg}")
def hdr(msg):  print(f"\n{BOLD}{CYAN}{'─'*52}{RESET}\n{BOLD}{CYAN}  {msg}{RESET}\n{BOLD}{CYAN}{'─'*52}{RESET}")


# ── 비밀번호 해시 ──────────────────────────────────────────────────────────
def _try_app_hash(pw: str):
    """앱 소스의 해시 함수를 탐색해 우선 사용"""
    candidates = [
        ("app.core.utils",     "hash_password"),   # ← 최우선: 로그인 verify와 동일 모듈
        ("app.core.security",  "hash_password"),
        ("app.core.security",  "get_password_hash"),
        ("app.utils.security", "hash_password"),
        ("app.utils.security", "get_password_hash"),
        ("app.auth.security",  "hash_password"),
        ("app.auth.security",  "get_password_hash"),
        ("app.routers.auth",   "hash_password"),
        ("app.routers.auth",   "get_password_hash"),
        ("app.dependencies",   "hash_password"),
    ]
    for mod_name, fn_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn  = getattr(mod, fn_name, None)
            if callable(fn):
                result = fn(pw)
                ok(f"해시: {mod_name}.{fn_name}() 사용")
                return result
        except Exception:
            continue
    return None

def make_hash(pw: str) -> str:
    # 1순위: 앱 내 해시 함수
    h = _try_app_hash(pw)
    if h:
        return h

    # 2순위: passlib bcrypt
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        ok("해시: passlib bcrypt 사용")
        return ctx.hash(pw)
    except ImportError:
        pass

    # 3순위: werkzeug pbkdf2
    try:
        from werkzeug.security import generate_password_hash
        ok("해시: werkzeug pbkdf2 사용")
        return generate_password_hash(pw)
    except ImportError:
        pass

    # 최후 수단: pure-Python PBKDF2
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000)
    warn("해시: pure-python PBKDF2 사용 — 앱 검증 포맷과 다를 수 있음")
    return f"pbkdf2:sha256:260000${salt}${dk.hex()}"


# ── 테이블 삭제 ────────────────────────────────────────────────────────────
# 외래키 의존도 기준: 자식 테이블부터 삭제
_DELETE_PRIORITY = [
    "chat_messages", "group_chat_messages",
    "chats", "group_chats",
    "wishlist", "wishlists",
    "post_joins", "post_participants", "groupbuy_participants",
    "qr_transactions", "qr_sessions", "qr_codes", "qr_requests",
    "receipt_items", "receipts", "receipt_verifications",
    "fridge_items",
    "location_verify_sessions", "location_sessions", "gps_sessions",
    "transactions",
    "reports",
    "notices", "admin_notices",
    "posts",
    "users",
]

def clear_tables(conn: sqlite3.Connection, tables: list[str]):
    conn.execute("PRAGMA foreign_keys = OFF")

    ordered   = [t for t in _DELETE_PRIORITY if t in tables]
    remaining = [t for t in tables if t not in ordered]

    for tbl in ordered + remaining:
        conn.execute(f"DELETE FROM [{tbl}]")
        ok(f"DELETE FROM {tbl}")

    # sqlite_sequence 초기화 → id가 1부터 다시 시작
    all_tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if "sqlite_sequence" in all_tables:
        conn.execute("DELETE FROM sqlite_sequence")
        ok("sqlite_sequence 초기화 (auto-increment 리셋)")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


# ── Admin 계정 생성 ────────────────────────────────────────────────────────
def create_admin(conn: sqlite3.Connection, pw: str):
    # 실제 컬럼 확인
    cols_info = conn.execute("PRAGMA table_info(users)").fetchall()
    cols = {r[1] for r in cols_info}

    if not cols:
        err("users 테이블을 찾을 수 없습니다.")
        return False

    pw_hash = make_hash(pw)
    now     = datetime.now().isoformat()

    # 컬럼명 후보 매핑
    col_map = {
        "login_id":    ("login_id", "username", "user_id", "account"),
        "password":    ("password", "password_hash", "hashed_password", "pw"),
        "phone":       ("phone_number", "phone", "mobile"),
        "nickname":    ("nickname", "nick", "display_name", "name"),
        "role":        ("role", "user_role", "is_admin"),
        "status":      ("status", "user_status", "is_active"),
        "created_at":  ("created_at", "created", "joined_at", "register_date"),
        "updated_at":  ("updated_at", "updated"),
    }

    def find_col(candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    c_login      = find_col(col_map["login_id"])
    c_password   = find_col(col_map["password"])
    c_phone      = find_col(col_map["phone"])
    c_nickname   = find_col(col_map["nickname"])
    c_role       = find_col(col_map["role"])
    c_status     = find_col(col_map["status"])
    c_created    = find_col(col_map["created_at"])
    c_updated    = find_col(col_map["updated_at"])

    if not c_login or not c_password:
        err(f"필수 컬럼 미발견 — users 컬럼 목록: {sorted(cols)}")
        return False

    # INSERT 구성
    insert_cols = [c_login, c_password]
    insert_vals = [ADMIN_LOGIN_ID, pw_hash]

    for col, val in [
        (c_phone,    ADMIN_PHONE),
        (c_nickname, ADMIN_NICKNAME),
        (c_role,     "admin"),
        (c_status,   "active"),
        (c_created,  now),
        (c_updated,  now),
    ]:
        if col:
            insert_cols.append(col)
            insert_vals.append(val)

    sql = (f"INSERT INTO users ({', '.join(insert_cols)}) "
           f"VALUES ({', '.join(['?']*len(insert_vals))})")

    try:
        cur = conn.execute(sql, insert_vals)
        conn.commit()
        ok(f"Admin 계정 생성 완료 (id={cur.lastrowid})")
        return True
    except Exception as e:
        err(f"Admin 계정 생성 실패: {e}")
        warn(f"users 실제 컬럼: {sorted(cols)}")
        conn.rollback()
        return False


# ── 메인 ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NeighborFood DB 초기화")
    parser.add_argument("--yes", action="store_true", help="확인 프롬프트 생략")
    parser.add_argument("--pw", default=ADMIN_PASSWORD, help="Admin 비밀번호 지정")
    args = parser.parse_args()

    if not DB_PATH.exists():
        err(f"DB 파일 없음: {DB_PATH}")
        sys.exit(1)

    if not args.yes:
        print(f"\n{YELLOW}{BOLD}⚠  경고{RESET}")
        print(f"  {DB_PATH} 의 모든 회원·게시글 데이터가 삭제됩니다.")
        print(f"  Admin 계정이 login_id='{ADMIN_LOGIN_ID}' / pw='{args.pw}' 로 새로 생성됩니다.\n")
        ans = input("  계속하시겠습니까? (y/N): ").strip().lower()
        if ans != "y":
            print("  취소됨.")
            sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    # 테이블 목록
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]

    hdr("1. 데이터 삭제")
    print(f"  발견된 테이블 ({len(tables)}개): {', '.join(tables)}\n")
    clear_tables(conn, tables)

    hdr("2. Admin 계정 생성")
    success = create_admin(conn, args.pw)

    conn.close()

    hdr("완료")
    if success:
        print(f"  {GREEN}{BOLD}DB 초기화 성공{RESET}\n")
        print(f"  Admin 로그인 정보")
        print(f"    login_id : {ADMIN_LOGIN_ID}")
        print(f"    password : {args.pw}\n")
        print(f"  다음 단계:")
        print(f"    1. python seed_admin.py     (role 확인, 선택사항)")
        print(f"    2. python nf_functional_test.py")
        print(f"       또는: set ADMIN_PW={args.pw} && python nf_functional_test.py")
    else:
        print(f"  {YELLOW}테이블 삭제는 완료됐으나 Admin 계정 생성에 실패했습니다.{RESET}")
        print(f"  users 테이블 컬럼명을 확인한 뒤 스크립트 상단 col_map을 수정하세요.")
    print()


if __name__ == "__main__":
    main()