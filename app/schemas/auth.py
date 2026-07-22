"""Pydantic schemas for the auth/SSO endpoints. Story 1.3.

`tenant_slug` (multi-tenancy extension) scopes login to one tenant; omit it
only for the platform-superuser login path.
"""
from pydantic import BaseModel


class SSOLoginUrlResponse(BaseModel):
    authorize_url: str
    state: str


class SSOCallbackRequest(BaseModel):
    code: str
    tenant_slug: str | None = None
