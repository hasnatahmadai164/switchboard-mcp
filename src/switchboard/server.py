from mcp.server.fastmcp import FastMCP

@mcp.tool()
def ping() -> str:
    """Health-check tool. Confirms the server is reachable and the
    Streamable HTTP transport is wired up correctly."""
    return "pong"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
