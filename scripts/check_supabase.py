"""Read-only schema and bucket check. No secrets printed."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.config
from app.db.postgres import Connection
from app import storage
import requests
with Connection() as db:
    row=db.conn.execute('SELECT version FROM public.neighborfood_schema_version').fetchone()
    if not row or row['version']!='28190b4-v1': raise SystemExit('Schema version mismatch')
    count=db.conn.execute("SELECT count(*) AS n FROM pg_tables WHERE schemaname='public' AND tablename <> 'neighborfood_schema_version'").fetchone()['n']
    print(f'PostgreSQL connected; {count} app tables; schema version OK')
url,headers=storage.config()
for bucket,public in [('food-images',True),('receipts',False)]:
    response=requests.get(url+'/storage/v1/bucket/'+bucket,headers=headers,timeout=15)
    if response.status_code!=200: raise SystemExit(f'{bucket}: missing or server key rejected ({response.status_code})')
    if response.json().get('public')!=public: raise SystemExit(f'{bucket}: wrong visibility setting')
    print(bucket+': visibility OK')
print('Configuration check passed. Test real uploads/OCR/QR/payments through the app next.')
