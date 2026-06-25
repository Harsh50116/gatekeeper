-- Migration 0004 — add summary column to digest_run_inputs
-- Stores the pass-one LLM summary (per subcategory) alongside each input item.

ALTER TABLE digest_run_inputs ADD COLUMN IF NOT EXISTS summary TEXT;
