"""gcal.py and gmail.py, with a fake Gmail service - no network."""
import base64
import email

import pytest

import gcal
import gmail
import google_auth


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


# --- Sign-in on a server ------------------------------------------------------

def test_headless_server_fails_instead_of_waiting_for_a_browser(tmp_path, monkeypatch):
    monkeypatch.setattr(google_auth, "TOKEN_FILE", tmp_path / "no-token.json")
    monkeypatch.setenv("NOVA_HEADLESS", "1")
    with pytest.raises(RuntimeError, match="python google_auth.py"):
        google_auth.get_credentials()


# --- Calendar formatting ----------------------------------------------------

def test_describe_timed_event():
    event = {"summary": "Team meeting",
             "start": {"dateTime": "2026-10-05T10:00:00+05:30"},
             "end": {"dateTime": "2026-10-05T11:00:00+05:30"}}
    line = gcal.describe_event(event)
    assert line.endswith(": Team meeting") and " - " in line


def test_describe_all_day_and_untitled_events():
    assert gcal.describe_event({"summary": "Diwali", "start": {"date": "2026-11-08"}, "end": {"date": "2026-11-09"}}) \
        == "Sun 08 Nov (all day): Diwali"
    assert gcal.describe_event({"start": {"date": "2026-10-06"}, "end": {"date": "2026-10-07"}}) \
        == "Tue 06 Oct (all day): (no title)"


# --- Gmail parsing -----------------------------------------------------------

def test_find_plain_text_in_nested_parts():
    payload = {"mimeType": "multipart/mixed", "parts": [
        {"mimeType": "multipart/alternative", "parts": [
            {"mimeType": "text/plain", "body": {"data": b64("Hello there")}},
            {"mimeType": "text/html", "body": {"data": b64("<p>Hello</p>")}},
        ]},
    ]}
    assert gmail.find_plain_text(payload) == "Hello there"


def test_find_plain_text_returns_none_for_html_only():
    assert gmail.find_plain_text({"mimeType": "text/html", "body": {"data": b64("<p>Hi</p>")}}) is None


def test_get_header_ignores_case():
    message = {"payload": {"headers": [{"name": "Subject", "value": "Interview"}]}}
    assert gmail.get_header(message, "subject") == "Interview"
    assert gmail.get_header(message, "From") == ""


class Call:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class FakeGmail:
    """Just enough of the Gmail API for read_email and create_draft."""

    def __init__(self, message=None):
        self.message = message
        self.drafts_saved = []

    def users(self):
        return self

    def messages(self):
        return self

    def drafts(self):
        return self

    def get(self, userId, id, format, metadataHeaders=None):
        return Call(self.message)

    def create(self, userId, body):
        self.drafts_saved.append(body)
        return Call({"id": "draft1"})


def test_read_email_is_labelled_untrusted_and_cut_short(monkeypatch):
    message = {"snippet": "News", "payload": {
        "mimeType": "text/plain",
        "headers": [{"name": "From", "value": "news@x.com"}],
        "body": {"data": b64("word " * 2000)},
    }}
    monkeypatch.setattr(gmail, "get_service", lambda: FakeGmail(message))
    text = gmail.read_email("id1")
    assert text.startswith(gmail.UNTRUSTED_NOTE)
    assert text.endswith("[... email cut short ...]")


def test_create_draft_builds_a_valid_email(monkeypatch):
    fake = FakeGmail()
    monkeypatch.setattr(gmail, "get_service", lambda: fake)
    result = gmail.create_draft("prof@uni.edu", "Late submission", "Sorry, running late.")
    assert "not sent" in result
    raw = fake.drafts_saved[0]["message"]["raw"]
    sent = email.message_from_bytes(base64.urlsafe_b64decode(raw))
    assert sent["To"] == "prof@uni.edu"
    assert sent["Subject"] == "Late submission"
    assert sent.get_payload().strip() == "Sorry, running late."
