"""Tenant CRUD + per-tenant settings — multi-tenancy extension.

Two entry points are provided deliberately:
- **Async** (`create_tenant`, `get_tenant`, ...) — for the FastAPI admin API.
- **Sync** (`get_tenant_setting_sync`) — for `LokaliseService`/`FigmaService`,
  which run inside Celery workers and need a per-tenant credential override
  with a global (`.env`) fallback (see `app/services/lokalise_service.py`,
  `app/services/figma_service.py`).
"""
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_value, encrypt_value
from app.models.system_settings import SystemSetting
from app.models.tenants import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


class DuplicateTenantSlugError(Exception):
    """Raised when `slug` is not unique (`tenants.slug` UNIQUE)."""


async def create_tenant(db: AsyncSession, body: TenantCreate) -> Tenant:
    tenant = Tenant(name=body.name, slug=body.slug, metadata_=body.metadata)
    db.add(tenant)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateTenantSlugError(f"slug '{body.slug}' already exists") from exc
    return tenant


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    return await db.get(Tenant, tenant_id)


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    return (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()


async def update_tenant(db: AsyncSession, tenant: Tenant, body: TenantUpdate) -> Tenant:
    if body.name is not None:
        tenant.name = body.name
    if body.is_active is not None:
        tenant.is_active = body.is_active
    if body.metadata is not None:
        tenant.metadata_ = body.metadata
    await db.flush()
    return tenant


async def list_tenants(db: AsyncSession, *, page: int, limit: int) -> tuple[list[Tenant], int]:
    total = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    query = select(Tenant).order_by(Tenant.created_at.desc()).offset((page - 1) * limit).limit(limit)
    tenants = (await db.execute(query)).scalars().all()
    return list(tenants), total


async def upsert_tenant_setting(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    setting_key: str,
    setting_value: str,
    is_encrypted: bool = False,
    description: str | None = None,
) -> SystemSetting:
    """Create/update a per-tenant override (e.g. `lokalise_api_token`,
    `lokalise_project_id`, `figma_access_token`) consumed by
    `get_tenant_setting_sync`.
    """
    existing = (
        await db.execute(
            select(SystemSetting).where(
                SystemSetting.tenant_id == tenant_id, SystemSetting.setting_key == setting_key
            )
        )
    ).scalar_one_or_none()

    stored_value = encrypt_value(setting_value) if is_encrypted else setting_value

    if existing is not None:
        existing.setting_value = stored_value
        existing.is_encrypted = is_encrypted
        existing.description = description
        await db.flush()
        return existing

    setting = SystemSetting(
        tenant_id=tenant_id,
        setting_key=setting_key,
        setting_value=stored_value,
        is_encrypted=is_encrypted,
        description=description,
    )
    db.add(setting)
    await db.flush()
    return setting


def find_tenant_id_by_lokalise_project_id(lokalise_project_id: str) -> uuid.UUID | None:
    """Reverse-lookup: given a Lokalise webhook payload's `project.id`, find
    which tenant configured that project id as their override, so the
    webhook receiver can verify against that tenant's signing secret
    (`app/api/v1/endpoints/webhooks.py`). Sync — for use in the webhook path.
    """
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        setting = (
            db.execute(
                select(SystemSetting).where(
                    SystemSetting.setting_key == "lokalise_project_id",
                    SystemSetting.setting_value == lokalise_project_id,
                    SystemSetting.tenant_id.is_not(None),
                )
            )
            .scalars()
            .first()
        )
        return setting.tenant_id if setting else None


def get_tenant_setting_sync(tenant_id: uuid.UUID | None, setting_key: str) -> str | None:
    """Resolve a per-tenant setting override (sync — for use inside Celery
    workers / service clients). Returns `None` if unset so callers fall back
    to the platform-wide `.env` default.
    """
    if tenant_id is None:
        return None

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        setting = (
            db.execute(
                select(SystemSetting).where(
                    SystemSetting.tenant_id == tenant_id, SystemSetting.setting_key == setting_key
                )
            )
            .scalars()
            .first()
        )
        if setting is None:
            return None
        return decrypt_value(setting.setting_value) if setting.is_encrypted else setting.setting_value
