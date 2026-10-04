"""Access to your Google Calendar: read events, and create them (after approval).

Not named calendar.py on purpose: that would hide Python's built-in
calendar module from every file that imports it.

Run this file directly to sign in and see tomorrow's events:
    python gcal.py
"""
from datetime import date, datetime, timedelta
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

# calendar.events: see, create, edit and delete events - but not delete whole
# calendars or change sharing. Writes only happen through approvals.py.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Saved after the first browser sign-in, so you are not asked every time.
# It is a login pass for your calendar - it is in .gitignore.
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_service():
    """Return a connection to the Calendar API, signing in if needed."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # A token approved for fewer permissions (e.g. the old read-only one) cannot
    # do what we now need. Throw it away so the sign-in below asks again.
    if creds and not creds.has_scopes(SCOPES):
        creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            # The token lasts about an hour; refreshing gets a new one silently.
            creds.refresh(Request())
        except RefreshError:
            # Google refused - e.g. the 7-day limit for apps in Testing mode.
            # Throw the old token away and sign in again below.
            creds = None

    if not creds or not creds.valid:
        # Opens your browser at Google's sign-in page. After you approve,
        # Google sends the token back to a temporary local web server.
        flow = InstalledAppFlow.from_client_secrets_file(str(config.GOOGLE_CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def describe_event(event):
    """Turn one event from Google into a line like 'Mon 05 Oct, 10:00 AM - 11:00 AM: Title'."""
    title = event.get("summary", "(no title)")
    start = event["start"]
    end = event["end"]

    # All-day events have a "date"; timed events have a "dateTime".
    if "date" in start:
        day = date.fromisoformat(start["date"])
        return f"{day:%a %d %b} (all day): {title}"

    starts = datetime.fromisoformat(start["dateTime"]).astimezone()
    ends = datetime.fromisoformat(end["dateTime"]).astimezone()
    return f"{starts:%a %d %b, %I:%M %p} - {ends:%I:%M %p}: {title}"


def get_events(start_date, end_date):
    """Return events from start_date to end_date (both 'YYYY-MM-DD', inclusive) as text."""
    # Google needs exact moments with a timezone. .astimezone() uses your
    # laptop's timezone, so "2026-10-05" means midnight in your local time.
    time_min = datetime.fromisoformat(start_date).astimezone()
    time_max = (datetime.fromisoformat(end_date) + timedelta(days=1)).astimezone()

    result = get_service().events().list(
        calendarId="primary",            # your main calendar
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,               # expand repeating events into single ones
        orderBy="startTime",
        maxResults=50,
    ).execute()

    events = result.get("items", [])
    if not events:
        return f"No events between {start_date} and {end_date}."

    text = ""
    for event in events:
        text += describe_event(event) + "\n"
    return text


def create_event(title, start, end):
    """Create an event. start and end are local times like '2026-10-06T07:00'.

    Never call this directly from a tool - it must go through approvals.py.
    """
    event = {
        "summary": title,
        "start": {"dateTime": datetime.fromisoformat(start).astimezone().isoformat()},
        "end": {"dateTime": datetime.fromisoformat(end).astimezone().isoformat()},
    }
    created = get_service().events().insert(calendarId="primary", body=event).execute()
    return f"added to your calendar: {describe_event(created)}"


if __name__ == "__main__":
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    print(f"Events for tomorrow ({tomorrow}):")
    print(get_events(tomorrow, tomorrow))
