"""Exercise actual transaction, GPS and QR APIs without real devices or services."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from datetime import timedelta

from app.core.utils import now_utc
from app.routers import qr

LAT, LNG = 37.5665, 126.9780


def create_trade(provider, receiver):
    post = provider.post('/posts', {'type':'share', 'title':'가상 식재료'}).json()['id']
    assert provider.post(f'/posts/{post}/appointment', {'place':'가상 약속 장소', 'lat':LAT, 'lng':LNG}).status_code == 200
    response = receiver.post('/api/transactions', {'post_id':post})
    assert response.status_code == 200
    return response.json()['transactionId']


def gps(user, tx, lat=LAT, lng=LNG):
    return user.post(f'/api/transactions/{tx}/gps', {'lat':lat, 'lng':lng, 'accuracy':10})


def issue(user, tx):
    return user.post('/api/qr/request', {'subjectId':str(user.id), 'transactionId':tx})


def verify(user, tx, token):
    return user.post('/api/qr/verify', {'token':token, 'transactionId':tx})


def test_two_party_trade_and_cross_trade_guards(client, make_user):
    provider, receiver, outsider = make_user('provider'), make_user('receiver'), make_user('outsider')
    tx = create_trade(provider, receiver)
    assert client.post('/api/qr/request', json={'subjectId':str(receiver.id)}).status_code == 401
    assert receiver.patch(f'/api/transactions/{tx}', {'status':'confirmed'}).status_code == 403
    assert provider.patch(f'/api/transactions/{tx}', {'status':'confirmed'}).status_code == 200
    assert receiver.patch(f'/api/transactions/{tx}', {'status':'completed'}).status_code == 409
    assert outsider.patch(f'/api/transactions/{tx}', {'status':'canceled'}).status_code == 403
    assert issue(receiver, tx).status_code == 400
    assert gps(outsider, tx).status_code == 403
    assert gps(receiver, tx, LAT + .02, LNG).status_code == 400
    assert receiver.post(f'/api/transactions/{tx}/gps', {'lat':LAT, 'lng':LNG, 'accuracy':200}).status_code == 400
    assert gps(receiver, tx).status_code == 200
    old_token = issue(receiver, tx).json()['session']['token']
    token = issue(receiver, tx).json()['session']['token']
    assert verify(provider, tx, old_token).json()['result'] == 'expired'
    assert verify(outsider, tx, token).status_code == 403
    assert verify(receiver, tx, token).status_code == 403
    other = create_trade(provider, receiver)
    assert provider.patch(f'/api/transactions/{other}', {'status':'confirmed'}).status_code == 200
    assert verify(provider, other, token).status_code == 403
    assert verify(provider, tx, token).json()['ok'] is True
    assert verify(provider, tx, token).json()['ok'] is False
    assert verify(provider, tx, 'forged-token').json()['result'] == 'not_found'
    with sqlite3.connect(client.db_path) as db:
        outcomes = {row[0] for row in db.execute("SELECT outcome FROM qr_verification_events")}
    assert {'verified', 'already_used', 'rejected', 'not_found'} <= outcomes
    for user in (provider, receiver):
        row = next(x for x in user.get('/api/transactions').json()['items'] if x['id'] == tx)
        assert row['status'] == 'completed'
    original = provider.get('/api/users/me').json()['trustScore']
    rating = receiver.post('/api/ratings', {'transaction_id':tx, 'score':1})
    assert rating.status_code == 200
    rating_id = rating.json()['ratingId']
    assert receiver.post('/api/ratings', {'transaction_id':tx, 'score':1}).status_code == 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        updates = list(pool.map(lambda _: receiver.patch(f'/api/ratings/{rating_id}', {'score':-1}), range(2)))
    assert all(result.status_code == 200 for result in updates)
    assert provider.get('/api/users/me').json()['trustScore'] == original - 0.5
    with ThreadPoolExecutor(max_workers=2) as pool:
        deletes = list(pool.map(lambda _: receiver.delete(f'/api/ratings/{rating_id}'), range(2)))
    assert sorted(result.status_code for result in deletes) == [200, 404]
    assert provider.get('/api/users/me').json()['trustScore'] == original


def test_qr_remains_bound_to_its_original_gps_after_appointment_change(client, make_user):
    provider, receiver = make_user('appointment_provider'), make_user('appointment_receiver')
    tx = create_trade(provider, receiver)
    assert provider.patch(f'/api/transactions/{tx}', {'status': 'confirmed'}).status_code == 200
    first_gps = gps(receiver, tx).json()['sessionId']
    old_token = issue(receiver, tx).json()['session']['token']
    with sqlite3.connect(client.db_path) as db:
        post = db.execute("SELECT post_id FROM transactions WHERE id = ?", (tx,)).fetchone()[0]
        assert db.execute("SELECT location_session_id FROM qr_sessions WHERE transaction_id = ?", (tx,)).fetchone()[0] == first_gps
    new_lat = LAT + .002
    assert provider.post(f'/posts/{post}/appointment', {'place': '변경된 장소', 'lat': new_lat, 'lng': LNG}).status_code == 200
    assert gps(receiver, tx, new_lat, LNG).status_code == 200
    assert verify(provider, tx, old_token).status_code == 400
    assert next(x for x in receiver.get('/api/transactions').json()['items'] if x['id'] == tx)['status'] == 'confirmed'
    new_token = issue(receiver, tx).json()['session']['token']
    assert verify(provider, tx, new_token).json()['ok'] is True


def test_cancel_and_expired_qr_cannot_complete(client, make_user, monkeypatch):
    provider, receiver = make_user('giver'), make_user('taker')
    tx = create_trade(provider, receiver)
    assert provider.patch(f'/api/transactions/{tx}', {'status':'confirmed'}).status_code == 200
    assert gps(receiver, tx).status_code == 200
    token = issue(receiver, tx).json()['session']['token']
    assert receiver.patch(f'/api/transactions/{tx}', {'status':'canceled'}).status_code == 200
    assert verify(provider, tx, token).status_code == 409
    tx2 = create_trade(provider, receiver)
    assert provider.patch(f'/api/transactions/{tx2}', {'status':'confirmed'}).status_code == 200
    assert gps(receiver, tx2).status_code == 200
    token2 = issue(receiver, tx2).json()['session']['token']
    monkeypatch.setattr(qr, 'now_utc', lambda: now_utc() + timedelta(minutes=6))
    expired = verify(provider, tx2, token2)
    assert expired.json()['result'] == 'expired'
    assert next(x for x in receiver.get('/api/transactions').json()['items'] if x['id'] == tx2)['status'] == 'confirmed'


def test_concurrent_qr_scan_completes_once(client, make_user):
    provider, receiver = make_user('concurrent_provider'), make_user('concurrent_receiver')
    tx = create_trade(provider, receiver)
    assert provider.patch(f'/api/transactions/{tx}', {'status':'confirmed'}).status_code == 200
    assert gps(receiver, tx).status_code == 200
    token = issue(receiver, tx).json()['session']['token']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: verify(provider, tx, token), range(2)))
    assert sum(bool(r.json().get('ok')) for r in results) == 1
    assert next(x for x in provider.get('/api/transactions').json()['items'] if x['id'] == tx)['status'] == 'completed'
