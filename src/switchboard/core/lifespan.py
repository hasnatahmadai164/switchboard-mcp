"""
Server-wide startup/shutdown: two asyncpg connection pools (one per
Postgres role, see db/init/03-create-roles.sh), one Pinecone client, and
one Google Credentials object (see core/google_auth.py).

A "lifespan" runs once for the life of the whole process, not once per
request -- exactly right for a connection pool or API client, which is
expensive to open and meant to be shared across every tool call, rather
than opened and closed on every single request.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import asyncpg
from google.oauth2.credentials import Credentials
from mcp.server.fastmcp import FastMCP
from pinecone import AsyncPinecone

from switchboard.core.config import settings
from switchboard.core.google_auth import build_google_credentials


@dataclass
class AppContext:
    readonly_pool: asyncpg.Pool
    write_pool: asyncpg.Pool
    pinecone_client: AsyncPinecone
    google_credentials: Credentials


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:

    readonly_pool = await asyncpg.create_pool(settings.postgres_readonly_dsn, min_size=1, max_size=5)
    write_pool = await asyncpg.create_pool(settings.postgres_write_dsn, min_size=1, max_size=5)
  
    pinecone_client = AsyncPinecone(api_key=settings.pinecone_api_key)
   
    google_credentials = build_google_credentials()
    try:
        yield AppContext(
            readonly_pool=readonly_pool,
            write_pool=write_pool,
            pinecone_client=pinecone_client,
            google_credentials=google_credentials,
        )
    finally:
        await pinecone_client.close()
        await write_pool.close()
        await readonly_pool.close()
