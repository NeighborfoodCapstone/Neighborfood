"""Legacy local receipt files stay private but remain accessible to their owner."""
from app.db import receipt_db
from app.routers import receipt
import main


def test_legacy_local_receipt_requires_ownership(client, make_user, tmp_path, monkeypatch):
    owner, stranger = make_user('receipt_owner'), make_user('receipt_stranger')
    uploads = tmp_path / 'old_uploads'
    uploads.mkdir()
    name = 'receipt_existing.png'
    (uploads / name).write_bytes(b'private test content')
    monkeypatch.setattr(main, 'UPLOAD_DIR', str(uploads))
    monkeypatch.setattr(receipt, 'UPLOAD_DIR', str(uploads))
    monkeypatch.setattr(receipt, 'DATA_DIR', str(tmp_path / 'private_data'))
    with receipt_db.get_conn() as conn:
        conn.execute("""INSERT INTO receipts
            (id, subject_id, image_path, status, scanned_at, created_at, updated_at)
            VALUES (?, ?, ?, 'SCANNED', ?, ?, ?)""",
            ('legacy', str(owner.id), name, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'))
        conn.commit()
    assert client.get('/uploads/' + name).status_code == 404
    assert client.get('/uploads/' + name.upper()).status_code == 404
    assert client.get('/api/receipt/image/' + name).status_code == 401
    assert stranger.get('/api/receipt/image/' + name).status_code == 404
    image = owner.get('/api/receipt/image/' + name)
    assert image.status_code == 200 and image.content == b'private test content'
