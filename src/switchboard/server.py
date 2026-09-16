"""
Switchboard MCP Server -- entry point.

Stage 2 adds OAuth 2.1 resource-server auth: every request now needs a
valid bearer token, issued by Auth0, carrying the `mcp:invoke` scope.
This server never issues tokens or handles login itself -- it only ever
validates tokens someone else (Auth0) already issued. See the two-auth-
layers split in the project README for why that split exists.
"""

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from switchboard.auth.scopes import MCP_INVOKE
from switchboard.auth.token_validation import Auth0TokenVerifier
from switchboard.core.config import settings

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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
