"""Google Calendar integration for watcher.

Fetches upcoming events and returns a snapshot for diffing.

Expected snapshot shape:
{
  "status": "ok",
  "events": [
    {"id": "evt_123", "title": "Meeting", "start": "...", "end": "...", "attendees": []}
  ]
}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def fetch_state(config: dict) -> dict:
    """Fetch upcoming calendar events as a snapshot."""
    # Always use credentials from settings (never from untrusted task config)
    client_id = settings.google_client_id
    client_secret = settings.google_client_secret
    refresh_token = settings.google_refresh_token

    if not client_id or not client_secret or not refresh_token:
        return {"status": "not_configured", "events": []}

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=TOKEN_URI,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        service = build("calendar", "v3", credentials=creds)

        calendar_id = config.get("calendar_id") or settings.google_calendar_id or "primary"
        time_min = datetime.now(timezone.utc).isoformat()

        result = service.events().list(
            calendarId=calendar_id,
            maxResults=50,
            timeMin=time_min,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            attendees = [
                a.get("email", "") for a in item.get("attendees", [])
            ]
            events.append({
                "id": item.get("id", ""),
                "title": item.get("summary", ""),
                "start": start.get("dateTime") or start.get("date", ""),
                "end": end.get("dateTime") or end.get("date", ""),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
                "attendees": attendees,
            })

        return {"status": "ok", "events": events}

    except Exception as exc:
        log.error("Google Calendar fetch failed: %s", exc)
        return {"status": "error", "events": [], "error": str(exc)}
