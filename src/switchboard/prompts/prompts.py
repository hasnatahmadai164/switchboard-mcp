"""
MCP Prompts: reusable message templates a client can request by name,
optionally parameterized -- the third MCP primitive most tutorial
servers skip, alongside Resources (see resources/resources.py).

Both return plain strings, wrapped as a single user message
automatically -- the simplest, most universally-supported prompt
return type, and all either of these actually needs.

summarize_week_events is async and reuses the same Calendar API call
the list_events tool and the upcoming_calendar_events resource both
use -- one real implementation of "list events in a range," not three.
Like resources.py, it reads shared state via get_app_context() rather
than a `ctx: Context` parameter, for consistency with that module.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from switchboard.core.lifespan import get_app_context
from switchboard.tools.calendar_tools import _list_events


def draft_follow_up_email(recipient_name: str, topic: str) -> str:
    """Generates a request to draft a polite, concise follow-up email."""
    return (
        f"Draft a brief, professional follow-up email to {recipient_name} "
        f"regarding {topic}. Keep it concise, make clear this is a "
        f"follow-up rather than a first contact, and end with a clear, "
        f"low-friction call to action."
    )


async def summarize_week_events() -> str:
    """Generates a request to summarize the demo account's calendar for
    the next 7 days -- with the actual events already fetched and
    included, not just a generic instruction with nothing to work from."""
    credentials = get_app_context().google_credentials
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=7)).isoformat()
    result = await asyncio.to_thread(_list_events, credentials, "primary", time_min, time_max, None)

    if not result["events"]:
        events_text = "(No events found in the next 7 days.)"
    else:
        events_text = "\n".join(
            f"- {event['summary']} ({event['start']} to {event['end']})" for event in result["events"]
        )

    return (
        "Summarize the following calendar events for the upcoming week into "
        "a short, readable digest grouped by day. Call out anything that "
        "looks like a scheduling conflict or a particularly busy day.\n\n"
        f"{events_text}"
    )
