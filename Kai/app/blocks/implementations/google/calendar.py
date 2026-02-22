"""Google Calendar integration blocks — list, create, update, delete events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.blocks.executor import register_implementation
from app.blocks.implementations.google.client import get_calendar_service
from app.config import settings

logger = logging.getLogger("agentflow.blocks.google.calendar")


def _resolve_calendar_id(inputs: dict[str, Any]) -> str:
    return _resolve_calendar_id(inputs)


@register_implementation("calendar_list_events")
async def calendar_list_events(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch upcoming events from a Google Calendar."""
    calendar_id = _resolve_calendar_id(inputs)
    max_results = min(int(inputs.get("max_results", 10)), 250)
    time_min = inputs.get("time_min") or datetime.now(timezone.utc).isoformat()
    time_max = inputs.get("time_max")

    try:
        service = get_calendar_service()
        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "timeMin": time_min,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max:
            kwargs["timeMax"] = time_max

        result = service.events().list(**kwargs).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Google Calendar list error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Google Calendar list failed: {type(e).__name__}") from None

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        events.append({
            "id": item.get("id", ""),
            "summary": item.get("summary", ""),
            "start": start.get("dateTime") or start.get("date", ""),
            "end": end.get("dateTime") or end.get("date", ""),
            "location": item.get("location", ""),
            "description": item.get("description", ""),
        })

    return {
        "events": events,
        "event_count": len(events),
    }


@register_implementation("calendar_create_event")
async def calendar_create_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a new event on Google Calendar."""
    summary = inputs["summary"]
    start_time = inputs["start_time"]
    end_time = inputs["end_time"]
    description = inputs.get("description", "")
    location = inputs.get("location", "")
    attendees = inputs.get("attendees", [])
    calendar_id = _resolve_calendar_id(inputs)

    event_body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]

    try:
        service = get_calendar_service()
        event = service.events().insert(
            calendarId=calendar_id, body=event_body
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Google Calendar create error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Google Calendar create failed: {type(e).__name__}") from None

    return {
        "event_id": event.get("id", ""),
        "html_link": event.get("htmlLink", ""),
        "status": event.get("status", "confirmed"),
    }


@register_implementation("calendar_update_event")
async def calendar_update_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Update an existing Google Calendar event."""
    event_id = inputs["event_id"]
    calendar_id = _resolve_calendar_id(inputs)

    try:
        service = get_calendar_service()
        existing = service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()

        if "summary" in inputs:
            existing["summary"] = inputs["summary"]
        if "start_time" in inputs:
            existing["start"] = {"dateTime": inputs["start_time"], "timeZone": "UTC"}
        if "end_time" in inputs:
            existing["end"] = {"dateTime": inputs["end_time"], "timeZone": "UTC"}
        if "description" in inputs:
            existing["description"] = inputs["description"]
        if "location" in inputs:
            existing["location"] = inputs["location"]

        updated = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=existing
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Google Calendar update error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Google Calendar update failed: {type(e).__name__}") from None

    return {
        "event_id": updated.get("id", ""),
        "html_link": updated.get("htmlLink", ""),
        "status": updated.get("status", "confirmed"),
        "updated": updated.get("updated", ""),
    }


@register_implementation("calendar_delete_event")
async def calendar_delete_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Delete an event from Google Calendar."""
    event_id = inputs["event_id"]
    calendar_id = _resolve_calendar_id(inputs)

    try:
        service = get_calendar_service()
        service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Google Calendar delete error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Google Calendar delete failed: {type(e).__name__}") from None

    return {
        "status": "deleted",
        "deleted_event_id": event_id,
    }
