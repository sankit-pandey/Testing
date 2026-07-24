"""Auth endpoints — DeepHealth SSO exchange, JWT issuance/refresh. Story 1.3."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.models.users import User
from app.schemas.auth import SSOCallbackRequest, SSOLoginUrlResponse
from app.schemas.user import RefreshTokenRequest, TokenPair, UserRead
from app.services.audit_service import record_audit_log
from app.services.sso_service import SSOError, SSOService
from app.services.user_service import UserNotProvisionedError, get_or_link_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/sso/login-url", response_model=SSOLoginUrlResponse)
async def sso_login_url() -> SSOLoginUrlResponse:
    """Return the DeepHealth SSO authorize URL the SPA should redirect to."""
    state = str(uuid.uuid4())
    try:
        url = SSOService().build_authorize_url(state)
    except SSOError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return SSOLoginUrlResponse(authorize_url=url, state=state)


@router.post("/sso/callback", response_model=TokenPair)
async def sso_callback(
    body: SSOCallbackRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """Exchange the SSO authorization code, resolve the Knewron user, issue JWTs."""
    sso = SSOService()
    try:
        tokens = await sso.exchange_code(body.code)
        claims = await sso.get_claims(tokens["id_token"])
        user = await get_or_link_user(db, claims)
    except SSOError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except UserNotProvisionedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    user.last_login_at = datetime.now(timezone.utc)
    await record_audit_log(
        db,
        user_id=user.user_id,
        action="login",
        entity_type="user",
        entity_id=user.user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return TokenPair(
        access_token=create_access_token(user.user_id, user.role),
        refresh_token=create_refresh_token(user.user_id, user.role),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Exchange a valid refresh token for a new access/refresh token pair."""
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenPair(
        access_token=create_access_token(user.user_id, user.role),
        refresh_token=create_refresh_token(user.user_id, user.role),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user
