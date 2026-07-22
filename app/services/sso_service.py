"""DeepHealth SSO (OAuth 2.0 / OIDC) integration.

Design ref: `Technical_Design_Document.md` §5.3 — authorization-code exchange,
token validation, session creation. `Requirements_Document.md` §6.4.1 (SSO,
no local passwords). Story 1.3.

The identity provider's exact endpoints/claims are configured via
`SSO_*` settings (Open Item — provider details still TBD per
`Requirements/Open_Items_Tracker.md`); this client speaks standard
OAuth2 authorization-code + OIDC discovery/JWKS so no provider-specific
behavior is hardcoded.
"""
from typing import Any

import httpx
from jose import jwt as jose_jwt

from app.core.config import get_settings


class SSOError(Exception):
    """Raised when the SSO exchange or token validation fails."""


class SSOService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens at the SSO token endpoint."""
        if not self.settings.sso_token_url:
            raise SSOError("SSO_TOKEN_URL is not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.settings.sso_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.settings.sso_client_id,
                    "client_secret": self.settings.sso_client_secret,
                    "redirect_uri": self.settings.sso_redirect_uri,
                },
            )
        if response.status_code != 200:
            raise SSOError(f"SSO token exchange failed: {response.status_code} {response.text}")
        return response.json()

    async def get_claims(self, id_token: str) -> dict[str, Any]:
        """Validate the OIDC `id_token` against the IdP's JWKS and return its claims."""
        if not self.settings.sso_jwks_url:
            raise SSOError("SSO_JWKS_URL is not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            jwks_response = await client.get(self.settings.sso_jwks_url)
        if jwks_response.status_code != 200:
            raise SSOError("Unable to fetch SSO JWKS")
        jwks = jwks_response.json()

        try:
            unverified_header = jose_jwt.get_unverified_header(id_token)
            key = next(k for k in jwks["keys"] if k["kid"] == unverified_header["kid"])
            claims = jose_jwt.decode(
                id_token,
                key,
                algorithms=[unverified_header["alg"]],
                audience=self.settings.sso_client_id,
                issuer=self.settings.sso_issuer,
            )
        except Exception as exc:  # noqa: BLE001 — any validation failure surfaces as SSOError
            raise SSOError(f"Invalid SSO id_token: {exc}") from exc
        return claims

    def build_authorize_url(self, state: str) -> str:
        """Build the redirect URL that starts the SSO login flow."""
        if not self.settings.sso_authorize_url:
            raise SSOError("SSO_AUTHORIZE_URL is not configured")
        params = httpx.QueryParams(
            {
                "response_type": "code",
                "client_id": self.settings.sso_client_id,
                "redirect_uri": self.settings.sso_redirect_uri,
                "scope": "openid email profile",
                "state": state,
            }
        )
        return f"{self.settings.sso_authorize_url}?{params}"
