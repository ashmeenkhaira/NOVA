"""Google tokens, one per chat.

NOVA used to keep a single token.json belonging to the owner. This table lets
each chat connect its own Google account, so the Calendar and Gmail tools act
as whoever is asking instead of always as the owner.

Same shape as memory.py: one table, four small functions, no ORM.

SECURITY NOTE: tokens are stored as plain text, like the facts in memory.db.
That is acceptable while only the owner connects, because the file is chmod 600
on a machine only they can reach. Encrypt this column before letting other
people connect from their own devices.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

# Same database file as memory.py - one file, two tables.
DB_FILE = Path(__file__).parent / "memory.db"


def connect():
    """Open the database, creating the google_tokens table the first time."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS google_tokens (
            chat_id    INTEGER PRIMARY KEY,
            token_json TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    return conn


def save_token(chat_id, token_json):
    """Store this chat's Google token, replacing any earlier one.

    chat_id is the PRIMARY KEY, so INSERT OR REPLACE means re-connecting
    overwrites instead of creating a second row for the same person.
    """
    conn = connect()
    conn.execute(
        "INSERT OR REPLACE INTO google_tokens (chat_id, token_json, created_at) VALUES (?, ?, ?)",
        (chat_id, token_json, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def get_token(chat_id):
    """Return this chat's token as JSON text, or None if they have not connected."""
    conn = connect()
    row = conn.execute(
        "SELECT token_json FROM google_tokens WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def has_token(chat_id):
    """True if this chat has connected a Google account."""
    return get_token(chat_id) is not None


def delete_token(chat_id):
    """Forget this chat's token. Returns True if there was one to forget."""
    conn = connect()
    cursor = conn.execute("DELETE FROM google_tokens WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
