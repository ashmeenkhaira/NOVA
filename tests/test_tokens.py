"""tokens.py: one Google account per chat."""
import google_auth
import pytest
import tokens
from conftest import FRIEND, OWNER

FAKE = '{"token": "abc", "refresh_token": "r"}'


def test_no_token_until_one_is_saved():
    assert tokens.get_token(OWNER) is None
    assert tokens.has_token(OWNER) is False


def test_save_and_read_back():
    tokens.save_token(OWNER, FAKE)
    assert tokens.get_token(OWNER) == FAKE
    assert tokens.has_token(OWNER) is True


def test_tokens_are_kept_per_chat():
    tokens.save_token(OWNER, '{"token": "mine"}')
    tokens.save_token(FRIEND, '{"token": "theirs"}')
    assert tokens.get_token(OWNER) == '{"token": "mine"}'
    assert tokens.get_token(FRIEND) == '{"token": "theirs"}'


def test_reconnecting_replaces_instead_of_duplicating():
    tokens.save_token(OWNER, '{"token": "old"}')
    tokens.save_token(OWNER, '{"token": "new"}')
    assert tokens.get_token(OWNER) == '{"token": "new"}'


def test_delete_token():
    tokens.save_token(OWNER, FAKE)
    assert tokens.delete_token(OWNER) is True
    assert tokens.has_token(OWNER) is False
    assert tokens.delete_token(OWNER) is False   # already gone


def test_deleting_one_chat_leaves_the_other_alone():
    tokens.save_token(OWNER, FAKE)
    tokens.save_token(FRIEND, FAKE)
    tokens.delete_token(FRIEND)
    assert tokens.has_token(OWNER) is True


def test_unlinked_chat_raises_not_connected():
    with pytest.raises(google_auth.NotConnected):
        google_auth.get_credentials(FRIEND)


def test_token_missing_scopes_is_thrown_away():
    # A token approved for only one of the three scopes we need.
    weak = ('{"token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s",'
            ' "scopes": ["https://www.googleapis.com/auth/calendar.events"]}')
    tokens.save_token(OWNER, weak)

    with pytest.raises(google_auth.NotConnected, match="permissions"):
        google_auth.get_credentials(OWNER)
    # It is removed, so the user is asked to connect again rather than
    # hitting a confusing 403 from Google later.
    assert tokens.has_token(OWNER) is False


def test_legacy_token_file_is_imported_once(tmp_path, monkeypatch):
    """An existing single-user token.json moves into the database for the owner."""
    legacy = tmp_path / "token.json"
    legacy.write_text(FAKE)
    monkeypatch.setattr(google_auth, "LEGACY_TOKEN_FILE", legacy)

    google_auth._import_legacy_token(OWNER)
    assert tokens.get_token(OWNER) == FAKE

    # A friend's chat never picks up the owner's old token.
    google_auth._import_legacy_token(FRIEND)
    assert tokens.has_token(FRIEND) is False
