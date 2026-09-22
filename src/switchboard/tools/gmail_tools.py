"""
Gmail tools: search, read, draft, and send -- using the demo account's
Google credentials (see core/google_auth.py). The Gmail API client is
synchronous, so every call here runs in a worker thread via
asyncio.to_thread rather than blocking the event loop.

Each private helper builds its own service client and does the actual
(blocking) API call, entirely inside the thread asyncio.to_thread hands
it -- nothing Google-related touches the event loop thread.
"""

import asyncio
import base64
from email.mime.text import MIMEText
from typing import Any

from mcp.server.fastmcp import Context

from switchboard.core.google_auth import build_gmail_service


def _encode_message(to: str, subject: str, body: str) -> dict[str, str]:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    # Gmail's API wants the raw RFC 2822 message base64url-encoded, not
    # plain base64 -- '+' and '/' would otherwise need escaping in a URL.
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def _extract_plain_text(payload: dict[str, Any]) -> str:
    """Walks a Gmail message payload for the first text/plain part and
    decodes it. A simple message has its body directly on the top-level
    payload; a multipart one nests it under payload["parts"], so this
    recurses until it finds one."""
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    return ""


def _search_emails(credentials, query: str, max_results: int) -> list[dict[str, str]]:
    service = build_gmail_service(credentials)
    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    # list() only returns id/threadId stubs, not content -- read_email
    # fetches the actual message once you know which one you want.
    return [{"id": msg["id"], "threadId": msg["threadId"]} for msg in result.get("messages", [])]


def _read_email(credentials, message_id: str) -> dict[str, Any]:
    service = build_gmail_service(credentials)
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}
    return {
        "id": message["id"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": _extract_plain_text(message["payload"]),
    }


def _create_draft(credentials, to: str, subject: str, body: str) -> str:
    service = build_gmail_service(credentials)
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": _encode_message(to, subject, body)})
        .execute()
    )
    return f"Draft created (id: {draft['id']})."


def _send_email(credentials, to: str, subject: str, body: str) -> str:
    service = build_gmail_service(credentials)
    sent = service.users().messages().send(userId="me", body=_encode_message(to, subject, body)).execute()
    return f"Email sent (id: {sent['id']})."


async def search_emails(query: str, ctx: Context, max_results: int = 10) -> list[dict[str, str]]:
    """Search the demo account's Gmail for messages matching a query.

    Args:
        query: Gmail search syntax, e.g. "from:alice@example.com is:unread".
        max_results: Maximum number of matching messages to return.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_search_emails, credentials, query, max_results)


async def read_email(message_id: str, ctx: Context) -> dict[str, Any]:
    """Read one email's headers and plain-text body.

    Args:
        message_id: A message id, e.g. from search_emails' results.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_read_email, credentials, message_id)


async def create_draft(to: str, subject: str, body: str, ctx: Context) -> str:
    """Create a draft email. Does not send it -- the safer default.
    Not idempotent: calling this twice creates two separate drafts.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_create_draft, credentials, to, subject, body)


async def send_email(to: str, subject: str, body: str, ctx: Context) -> str:
    """Send an email immediately. Destructive -- unlike create_draft,
    this cannot be undone once sent, and calling it twice sends two
    emails.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    """
    credentials = ctx.request_context.lifespan_context.google_credentials
    return await asyncio.to_thread(_send_email, credentials, to, subject, body)
