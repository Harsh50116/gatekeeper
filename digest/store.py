import sqlite3
import os
import uuid
from datetime import datetime, timezone

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
