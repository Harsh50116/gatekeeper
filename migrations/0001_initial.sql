-- Migration 0001 — initial schema
-- Created: 2026-05-12
--
-- Defines all tables and indexes for the digest service. This is the canonical
-- schema source; Python code does NOT create or alter tables.
--
-- Idempotent (uses IF NOT EXISTS), so it's safe to re-apply to any environment.
-- Apply with:  psql "<DB_CONNECTION_STRING>" -f migrations/0001_initial.sql
-- Or locally:  make db-init


-- Scraped news items, shared across all users.
-- id is sha256(url); ON CONFLICT DO NOTHING in app code handles dedup.
CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    title       TEXT NOT NULL,
    summary     TEXT,
    url         TEXT NOT NULL,
    published   TEXT NOT NULL,
    source      TEXT NOT NULL,
    fetched_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_category_published
    ON items (category, published);


-- Registered users.
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);


-- User -> category subscriptions. Composite PK enforces uniqueness per pair.
CREATE TABLE IF NOT EXISTS user_categories (
    user_id   TEXT NOT NULL,
    category  TEXT NOT NULL,
    PRIMARY KEY (user_id, category),
    FOREIGN KEY (user_id) REFERENCES users(id)
);


-- One digest per user per day. Read by the pipeline as "yesterday's digest"
-- to give the LLM continuity context (skip overlapping stories, link
-- continuing ones).
CREATE TABLE IF NOT EXISTS digest_history (
    user_id     TEXT NOT NULL,
    digest_date TEXT NOT NULL,
    digest_text TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, digest_date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
