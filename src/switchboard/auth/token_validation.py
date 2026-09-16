"""
Verifies bearer tokens against Auth0 as the external Authorization Server.

This file is the entire trust boundary for "who is allowed to call this
server" (see the two-auth-layers split in the project README). A resource
server has three jobs here, per RFC 9068 and the MCP authorization spec:

  1. Verify the JWT's signature against Auth0's public JWKS -- proves
     Auth0 actually issued it, rather than trusting a token that merely
     claims to be Auth0's.
  2. Verify `iss` and `aud` match this exact deployment, so a token minted
     for a *different* API on the same Auth0 tenant can't be replayed
     here -- the "confused deputy" problem RFC 8707 resource indicators
     exist to prevent.
  3. Surface the granted `scope`s so the SDK's bearer-auth middleware can
     reject calls lacking a required scope before any tool ever runs.

No secrets live in this file. JWKS are public keys by design -- that's
exactly why stateless local verification is possible without calling
Auth0 on every single request.
"""

import logging

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

from switchboard.core.config import settings

logger = logging.getLogger(__name__)


_jwks_client = PyJWKClient(settings.jwks_uri)


class Auth0TokenVerifier(TokenVerifier):
    """Validates access tokens issued by Auth0 for this resource server."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.mcp_resource_server_url,
                issuer=settings.issuer_url,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            logger.warning("Rejected bearer token: %s", exc)
            return None

        scopes = claims.get("scope", "").split()

        return AccessToken(
            token=token,
            client_id=claims.get("azp") or claims.get("sub", "unknown"),
            scopes=scopes,
            expires_at=claims.get("exp"),
            resource=settings.mcp_resource_server_url,
        )
