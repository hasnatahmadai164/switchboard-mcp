"""
Unit tests for Settings' computed properties -- exactly the kind of
small, easy-to-get-wrong string formatting that caused a real bug
earlier in this project (a field rename that silently broke the
Postgres DSN properties). Cheap to test, so there's no excuse not to.
"""

from switchboard.core.config import Settings


def _make_settings(**overrides) -> Settings:
    defaults = {
        "auth0_domain": "test-tenant.us.auth0.com",
        "switchboard_db_readonly_user": "ro_user",
        "switchboard_db_readonly_password": "ro_pass",
        "switchboard_db_write_user": "rw_user",
        "switchboard_db_write_password": "rw_pass",
        "pinecone_api_key": "test-key",
        "google_client_id": "test-client-id",
        "google_client_secret": "test-client-secret",
        "google_refresh_token": "test-refresh-token",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_issuer_url_has_trailing_slash():
    settings = _make_settings(auth0_domain="dev-abc123.us.auth0.com")
    assert settings.issuer_url == "https://dev-abc123.us.auth0.com/"


def test_jwks_uri():
    settings = _make_settings(auth0_domain="dev-abc123.us.auth0.com")
    assert settings.jwks_uri == "https://dev-abc123.us.auth0.com/.well-known/jwks.json"


def test_postgres_readonly_dsn_uses_readonly_credentials():
    settings = _make_settings(
        switchboard_db_readonly_user="ro",
        switchboard_db_readonly_password="ro-pw",
        postgres_host="db.internal",
        postgres_port=5433,
        postgres_db="mydb",
    )
    assert settings.postgres_readonly_dsn == "postgresql://ro:ro-pw@db.internal:5433/mydb"


def test_postgres_write_dsn_uses_write_credentials():
    settings = _make_settings(
        switchboard_db_write_user="rw",
        switchboard_db_write_password="rw-pw",
        postgres_host="db.internal",
        postgres_port=5433,
        postgres_db="mydb",
    )
    assert settings.postgres_write_dsn == "postgresql://rw:rw-pw@db.internal:5433/mydb"


def test_readonly_and_write_dsns_are_different():
    settings = _make_settings()
    assert settings.postgres_readonly_dsn != settings.postgres_write_dsn
