"""Storage HTTP API. Keep existing filename payloads and /uploads URLs."""
import mimetypes
import os
from urllib.parse import quote
import requests
from fastapi import HTTPException

MAX_BYTES=4 * 1024 * 1024  # Keep multipart requests within Vercel's request limit.

def enabled():
    return bool(os.getenv('SUPABASE_URL','').strip())

def config():
    url=os.getenv('SUPABASE_URL','').rstrip('/')
    key=os.getenv('SUPABASE_SECRET_KEY','')
    if not url or not key:
        raise HTTPException(503,'Supabase Storage 서버 설정이 필요합니다.')
    return url, {'Authorization': 'Bearer '+key, 'apikey': key}

def save(bucket, name, data):
    if len(data)>MAX_BYTES: raise HTTPException(413,'이미지는 4MB 이하로 올려주세요.')
    url,headers=config()
    headers['Content-Type']=mimetypes.guess_type(name)[0] or 'application/octet-stream'
    try:
        response=requests.post(url+'/storage/v1/object/'+quote(bucket)+'/'+quote(name),headers=headers,data=data,timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        raise HTTPException(502,'이미지 저장에 실패했습니다. 다시 시도해 주세요.') from None

def public_url(name):
    url,_=config()
    return url+'/storage/v1/object/public/food-images/'+quote(name,safe='')

def signed_receipt_url(name):
    url,headers=config()
    try:
        response=requests.post(url+'/storage/v1/object/sign/receipts/'+quote(name,safe=''),headers=headers,json={'expiresIn':300},timeout=15)
        response.raise_for_status()
        signed=response.json()['signedURL']
        return signed if signed.startswith('https://') else url+'/storage/v1'+signed
    except (requests.RequestException,KeyError,ValueError):
        raise HTTPException(502,'영수증 이미지 조회에 실패했습니다.') from None
