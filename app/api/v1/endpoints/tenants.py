"""Tenant management — multi-tenancy extension. Superuser-only: creating/
managing tenants is a platform-level action, not a per-tenant one.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_superuser
from app.db.session import get_db
from app.models.users import User
from app.schemas.tenant import (
    TenantCreate,
    TenantList,
    TenantRead,
    TenantSettingUpsert,
    TenantUpdate,
)
from app.services import tenant_service
from app.services.audit_service import record_audit_log
from app.utils.pagination import build_pagination_meta

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> TenantRead:
    try:
        tenant = await tenant_service.create_tenant(db, body)
    except tenant_service.DuplicateTenantSlugError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="create_tenant",
        entity_type="tenant",
        entity_id=tenant.tenant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return TenantRead.from_orm_model(tenant)


@router.get("", response_model=TenantList)
async def list_tenants(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> TenantList:
    tenants, total = await tenant_service.list_tenants(db, page=page, limit=limit)
    return TenantList(
        tenants=[TenantRead.from_orm_model(t) for t in tenants],
        pagination=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> TenantRead:
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantRead.from_orm_model(tenant)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> TenantRead:
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant = await tenant_service.update_tenant(db, tenant, body)
    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="update_tenant",
        entity_type="tenant",
        entity_id=tenant.tenant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        changes=body.model_dump(exclude_unset=True, by_alias=True),
    )
    await db.commit()
    return TenantRead.from_orm_model(tenant)


@router.put("/{tenant_id}/settings", status_code=status.HTTP_204_NO_CONTENT)
async def upsert_tenant_setting(
    tenant_id: uuid.UUID,
    body: TenantSettingUpsert,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> None:
    """Set a per-tenant integration credential override (e.g.
    `lokalise_api_token`, `lokalise_project_id`, `lokalise_webhook_secret`,
    `figma_access_token`) — consumed by `LokaliseService`/`FigmaService` with
    a fallback to the platform-wide `.env` default.
    """
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    await tenant_service.upsert_tenant_setting(
        db,
        tenant_id,
        setting_key=body.setting_key,
        setting_value=body.setting_value,
        is_encrypted=body.is_encrypted,
        description=body.description,
    )
    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="upsert_tenant_setting",
        entity_type="tenant",
        entity_id=tenant_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        changes={"setting_key": body.setting_key},  # never log the value itself
    )
    await db.commit()
