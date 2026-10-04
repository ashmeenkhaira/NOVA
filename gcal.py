"""Access to your Google Calendar: read events, and create them (after approval).

Not named calendar.py on purpose: that would hide Python's built-in
calendar module from every file that imports it.

Run this file directly to see tomorrow's events (signs in if needed):
    python gcal.py
"""
from datetime import date, datetime, timedelta

from googleapiclient.discovery import build

import google_auth


def get_service():
    """Return a connection to the Calendar API. Sign-in lives in google_auth.py."""
    return build("calendar", "v3", credentials=google_auth.get_credentials())


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
