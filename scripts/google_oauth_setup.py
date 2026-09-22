"""
One-time interactive setup: authorizes ONE dedicated Google account for
Sheets and Gmail access, and prints a refresh token to paste into .env.

Run this locally (not in Docker) -- it opens a browser for you to log
into the DEMO Google account (not your personal one) and grant consent.
Run it once. The server itself never does an interactive login; it only
ever refreshes the token this script produces (see core/google_auth.py).
Re-run this only if that refresh token is later revoked or expires.

Usage:
    python scripts/google_oauth_setup.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> None:
    client_id = input("Google OAuth Client ID: ").strip()
    client_secret = input("Google OAuth Client Secret: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    credentials = flow.run_local_server(port=0)

    print("\nAuthorization complete. Add these three lines to your .env:\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
