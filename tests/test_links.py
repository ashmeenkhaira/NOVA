"""links.py: the one-time state values that tie a Google sign-in to a chat."""
import time

import links
from conftest import FRIEND, OWNER


def test_each_state_is_unique_and_long_enough_to_be_unguessable():
    first = links.create(OWNER)
    second = links.create(OWNER)
    assert first != second
    assert len(first) >= 32


def test_claim_returns_the_chat_that_asked():
    state = links.create(OWNER)
    assert links.claim(state) == OWNER


def test_a_link_works_only_once():
    """Stops a captured callback URL being replayed to re-link an account."""
    state = links.create(OWNER)
    assert links.claim(state) == OWNER
    assert links.claim(state) is None


def test_a_made_up_state_is_refused():
    assert links.claim("not-a-real-state") is None
    assert links.claim("") is None


def test_expired_links_are_refused():
    state = links.create(OWNER)
    links.pending[state]["expires_at"] = time.time() - 1
    assert links.claim(state) is None


def test_cancel_drops_only_that_chats_links():
    mine = links.create(OWNER)
    theirs = links.create(FRIEND)

    links.cancel(OWNER)

    assert links.claim(mine) is None
    assert links.claim(theirs) == FRIEND
