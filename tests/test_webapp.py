"""webapp.py: what happens when Google redirects someone back to us."""
import google_auth
import links
import tokens
import webapp
from conftest import OWNER

FRESH_TOKEN = '{"token": "fresh"}'


class FakeCredentials:
    def to_json(self):
        return FRESH_TOKEN


def exchange_succeeds(monkeypatch):
    monkeypatch.setattr(google_auth, "exchange_code", lambda state, code: FakeCredentials())


def test_approving_saves_the_token_for_the_right_chat(monkeypatch):
    exchange_succeeds(monkeypatch)
    state = links.create(OWNER)

    title, _ = webapp.handle_callback({"state": [state], "code": ["one-time-code"]})

    assert title == "Connected"
    assert tokens.get_token(OWNER) == FRESH_TOKEN


def test_the_same_callback_cannot_be_used_twice(monkeypatch):
    exchange_succeeds(monkeypatch)
    state = links.create(OWNER)
    webapp.handle_callback({"state": [state], "code": ["c"]})
    tokens.delete_token(OWNER)

    title, _ = webapp.handle_callback({"state": [state], "code": ["c"]})

    assert title == "Link expired"
    assert tokens.has_token(OWNER) is False


def test_a_forged_state_links_nothing(monkeypatch):
    """Someone hitting the callback with a state we never issued gets nowhere."""
    exchange_succeeds(monkeypatch)

    title, _ = webapp.handle_callback({"state": ["forged"], "code": ["c"]})

    assert title == "Link expired"
    assert tokens.has_token(OWNER) is False


def test_pressing_cancel_on_google_is_reported(monkeypatch):
    exchange_succeeds(monkeypatch)
    links.create(OWNER)

    title, message = webapp.handle_callback({"error": ["access_denied"]})

    assert title == "Not connected"
    assert "access_denied" in message
    assert tokens.has_token(OWNER) is False


def test_a_failed_exchange_saves_nothing(monkeypatch):
    def boom(state, code):
        raise RuntimeError("Google said no")

    monkeypatch.setattr(google_auth, "exchange_code", boom)
    state = links.create(OWNER)

    title, _ = webapp.handle_callback({"state": [state], "code": ["c"]})

    assert title == "Something went wrong"
    assert tokens.has_token(OWNER) is False
