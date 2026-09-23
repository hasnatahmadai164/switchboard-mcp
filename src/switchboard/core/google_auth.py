"""
Builds Google API clients from the demo account's stored OAuth tokens.

This is backend integration credentials (layer 2 of the two-auth-layers
split in the project README), not MCP-level auth -- it has nothing to do
with who's allowed to call this server. One dedicated Google account's
tokens are used for every MCP caller, on purpose -- full per-caller
Google delegation is a real pattern but adds a second OAuth flow for no
real benefit at this project's scale (see the README).

google-api-python-client is synchronous (no official async client), so
every actual Sheets/Gmail call in the tools modules wraps these clients
with asyncio.to_thread -- never call them directly from async code.

Google's own client library warns that a built service `Resource` isn't
safe to share across threads. Since asyncio.to_thread can run different
calls on different worker threads, each tool call builds its own fresh
Resource here rather than reusing one cached globally -- cheap, since
build() for a known API like Sheets/Gmail resolves from a bundled static
discovery document rather than a network call. The one thing that IS
shared across calls is the Credentials object itself (see lifespan.py),
so a still-valid access token gets reused instead of exchanging the
refresh token on every single tool call.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from switchboard.core.config import settings

_TOKEN_URI = "https://oauth2.googleapis.com/token"

# Must list every scope any Google tool needs -- Credentials.refresh()
# uses this to validate the token still covers what's being requested.
# Keep in sync with scripts/google_oauth_setup.py's SCOPES.
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


def build_google_credentials() -> Credentials:
    """Builds a Credentials object from the refresh token minted by
    scripts/google_oauth_setup.py. No access token is supplied here --
    Google's client library fetches a fresh one from the refresh token
    automatically on first use, and again whenever it expires."""
    return Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri=_TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=_SCOPES,
    )


def build_sheets_service(credentials: Credentials) -> Resource:
    return build("sheets", "v4", credentials=credentials)


def build_gmail_service(credentials: Credentials) -> Resource:
    return build("gmail", "v1", credentials=credentials)


def build_calendar_service(credentials: Credentials) -> Resource:
    return build("calendar", "v3", credentials=credentials)
