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


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id          TEXT PRIMARY KEY,
            category    TEXT NOT NULL,
            title       TEXT NOT NULL,
            summary     TEXT,
            url         TEXT NOT NULL,
            published   TEXT NOT NULL,
            source      TEXT NOT NULL,
            fetched_at  TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_items_category_published
            ON items (category, published)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_categories (
            user_id   TEXT NOT NULL,
            category  TEXT NOT NULL,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS digest_history (
            user_id     TEXT NOT NULL,
            digest_date TEXT NOT NULL,
            digest_text TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            PRIMARY KEY (user_id, digest_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


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
