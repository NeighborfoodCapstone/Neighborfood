"""Storage routing and receipt access checks without external keys or services."""
import pytest
from app import storage
@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_SECRET_KEY','sb_secret_test_only')
    calls=[]
    monkeypatch.setattr(storage,'save',lambda bucket,name,data: calls.append((bucket,name,data)))
    monkeypatch.setattr(storage,'signed_receipt_url',lambda name:'https://test.supabase.co/private/'+name)
    from app.db import receipt_db
    monkeypatch.setattr(receipt_db,'run_ocr',lambda path: ('ocr_empty','',{}))
    return calls

def test_cloud_upload_requires_login_and_preserves_filename(client,make_user,cloud):
    assert client.post('/upload-images',files={'files':('a.png',b'image','image/png')}).status_code==401
    user=make_user('photo')
    response=client.post('/upload-images',headers=user.h,files={'files':('a.png',b'image','image/png')})
    assert response.status_code==200
    assert cloud[0][0]=='food-images'
    assert response.json()['files']==[cloud[0][1]]

def test_receipt_cloud_ownership_and_history(client,make_user,cloud):
    a,b=make_user('alice'),make_user('bob')
    response=client.post('/api/receipt/scan',headers=a.h,files={'file':('receipt.png',b'fake-image','image/png')})
    assert response.status_code==200,response.text
    record=response.json()['scan']
    assert record['imageUrl'].startswith('https://test.supabase.co/private/')
    assert cloud[0][0]=='receipts'
    assert a.get('/api/receipt/history').json()['items'][0]['id']==record['id']
    assert b.get('/api/receipt/history').json()['items']==[]
    name=cloud[0][1]
    assert client.get('/api/receipt/image/'+name,headers=b.h,follow_redirects=False).status_code==404
    redirect=client.get('/api/receipt/image/'+name,headers=a.h,follow_redirects=False)
    assert redirect.status_code==307
    assert 'private/' in redirect.headers['location']
    verify={'scanId':record['id'],'subjectId':str(b.id),'items':[{'name':'사과','qty':1,'price':1000}]}
    assert b.post('/api/receipt/verify',verify).status_code==403
    spoof=client.post('/api/receipt/scan?subjectId='+str(b.id),headers=a.h,files={'file':('r.png',b'fake','image/png')})
    assert spoof.status_code==403

def test_receipt_limit_and_login(client,make_user,cloud):
    assert client.post('/api/receipt/scan',files={'file':('r.png',b'x','image/png')}).status_code==401
    user=make_user('limit')
    response=client.post('/api/receipt/scan',headers=user.h,files={'file':('r.png',b'x'*(storage.MAX_BYTES+1),'image/png')})
    assert response.status_code==413
    assert not cloud
