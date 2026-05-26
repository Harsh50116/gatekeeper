# Digest

A personalized daily audio news briefing. Users pick the sectors they care about, and every morning they receive an email link to audio digest narrated in a conversational radio-host style.

Long-term goal: extend into an agentic event planner that discovers and books events in the user's chosen fields.

**Live:** https://digestinfo-staging.up.railway.app/

---

## How it works

```
   ┌─ Web (Flask) ────────────────┐         ┌─ Cron (APScheduler, 7:00 UTC) ─┐
   │ /          registration form │         │  daily for each user:          │
   │ /play      audio player      │         │   scrape → Pass 1 summarize    │
   │ /register  welcome digest    │         │   → Pass 2 narrate (~430w)     │
   └──────────────┬───────────────┘         │   → edge-tts → upload          │
                  │                         │   → save digest → email        │
                  └────────────┬────────────┘────────────────┬───────────────┘
                               │                             │
                          Postgres (Supabase / Docker)   Supabase Storage
```

- **Sources** (15+ across 5 categories): RSS feeds, Hacker News API, ESPN scoreboard JSON, yfinance.
- **LLM**: Llama-3.3-70B via Hyperbolic. Two-pass — per-category summary cached in-memory, then a single narrative call.
- **Continuity**: yesterday's digest is fed back into the prompt so the LLM avoids repeating stories and links continuing ones.
- **TTS**: `edge-tts` (`en-US-GuyNeural`), MP3 output.
- **Email**: Brevo HTTP API, link to web player.

---

## Local development

Prerequisites: Python 3.11+, Docker Desktop.

```bash
# 1. install deps
pip install -r requirements.txt

# 2. start local Postgres (Docker)
make db-up
make db-init

# 3. run the web app
python -m digest.app                # http://localhost:8080

# 4. (optional) trigger a one-off pipeline run
python -m digest.pipeline
```

Register a test user via the form using **your own email** — the pipeline will scrape, build a digest, and actually email you.

See [`temp/local_db_workflow.md`](temp/local_db_workflow.md) for the full DB cheat-sheet.

---

## Environments

Three isolated databases, identical schema:

| Env       | DB                                    | Cron        | URL                                          |
|-----------|---------------------------------------|-------------|----------------------------------------------|
| local     | Docker Postgres (`localhost:5432`)    | manual run  | http://localhost:8080                        |
| staging   | Supabase project (us-west-2)          | active      | https://digestinfo-staging.up.railway.app/   |
| prod      | Supabase project (us-east-2)          | paused      | https://digestinfo.up.railway.app/           |

Schema lives only in `migrations/*.sql`. The app never auto-creates tables — apply migrations explicitly per environment.

Deployed on Railway: web + cron as separate services, one Railway environment per git branch (`staging` → staging env, `main` → prod env).

---

## Required environment variables

| Var                      | Used by                                      |
|--------------------------|----------------------------------------------|
| `DB_CONNECTION_STRING`   | `store.py` — Postgres                        |
| `HYPERBOLIC_KEY`         | `summarizer.py` — LLM                        |
| `SUPABASE_URL`, `SUPABASE_KEY` | `storage.py` — MP3 upload              |
| `BREVO_API_KEY`, `FROM_EMAIL`  | `mailer.py` — outbound email           |
| `APP_URL`                | `pipeline.py` — base URL for player links    |
| `DIGEST_HOUR`, `DIGEST_MINUTE` (optional) | `scheduler.py` — defaults 7:00 UTC |


