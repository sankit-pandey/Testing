"""Shared FastAPI dependencies — DB session, current user, RBAC guards.

Design ref: `Requirements_Document.md` §2.2 (roles); `LOCKED_Design_v1.0.md`
§12 (RBAC). Story 1.3.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer access token."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = uuid.UUID(payload["sub"])
    user = (await db.execute(select(User).where(User.user_id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*allowed: Role):
    """Dependency factory enforcing that `current_user.role` is one of `allowed`.

    `viewer` is read-only by design: GET-only routers depend on
    `require_roles(*ALL_ROLES)`, mutating routers depend on
    `require_roles(*WRITE_ROLES)`.
    """

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in {r.value for r in allowed}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform this action",
            )
        return current_user

    return _guard


def require_any_role(current_user: User = Depends(get_current_user)) -> User:
    """Any authenticated, active user (including `viewer`)."""
    return current_user
