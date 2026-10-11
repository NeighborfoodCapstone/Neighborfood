"""Enter secrets locally. Existing OCR/PortOne/Kakao environment values are preserved."""
import getpass
import os
import re
import shutil
import subprocess
import warnings
from pathlib import Path
from urllib.parse import quote

root=Path(__file__).resolve().parents[1]
env=root/'.env'
if subprocess.run(['git','ls-files','--error-unmatch','.env'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
    raise SystemExit('.env is tracked by Git. Untrack it before configuring secrets.')
warnings.simplefilter('error',getpass.GetPassWarning)
try:
    password=getpass.getpass('Seoul project database password (hidden): ')
    secret=getpass.getpass('Supabase secret key, including sb_secret_ (hidden): ')
except getpass.GetPassWarning:
    raise SystemExit('Terminal cannot hide input. Run this script from PowerShell instead.')
if not password or not secret.startswith('sb_secret_'):
    raise SystemExit('Password required; server key must start with sb_secret_. No files changed.')
values={
'DATABASE_URL':'postgresql://postgres.msqzjrigztlumcwecqve:'+quote(password,safe='')+'@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres',
'DATABASE_SSLMODE':'require',
'SUPABASE_URL':'https://msqzjrigztlumcwecqve.supabase.co',
'SUPABASE_SECRET_KEY':secret,
}
old=env.read_text(encoding='utf-8-sig') if env.exists() else ''
if not re.search(r'^ALLOWED_ORIGINS=',old,re.M): values['ALLOWED_ORIGINS']='http://localhost:5173'
lines=old.splitlines()
lines=[line for line in lines if not any(re.match(r'^\s*(?:export\s+)?'+re.escape(key)+r'\s*=',line) for key in values)]
lines+=['']+[key+'='+value for key,value in values.items()]
if env.exists():
    backup=root/'.env.supabase.bak'
    if backup.exists(): raise SystemExit('Existing .env.supabase.bak found; move it to a safe place before configuring again.')
    shutil.copy2(env,backup)
    try: backup.chmod(0o600)
    except OSError: pass
staged=root/'.env.supabase.tmp'
staged.write_text('\n'.join(lines)+'\n',encoding='utf-8')
try: staged.chmod(0o600)
except OSError: pass
os.replace(staged,env)
frontend=root/'frontend-react/.env.local'
old_front=frontend.read_text(encoding='utf-8-sig') if frontend.exists() else ''
if not re.search(r'^VITE_API_BASE_URL=',old_front,re.M):
    frontend.write_text(old_front+'\nVITE_API_BASE_URL=http://127.0.0.1:8000\n',encoding='utf-8')
print('Server .env configured. Existing service settings preserved. No secret values printed.')
print('Next: python scripts/supabase_migrate.py')
