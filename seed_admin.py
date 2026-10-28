#!/usr/bin/env python3
"""Explicitly promote or revoke an already registered account; no default credentials.

Run interactively against the intended database only after obtaining approval and
verifying a backup. This script does not create accounts or reset data.
"""
import argparse
import getpass

from app.core.utils import now_utc, to_iso
from app.db.auth_db import get_conn


def main():
    parser = argparse.ArgumentParser(description="기존 계정의 관리자 권한을 부여하거나 회수합니다.")
    parser.add_argument("action", choices=("promote", "revoke"))
    args = parser.parse_args()
    login_id = getpass.getpass("대상 계정 로그인 ID: ").strip()
    if not login_id:
        raise SystemExit("대상 계정이 필요합니다.")
    desired = "admin" if args.action == "promote" else "user"
    with get_conn() as conn:
        row = conn.execute("SELECT id, role, status FROM users WHERE login_id = ?", (login_id,)).fetchone()
        if not row:
            raise SystemExit("대상 계정을 찾을 수 없습니다. 먼저 일반 가입을 완료하세요.")
        if desired == "admin" and row["status"] != "active":
            raise SystemExit("활성 계정만 관리자 권한을 받을 수 있습니다.")
        if row["role"] == desired:
            print("이미 요청한 권한 상태입니다. 변경하지 않았습니다.")
            return
        if input("대상 DB와 백업을 확인했습니다. 변경하려면 CONFIRM 입력: ").strip() != "CONFIRM":
            raise SystemExit("변경을 취소했습니다.")
        conn.execute("UPDATE users SET role = ?, updated_at = ? WHERE id = ?", (desired, to_iso(now_utc()), row["id"]))
        conn.commit()
    print("관리자 권한 변경 완료. 시연 종료 후 회수 여부를 확인하세요.")


if __name__ == "__main__":
    main()
