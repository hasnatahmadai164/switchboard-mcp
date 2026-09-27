"""
Unit tests for Auth0TokenVerifier -- the resource-server trust boundary
(see auth/token_validation.py's own docstring). These generate a real
RS256 keypair and sign real JWTs with it, so the actual cryptographic
verification path runs for real; only the network fetch of Auth0's JWKS
is mocked, since these tests must never call the real Auth0.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from switchboard.auth.token_validation import Auth0TokenVerifier
from switchboard.core.config import settings

TEST_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_token(**overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": settings.issuer_url,
        "aud": settings.mcp_resource_server_url,
        "sub": "test-client@clients",
        "azp": "test-client",
        "scope": "mcp:invoke",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, TEST_KEY, algorithm="RS256")


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


@pytest.fixture(autouse=True)
def mock_jwks(monkeypatch):
    """Every test in this file uses the locally-generated keypair above
    instead of fetching Auth0's real JWKS -- these tests must never
    touch the network or depend on a real Auth0 tenant existing."""
    monkeypatch.setattr(
        "switchboard.auth.token_validation._jwks_client.get_signing_key_from_jwt",
        lambda token: _FakeSigningKey(TEST_KEY.public_key()),
    )


@pytest.mark.asyncio
async def test_valid_token_is_accepted():
    token = _make_token()
    result = await Auth0TokenVerifier().verify_token(token)
    assert result is not None
    assert result.client_id == "test-client"
    assert "mcp:invoke" in result.scopes


@pytest.mark.asyncio
async def test_expired_token_is_rejected():
    token = _make_token(exp=int(time.time()) - 60)
    result = await Auth0TokenVerifier().verify_token(token)
    assert result is None


@pytest.mark.asyncio
async def test_wrong_audience_is_rejected():
    token = _make_token(aud="http://some-other-resource")
    result = await Auth0TokenVerifier().verify_token(token)
    assert result is None


@pytest.mark.asyncio
async def test_wrong_issuer_is_rejected():
    token = _make_token(iss="https://a-different-tenant.us.auth0.com/")
    result = await Auth0TokenVerifier().verify_token(token)
    assert result is None


@pytest.mark.asyncio
async def test_client_credentials_token_uses_sub_when_azp_absent():
    """M2M tokens sometimes carry no azp claim -- client_id should fall
    back to sub in that case (see token_validation.py's own comment on
    this distinction)."""
    token = _make_token(azp=None)
    result = await Auth0TokenVerifier().verify_token(token)
    assert result is not None
    assert result.client_id == "test-client@clients"
