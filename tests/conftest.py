"""Shared setup for every test.

Tests never call Groq, Google or Telegram, and never touch your real memory.db.
Run them from the project folder with:  python -m pytest
"""
import os
import sys
from pathlib import Path

import pytest

# Fake settings, set BEFORE config.py is imported anywhere. load_dotenv does not
# overwrite variables that already exist, so the real .env is ignored in tests.
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test-token"
os.environ["MY_CHAT_ID"] = "111"
os.environ["GOOGLE_CREDENTIALS_FILE"] = "credentials.json"

# Let the tests import the project's files (config, tools, ...).
sys.path.insert(0, str(Path(__file__).parent.parent))

OWNER = 111
FRIEND = 222


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    """Every test gets its own empty database, and never sees the real token.json."""
    import google_auth
    import memory
    import tokens

    # memory.py and tokens.py each point at the same file, so patch both.
    monkeypatch.setattr(memory, "DB_FILE", tmp_path / "test.db")
    monkeypatch.setattr(tokens, "DB_FILE", tmp_path / "test.db")

    # Otherwise the owner's real token.json would be imported into the test
    # database and some tests would pass for the wrong reason.
    monkeypatch.setattr(google_auth, "LEGACY_TOKEN_FILE", tmp_path / "no-token.json")


@pytest.fixture(autouse=True)
def no_pending_approvals():
    """Every test starts with no waiting write actions."""
    import approvals
    approvals.pending.clear()
    yield
    approvals.pending.clear()
