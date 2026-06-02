# Database migrations

Each `*.sql` file in this directory is a numbered, forward-only schema migration. They are the **single source of truth** for the schema across all environments (local Docker, staging Supabase, prod Supabase). Python code does not create or alter tables — that was deliberately removed when DB environments were separated.

## First-time setup for a fresh environment

Schema does not auto-apply on app startup. Before running the app or pipeline against a fresh DB:

```bash
# Local
make db-up
make db-init

# Staging or prod
psql "<connection-string>" -f migrations/0001_initial.sql
```

## Apply migrations to an environment

```bash
psql "<DB_CONNECTION_STRING>" -f migrations/0001_initial.sql
```

The connection string per env:

- **Local**: `postgres://postgres:postgres@localhost:5432/gatekeeper` (Docker)
- **Staging**: pooled URL from Supabase project `gatekeeper-staging`
- **Prod**: pooled URL from Supabase project `gatekeeper-prod`

All migrations use `IF NOT EXISTS`, so re-applying a migration is a safe no-op.

## Adding a new migration

1. Create the next numbered file: `0002_<short_description>.sql`.
2. Write idempotent DDL where possible (`IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, etc.).
3. Apply to local first, then staging, then prod — in that order, on separate runs.
4. Commit the file with the PR that introduces the schema change.

## Why a flat folder of SQL files instead of Alembic / Supabase CLI?

We have ~10 tables, no ORM, and no plans for downgrade scripts. A folder of SQL files is the simplest thing that solves the problem, and any developer can read/apply it without learning a tool first. Revisit when we outgrow it.
