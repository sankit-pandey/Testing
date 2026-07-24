"""User provisioning/lookup for SSO login.

Design ref: `Requirements_Document.md` §2.2 (Admin manages users; roles are
assigned within Knewron, not derived from the IdP) and §6.4.1 (SSO auth, no
local passwords). Story 1.3.

Users must be **provisioned in Knewron first** (by an Admin, with a role and
email) before they can sign in via SSO — the IdP proves *identity*, Knewron
owns *authorization*. First successful SSO login links `users.sso_id`.
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class UserNotProvisionedError(Exception):
    """Raised when an SSO-authenticated identity has no matching Knewron user."""


async def get_or_link_user(db: AsyncSession, claims: dict[str, Any]) -> User:
    """Resolve the Knewron `User` for validated SSO claims, linking `sso_id` on first login."""
    sso_id = claims.get("sub")
    email = claims.get("email")

    user = None
    if sso_id:
        user = (await db.execute(select(User).where(User.sso_id == sso_id))).scalar_one_or_none()

    if user is None and email:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is not None and user.sso_id is None:
            user.sso_id = sso_id

    if user is None or not user.is_active:
        raise UserNotProvisionedError(
            "No active Knewron account found for this identity; ask an Admin to provision one."
        )

    if claims.get("name"):
        user.full_name = claims["name"]

    return user
