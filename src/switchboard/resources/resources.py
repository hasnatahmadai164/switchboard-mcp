"""
MCP Resources: read-only, ambient context a client can load without
invoking a tool -- the MCP primitive most tutorial servers skip
entirely (per the project README).

Unlike tools, resources take no caller-supplied arguments here (both
URIs below are static, not templated) -- they're meant as always-
available background context, not parameterized queries. A caller
wanting a specific custom range still reaches for the list_events tool;
this resource is just "what's coming up," no arguments needed.

Neither function takes a `ctx: Context` parameter -- a confirmed
upstream SDK bug rejects that for a static (non-templated) URI (see
core/lifespan.py's get_app_context() docstring for the full story).
Both read the shared AppContext from there instead.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from switchboard.core.lifespan import get_app_context
from switchboard.tools.calendar_tools import _list_events


async def db_schema() -> str:
    """Live schema of every table in the public Postgres schema: each
    table's columns, with their data types and nullability. Reflects the
    database as it actually is right now, not a static snapshot."""
    pool = get_app_context().readonly_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
    schema: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        schema.setdefault(row["table_name"], []).append(
            {"column": row["column_name"], "type": row["data_type"], "nullable": row["is_nullable"]}
        )
    return json.dumps(schema, indent=2)


async def upcoming_calendar_events() -> str:
    """Events on the demo account's primary calendar over the next 7
    days. Reuses the same Calendar API call the list_events tool uses --
    one real implementation, not a duplicate."""
    credentials = get_app_context().google_credentials
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=7)).isoformat()
    result = await asyncio.to_thread(_list_events, credentials, "primary", time_min, time_max, None)
    return json.dumps(result["events"], indent=2)
