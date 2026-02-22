"""Google Calendar integration blocks."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.blocks.executor import register_implementation
from app.blocks.implementations.google.client import get_calendar_service

logger = logging.getLogger("agentflow.blocks.google.calendar")

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _event_time(value: str | None, time_zone: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    if _DATE_ONLY_RE.fullmatch(value):
        return {"date": value}
    payload: dict[str, Any] = {"dateTime": value}
    if time_zone:
        payload["timeZone"] = time_zone
    return payload


def _normalize_attendees(attendees: Any) -> list[dict[str, str]]:
    if not attendees:
        return []
    if isinstance(attendees, list):
        normalized = []
        for entry in attendees:
            if isinstance(entry, dict):
                email = entry.get("email")
                normalized.append({"email": str(email)} if email else entry)
            else:
                normalized.append({"email": str(entry)})
        return normalized
    return [{"email": str(attendees)}]


@register_implementation("google_calendar_list_calendars")
async def calendar_list_calendars(inputs: dict[str, Any]) -> dict[str, Any]:
    """List calendars available to the user."""
    try:
        service = get_calendar_service()
        params = _clean_params({
            "minAccessRole": inputs.get("min_access_role"),
            "showHidden": inputs.get("show_hidden"),
            "showDeleted": inputs.get("show_deleted"),
            "maxResults": inputs.get("max_results"),
            "pageToken": inputs.get("page_token"),
        })
        response = service.calendarList().list(**params).execute()
    except Exception as e:
        logger.error("Calendar list error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar list failed: {type(e).__name__}") from None

    return {
        "calendars": response.get("items", []),
        "next_page_token": response.get("nextPageToken", ""),
    }


@register_implementation("google_calendar_get_calendar")
async def calendar_get_calendar(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a calendar by ID."""
    calendar_id = inputs["calendar_id"]
    try:
        service = get_calendar_service()
        calendar = service.calendars().get(calendarId=calendar_id).execute()
    except Exception as e:
        logger.error("Calendar get error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar get failed: {type(e).__name__}") from None

    return {"calendar": calendar}


@register_implementation("google_calendar_create_calendar")
async def calendar_create_calendar(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a new calendar."""
    body = _clean_params({
        "summary": inputs.get("summary"),
        "description": inputs.get("description"),
        "timeZone": inputs.get("time_zone"),
    })
    try:
        service = get_calendar_service()
        calendar = service.calendars().insert(body=body).execute()
    except Exception as e:
        logger.error("Calendar create error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar create failed: {type(e).__name__}") from None

    return {"calendar_id": calendar.get("id", ""), "summary": calendar.get("summary", "")}


@register_implementation("google_calendar_delete_calendar")
async def calendar_delete_calendar(inputs: dict[str, Any]) -> dict[str, Any]:
    """Delete a calendar."""
    calendar_id = inputs["calendar_id"]
    try:
        service = get_calendar_service()
        service.calendars().delete(calendarId=calendar_id).execute()
    except Exception as e:
        logger.error("Calendar delete error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar delete failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_calendar_list_events")
async def calendar_list_events(inputs: dict[str, Any]) -> dict[str, Any]:
    """List calendar events."""
    calendar_id = inputs.get("calendar_id") or "primary"
    try:
        service = get_calendar_service()
        params = _clean_params({
            "timeMin": inputs.get("time_min"),
            "timeMax": inputs.get("time_max"),
            "q": inputs.get("query"),
            "maxResults": inputs.get("max_results"),
            "pageToken": inputs.get("page_token"),
            "singleEvents": inputs.get("single_events"),
            "orderBy": inputs.get("order_by"),
        })
        response = service.events().list(calendarId=calendar_id, **params).execute()
    except Exception as e:
        logger.error("Calendar list events error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar list events failed: {type(e).__name__}") from None

    return {
        "events": response.get("items", []),
        "next_page_token": response.get("nextPageToken", ""),
    }


@register_implementation("google_calendar_get_event")
async def calendar_get_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a calendar event by ID."""
    calendar_id = inputs.get("calendar_id") or "primary"
    event_id = inputs["event_id"]
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as e:
        logger.error("Calendar get event error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar get event failed: {type(e).__name__}") from None

    return {"event": event}


@register_implementation("google_calendar_create_event")
async def calendar_create_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a calendar event."""
    calendar_id = inputs.get("calendar_id") or "primary"
    time_zone = inputs.get("time_zone")
    event_body: dict[str, Any] = _clean_params({
        "summary": inputs.get("summary"),
        "description": inputs.get("description"),
        "location": inputs.get("location"),
    })

    start = _event_time(inputs.get("start"), time_zone)
    end = _event_time(inputs.get("end"), time_zone)
    if start:
        event_body["start"] = start
    if end:
        event_body["end"] = end

    attendees = _normalize_attendees(inputs.get("attendees"))
    if attendees:
        event_body["attendees"] = attendees

    try:
        service = get_calendar_service()
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    except Exception as e:
        logger.error("Calendar create event error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar create event failed: {type(e).__name__}") from None

    return {"event_id": event.get("id", ""), "html_link": event.get("htmlLink", "")}


@register_implementation("google_calendar_update_event")
async def calendar_update_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Update a calendar event."""
    calendar_id = inputs.get("calendar_id") or "primary"
    event_id = inputs["event_id"]
    time_zone = inputs.get("time_zone")

    event_body: dict[str, Any] = _clean_params({
        "summary": inputs.get("summary"),
        "description": inputs.get("description"),
        "location": inputs.get("location"),
    })
    start = _event_time(inputs.get("start"), time_zone)
    end = _event_time(inputs.get("end"), time_zone)
    if start:
        event_body["start"] = start
    if end:
        event_body["end"] = end
    attendees = _normalize_attendees(inputs.get("attendees"))
    if attendees:
        event_body["attendees"] = attendees

    try:
        service = get_calendar_service()
        event = (
            service.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=event_body)
            .execute()
        )
    except Exception as e:
        logger.error("Calendar update event error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar update event failed: {type(e).__name__}") from None

    return {"event": event}


@register_implementation("google_calendar_delete_event")
async def calendar_delete_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Delete a calendar event."""
    calendar_id = inputs.get("calendar_id") or "primary"
    event_id = inputs["event_id"]
    try:
        service = get_calendar_service()
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as e:
        logger.error("Calendar delete event error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar delete event failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_calendar_quick_add_event")
async def calendar_quick_add_event(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create an event from free-form text."""
    calendar_id = inputs.get("calendar_id") or "primary"
    text = inputs["text"]
    try:
        service = get_calendar_service()
        event = service.events().quickAdd(calendarId=calendar_id, text=text).execute()
    except Exception as e:
        logger.error("Calendar quick add error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar quick add failed: {type(e).__name__}") from None

    return {"event_id": event.get("id", "")}


@register_implementation("google_calendar_freebusy_query")
async def calendar_freebusy_query(inputs: dict[str, Any]) -> dict[str, Any]:
    """Query free/busy availability."""
    time_min = inputs["time_min"]
    time_max = inputs["time_max"]
    calendar_ids = inputs.get("calendar_ids") or ["primary"]
    items = [{"id": str(entry)} for entry in calendar_ids]
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": inputs.get("time_zone"),
        "items": items,
    }
    try:
        service = get_calendar_service()
        response = service.freebusy().query(body=body).execute()
    except Exception as e:
        logger.error("Calendar freebusy query error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Calendar freebusy query failed: {type(e).__name__}") from None

    return {"calendars": response.get("calendars", {})}
