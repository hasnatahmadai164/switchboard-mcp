"""
Postgres tools: read-only queries, schema discovery, and a clearly
separate destructive write path.

Every query goes through the driver's native parameter binding
($1, $2, ...) -- this file never builds SQL by string-formatting a
caller-supplied value into a query. Three independent layers protect the
data, on purpose: parameterized queries (this file), statement-shape
checks (sql_guard), and least-privilege database roles (db/init/) --
see the project's security posture notes for why all three exist rather
than just one.

These functions are plain, undecorated async functions on purpose --
server.py registers them as tools and attaches annotations there, so this
module stays focused on the Postgres logic itself, not MCP wiring.
"""

from typing import Any

from mcp.server.fastmcp import Context

from switchboard.security.sql_guard import assert_read_only, assert_write_statement


async def query_database(sql: str, ctx: Context, params: list[Any] | None = None) -> list[dict[str, Any]]:
    """Run a read-only, parameterized SQL query against the demo database.

    Args:
        sql: A single SELECT statement. Use $1, $2, ... placeholders for
             any values -- never interpolate values directly into `sql`.
        params: Positional values for the placeholders, in order.
    """
    assert_read_only(sql)
    pool = ctx.request_context.lifespan_context.readonly_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params or []))
    return [dict(row) for row in rows]


async def list_tables(ctx: Context) -> list[str]:
    """List all tables in the public schema."""
    pool = ctx.request_context.lifespan_context.readonly_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
    return [row["table_name"] for row in rows]


async def describe_table(table_name: str, ctx: Context) -> list[dict[str, Any]]:
    """Describe a table's columns: name, data type, and nullability.

    Args:
        table_name: Table to describe. Passed as a query parameter, never
                    interpolated into SQL, even though this is schema
                    metadata rather than user data.
    """
    pool = ctx.request_context.lifespan_context.readonly_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
            """,
            table_name,
        )
    if not rows:
        raise ValueError(f"No table named '{table_name}' found in the public schema.")
    return [dict(row) for row in rows]


async def execute_write(sql: str, ctx: Context, params: list[Any] | None = None) -> str:
    """Run a single, parameterized INSERT, UPDATE, or DELETE statement.

    Destructive -- runs under a database role with write access, unlike
    every other tool in this module.

    Args:
        sql: A single INSERT, UPDATE, or DELETE statement. Use $1, $2, ...
             placeholders for any values -- never interpolate values
             directly into `sql`.
        params: Positional values for the placeholders, in order.
    """
    assert_write_statement(sql)
    pool = ctx.request_context.lifespan_context.write_pool
    async with pool.acquire() as conn:
        result = await conn.execute(sql, *(params or []))
    return result
