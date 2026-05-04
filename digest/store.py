import sqlite3
import os
import uuid
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "digest.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
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

        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            email       TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_categories (
            user_id   TEXT NOT NULL,
            category  TEXT NOT NULL,
            PRIMARY KEY (user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.close()


def insert_items(items: list[dict]) -> int:
    if not items:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    for item in items:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO items (id, category, title, summary, url, published, source, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
            inserted += cursor.rowcount
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return inserted


def register_user(email: str, categories: list[str]) -> str:
    conn = get_connection()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO users (id, email, created_at) VALUES (?, ?, ?)",
            (user_id, email, now),
        )
        for cat in categories:
            conn.execute(
                "INSERT INTO user_categories (user_id, category) VALUES (?, ?)",
                (user_id, cat),
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Email already registered")
    conn.close()
    return user_id


def get_all_users() -> list[dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.id, u.email, GROUP_CONCAT(uc.category) AS categories
        FROM users u
        JOIN user_categories uc ON u.id = uc.user_id
        GROUP BY u.id, u.email
    """).fetchall()
    conn.close()
    return [
        {"id": r["id"], "email": r["email"], "categories": r["categories"].split(",")}
        for r in rows
    ]


def get_user_items(user_id: str) -> dict[str, list[dict]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT i.title, i.summary, i.url, i.source, i.category, i.published
        FROM items i
        JOIN user_categories uc ON i.category = uc.category
        WHERE uc.user_id = ?
          AND i.published >= ?
        ORDER BY i.category, i.published DESC
    """, (user_id, cutoff)).fetchall()
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
