-- Apply only after a verified backup and a rehearsal on an isolated database.
-- Additive migration; OCR remains disabled until an authorized operator completes
-- the external protection and firewall checks. Existing application rows are untouched.
-- The migration runner supplies the transaction.

CREATE TABLE public.ocr_guard_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    user_daily_limit INTEGER NOT NULL CHECK (user_daily_limit > 0),
    user_monthly_limit INTEGER NOT NULL CHECK (user_monthly_limit > 0),
    global_monthly_limit INTEGER NOT NULL CHECK (global_monthly_limit > 0),
    updated_at TEXT NOT NULL
);

CREATE TABLE public.ocr_requests (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.users(id),
    idempotency_key TEXT NOT NULL,
    image_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('reserved', 'sent', 'completed', 'failed', 'canceled')),
    scan_id TEXT UNIQUE REFERENCES public.receipts(id),
    object_name TEXT,
    storage_kind TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key)
);
CREATE INDEX idx_ocr_created ON public.ocr_requests (created_at);
CREATE INDEX idx_ocr_user_created ON public.ocr_requests (user_id, created_at);

CREATE TABLE public.ocr_guard_audit (
    id TEXT PRIMARY KEY,
    actor_id BIGINT NOT NULL REFERENCES public.users(id),
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL
);

INSERT INTO public.ocr_guard_settings
    (id, enabled, user_daily_limit, user_monthly_limit, global_monthly_limit, updated_at)
VALUES (1, 0, 3, 30, 300, to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'));

ALTER TABLE public.ocr_guard_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_guard_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.ocr_guard_settings, public.ocr_requests, public.ocr_guard_audit FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
        REVOKE ALL ON public.ocr_guard_settings, public.ocr_requests, public.ocr_guard_audit FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
        REVOKE ALL ON public.ocr_guard_settings, public.ocr_requests, public.ocr_guard_audit FROM authenticated;
    END IF;
END $$;
