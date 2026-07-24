"""JWT issuance/validation for session tokens.

Design ref: `Technical_Design_Document.md` §6.1 (JWT tokens, secure sessions);
§5.3 (SSO token exchange flow, 1h access / 30d refresh expiry). Story 1.3.

Authentication is delegated to DeepHealth SSO (OAuth 2.0); this module issues
and validates the platform's own short-lived JWT session tokens minted after
a successful SSO exchange (see `app/services/sso_service.py`).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT fails validation."""


def _create_token(subject: uuid.UUID, role: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Mint a short-lived access token carrying the user's role for RBAC checks."""
    return _create_token(
        user_id,
        role,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: uuid.UUID, role: str) -> str:
    """Mint a long-lived refresh token used to obtain new access tokens."""
    return _create_token(
        user_id,
        role,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: str = ACCESS_TOKEN_TYPE) -> dict[str, Any]:
    """Decode and validate a JWT; raises `InvalidTokenError` on any failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"expected token type '{expected_type}'")
    return payload
