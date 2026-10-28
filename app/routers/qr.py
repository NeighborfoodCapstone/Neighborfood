import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import get_current_user
from app.core.utils import now_utc, to_iso, from_iso, hash_token, parse_token
from app.db import qr_db, trade_verification as tv
from app.models.qr import QrIssueRequest, QrVerifyRequest

router = APIRouter()

def _audit(conn, actor_id, session_id, outcome):
    conn.execute("""INSERT INTO qr_verification_events (id, qr_session_id, actor_id, outcome, created_at)
                    VALUES (?, ?, ?, ?, ?)""",
                 ('qre_' + secrets.token_hex(16), session_id, actor_id, outcome, to_iso(now_utc())))


def _reject(conn, actor_id, session_id, status, detail):
    _audit(conn, actor_id, session_id, 'rejected')
    conn.commit()
    raise HTTPException(status, detail)


def _trade(conn, transaction_id, settlement_id, issuer_id, verifier_id=None, gps_session_id=None):
    """Lock the trade and ensure its receiver's GPS evidence belongs to it."""
    if transaction_id and settlement_id:
        raise HTTPException(400, '하나의 거래 또는 정산만 지정할 수 있습니다.')
    if transaction_id:
        tx = tv.lock_row(conn, 'transactions', transaction_id)
        if not tx:
            raise HTTPException(404, '거래를 찾을 수 없습니다.')
        if tx['receiver_id'] != issuer_id or (verifier_id is not None and tx['provider_id'] != verifier_id):
            raise HTTPException(403, '해당 거래의 QR 발급자 또는 검증자가 아닙니다.')
        if tx['status'] != 'confirmed':
            raise HTTPException(409, '수락된 거래에서만 QR 인증을 진행할 수 있습니다.')
        post = tv.lock_row(conn, 'posts', tx['post_id'])
        if not post or post['status'] == 'deleted':
            raise HTTPException(409, '거래 게시글을 사용할 수 없습니다.')
        gps = tv.require_gps(conn, 'transaction', transaction_id, issuer_id,
                             post['appointment_lat'], post['appointment_lng'], gps_session_id)
        return tx, gps
    if settlement_id:
        settlement = tv.lock_row(conn, 'settlements', settlement_id)
        if not settlement:
            raise HTTPException(404, '정산을 찾을 수 없습니다.')
        share = conn.execute('SELECT * FROM settlement_shares WHERE settlement_id = ? AND user_id = ?',
                             (settlement_id, issuer_id)).fetchone()
        if not share or (verifier_id is not None and settlement['requester_id'] != verifier_id):
            raise HTTPException(403, '해당 정산의 QR 발급자 또는 주최자가 아닙니다.')
        if settlement['status'] != 'pending' or share['status'] not in ('unpaid', 'paid'):
            raise HTTPException(409, '진행 중인 정산의 참여자만 QR을 사용할 수 있습니다.')
        if not share['gps_verified']:
            raise HTTPException(400, '이 정산의 GPS 인증을 먼저 완료해 주세요.')
        gps = tv.require_gps(conn, 'settlement', settlement_id, issuer_id,
                             settlement['appointment_lat'], settlement['appointment_lng'], gps_session_id)
        return settlement, gps
    return None, None


@router.post('/request')
def issue_qr(body: QrIssueRequest, user: dict = Depends(get_current_user)):
    qr_db.init_qr_db()
    if body.subjectId.strip() != str(user['id']):
        raise HTTPException(403, '본인 계정의 QR만 발급할 수 있습니다.')
    if body.transactionId and body.settlementId:
        raise HTTPException(400, '하나의 거래 또는 정산만 지정할 수 있습니다.')
    session_id = 'qrs_' + secrets.token_hex(8)
    token = secrets.token_urlsafe(32)
    with qr_db.get_conn() as conn:
        tv.begin(conn)
        _, gps = _trade(conn, body.transactionId, body.settlementId, user['id'])
        issued = now_utc()
        issued_text = to_iso(issued)
        expires_text = to_iso(issued + timedelta(seconds=body.ttlSeconds))
        if body.transactionId:
            conn.execute("""UPDATE qr_sessions SET status = 'EXPIRED', updated_at = ?
                WHERE subject_id = ? AND transaction_id = ? AND status = 'ISSUED'""",
                (issued_text, str(user['id']), body.transactionId))
        elif body.settlementId:
            conn.execute("""UPDATE qr_sessions SET status = 'EXPIRED', updated_at = ?
                WHERE subject_id = ? AND settlement_id = ? AND status = 'ISSUED'""",
                (issued_text, str(user['id']), body.settlementId))
        conn.execute("""INSERT INTO qr_sessions
            (id, subject_id, purpose, token_hash, status, issued_at, expires_at,
             created_at, updated_at, transaction_id, settlement_id, location_session_id)
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, str(user['id']), body.purpose, hash_token(token), issued_text,
             expires_text, issued_text, issued_text, body.transactionId, body.settlementId,
             gps['id'] if gps else None))
        conn.commit()
    return {'ok': True, 'session': {'id': session_id, 'subjectId': str(user['id']),
        'purpose': body.purpose, 'status': 'ISSUED', 'issuedAt': issued_text,
        'expiresAt': expires_text, 'usedAt': None, 'lastScannedAt': None,
        'token': token, 'verifyUrl': f'/api/qr/verify/{token}'}}


@router.post('/verify')
def verify_qr(body: QrVerifyRequest, request: Request, user: dict = Depends(get_current_user)):
    qr_db.init_qr_db()
    token = parse_token(body.token or body.rawValue or '')
    if not token:
        with qr_db.get_conn() as conn:
            _audit(conn, user['id'], None, 'invalid_input')
            conn.commit()
        return {'ok': False, 'result': 'invalid_input', 'message': 'QR 토큰이 비어 있습니다.'}
    with qr_db.get_conn() as conn:
        tv.begin(conn)
        found = conn.execute('SELECT id, transaction_id, settlement_id FROM qr_sessions WHERE token_hash = ?', (hash_token(token),)).fetchone()
        if not found:
            _audit(conn, user['id'], None, 'not_found')
            conn.commit()
            return {'ok': False, 'result': 'not_found', 'message': '저장된 인증 세션을 찾을 수 없습니다.'}
        # Lock trade before QR consistently with issuance and cancellation.
        authorized = None
        if found['transaction_id']:
            authorized = tv.lock_row(conn, 'transactions', found['transaction_id'])
        elif found['settlement_id']:
            authorized = tv.lock_row(conn, 'settlements', found['settlement_id'])
        row = tv.lock_row(conn, 'qr_sessions', found['id'])
        if row['transaction_id'] != body.transactionId or row['settlement_id'] != body.settlementId:
            _reject(conn, user['id'], row['id'], 403, '이 QR은 현재 거래 또는 정산에 속하지 않습니다.')
        if row['subject_id'] == str(user['id']):
            _reject(conn, user['id'], row['id'], 403, '본인이 발급한 QR은 직접 검증할 수 없습니다.')
        if row['transaction_id']:
            # The transaction row was locked before the QR row above.
            if not authorized or authorized['provider_id'] != user['id']:
                _reject(conn, user['id'], row['id'], 403, '해당 거래의 제공자만 QR을 검증할 수 있습니다.')
        elif row['settlement_id']:
            # The settlement row was locked before the QR row above.
            if not authorized or authorized['requester_id'] != user['id']:
                _reject(conn, user['id'], row['id'], 403, '해당 정산의 주최자만 QR을 검증할 수 있습니다.')
        if row['status'] != 'ISSUED':
            _audit(conn, user['id'], row['id'], 'already_used' if row['status'] == 'VERIFIED' else 'expired')
            conn.commit()
            return {'ok': False, 'result': 'already_used' if row['status'] == 'VERIFIED' else 'expired',
                    'message': '이미 사용했거나 만료된 QR입니다.'}
        if from_iso(row['expires_at']) <= now_utc():
            conn.execute("UPDATE qr_sessions SET status = 'EXPIRED', updated_at = ? WHERE id = ?", (to_iso(now_utc()), row['id']))
            _audit(conn, user['id'], row['id'], 'expired')
            conn.commit()
            return {'ok': False, 'result': 'expired', 'message': '만료된 QR입니다.'}
        try:
            issuer_id = int(row['subject_id'])
        except ValueError:
            _reject(conn, user['id'], row['id'], 403, '유효하지 않은 QR 발급자입니다.')
        if (row['transaction_id'] or row['settlement_id']) and not row['location_session_id']:
            _reject(conn, user['id'], row['id'], 400, '이 거래에 연결된 GPS 인증이 없습니다. QR을 다시 발급해 주세요.')
        try:
            trade, _ = _trade(conn, row['transaction_id'], row['settlement_id'], issuer_id,
                              user['id'], row['location_session_id'])
        except HTTPException:
            _audit(conn, user['id'], row['id'], 'rejected')
            conn.commit()
            raise
        now = to_iso(now_utc())
        result = conn.execute("""UPDATE qr_sessions SET status = 'VERIFIED', used_at = ?, last_scanned_at = ?,
            scanner_id = ?, updated_at = ? WHERE id = ? AND status = 'ISSUED'""",
            (now, now, user['id'], now, row['id']))
        if result.rowcount != 1:
            raise HTTPException(409, '이미 사용된 QR입니다.')
        if row['transaction_id']:
            updated = conn.execute("""UPDATE transactions SET status = 'completed', completed_at = ?, qr_session_id = ?
                WHERE id = ? AND status = 'confirmed'""", (now, row['id'], trade['id']))
            if updated.rowcount != 1:
                raise HTTPException(409, '거래 상태가 변경되었습니다.')
        elif row['settlement_id']:
            updated = conn.execute("""UPDATE settlement_shares SET quality_agreed = 1
                WHERE settlement_id = ? AND user_id = ? AND status IN ('unpaid', 'paid') AND gps_verified = 1""",
                (trade['id'], issuer_id))
            if updated.rowcount != 1:
                raise HTTPException(409, '정산 참여 상태가 변경되었습니다.')
        _audit(conn, user['id'], row['id'], 'verified')
        updated_row = conn.execute('SELECT * FROM qr_sessions WHERE id = ?', (row['id'],)).fetchone()
        conn.commit()
    return {'ok': True, 'result': 'verified', 'message': 'QR 인증이 완료되었습니다.',
            'session': qr_db.row_to_dict(updated_row)}


@router.get('/verify/{token}')
def verify_qr_by_url(token: str, request: Request, user: dict = Depends(get_current_user)):
    return verify_qr(QrVerifyRequest(token=token), request, user)


@router.post('/verify/{token}')
def verify_qr_post_by_url(token: str, request: Request, user: dict = Depends(get_current_user)):
    return verify_qr(QrVerifyRequest(token=token), request, user)


@router.get('/history')
def get_qr_history(limit: int = 20, user: dict = Depends(get_current_user)):
    qr_db.init_qr_db()
    qr_db.expire_old_sessions()
    with qr_db.get_conn() as conn:
        rows = conn.execute('SELECT * FROM qr_sessions WHERE subject_id = ? ORDER BY issued_at DESC LIMIT ?',
                            (str(user['id']), max(1, min(limit, 50)))).fetchall()
    return {'ok': True, 'items': [qr_db.row_to_dict(row) for row in rows]}


@router.get('/my-history')
def my_qr_history(limit: int = 20, user: dict = Depends(get_current_user)):
    return get_qr_history(limit, user)
