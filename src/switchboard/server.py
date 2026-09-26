"""
Switchboard MCP Server -- entry point.

Stage 9 adds the server's first MCP Prompts -- reusable message
templates a client can request by name, the third primitive (alongside
Resources) most tutorial servers skip entirely (see prompts/prompts.py).
Every tool below is registered here, in one place, with explicit
annotations (readOnlyHint/destructiveHint/idempotentHint/openWorldHint)
-- the MCP metadata that lets a calling agent (or a human approving its
actions) reason about risk before invoking a tool, without having to
read the tool's implementation. Per the project README, these are all
things most tutorial MCP servers skip.
"""

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from switchboard.auth.scopes import MCP_INVOKE
from switchboard.auth.token_validation import Auth0TokenVerifier
from switchboard.core.config import settings
from switchboard.core.lifespan import app_lifespan
from switchboard.prompts.prompts import draft_follow_up_email, summarize_week_events
from switchboard.resources.resources import db_schema, upcoming_calendar_events
from switchboard.tools.calendar_tools import (
    check_availability,
    create_event,
    list_events,
)
from switchboard.tools.gmail_tools import (
    create_draft,
    read_email,
    search_emails,
    send_email,
)
from switchboard.tools.pinecone_tools import (
    delete_vectors,
    list_indexes as pinecone_list_indexes,
    semantic_search,
    upsert_documents,
)
from switchboard.tools.postgres_tools import (
    describe_table,
    execute_write,
    list_tables,
    query_database,
)
from switchboard.tools.sheets_tools import (
    append_row,
    list_sheets,
    read_range,
    update_range,
)

# host is passed to the constructor (not just run()) on purpose: when this
# runs behind Docker's network and binds 0.0.0.0, the SDK's DNS-rebinding
# protection needs to know the real bind host up front, or it assumes
# localhost and can reject legitimate requests. Cheap to get right now,
# annoying to debug later.
mcp = FastMCP(
    name="switchboard",
    host=settings.switchboard_host,
    port=settings.switchboard_port,
    # token_verifier and auth always travel together -- the SDK raises at
    # startup if only one is given, rather than silently running
    # unauthenticated. Wiring these in is also what makes the SDK expose
    # the RFC 9728 "protected resource metadata" endpoint and the
    # WWW-Authenticate challenge header automatically -- we don't write
    # any of that plumbing ourselves.
    token_verifier=Auth0TokenVerifier(),
    auth=AuthSettings(
        issuer_url=settings.issuer_url,
        resource_server_url=settings.mcp_resource_server_url,
        required_scopes=[MCP_INVOKE],
    ),
    lifespan=app_lifespan,
)


@mcp.tool()
def ping() -> str:
    """Health-check tool. Confirms the server is reachable and the
    Streamable HTTP transport is wired up correctly."""
    return "pong"


@mcp.tool()
def whoami() -> str:
    """Returns the identity of the currently authenticated caller.
    Exists purely to prove the OAuth layer works end to end: if this
    returns a client_id, the bearer token was already validated and
    scope-checked by the auth middleware before this function ever ran."""
    access_token = get_access_token()
    if access_token is None:
        raise ValueError("No authenticated caller found")
    return f"Authenticated as: {access_token.client_id} (scopes: {', '.join(access_token.scopes)})"




READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

DESTRUCTIVE_NONIDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)

DESTRUCTIVE_IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)

DATA_MODIFYING_IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)

DATA_MODIFYING_NONIDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

mcp.tool(annotations=READ_ONLY)(query_database)
mcp.tool(annotations=READ_ONLY)(list_tables)
mcp.tool(annotations=READ_ONLY)(describe_table)
mcp.tool(annotations=DESTRUCTIVE_NONIDEMPOTENT)(execute_write)

mcp.tool(annotations=READ_ONLY)(pinecone_list_indexes)
mcp.tool(annotations=READ_ONLY)(semantic_search)
mcp.tool(annotations=DATA_MODIFYING_IDEMPOTENT)(upsert_documents)
mcp.tool(annotations=DESTRUCTIVE_IDEMPOTENT)(delete_vectors)

mcp.tool(annotations=READ_ONLY)(read_range)
mcp.tool(annotations=READ_ONLY)(list_sheets)
mcp.tool(annotations=DATA_MODIFYING_NONIDEMPOTENT)(append_row)
mcp.tool(annotations=DATA_MODIFYING_IDEMPOTENT)(update_range)

mcp.tool(annotations=READ_ONLY)(search_emails)
mcp.tool(annotations=READ_ONLY)(read_email)
mcp.tool(annotations=DATA_MODIFYING_NONIDEMPOTENT)(create_draft)
mcp.tool(annotations=DESTRUCTIVE_NONIDEMPOTENT)(send_email)

mcp.tool(annotations=READ_ONLY)(list_events)
mcp.tool(annotations=READ_ONLY)(check_availability)
mcp.tool(annotations=DATA_MODIFYING_NONIDEMPOTENT)(create_event)


mcp.resource("switchboard://postgres/schema", mime_type="application/json")(db_schema)
mcp.resource("switchboard://calendar/upcoming", mime_type="application/json")(upcoming_calendar_events)


mcp.prompt()(draft_follow_up_email)
mcp.prompt()(summarize_week_events)


if __name__ == "__main__":
    
    mcp.run(transport="streamable-http")
