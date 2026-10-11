"""Apply the reviewed initial migration to an EMPTY Supabase database."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.config  # loads .env
from app.db.postgres import Connection

with Connection() as db:
    db.conn.execute("SELECT pg_advisory_xact_lock(281904)")
    marker=db.conn.execute("SELECT to_regclass('public.neighborfood_schema_version') AS name").fetchone()['name']
    if marker:
        version=db.conn.execute('SELECT version FROM public.neighborfood_schema_version').fetchone()
        if not version or version['version'] != '28190b4-v1':
            raise SystemExit('Unexpected migration version; stop and review.')
        print('Migration already applied; no changes.')
    else:
        existing=db.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'").fetchall()
        if existing:
            raise SystemExit('Target database must have an empty public schema. Existing data is not overwritten.')
        sql=(Path(__file__).resolve().parents[1]/'migrations/001_supabase.sql').read_text()
        db.conn.execute(sql,prepare=False)
        print('Migration 28190b4-v1 applied.')
