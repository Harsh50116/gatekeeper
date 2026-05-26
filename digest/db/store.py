import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DB_CONNECTION_STRING", "")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DB_CONNECTION_STRING not set in environment")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


# Schema lives in migrations/*.sql, not here. Apply with `make db-init` (local)
# or `psql "<DB_CONNECTION_STRING>" -f migrations/0001_initial.sql` (staging/prod).
# The previous in-code init_db() was removed to prevent local dev from silently
# creating tables in shared cloud DBs.


def insert_items(items: list[dict]) -> int:
    if not items:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    for item in items:
        cur.execute(
            "INSERT INTO items (id, category, title, summary, url, published, source, fetched_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (
                item["id"],
                item["category"],
                item["title"],
                item.get("summary"),
                item["url"],
                item["published"],
                item["source"],
                item["fetched_at"],
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    conn.close()
    return inserted


def get_user_by_email(email: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, email FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return None
    cur.execute("SELECT category FROM user_categories WHERE user_id = %s", (user["id"],))
    cats = [r["category"] for r in cur.fetchall()]
    conn.close()
    return {"id": user["id"], "email": user["email"], "categories": cats}


def update_user_categories(user_id: str, categories: list[str]) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_categories WHERE user_id = %s", (user_id,))
    for cat in categories:
        cur.execute("INSERT INTO user_categories (user_id, category) VALUES (%s, %s)", (user_id, cat))
    conn.commit()
    conn.close()


def register_user(email: str, categories: list[str]) -> str:
    conn = get_connection()
    cur = conn.cursor()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        cur.execute(
            "INSERT INTO users (id, email, created_at) VALUES (%s, %s, %s)",
            (user_id, email, now),
        )
        for cat in categories:
            cur.execute(
                "INSERT INTO user_categories (user_id, category) VALUES (%s, %s)",
                (user_id, cat),
            )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        raise ValueError("Email already registered")
    conn.close()
    return user_id


def get_all_users() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.id, u.email, STRING_AGG(uc.category, ',') AS categories
        FROM users u
        JOIN user_categories uc ON u.id = uc.user_id
        GROUP BY u.id, u.email
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r["id"], "email": r["email"], "categories": r["categories"].split(",")}
        for r in rows
    ]


def get_all_recent_items() -> dict[str, list[dict]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT title, summary, url, source, category, published
        FROM items
        WHERE published >= %s
        ORDER BY category, published DESC
    """, (cutoff,))
    rows = cur.fetchall()
    conn.close()

    items_by_category: dict[str, list[dict]] = {}
    for r in rows:
        cat = r["category"]
        items_by_category.setdefault(cat, []).append({
            "title": r["title"],
            "summary": r["summary"],
            "url": r["url"],
            "source": r["source"],
            "published": r["published"],
        })
    return items_by_category


def save_digest(user_id: str, digest_text: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO digest_history (user_id, digest_date, digest_text, created_at) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, digest_date) DO UPDATE SET digest_text = %s",
        (user_id, today, digest_text, now, digest_text),
    )
    conn.commit()
    conn.close()


def get_previous_digest(user_id: str) -> str | None:
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT digest_text FROM digest_history WHERE user_id = %s AND digest_date = %s",
        (user_id, yesterday),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_digest_by_date(user_id: str, digest_date: str) -> str | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT digest_text FROM digest_history WHERE user_id = %s AND digest_date = %s",
        (user_id, digest_date),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_user_items(user_id: str) -> dict[str, list[dict]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT i.title, i.summary, i.url, i.source, i.category, i.published
        FROM items i
        JOIN user_categories uc ON i.category = uc.category
        WHERE uc.user_id = %s
          AND i.published >= %s
        ORDER BY i.category, i.published DESC
    """, (user_id, cutoff))
    rows = cur.fetchall()
    conn.close()

    items_by_category: dict[str, list[dict]] = {}
    for r in rows:
        cat = r["category"]
        items_by_category.setdefault(cat, []).append({
            "title": r["title"],
            "summary": r["summary"],
            "url": r["url"],
            "source": r["source"],
            "published": r["published"],
        })
    return items_by_category
