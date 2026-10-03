"""Long-term memory: facts about each chat, saved in a SQLite database file.

Unlike the histories in bot.py, these survive restarting the bot.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

# The database is one file next to this one. It holds personal details,
# so *.db is in .gitignore - it must never be committed.
DB_FILE = Path(__file__).parent / "memory.db"


def connect():
    """Open the database, creating the memories table the first time."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            fact       TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    return conn


def add_fact(chat_id, fact):
    """Save one fact for a chat. Returns the new fact's id."""
    created_at = datetime.now().isoformat(timespec="seconds")

    conn = connect()
    # The ? marks are filled in safely by sqlite3 with the values in brackets,
    # in order. Never glue values into SQL text yourself.
    cursor = conn.execute(
        "INSERT INTO memories (chat_id, fact, created_at) VALUES (?, ?, ?)",
        (chat_id, fact, created_at),
    )
    conn.commit()  # save the change to the file
    conn.close()
    return cursor.lastrowid


def get_facts(chat_id):
    """Return all facts for a chat, oldest first, as a list of (id, fact) pairs."""
    conn = connect()
    rows = conn.execute(
        "SELECT id, fact FROM memories WHERE chat_id = ? ORDER BY id",
        (chat_id,),
    ).fetchall()
    conn.close()
    return rows


def delete_fact(chat_id, fact_id):
    """Delete one fact. Returns True if it existed and belonged to this chat."""
    conn = connect()
    # Checking chat_id too means one chat can never delete another chat's facts.
    cursor = conn.execute(
        "DELETE FROM memories WHERE id = ? AND chat_id = ?",
        (fact_id, chat_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
