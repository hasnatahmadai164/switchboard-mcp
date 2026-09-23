"""
Google Calendar tools: list events, check availability, and create
events -- using the demo account's Google credentials (see
core/google_auth.py). The Calendar API client is synchronous, so every
call here runs in a worker thread via asyncio.to_thread rather than
blocking the event loop.

_list_events is also reused directly by the "upcoming calendar events"
MCP resource (see resources/resources.py) -- one real implementation of
"list events in a range", not two.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import Context

from switchboard.core.google_auth import build_calendar_service


def _list_events(
    credentials, calendar_id: str, time_min: str, time_max: str, page_token: str | None
) -> dict[str, Any]:
    service = build_calendar_service(credentials)
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        )
        .execute()
    )
    events = [
        {
            "id": event["id"],
            "summary": event.get("summary", ""),
            "start": event.get("start", {}).get("dateTime") or event.get("start", {}).get("date"),
            "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
        }
        for event in result.get("items", [])
    ]
    return {"events": events, "next_page_token": result.get("nextPageToken")}


def _check_availability(credentials, calendar_id: str, time_min: str, time_max: str) -> list[dict[str, str]]:
    service = build_calendar_service(credentials)
    result = (
        service.freebusy()
        .query(body={"timeMin": time_min, "timeMax": time_max, "items": [{"id": calendar_id}]})
        .execute()
    )
    return result["calendars"].get(calendar_id, {}).get("busy", [])


def _create_event(
    credentials,
    calendar_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None,
    attendees: list[str] | None,
) -> dict[str, str]:
    service = build_calendar_service(credentials)
    body: dict[str, Any] = {"summary": summary, "start": {"dateTime": start}, "end": {"dateTime": end}}
    if description:
        body["description"] = description
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    event = service.events().insert(calendarId=calendar_id, body=body).execute()
    return {"id": event["id"], "htmlLink": event.get("htmlLink", "")}


async def list_events(
    calendar_id: str, time_min: str, time_max: str, ctx: Context, page_token: str | None = None
) -> dict[str, Any]:
    """List events on a calendar within a time range, paginated.

    Args:
        calendar_id: Calendar to list, e.g. "primary" for the demo account's main calendar.
        time_min: RFC3339 start of the range, e.g. "2026-09-25T00:00:00Z".
        time_max: RFC3339 end of the range.
        page_token: Pass the previous call's next_page_token to fetch the next page.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_list_events, credentials, calendar_id, time_min, time_max, page_token)


async def check_availability(calendar_id: str, time_min: str, time_max: str, ctx: Context) -> list[dict[str, str]]:
    """Check busy time blocks on a calendar within a range. Higher-level
    than list_events: returns just busy start/end pairs, not full event
    details -- use this to answer "is X free at time Y" without needing
    to inspect every event.

    Args:
        calendar_id: Calendar to check, e.g. "primary".
        time_min: RFC3339 start of the range.
        time_max: RFC3339 end of the range.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_check_availability, credentials, calendar_id, time_min, time_max)


async def create_event(
    calendar_id: str,
    summary: str,
    start: str,
    end: str,
    ctx: Context,
    description: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, str]:
    """Create a calendar event. Data-modifying, not idempotent -- calling
    this twice creates two separate events.

    Args:
        calendar_id: Calendar to create the event on, e.g. "primary".
        summary: Event title.
        start: RFC3339 start datetime, e.g. "2026-09-25T10:00:00-07:00".
        end: RFC3339 end datetime.
        description: Optional event description.
        attendees: Optional list of attendee email addresses.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(
        _create_event, credentials, calendar_id, summary, start, end, description, attendees
    )
