"""PortOne V2 sandbox checkout. Never changes settlement payment status."""
import os
import uuid
from urllib.parse import quote
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.deps import get_current_user
from app.db.transaction_db import get_conn
from app.routers.settlements import _load_and_authorize

router = APIRouter()


def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS portone_test_payments (
            payment_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            settlement_id INTEGER NOT NULL, amount INTEGER NOT NULL,
            store_id TEXT NOT NULL, channel_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'READY',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            checked_at TEXT,
            UNIQUE(user_id, settlement_id)
        )''')

        conn.execute("""CREATE TABLE IF NOT EXISTS portone_quick_test_payments (
            payment_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, store_id TEXT NOT NULL, channel_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'READY',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, checked_at TEXT
        )""")


@router.post('/quick-prepare')
def quick_prepare(user: dict = Depends(get_current_user)):
    store, channel, _ = settings()
    payment_id = 'nf-quick-' + uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute("""INSERT INTO portone_quick_test_payments
            (payment_id,user_id,amount,store_id,channel_key) VALUES (?,?,?,?,?)""",
            (payment_id, user['id'], 1000, store, channel))
    return {'request': {'storeId': store, 'channelKey': channel,
        'paymentId': payment_id, 'orderName': 'Neighborfood quick test',
        'totalAmount': 1000, 'currency': 'CURRENCY_KRW', 'payMethod': 'CARD'}}


def settings():
    names = ('PORTONE_STORE_ID', 'PORTONE_CHANNEL_KEY', 'PORTONE_API_SECRET')
    values = [os.getenv(n, '').strip() for n in names]
    if os.getenv('PORTONE_TEST_ENABLED', '').lower() != 'true' or not all(values):
        raise HTTPException(503, '포트원 테스트 설정이 필요합니다. 서버의 PORTONE_* 설정을 확인해 주세요.')
    return values


class Prepare(BaseModel):
    settlement_id: int = Field(gt=0)


@router.get('/config')
def config(user: dict = Depends(get_current_user)):
    ready = os.getenv('PORTONE_TEST_ENABLED', '').lower() == 'true' and all(
        os.getenv(n, '').strip() for n in ('PORTONE_STORE_ID', 'PORTONE_CHANNEL_KEY', 'PORTONE_API_SECRET'))
    return {'enabled': ready, 'mode': 'test'}


@router.post('/prepare')
def prepare(body: Prepare, user: dict = Depends(get_current_user)):
    store, channel, _ = settings()
    settlement, _, share = _load_and_authorize(body.settlement_id, user)
    if not share:
        raise HTTPException(403, '본인 분담금만 테스트할 수 있습니다.')
    if settlement['status'] != 'pending' or share['status'] != 'unpaid':
        raise HTTPException(409, '진행 중인 미납 분담금만 테스트할 수 있습니다.')
    if not share.get('gps_verified') or not share.get('quality_agreed'):
        raise HTTPException(400, 'GPS 인증 후 QR 인증을 먼저 완료해 주세요.')
    if share['amount'] <= 0:
        raise HTTPException(400, '결제 금액은 0원보다 커야 합니다.')
    with get_conn() as conn:
        # Same order always uses the same payment ID, including retries and concurrent clicks.
        conn.execute('''INSERT OR IGNORE INTO portone_test_payments
            (payment_id,user_id,settlement_id,amount,store_id,channel_key)
            VALUES (?,?,?,?,?,?)''', ('nf-test-' + uuid.uuid4().hex, user['id'],
                settlement['id'], share['amount'], store, channel))
        row = dict(conn.execute('SELECT * FROM portone_test_payments WHERE user_id=? AND settlement_id=?',
            (user['id'], settlement['id'])).fetchone())
        if row['amount'] != share['amount'] or row['store_id'] != store or row['channel_key'] != channel:
            raise HTTPException(409, '기존 테스트 주문과 설정이 다릅니다. 기존 결제를 먼저 확인해 주세요.')
    return {'request': {'storeId': store, 'channelKey': channel,
        'paymentId': row['payment_id'], 'orderName': 'Neighborfood test',
        'totalAmount': row['amount'], 'currency': 'CURRENCY_KRW', 'payMethod': 'CARD'},
        'status': row['status']}


def lookup(payment_id, store, secret):
    try:
        response = requests.get('https://api.portone.io/payments/' + quote(payment_id, safe=''),
            params={'storeId': store}, headers={'Authorization': 'PortOne ' + secret}, timeout=(5, 15))
        if response.status_code == 404:
            raise HTTPException(409, '아직 결제 내역이 없습니다. 결제창을 완료한 뒤 다시 확인해 주세요.')
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError('Unexpected response')
        return data
    except (requests.RequestException, ValueError):
        raise HTTPException(502, '포트원 결제 조회에 실패했습니다. 잠시 후 다시 확인해 주세요.') from None


@router.post('/{payment_id}/verify')
def verify(payment_id: str, user: dict = Depends(get_current_user)):
    store, channel, secret = settings()
    table = 'portone_test_payments'
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM portone_test_payments WHERE payment_id=? AND user_id=?',
            (payment_id, user['id'])).fetchone()
        if row is None:
            table = 'portone_quick_test_payments'
            row = conn.execute('SELECT * FROM portone_quick_test_payments WHERE payment_id=? AND user_id=?',
                (payment_id, user['id'])).fetchone()
    if row is None:
        raise HTTPException(404, '본인의 테스트 주문을 찾을 수 없습니다.')
    if row['store_id'] != store or row['channel_key'] != channel:
        raise HTTPException(409, '결제 요청 당시의 포트원 설정으로 조회해 주세요.')
    payment = lookup(payment_id, store, secret)
    amount = payment.get('amount') or {}
    payment_channel = payment.get('channel') or {}
    if (payment.get('id') != payment_id or payment.get('storeId') != row['store_id']
            or payment.get('currency') != 'KRW'
            or amount.get('total') != row['amount']
            or payment_channel.get('key') != row['channel_key']):
        raise HTTPException(409, '결제 ID·금액·통화·채널 검증에 실패했습니다.')
    # Do not accept a live payment as a sandbox success, even if the console is misconfigured.
    if payment_channel.get('type') != 'TEST':
        raise HTTPException(409, '테스트 결제가 아닙니다. 포트원 콘솔에서 테스트 채널을 확인해 주세요.')
    status = payment.get('status')
    if status not in {'READY', 'PENDING', 'PAID', 'FAILED', 'CANCELLED', 'PARTIAL_CANCELLED', 'VIRTUAL_ACCOUNT_ISSUED'}:
        raise HTTPException(502, '알 수 없는 결제 상태입니다.')
    with get_conn() as conn:
        conn.execute(f'UPDATE {table} SET status=?, checked_at=CURRENT_TIMESTAMP WHERE payment_id=?',
            (status, payment_id))
        saved = conn.execute(f'SELECT status, checked_at FROM {table} WHERE payment_id=?',
            (payment_id,)).fetchone()
    return {'amount': row['amount'], 'currency': 'KRW',
        'checkedAt': saved['checked_at'] + 'Z', 'recordedStatus': saved['status'],
        'paymentId': payment_id, 'status': status, 'verified': status == 'PAID',
        'mode': 'test', 'settlementUpdated': False}
