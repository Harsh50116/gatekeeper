"""
Phase 0 snapshot tool for DB migration.

Exports users, user_categories, digest_history, items from the DB pointed to by
DB_CONNECTION_STRING into backups/*.csv, plus a row-count report used to verify
the data later when we load it into local Docker + the new prod Supabase project.

Read-only against the source DB. Re-runnable (overwrites existing CSVs).
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

TABLES = ["users", "user_categories", "digest_history", "items"]
BACKUPS_DIR = Path(__file__).resolve().parent.parent / "backups"


def _redact(conn_str: str) -> str:
    if "@" not in conn_str:
        return "unknown"
    return conn_str.split("@", 1)[1].split("/", 1)[0]


def main() -> int:
    conn_str = os.environ.get("DB_CONNECTION_STRING", "")
    if not conn_str:
        print("ERROR: DB_CONNECTION_STRING not set in environment", file=sys.stderr)
        return 1

    BACKUPS_DIR.mkdir(exist_ok=True)

    print(f"Source: {_redact(conn_str)}")
    print(f"Output: {BACKUPS_DIR}")
    print()

    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()

    counts: dict[str, int] = {}
    for table in TABLES:
        out_path = BACKUPS_DIR / f"{table}.csv"
        print(f"Exporting {table}...", end=" ", flush=True)
        with open(out_path, "wb") as f:
            cur.copy_expert(f"COPY {table} TO STDOUT WITH CSV HEADER", f)
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        counts[table] = count
        size_kb = out_path.stat().st_size / 1024
        print(f"{count} rows ({size_kb:.1f} KB)")

    timestamp = datetime.now(timezone.utc).isoformat()
    counts_path = BACKUPS_DIR / "snapshot_counts.txt"
    with open(counts_path, "w") as f:
        f.write(f"Snapshot taken: {timestamp}\n")
        f.write(f"Source: {_redact(conn_str)}\n\n")
        for table, count in counts.items():
            f.write(f"{table}: {count}\n")

    cur.close()
    conn.close()

    print(f"\nSnapshot complete. Counts written to backups/snapshot_counts.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
