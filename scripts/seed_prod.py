"""
Seed a fresh DB (initially: the new prod Supabase project) with schema +
Phase 0 snapshot data.

Usage:
    DB_CONNECTION_STRING='postgres://...' python3 scripts/seed_prod.py
    DB_CONNECTION_STRING='postgres://...' python3 scripts/seed_prod.py --force

What it does:
1. Applies migrations/0001_initial.sql (idempotent — uses IF NOT EXISTS).
2. Loads users.csv, user_categories.csv, digest_history.csv from backups/.
   (items.csv is intentionally skipped — items regenerate on the next scrape.)
3. Verifies row counts against the snapshot.

Safety:
- Refuses to load if any of the three target tables already has rows,
  unless --force is passed (which wipes those three tables first).
- Connection string is NEVER read from .env. It must be provided explicitly
  on the command line so there's no chance of accidentally seeding the wrong
  environment from a stale .env value.
"""

import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "migrations" / "0001_initial.sql"
BACKUPS = ROOT / "backups"

# Load order matters: users first (others have FK -> users).
LOAD_ORDER = ["users", "user_categories", "digest_history"]


def _redact(conn_str: str) -> str:
    if "@" not in conn_str:
        return "unknown"
    return conn_str.split("@", 1)[1].split("/", 1)[0]


def _read_expected_counts() -> dict[str, int]:
    counts_path = BACKUPS / "snapshot_counts.txt"
    if not counts_path.exists():
        return {}
    expected: dict[str, int] = {}
    for line in counts_path.read_text().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        try:
            expected[key.strip()] = int(val.strip())
        except ValueError:
            pass
    return expected


def main() -> int:
    conn_str = os.environ.get("DB_CONNECTION_STRING", "")
    if not conn_str:
        print("ERROR: DB_CONNECTION_STRING not set on command line", file=sys.stderr)
        print("Pass it inline:", file=sys.stderr)
        print("  DB_CONNECTION_STRING='postgres://...' python3 scripts/seed_prod.py", file=sys.stderr)
        return 1

    force = "--force" in sys.argv
    expected = _read_expected_counts()

    print(f"Target:    {_redact(conn_str)}")
    print(f"Migration: {MIGRATION.relative_to(ROOT)}")
    print(f"CSVs:      {BACKUPS.relative_to(ROOT)}/")
    print(f"Mode:      {'FORCE (will wipe existing rows)' if force else 'safe (abort if rows exist)'}")
    print()

    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    cur = conn.cursor()

    print("Applying migration...")
    cur.execute(MIGRATION.read_text())
    conn.commit()
    print("  Migration applied.\n")

    existing = {}
    for table in LOAD_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        existing[table] = cur.fetchone()[0]
    nonempty = {t: n for t, n in existing.items() if n > 0}

    if nonempty:
        if not force:
            print(f"ABORT: target has existing rows in {nonempty}.")
            print("Re-run with --force to wipe and reload, or investigate first.")
            return 1
        print(f"Wiping existing rows (--force): {nonempty}")
        for table in reversed(LOAD_ORDER):
            cur.execute(f"DELETE FROM {table}")
        conn.commit()
        print()

    print("Loading CSVs...")
    all_ok = True
    for table in LOAD_ORDER:
        csv_path = BACKUPS / f"{table}.csv"
        if not csv_path.exists():
            print(f"  {table}: SKIPPED (missing {csv_path.name})")
            continue
        with open(csv_path, "rb") as f:
            cur.copy_expert(f"COPY {table} FROM STDIN WITH CSV HEADER", f)
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        exp = expected.get(table)
        if exp is None:
            print(f"  {table}: {count} rows loaded (no expected count to verify)")
        elif count == exp:
            print(f"  {table}: {count} rows loaded (matches snapshot)")
        else:
            print(f"  {table}: {count} rows loaded (EXPECTED {exp}) — MISMATCH")
            all_ok = False

    conn.commit()
    cur.close()
    conn.close()

    print()
    if all_ok:
        print("Seed complete. Row counts match the Phase 0 snapshot.")
        return 0
    else:
        print("Seed complete BUT row counts diverge from snapshot. Investigate.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
