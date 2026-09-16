"""
Central runtime configuration for Switchboard.

Everything here is loaded from environment variables (via `.env` locally,
or real env vars in Docker/CI) -- never hardcoded, per the project's
credential-handling rules. `auth0_domain` has no default on purpose: a
resource server that silently falls back to a placeholder identity
provider is worse than one that refuses to start.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Server ---
    switchboard_host: str = "0.0.0.0"
    switchboard_port: int = 8000

   
    auth0_domain: str

    mcp_resource_server_url: str = "http://localhost:8000"

    @property
    def issuer_url(self) -> str:
        """Auth0's OIDC issuer for this tenant -- always this exact form."""
        return f"https://{self.auth0_domain}/"

    @property
    def jwks_uri(self) -> str:
        """Where Auth0 publishes the public keys used to sign tokens."""
        return f"https://{self.auth0_domain}/.well-known/jwks.json"


settings = Settings()
