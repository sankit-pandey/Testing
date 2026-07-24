"""Pydantic schemas for the auth/SSO endpoints. Story 1.3."""
from pydantic import BaseModel


class SSOLoginUrlResponse(BaseModel):
    authorize_url: str
    state: str


class SSOCallbackRequest(BaseModel):
    code: str
