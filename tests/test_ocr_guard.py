"""OCR budget and authorization checks; never contact an external provider."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from datetime import datetime, timedelta, timezone
from threading import Lock
from PIL import Image

from app.db import ocr_guard, receipt_db

_image = BytesIO()
Image.new('RGB', (1, 1), 'white').save(_image, format='PNG')
PNG = _image.getvalue()


def settings(**changes):
    with ocr_guard.get_conn() as conn:
        for key, value in changes.items():
            assert key in {'enabled', 'user_daily_limit', 'user_monthly_limit', 'global_monthly_limit'}
            conn.execute(f'UPDATE ocr_guard_settings SET {key} = ? WHERE id = 1', (value,))
        conn.commit()


def scan(client, user, key, suffix=b'1'):
    return client.post('/api/receipt/scan', headers={**user.h, 'Idempotency-Key': key},
                       files={'file': ('receipt.png', PNG + suffix, 'image/png')})


def test_disabled_invalid_input_and_fail_closed(client, make_user, monkeypatch):
    user = make_user('guard_user')
    calls = []
    monkeypatch.setattr(receipt_db, 'run_ocr', lambda path: calls.append(path))
    assert scan(client, user, 'disabled_key_123456').status_code == 503
    settings(enabled=1)
    invalid = client.post('/api/receipt/scan', headers={**user.h, 'Idempotency-Key':'invalid_file_12345'},
                          files={'file': ('x.png', b'not a png', 'image/png')})
    assert invalid.status_code == 400
    truncated = client.post('/api/receipt/scan', headers={**user.h, 'Idempotency-Key':'truncated_file_12345'},
                            files={'file': ('x.png', b'\x89PNG\r\n\x1a\n', 'image/png')})
    assert truncated.status_code == 400
    assert scan(client, user, 'short').status_code == 400
    def unavailable():
        raise RuntimeError('database unavailable')
    monkeypatch.setattr(ocr_guard, 'get_conn', unavailable)
    assert scan(client, user, 'database_error_12345').status_code == 503
    assert user.get('/api/users/me').status_code == 200
    assert calls == []


def test_image_mime_and_pixel_limit_reject_before_provider(client, make_user, monkeypatch):
    user = make_user('image_limit_user')
    settings(enabled=1)
    calls = []
    monkeypatch.setattr(receipt_db, 'run_ocr', lambda path: calls.append(path))
    mismatched = client.post('/api/receipt/scan', headers={**user.h, 'Idempotency-Key':'mime_mismatch_12345'},
                             files={'file': ('x.jpg', PNG, 'image/jpeg')})
    assert mismatched.status_code == 400
    huge = BytesIO()
    Image.new('1', (5000, 5000)).save(huge, format='PNG')
    oversized = client.post('/api/receipt/scan', headers={**user.h, 'Idempotency-Key':'pixel_limit_1234567'},
                            files={'file': ('x.png', huge.getvalue(), 'image/png')})
    assert oversized.status_code == 400
    assert calls == []
    assert ocr_guard.usage()['globalMonthlyUsed'] == 0


def test_provider_error_response_is_not_a_success(tmp_path, monkeypatch):
    image = tmp_path / 'receipt.png'
    image.write_bytes(PNG)
    monkeypatch.setattr(receipt_db, '_clova_env', lambda: ('https://invalid.test', 'test-only'))
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'images': [{'inferResult': 'ERROR'}]}
    monkeypatch.setattr(receipt_db.requests, 'post', lambda *args, **kwargs: Response())
    text, result = receipt_db.clova_ocr_text(str(image))
    assert text == '' and result['ok'] is False


def test_replay_and_ambiguous_provider_failure_are_not_rebilled(client, make_user, monkeypatch):
    user = make_user('replay_user')
    settings(enabled=1)
    calls = []
    def provider(path):
        calls.append(path)
        return 'clova', '', {'enabled': True, 'ok': True, 'raw': {'private': 'not saved'}}
    monkeypatch.setattr(receipt_db, 'run_ocr', provider)
    first = scan(client, user, 'replay_key_12345678')
    assert first.status_code == 200, first.text
    replay = scan(client, user, 'replay_key_12345678')
    assert replay.status_code == 200 and replay.json()['scan']['id'] == first.json()['scan']['id']
    assert scan(client, user, 'replay_key_12345678', b'other').status_code == 409
    assert scan(client, user, 'different_key_123456').status_code == 409
    assert len(calls) == 1
    history = user.get('/api/receipt/history').json()['items']
    assert history[0]['rawOcr'] == {}
    monkeypatch.setattr(ocr_guard, 'now_utc', lambda: datetime.now(timezone.utc) + timedelta(seconds=6))
    def timeout(path):
        calls.append(path)
        raise TimeoutError()
    monkeypatch.setattr(receipt_db, 'run_ocr', timeout)
    assert scan(client, user, 'timeout_key_1234567', b'2').status_code == 503
    assert scan(client, user, 'timeout_key_1234567', b'2').status_code == 409
    assert len(calls) == 2
    assert ocr_guard.usage()['globalMonthlyUsed'] == 2


def test_global_limit_across_concurrent_accounts(client, make_user, monkeypatch):
    users = [make_user('parallel' + str(i)) for i in range(6)]
    settings(enabled=1, global_monthly_limit=2, user_daily_limit=10, user_monthly_limit=10)
    calls, lock = [], Lock()
    def provider(path):
        with lock:
            calls.append(path)
        return 'clova', '', {'enabled': True, 'ok': True}
    monkeypatch.setattr(receipt_db, 'run_ocr', provider)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda pair: scan(client, pair[1], f'parallel_key_{pair[0]:08d}', str(pair[0]).encode()), enumerate(users)))
    assert sorted(r.status_code for r in results) == [200, 200, 429, 429, 429, 429]
    assert len(calls) == 2
    assert ocr_guard.usage()['globalMonthlyUsed'] == 2
    assert all(r.headers.get('Retry-After') for r in results if r.status_code == 429)


def test_per_user_rate_limit_does_not_block_replay(client, make_user, monkeypatch):
    user = make_user('rate_user')
    settings(enabled=1)
    monkeypatch.setattr(receipt_db, 'run_ocr', lambda path: ('clova', '', {'enabled':True, 'ok':True}))
    first = scan(client, user, 'rate_first_12345678', b'first')
    assert first.status_code == 200
    assert scan(client, user, 'rate_first_12345678', b'first').status_code == 200
    limited = scan(client, user, 'rate_second_1234567', b'second')
    assert limited.status_code == 429 and int(limited.headers['Retry-After']) > 0


def test_daily_limit_and_utc_month_boundary(client, make_user, monkeypatch):
    user = make_user('boundary_user')
    settings(enabled=1, user_daily_limit=1, user_monthly_limit=1, global_monthly_limit=1)
    monkeypatch.setattr(receipt_db, 'run_ocr', lambda path: ('clova', '', {'enabled':True, 'ok':True}))
    monkeypatch.setattr(ocr_guard, 'now_utc', lambda: datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc))
    assert scan(client, user, 'boundary_old_123456', b'old').status_code == 200
    assert scan(client, user, 'boundary_block_12345', b'blocked').status_code == 429
    monkeypatch.setattr(ocr_guard, 'now_utc', lambda: datetime(2026, 11, 1, 0, 0, 5, tzinfo=timezone.utc))
    assert scan(client, user, 'boundary_new_123456', b'new').status_code == 200
    assert ocr_guard.usage()['globalMonthlyUsed'] == 1


def test_admin_switch_requires_role_and_explicit_acknowledgement(client, make_user):
    admin, member = make_user('admin_user'), make_user('normal_user')
    with ocr_guard.get_conn() as conn:
        conn.execute("UPDATE users SET role='admin' WHERE id = ?", (admin.id,))
        conn.commit()
    assert client.get('/api/admin/ocr').status_code == 401
    assert member.get('/api/admin/ocr').status_code == 403
    assert member.patch('/api/admin/ocr', {'enabled': True, 'acknowledgeExternalSafety': True}).status_code == 403
    assert admin.patch('/api/admin/ocr', {'enabled': True}).status_code == 400
    assert admin.patch('/api/admin/ocr', {'enabled': True, 'acknowledgeExternalSafety': True}).status_code == 200
    assert admin.patch('/api/admin/ocr', {'enabled': False}).json()['enabled'] is False
    assert scan(client, member, 'stopped_key_1234567').status_code == 503
    with ocr_guard.get_conn() as conn:
        assert conn.execute('SELECT COUNT(*) AS n FROM ocr_guard_audit').fetchone()['n'] == 2
