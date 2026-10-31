"""Opt-in PostgreSQL regression against an explicitly named local test database."""
import os

import psycopg
import pytest

from app.db.postgres import Connection
from app.db.schema import validate_postgres_schema


def test_incomplete_postgres_schema_fails_before_initialization(monkeypatch):
    dsn = os.getenv('NEIGHBORFOOD_TEST_POSTGRES_DSN', '')
    if not dsn:
        pytest.skip('Set NEIGHBORFOOD_TEST_POSTGRES_DSN for the local PostgreSQL regression')

    params = psycopg.conninfo.conninfo_to_dict(dsn)
    if (params.get('host') not in {'127.0.0.1', 'localhost', '::1'}
            or not params.get('dbname', '').startswith('nf_test_')
            or params.get('hostaddr') or params.get('service')):
        pytest.fail('PostgreSQL regression requires a local nf_test_* database')

    monkeypatch.setenv('DATABASE_URL', dsn)
    monkeypatch.setenv('DATABASE_SSLMODE', 'disable')
    with Connection() as connection:
        validate_postgres_schema(connection)
        try:
            # PostgreSQL DDL is transactional: all changes below are rolled back.
            connection.conn.execute('ALTER TABLE public.transactions DROP COLUMN settlement_id')
            connection.conn.execute('ALTER TABLE public.ocr_guard_settings DROP COLUMN enabled')
            connection.conn.execute('DROP TABLE public.qr_verification_events')
            with pytest.raises(RuntimeError) as error:
                validate_postgres_schema(connection)
            message = str(error.value)
            assert 'transactions.settlement_id' in message
            assert 'ocr_guard_settings.enabled' in message
            assert 'qr_verification_events' in message
            assert 'docs/SUPABASE_MIGRATION.md' in message
        finally:
            connection.rollback()
        validate_postgres_schema(connection)
