-- Migration 0003 — digest_run_inputs snapshot table
-- Created: 2026-06-03
--
-- Records the exact RSS + Reddit items used when generating a user's digest.
-- Powers the admin eval dashboard.
--
-- Idempotent (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS digest_run_inputs (
    user_id      TEXT NOT NULL,
    digest_date  TEXT NOT NULL,
    source_type  TEXT NOT NULL,
    item_id      TEXT,
    category     TEXT NOT NULL,
    subcategory  TEXT,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL,
    source       TEXT NOT NULL,
    published    TEXT,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_digest_run_inputs_user_date
    ON digest_run_inputs (user_id, digest_date);
