"""
Switchboard MCP Server -- entry point.

Stage 3 adds the first real tool integration: Postgres. Every tool below
is registered here, in one place, with explicit annotations
(readOnlyHint/destructiveHint/idempotentHint/openWorldHint) -- the MCP
metadata that lets a calling agent (or a human approving its actions)
reason about risk before invoking a tool, without having to read the
tool's implementation. Most tutorial MCP servers skip this entirely;
per the project README, it's one of the things this one does properly.
"""

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from switchboard.auth.scopes import MCP_INVOKE
from switchboard.auth.token_validation import Auth0TokenVerifier
from switchboard.core.config import settings
from switchboard.core.lifespan import app_lifespan
from switchboard.tools.postgres_tools import (
    describe_table,
    execute_write,
    list_tables,
    query_database,
)

mcp = FastMCP(
    name="switchboard",
    host=settings.switchboard_host,
    port=settings.switchboard_port,
    
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
DESTRUCTIVE_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)

mcp.tool(annotations=READ_ONLY)(query_database)
mcp.tool(annotations=READ_ONLY)(list_tables)
mcp.tool(annotations=READ_ONLY)(describe_table)
mcp.tool(annotations=DESTRUCTIVE_WRITE)(execute_write)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
