import sqlite3
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import portone
from app.core.deps import get_current_user

@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.db')
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(portone, 'get_conn', connect)
    for k, v in {'PORTONE_TEST_ENABLED':'true', 'PORTONE_STORE_ID':'store-test',
                 'PORTONE_CHANNEL_KEY':'channel-test', 'PORTONE_API_SECRET':'private-test'}.items():
        monkeypatch.setenv(k, v)
    share = {'amount':1000, 'status':'unpaid', 'gps_verified':1, 'quality_agreed':1}
    monkeypatch.setattr(portone, '_load_and_authorize', lambda *a: ({'id':1,'status':'pending'}, False, share))
    portone.init_db()
    app = FastAPI()
    app.include_router(portone.router)
    user = {'id':1}
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), share, user, connect

def order(client):
    response = client.post('/prepare', json={'settlement_id':1, 'amount':1})
    assert response.status_code == 200
    return response.json()['request']

def paid(req):
    return {'id':req['paymentId'], 'storeId':'store-test', 'currency':'KRW',
        'amount':{'total':1000}, 'channel':{'key':'channel-test','type':'TEST'}, 'status':'PAID'}

def test_amount_owner_retry_and_secret(setup):
    client, share, user, conn = setup
    req = order(client)
    assert req['totalAmount'] == 1000
    assert order(client)['paymentId'] == req['paymentId']
    assert 'private-test' not in str(req) + client.get('/config').text
    user['id'] = 2
    assert client.post('/'+req['paymentId']+'/verify').status_code == 404

@pytest.mark.parametrize('field', ['gps_verified', 'quality_agreed'])
def test_gates(setup, field):
    client, share, _, _ = setup
    share[field] = 0
    assert client.post('/prepare',json={'settlement_id':1}).status_code == 400

@pytest.mark.parametrize('change', ['amount','currency','id','storeId','channel','live'])
def test_reject_mismatch(setup, change):
    client, _, _, _ = setup
    req = order(client); data = paid(req)
    if change == 'amount': data['amount']['total'] = 1
    elif change == 'channel': data['channel']['key'] = 'other'
    elif change == 'live': data['channel']['type'] = 'LIVE'
    else: data[change] = 'other'
    with patch.object(portone, 'lookup', return_value=data):
        assert client.post('/'+req['paymentId']+'/verify').status_code == 409

def test_verified_repeat_cancel_and_no_settlement_update(setup):
    client, _, _, conn = setup
    req = order(client); data = paid(req)
    with patch.object(portone, 'lookup', return_value=data):
        for _ in range(2):
            r=client.post('/'+req['paymentId']+'/verify')
            assert r.status_code == 200
            assert r.json()['verified'] and not r.json()['settlementUpdated']
        data['status']='CANCELLED'
        assert not client.post('/'+req['paymentId']+'/verify').json()['verified']
    with conn() as db:
        assert db.execute('SELECT count(*) FROM portone_test_payments').fetchone()[0] == 1
        assert db.execute('SELECT status FROM portone_test_payments').fetchone()[0] == 'CANCELLED'

def test_disabled(setup, monkeypatch):
    client, _, _, _ = setup
    monkeypatch.delenv('PORTONE_API_SECRET')
    assert not client.get('/config').json()['enabled']
    assert client.post('/prepare',json={'settlement_id':1}).status_code == 503

def test_timeout_and_not_found():
    import requests
    with patch.object(portone.requests, 'get', side_effect=requests.Timeout):
        with pytest.raises(Exception) as exc: portone.lookup('p','s','secret')
        assert exc.value.status_code == 502
    with patch.object(portone.requests, 'get') as get:
        get.return_value.status_code = 404
        with pytest.raises(Exception) as exc: portone.lookup('p','s','secret')
        assert exc.value.status_code == 409
