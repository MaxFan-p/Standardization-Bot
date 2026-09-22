"""Minimal persistence for tracking submitted specs and their reviews.

SQLite keeps the POC dependency-free. Swap for Airtable/Postgres/a Google
Sheet later without touching the handlers — just keep these function signatures.
"""
import sqlite3
from datetime import datetime, timezone

import config


def _conn():
    return sqlite3.connect(config.DB_PATH)


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT,
                spec_text TEXT NOT NULL,
                findings TEXT NOT NULL)
            """
        )


def save_review(user_id: str, channel_id: str, spec_text: str, findings: str):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO reviews (created_at, user_id, channel_id, spec_text, findings) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), user_id, channel_id, spec_text, findings),
        )
        return cur.lastrowid


def list_reviews(limit: int = 10):
    """Return recent reviews as a list of (id, created_at, user_id, snippet)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created_at, user_id, substr(spec_text, 1, 60) "
            "FROM reviews ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows