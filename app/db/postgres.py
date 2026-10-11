"""Compatibility for SQL used by Neighborfood at commit 28190b4.
Schema changes are applied explicitly, never in request handlers.
"""
import os
import re
import sqlite3
import psycopg

SERIAL_TABLES = {'notices', 'posts', 'transactions', 'settlements', 'users', 'manner_ratings', 'reports', 'conversations', 'messages'}

class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

def row_factory(cursor):
    names = [c.name for c in (cursor.description or [])]
    return lambda values: Row(zip(names, values))

class Cursor:
    def __init__(self, cursor=None, rows=None, lastrowid=None):
        self.cursor, self.rows, self.lastrowid = cursor, rows, lastrowid
        self.rowcount = cursor.rowcount if cursor is not None else 0
    def fetchone(self):
        if self.rows is not None:
            return self.rows.pop(0) if self.rows else None
        return self.cursor.fetchone()
    def fetchall(self):
        if self.rows is not None:
            rows, self.rows = self.rows, []
            return rows
        return self.cursor.fetchall()
    def __iter__(self):
        return iter(self.fetchall())

# Replace placeholders only outside SQL string literals.
def placeholders(sql):
    parts = re.split(r"('(?:''|[^'])*')", sql)
    return ''.join(p.replace('%', '%%').replace('?', '%s') if i % 2 == 0
                   else p.replace('%', '%%') for i, p in enumerate(parts))

def scalar_functions(sql):
    # SQLite scalar MAX(a,b)/MIN(a,b), preserving aggregate MAX(a)/MIN(a).
    matches = list(re.finditer(r'\b(MAX|MIN)\s*\(', sql, re.I))
    for match in reversed(matches):
        start=match.end(); depth=0; quoted=False; multi=False
        for ch in sql[start:]:
            if ch=="'": quoted=not quoted
            if quoted: continue
            if ch=='(': depth+=1
            elif ch==')':
                if depth==0: break
                depth-=1
            elif ch==',' and depth==0: multi=True
        if multi:
            sql=sql[:match.start()]+('GREATEST' if match[1].upper()=='MAX' else 'LEAST')+sql[match.start()+len(match[1]):]
    return sql

def translate(sql):
    sql=sql.strip().rstrip(';')
    sql=re.sub(r"date\('now',\s*'-' \|\| d \|\| ' days'\)",
               "to_char((CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - d * INTERVAL '1 day', 'YYYY-MM-DD')",sql,flags=re.I)
    sql=re.sub(r"date\('now',\s*'-6 days'\)",
               "to_char((CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - INTERVAL '6 days', 'YYYY-MM-DD')",sql,flags=re.I)
    sql=re.sub(r"date\('now'\)", "to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD')",sql,flags=re.I)
    sql=re.sub(r"datetime\('now'\)", 'CURRENT_TIMESTAMP',sql,flags=re.I)
    sql=re.sub(r'\bdatetime\(([a-z_][a-z_0-9.]*)\)', r"CAST(NULLIF(\1, '') AS timestamptz)", sql,flags=re.I)
    sql=scalar_functions(sql)
    sql=re.sub(r"\bLIKE\b", "ILIKE", sql, flags=re.I)
    if re.match(r'INSERT OR IGNORE',sql,re.I):
        sql=re.sub('INSERT OR IGNORE','INSERT',sql,count=1,flags=re.I)+' ON CONFLICT DO NOTHING'
    if re.match(r'INSERT OR REPLACE INTO auth_codes',sql,re.I):
        sql=re.sub('INSERT OR REPLACE','INSERT',sql,count=1,flags=re.I)+ ' ON CONFLICT (phone_number) DO UPDATE SET code=EXCLUDED.code, expiry_time=EXCLUDED.expiry_time'
    return sql

class Connection:
    def __init__(self):
        self.conn=psycopg.connect(os.environ['DATABASE_URL'],
            sslmode=os.getenv('DATABASE_SSLMODE','require'), connect_timeout=10,
            prepare_threshold=None, row_factory=row_factory)
        self.conn.execute("SET TIME ZONE 'UTC'")
    def __enter__(self): return self
    def __exit__(self, kind, value, tb):
        try:
            self.conn.rollback() if kind else self.conn.commit()
        finally: self.conn.close()
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()
    def execute(self, sql, params=()):
        pragma=re.match(r'\s*PRAGMA table_info\((\w+)\)',sql,re.I)
        if pragma:
            cur=self.conn.execute("SELECT ordinal_position-1 AS cid, column_name AS name, data_type AS type FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (pragma[1],))
            return Cursor(cur)
        if re.match(r'\s*(CREATE TABLE|CREATE INDEX|ALTER TABLE)',sql,re.I):
            # Migration script owns DDL. Missing schema must fail visibly.
            table=re.search(r'(?:TABLE(?: IF NOT EXISTS)?|ON)\s+(\w+)',sql,re.I)
            if table and not self.conn.execute('SELECT to_regclass(%s) AS name',('public.'+table[1],)).fetchone()['name']:
                raise RuntimeError('Run scripts/supabase_migrate.py before starting the API')
            return Cursor(rows=[])
        if 'sqlite_master' in sql:
            sql="SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' AND table_name='receipts'"
        sql=translate(sql)
        insert=re.match(r'INSERT INTO (\w+)',sql,re.I)
        returning=insert and insert[1] in SERIAL_TABLES
        if returning: sql+=' RETURNING id'
        # Savepoint lets existing IntegrityError handlers continue the transaction.
        try:
            with self.conn.transaction():
                cur=self.conn.execute(placeholders(sql) if params else sql, tuple(params) if params else None)
                value=cur.fetchone()['id'] if returning and cur.rowcount else None
        except psycopg.IntegrityError as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc
        return Cursor(cur,lastrowid=value)
