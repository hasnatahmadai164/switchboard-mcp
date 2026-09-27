"""
LangGraph agent client -- proves the Switchboard MCP server works end
to end with a real agent doing a real task, using langchain-mcp-adapters
to pull a subset of the server's tools into a LangGraph agent.

Deliberately uses langgraph.prebuilt.create_react_agent rather than the
newer langchain.agents.create_agent: the latter is the officially
recommended path going forward, but has had a confirmed regression
where it briefly disappeared from langchain.agents entirely (langchain
1.1.0) -- exactly the kind of fast-moving-ecosystem risk this project
avoids elsewhere (see the pinned MCP spec version in the main README).
create_react_agent is the "deprecated" path, but it's the one with a
long, boring, uninterrupted track record of just working, which is what
a demo that has to reliably run needs more than the newest API.

This is a demo/proof client, not a second flagship build (see the
project README) -- it exists to prove the server works end to end for a
real agentic workflow, not to be a polished product itself.

Demo task: check whether the demo Google account's calendar is free at
a given time, draft a follow-up email if so, and log the outcome as a
new row in a Google Sheet -- exercising Calendar, Gmail, and Sheets
tools together in one real agent run.

Usage:
    python client/agent.py
"""

import asyncio
import os

import httpx
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv()


ALLOWED_TOOLS = {"check_availability", "create_draft", "append_row"}


def get_access_token() -> str:
    """Mints a fresh Auth0 access token via the client-credentials
    grant -- the same M2M application used for manual testing
    throughout this project, fetched programmatically here instead of
    pasted by hand."""
    response = httpx.post(
        f"https://{os.environ['AUTH0_DOMAIN']}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["AUTH0_CLIENT_ID"],
            "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
            "audience": os.environ.get("SWITCHBOARD_RESOURCE_URL", "http://localhost:8000"),
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def main() -> None:
    token = get_access_token()
    server_url = os.environ.get("SWITCHBOARD_URL", "http://localhost:8000/mcp")

    client = MultiServerMCPClient(
        {
            "switchboard": {
                "transport": "streamable_http",
                "url": server_url,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        }
    )

    all_tools = await client.get_tools()
    tools = [tool for tool in all_tools if tool.name in ALLOWED_TOOLS]
    found = {tool.name for tool in tools}
    missing = ALLOWED_TOOLS - found
    if missing:
        raise RuntimeError(
            f"Server is missing expected tool(s): {missing}. "
            "Is switchboard actually running (docker compose up)?"
        )


    agent = create_react_agent(
        "openai:gpt-5-mini",
        tools=tools,
        prompt="You are an assistant that manages scheduling and follow-up emails.",
    )

    spreadsheet_id = os.environ["SWITCHBOARD_DEMO_SPREADSHEET_ID"]
    task = (
        "Check whether the 'primary' calendar is free tomorrow between "
        "14:00 and 15:00 UTC. If it's free, draft a follow-up email to "
        "Priya (priya@example.com) about scheduling a call at that "
        f"time. Then append a new row to sheet 'Log' in spreadsheet "
        f"{spreadsheet_id} recording: a timestamp, whether the slot was "
        "free or busy, and whether a draft was created."
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]})

    print("\n=== Agent run complete ===")
    for message in result["messages"]:
        role = getattr(message, "type", getattr(message, "role", "?"))
        content = getattr(message, "content", "")
        if content:
            print(f"[{role}] {content}")


if __name__ == "__main__":
    asyncio.run(main())
