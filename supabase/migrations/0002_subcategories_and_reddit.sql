-- Migration 0002 — subcategories + Reddit items
-- Created: 2026-05-29
--
-- Adds subcategory support to items, creates reddit_items table,
-- and adds user_subcategories for storing user preferences.
--
-- Idempotent (uses IF NOT EXISTS / IF NOT EXISTS column check).
-- Apply with:  psql "<DB_CONNECTION_STRING>" -f migrations/0002_subcategories_and_reddit.sql
-- Or locally:  make db-init


-- Add subcategory column to existing items (nullable — filled by LLM classifier).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'items' AND column_name = 'subcategory'
    ) THEN
        ALTER TABLE items ADD COLUMN subcategory TEXT;
    END IF;
END $$;


-- Reddit-sourced items. Separate from RSS items due to different fields
-- (upvotes, comment_count, subreddit). Subcategory is always set from
-- the subreddit mapping at fetch time.
CREATE TABLE IF NOT EXISTS reddit_items (
    id              TEXT PRIMARY KEY,
    subreddit       TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT,
    url             TEXT NOT NULL,
    upvotes         INTEGER NOT NULL DEFAULT 0,
    comment_count   INTEGER NOT NULL DEFAULT 0,
    category        TEXT NOT NULL,
    subcategory     TEXT NOT NULL,
    published       TEXT NOT NULL,
    fetched_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reddit_items_category_published
    ON reddit_items (category, published);

CREATE INDEX IF NOT EXISTS idx_reddit_items_subcategory
    ON reddit_items (subcategory);


-- User subcategory preferences. When empty for a category, treat as
-- "all subcategories selected" for backwards compatibility.
CREATE TABLE IF NOT EXISTS user_subcategories (
    user_id     TEXT NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    PRIMARY KEY (user_id, category, subcategory),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
