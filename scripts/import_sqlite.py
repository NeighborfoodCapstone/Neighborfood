"""Optional: copy a consistent SQLite snapshot into EMPTY migrated PostgreSQL tables.
Run before using the new app. The original SQLite file is never modified.
"""
import argparse
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.config
from app.db.postgres import Connection, SERIAL_TABLES

parser=argparse.ArgumentParser()
parser.add_argument('source',help='Path to the existing neighborfood.db')
args=parser.parse_args()
source=Path(args.source).resolve()
if not source.is_file(): raise SystemExit('SQLite source not found')
original=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
snapshot=sqlite3.connect(':memory:')
original.backup(snapshot)
original.close()
try:
    with Connection() as db:
        tables=db.conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'neighborfood_schema_version'").fetchall()
        target_names={r['tablename'] for r in tables}
        source_names=[r[0] for r in snapshot.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
        if set(source_names)-target_names: raise SystemExit('Unknown source tables; review before importing')
        for t in target_names:
            if db.conn.execute(f'SELECT COUNT(*) AS n FROM public."{t}"').fetchone()['n']:
                raise SystemExit('Target tables must be empty; no existing data is overwritten')
        counts={}
        # Creation order in the existing database follows parent-before-child order.
        for table in source_names:
            cur=snapshot.execute(f'SELECT * FROM "{table}"')
            columns=[d[0] for d in cur.description]
            target_cols={r['column_name'] for r in db.conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",(table,))}
            if set(columns)-target_cols: raise SystemExit(f'Unknown columns in {table}; stop and review')
            sql=f'INSERT INTO public."{table}" ('+','.join('"'+c+'"' for c in columns)+') VALUES ('+','.join('%s' for _ in columns)+')'
            n=0
            for row in cur:
                db.conn.execute(sql,row)
                n+=1
            actual=db.conn.execute(f'SELECT COUNT(*) AS n FROM public."{table}"').fetchone()['n']
            if n!=actual: raise RuntimeError(f'Row count mismatch: {table}')
            counts[table]=n
        for table in SERIAL_TABLES:
            db.conn.execute(f"SELECT setval(pg_get_serial_sequence('public.{table}','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM public.{table}")
        # PK, UNIQUE and foreign key constraints are enforced by PostgreSQL throughout.
    for table,n in counts.items(): print(f'{table}: {n} rows')
    print('Import committed. Upload images separately with import_uploads.py.')
finally:
    snapshot.close()
