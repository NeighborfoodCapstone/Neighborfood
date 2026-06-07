import sqlite3


def make_conn(path: str, foreign_keys: bool = False) -> sqlite3.Connection:
    """
    SQLite 연결 팩토리.
    모든 DB 연결은 이 함수를 통해 생성합니다.
    - row_factory를 sqlite3.Row로 설정해 컬럼명으로 접근 가능합니다.
    - foreign_keys=True 시 외래 키 제약 활성화 (receipt_db 전용).
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_all_databases() -> None:
    """
    서버 startup 이벤트에서 호출.
    모든 DB 스키마를 한 번에 초기화합니다 (idempotent).
    """
    from app.db.auth_db    import init_auth_db
    from app.db.qr_db      import init_qr_db
    from app.db.receipt_db import init_receipt_db

    init_auth_db()
    init_qr_db()
    init_receipt_db()
