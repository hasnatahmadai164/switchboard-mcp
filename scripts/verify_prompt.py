"""
Manual verification for MCP Prompts -- bypasses Inspector's CLI, which
has a documented issue with how it sends prompts/get arguments, and
calls the server directly via the real MCP Python client instead (the
same approach scripts/verify_stage2_auth.py uses for the auth layer).

Usage (PowerShell):
    python scripts/verify_prompt.py --token <access_token> --prompt draft_follow_up_email --arg recipient_name=Priya --arg topic="the Q3 proposal"

    python scripts/verify_prompt.py --token <access_token> --prompt summarize_week_events
"""

import argparse
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp"


async def get_prompt(token: str, prompt_name: str, arguments: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.get_prompt(prompt_name, arguments)
            for message in result.messages:
                print(f"[{message.role}] {message.content.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch an MCP prompt directly, bypassing Inspector's CLI.")
    parser.add_argument("--token", required=True, help="Auth0 access token")
    parser.add_argument("--prompt", required=True, help="Prompt name, e.g. draft_follow_up_email")
    parser.add_argument("--arg", action="append", default=[], help="key=value, repeat for multiple arguments")
    args = parser.parse_args()

    arguments = dict(a.split("=", 1) for a in args.arg)
    asyncio.run(get_prompt(args.token, args.prompt, arguments))
