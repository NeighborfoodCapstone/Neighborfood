-- Additive migration. Rehearse on an isolated copy after a verified backup.
-- Existing unbound GPS/QR records are retained but cannot authorize a trade.
BEGIN;
-- SQLite adds this on group cancellation; PostgreSQL request handlers do not run DDL.
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS is_system BIGINT NOT NULL DEFAULT 0;
ALTER TABLE public.transactions ADD COLUMN settlement_id BIGINT REFERENCES public.settlements(id);
CREATE UNIQUE INDEX idx_tx_settlement_receiver ON public.transactions (settlement_id, receiver_id)
    WHERE settlement_id IS NOT NULL;
ALTER TABLE public.location_verify_sessions
    ADD COLUMN transaction_id BIGINT REFERENCES public.transactions(id),
    ADD COLUMN settlement_id BIGINT REFERENCES public.settlements(id),
    ADD CONSTRAINT location_one_trade CHECK (transaction_id IS NULL OR settlement_id IS NULL);
CREATE INDEX idx_location_transaction_user ON public.location_verify_sessions (transaction_id, subject_id, verified_at);
CREATE INDEX idx_location_settlement_user ON public.location_verify_sessions (settlement_id, subject_id, verified_at);
ALTER TABLE public.qr_sessions
    ADD COLUMN transaction_id BIGINT REFERENCES public.transactions(id),
    ADD COLUMN settlement_id BIGINT REFERENCES public.settlements(id),
    ADD COLUMN scanner_id BIGINT REFERENCES public.users(id),
    ADD COLUMN location_session_id TEXT REFERENCES public.location_verify_sessions(id),
    ADD CONSTRAINT qr_one_trade CHECK (transaction_id IS NULL OR settlement_id IS NULL);
CREATE INDEX idx_qr_transaction_user ON public.qr_sessions (transaction_id, subject_id, status);
CREATE INDEX idx_qr_settlement_user ON public.qr_sessions (settlement_id, subject_id, status);
CREATE TABLE public.qr_verification_events (
    id TEXT PRIMARY KEY,
    qr_session_id TEXT REFERENCES public.qr_sessions(id),
    actor_id BIGINT NOT NULL REFERENCES public.users(id),
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL
);
ALTER TABLE public.qr_verification_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.qr_verification_events FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
        REVOKE ALL ON public.qr_verification_events FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
        REVOKE ALL ON public.qr_verification_events FROM authenticated;
    END IF;
END $$;
COMMIT;
