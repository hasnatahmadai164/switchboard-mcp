"""
Central runtime configuration for Switchboard.

Everything here is loaded from environment variables (via `.env` locally,
or real env vars in Docker/CI) -- never hardcoded, per the project's
credential-handling rules. Required fields with no default (auth0_domain,
the Postgres role credentials) are required on purpose: a server that
silently falls back to a placeholder credential is worse than one that
refuses to start.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    switchboard_host: str = "0.0.0.0"
    switchboard_port: int = 8000

    auth0_domain: str

    mcp_resource_server_url: str = "http://localhost:8000"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "switchboard"


    switchboard_db_readonly_user: str
    switchboard_db_readonly_password: str
    switchboard_db_write_user: str
    switchboard_db_write_password: str

    @property
    def issuer_url(self) -> str:
        """Auth0's OIDC issuer for this tenant -- always this exact form."""
        return f"https://{self.auth0_domain}/"

    @property
    def jwks_uri(self) -> str:
        """Where Auth0 publishes the public keys used to sign tokens."""
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    @property
    def postgres_readonly_dsn(self) -> str:
        return (
            f"postgresql://{self.switchboard_db_readonly_user}:{self.switchboard_db_readonly_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_write_dsn(self) -> str:
        return (
            f"postgresql://{self.switchboard_db_write_user}:{self.switchboard_db_write_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
