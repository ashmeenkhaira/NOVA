"""One Google sign-in shared by every Google service the bot uses.

gcal.py and gmail.py both get their credentials from here, so there is one
token.json and you approve all permissions together.

Run this file directly to sign in (or re-sign-in after adding a scope):
    python google_auth.py
"""
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config

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

# Saved after the first browser sign-in, so you are not asked every time.
# It is a login pass for your Google account - it is in .gitignore.
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_credentials():
    """Return valid Google credentials, signing in through the browser if needed."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # A token approved for fewer permissions cannot do everything we now need.
    # Throw it away so the sign-in below asks again.
    if creds and not creds.has_scopes(SCOPES):
        creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            # The token lasts about an hour; refreshing gets a new one silently.
            creds.refresh(Request())
        except RefreshError:
            # Google refused - e.g. the 7-day limit for apps in Testing mode.
            creds = None

    if not creds or not creds.valid:
        # On a server there is no browser, so signing in would wait forever.
        # The service file sets NOVA_HEADLESS=1; fail with instructions instead.
        if os.environ.get("NOVA_HEADLESS"):
            raise RuntimeError(
                "Google sign-in needed (it expires every 7 days in Testing mode). "
                "On your laptop run: python google_auth.py - then copy token.json to the server."
            )
        # Opens your browser at Google's sign-in page. After you approve,
        # Google sends the token back to a temporary local web server.
        flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Signed in. Permissions granted:")
    for scope in creds.scopes:
        print("  ", scope)
