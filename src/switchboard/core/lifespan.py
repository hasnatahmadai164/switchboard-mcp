"""
Server-wide startup/shutdown: two asyncpg connection pools (one per
Postgres role, see db/init/03-create-roles.sh) and one Pinecone client.

A "lifespan" runs once for the life of the whole process, not once per
request -- exactly right for a connection pool or API client, which is
expensive to open and meant to be shared across every tool call, rather
than opened and closed on every single request.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import asyncpg
from mcp.server.fastmcp import FastMCP
from pinecone import AsyncPinecone

from switchboard.core.config import settings


@dataclass
class AppContext:
    readonly_pool: asyncpg.Pool
    write_pool: asyncpg.Pool
    pinecone_client: AsyncPinecone


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    readonly_pool = await asyncpg.create_pool(settings.postgres_readonly_dsn, min_size=1, max_size=5)
    write_pool = await asyncpg.create_pool(settings.postgres_write_dsn, min_size=1, max_size=5)
    pinecone_client = AsyncPinecone(api_key=settings.pinecone_api_key)
    try:
        yield AppContext(readonly_pool=readonly_pool, write_pool=write_pool, pinecone_client=pinecone_client)
    finally:
        await pinecone_client.close()
        await write_pool.close()
        await readonly_pool.close()
