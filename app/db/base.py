import sqlite3


def make_conn(path: str, foreign_keys: bool = False) -> sqlite3.Connection:
    """SQLite 연결을 생성하고 WAL 모드·busy timeout을 설정합니다.
    컨텍스트 매니저(with make_conn(...) as conn:)로 사용하세요."""
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_all_databases() -> None:
    """서버 시작 시 1회 호출: 모든 DB 테이블을 생성/마이그레이션합니다.
    부모 테이블을 먼저 초기화하도록 순서를 유지해야 합니다."""
    from app.db.auth_db            import init_auth_db
    from app.db.qr_db              import init_qr_db
    from app.db.receipt_db         import init_receipt_db
    from app.db.transaction_db     import init_transaction_db
    from app.db.member_db          import init_member_db
    from app.db.fridge_db          import init_fridge_db
    from app.db.admin_db           import init_admin_db
    from app.db.location_verify_db import init_location_verify_db

    init_auth_db()              # ① users · sessions · auth_codes · posts
    init_transaction_db()       # ② transactions · groupbuy_participants
    init_qr_db()                # ③ qr_sessions
    init_receipt_db()           # ④ receipts
    init_member_db()            # ⑤ wishlists · conversations · messages
    init_fridge_db()            # ⑥ fridge_items
    init_admin_db()             # ⑦ notices · reports
    init_location_verify_db()   # ⑧ location_verify_sessions
