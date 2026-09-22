"""
Google Sheets tools: read/list/append/update against one spreadsheet at
a time, using the demo account's Google credentials (see
core/google_auth.py). The Sheets API client is synchronous, so every
call here runs in a worker thread via asyncio.to_thread rather than
blocking the event loop.

Each private helper builds its own service client and does the actual
(blocking) API call, entirely inside the thread asyncio.to_thread hands
it -- nothing Google-related touches the event loop thread.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import Context

from switchboard.core.google_auth import build_sheets_service


def _read_range(credentials, spreadsheet_id: str, range_: str) -> list[list[Any]]:
    service = build_sheets_service(credentials)
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_).execute()
    return result.get("values", [])


def _list_sheets(credentials, spreadsheet_id: str) -> list[str]:
    service = build_sheets_service(credentials)
    result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return [sheet["properties"]["title"] for sheet in result.get("sheets", [])]


def _append_row(credentials, spreadsheet_id: str, sheet_name: str, values: list[Any]) -> str:
    service = build_sheets_service(credentials)
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        )
        .execute()
    )
    return result.get("updates", {}).get("updatedRange", "Row appended.")


def _update_range(credentials, spreadsheet_id: str, range_: str, values: list[list[Any]]) -> str:
    service = build_sheets_service(credentials)
    result = (
        service.spreadsheets()
        .values()
        .update(spreadsheetId=spreadsheet_id, range=range_, valueInputOption="USER_ENTERED", body={"values": values})
        .execute()
    )
    return f"Updated {result.get('updatedCells', 0)} cell(s) in '{range_}'."


async def read_range(spreadsheet_id: str, range: str, ctx: Context) -> list[list[Any]]:
    """Read cell values from a spreadsheet range.

    Args:
        spreadsheet_id: The spreadsheet's id (from its URL).
        range: A1-notation range, e.g. "Sheet1!A1:C10".
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_read_range, credentials, spreadsheet_id, range)


async def list_sheets(spreadsheet_id: str, ctx: Context) -> list[str]:
    """List every sheet (tab) name in a spreadsheet.

    Args:
        spreadsheet_id: The spreadsheet's id (from its URL).
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_list_sheets, credentials, spreadsheet_id)


async def append_row(spreadsheet_id: str, sheet_name: str, values: list[Any], ctx: Context) -> str:
    """Append a new row to the end of a sheet. Not destructive -- always
    adds a row, never overwrites existing ones. Not idempotent either --
    calling this twice adds two rows.

    Args:
        spreadsheet_id: The spreadsheet's id (from its URL).
        sheet_name: Which sheet (tab) to append to.
        values: Cell values for the new row, in column order.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_append_row, credentials, spreadsheet_id, sheet_name, values)


async def update_range(spreadsheet_id: str, range: str, values: list[list[Any]], ctx: Context) -> str:
    """Overwrite cell values in a range. Data-modifying -- overwrites
    whatever was already in that range. Idempotent: writing the same
    values twice leaves the sheet in the same end state.

    Args:
        spreadsheet_id: The spreadsheet's id (from its URL).
        range: A1-notation range to overwrite, e.g. "Sheet1!A2:C2".
        values: Rows of cell values, e.g. [["a", "b", "c"]] for one row.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_update_range, credentials, spreadsheet_id, range, values)
