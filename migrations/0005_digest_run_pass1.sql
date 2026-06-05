-- Migration 0005 — digest_run_pass1 table
-- Stores the Pass 1 per-subcategory summaries produced during digest generation.
-- Powers the eval dashboard's two-view toggle.

CREATE TABLE IF NOT EXISTS digest_run_pass1 (
    user_id      TEXT NOT NULL,
    digest_date  TEXT NOT NULL,
    category     TEXT NOT NULL,
    subcategory  TEXT NOT NULL,
    summary      TEXT NOT NULL,
    item_count   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_digest_run_pass1_user_date
    ON digest_run_pass1 (user_id, digest_date);
