"""Pending account-link requests.

/connect creates one and gives the user a sign-in link. The link carries a
random "state" value. Google hands that value back when it redirects the user
to our callback, and that is how the callback knows WHICH chat asked.

Why the random value matters: without it, anyone who could reach the callback
could link a Google account to a chat id of their choosing. The state is
unguessable, single-use, and short-lived, so a callback can only ever complete
a link that this bot actually started.

In memory only - a restart just means sending /connect again.
"""
import secrets
import time

# How long a sign-in link stays usable.
LINK_TIMEOUT_SECONDS = 10 * 60

# {state: {"chat_id": ..., "expires_at": ...}}
pending = {}


def create(chat_id):
    """Start a link request for this chat. Returns the state value for the URL."""
    _drop_expired()
    # token_urlsafe uses the operating system's secure random source, so the
    # value cannot be guessed or predicted from earlier ones.
    state = secrets.token_urlsafe(32)
    pending[state] = {"chat_id": chat_id, "expires_at": time.time() + LINK_TIMEOUT_SECONDS}
    return state


def claim(state):
    """Return the chat_id this state belongs to, or None if it is unknown or expired.

    The state is removed on use, so the same callback URL can never be replayed.
    """
    _drop_expired()
    request = pending.pop(state, None)
    return None if request is None else request["chat_id"]


def cancel(chat_id):
    """Drop any link requests this chat has open (e.g. after /disconnect)."""
    for state in [s for s, r in pending.items() if r["chat_id"] == chat_id]:
        del pending[state]


def _drop_expired():
    """Forget link requests nobody completed in time."""
    now = time.time()
    for state in [s for s, r in pending.items() if r["expires_at"] <= now]:
        del pending[state]
