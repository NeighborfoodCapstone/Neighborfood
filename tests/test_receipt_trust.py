"""Receipt verification must update trust once, never for manual entries."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest
from app.db import receipt_db


def test_receipt_trust_once_and_manual_no_credit(client, make_user):
    user = make_user('receipt_trust_user')
    before = user.get('/api/users/me').json()['trustScore']
    now = '2026-01-01T00:00:00Z'
    with receipt_db.get_conn() as conn:
        conn.execute("""INSERT INTO receipts
            (id, subject_id, items, status, ocr_engine, scanned_at, created_at, updated_at)
            VALUES (?, ?, ?, 'SCANNED', 'clova', ?, ?, ?)""",
            ('scan-trust', str(user.id), '[{"name":"우유","qty":1,"price":1000}]', now, now, now))
        conn.commit()
    payload = {'scanId':'scan-trust', 'items':[{'name':'우유','qty':1,'price':1000}]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: user.post('/api/receipt/verify', payload).json(), range(2)))
    assert sum(result.get('result') == 'verified' for result in results) == 1
    assert user.get('/api/users/me').json()['trustScore'] == pytest.approx(before + 0.3)
    manual = user.post('/api/receipt/verify', {'items':[{'name':'직접 입력','qty':1,'price':1000}]}).json()
    assert manual['result'] == 'verified' and manual['trustDelta'] == 0
    assert user.get('/api/users/me').json()['trustScore'] == pytest.approx(before + 0.3)
    with receipt_db.get_conn() as conn:
        conn.execute("UPDATE users SET trust_score = 98.9 WHERE id = ?", (user.id,))
        conn.execute("""INSERT INTO receipts
            (id, subject_id, items, status, ocr_engine, scanned_at, created_at, updated_at)
            VALUES (?, ?, ?, 'SCANNED', 'clova', ?, ?, ?)""",
            ('scan-cap', str(user.id), '[{"name":"우유","qty":1,"price":1000}]', now, now, now))
        conn.commit()
    capped = user.post('/api/receipt/verify', {**payload, 'scanId':'scan-cap'}).json()
    assert capped['trustDelta'] == pytest.approx(0.1)
    assert user.get('/api/users/me').json()['trustScore'] == pytest.approx(99)


def test_receipt_and_trust_rollback_together_on_user_update_failure(client, make_user):
    user = make_user('receipt_rollback')
    before = user.get('/api/users/me').json()['trustScore']
    now = '2026-01-01T00:00:00Z'
    with receipt_db.get_conn() as conn:
        conn.execute("""INSERT INTO receipts
            (id, subject_id, items, status, ocr_engine, scanned_at, created_at, updated_at)
            VALUES (?, ?, ?, 'SCANNED', 'clova', ?, ?, ?)""",
            ('scan-rollback', str(user.id), '[{"name":"우유","qty":1,"price":1000}]', now, now, now))
        conn.execute(f"""CREATE TRIGGER reject_trust_update BEFORE UPDATE OF trust_score ON users
            WHEN NEW.id = {user.id} BEGIN SELECT RAISE(ABORT, 'injected failure'); END""")
        conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        user.post('/api/receipt/verify', {'scanId':'scan-rollback','items':[{'name':'우유','qty':1,'price':1000}]})
    with receipt_db.get_conn() as conn:
        assert conn.execute("SELECT status FROM receipts WHERE id = 'scan-rollback'").fetchone()['status'] == 'SCANNED'
        assert conn.execute("SELECT trust_score FROM users WHERE id = ?", (user.id,)).fetchone()['trust_score'] == before
