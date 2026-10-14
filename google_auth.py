"""Google sign-in, one account per chat.

Tokens live in the database (tokens.py), keyed by chat_id, so each person can
connect their own Google account. gcal.py and gmail.py ask here for the
credentials belonging to whoever is asking.

Sign in on this machine (opens a browser):
    python google_auth.py              # connects the owner's chat
    python google_auth.py 5551234      # connects someone else's chat id
"""
import json
import os
import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config
import tokens

# Every permission the bot needs, in one place:
#   calendar.events - see, create, edit and delete events (writes go through approvals.py)
#   gmail.readonly  - read emails and labels; cannot send, delete or change anything
#   gmail.compose   - create drafts. Google's scope also allows sending, but this
#                     code never sends: there is no send function or send tool.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

# The old single-user token file. Still read once, to carry an existing
# sign-in into the database; new tokens are never written here.
LEGACY_TOKEN_FILE = Path(__file__).parent / "token.json"


class NotConnected(Exception):
    """This chat has no usable Google account - it needs to connect one."""


def _import_legacy_token(chat_id):
    """One-time: carry the old token.json into the database for the owner."""
    if chat_id != config.MY_CHAT_ID or not LEGACY_TOKEN_FILE.exists():
        return
    if tokens.has_token(chat_id):
        return
    tokens.save_token(chat_id, LEGACY_TOKEN_FILE.read_text())
    print(f"[info] imported token.json into the database for chat {chat_id}")


def get_credentials(chat_id):
    """Valid Google credentials for this chat.

    Raises NotConnected if this chat has no account linked, if the saved token
    does not cover the permissions we need, or if Google refuses to renew it
    (e.g. the 7-day limit for apps in Testing mode). Callers do not need to
    handle that themselves - run_tool turns it into a friendly message.
    """
    _import_legacy_token(chat_id)

    raw = tokens.get_token(chat_id)
    if raw is None:
        raise NotConnected(f"chat {chat_id} has no Google account linked")

    # Load WITHOUT passing SCOPES. Passing them overwrites the credential's
    # scope list with what we are asking for, which would make the check below
    # always pass - it has to read the scopes Google actually granted.
    creds = Credentials.from_authorized_user_info(json.loads(raw))

    # A token approved for fewer permissions cannot do everything we need.
    if not creds.has_scopes(SCOPES):
        tokens.delete_token(chat_id)
        raise NotConnected("the linked account is missing some permissions")

    if creds.expired and creds.refresh_token:
        try:
            # The token lasts about an hour; refreshing gets a new one silently.
            creds.refresh(Request())
            tokens.save_token(chat_id, creds.to_json())
        except RefreshError:
            # Google refused - the sign-in has to be done again.
            tokens.delete_token(chat_id)
            raise NotConnected("the Google sign-in expired")

    if not creds.valid:
        raise NotConnected("the saved Google token is not usable")
    return creds


def sign_in(chat_id):
    """Sign in through a browser ON THIS MACHINE and save the token for chat_id.

    Only works where a browser is available, so today it is the owner linking
    an account from their own laptop. A hosted sign-in flow would let other
    people connect from their own device.
    """
    if os.environ.get("NOVA_HEADLESS"):
        raise RuntimeError(
            "No browser on this machine. Run 'python google_auth.py' on your laptop instead."
        )

    # Opens your browser at Google's sign-in page. After you approve, Google
    # sends the token back to a temporary local web server.
    flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    tokens.save_token(chat_id, creds.to_json())
    return creds


if __name__ == "__main__":
    # Optional argument: whose chat to link. Defaults to the owner.
    chat_id = int(sys.argv[1]) if len(sys.argv) > 1 else config.MY_CHAT_ID

    creds = sign_in(chat_id)
    print(f"Signed in and saved for chat {chat_id}. Permissions granted:")
    for scope in creds.scopes:
        print("  ", scope)
