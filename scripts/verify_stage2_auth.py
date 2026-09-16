import argparse
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp"


async def call_whoami(token: str | None) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with streamablehttp_client(SERVER_URL, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("whoami", {})
                print("SUCCESS:", result.content[0].text)
    except Exception as exc:
        if token is None:
            print(f"REJECTED as expected (no token supplied): {exc}")
        else:
            print(f"UNEXPECTED FAILURE: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Switchboard's OAuth resource-server layer.")
    parser.add_argument("--token", default=None, help="Auth0 access token to test with")
    args = parser.parse_args()
    asyncio.run(call_whoami(args.token))
