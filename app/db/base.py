import sqlite3


def make_conn(path: str, foreign_keys: bool = False) -> sqlite3.Connection:
    """
    SQLite 연결 팩토리. 모든 DB 연결은 이 함수를 통해 생성합니다.
    - timeout + busy_timeout + WAL 저널로 단일 파일 동시 접근 시
      'database is locked' 위험을 완화합니다.
    - row_factory를 sqlite3.Row로 설정해 컬럼명으로 접근 가능합니다.
    - foreign_keys=True 시 외래 키 제약 활성화 (통합 DB는 항상 True).
    """
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")    # 읽기/쓰기 동시성 개선 (1회 설정으로 영속)
    conn.execute("PRAGMA busy_timeout = 5000")   # 잠금 시 최대 5초 대기 후 재시도
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_all_databases() -> None:
    """
    서버 startup 이벤트에서 호출.
    단일 통합 DB(neighborfood.db) 안에 모든 테이블을 초기화합니다 (idempotent).
    FK 부모 테이블(users·posts)이 먼저 생성되도록 순서를 보장합니다.
    """
    from app.db.auth_db        import init_auth_db
    from app.db.qr_db          import init_qr_db
    from app.db.receipt_db     import init_receipt_db
    from app.db.transaction_db import init_transaction_db

    init_auth_db()          # ① users · sessions · auth_codes · posts
    init_transaction_db()   # ② transactions · groupbuy_participants (posts·users 참조)
    init_qr_db()            # ③ qr_sessions
    init_receipt_db()       # ④ receipts
