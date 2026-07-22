"""Pydantic schemas for `tenants` — multi-tenancy extension."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel, PaginationMeta


class TenantCreate(CamelModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, description="URL/subdomain-safe unique identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(CamelModel):
    name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class TenantRead(CamelModel):
    tenant_id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    @classmethod
    def from_orm_model(cls, tenant: Any) -> "TenantRead":
        return cls(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            slug=tenant.slug,
            is_active=tenant.is_active,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            metadata=tenant.metadata_,
        )


class TenantList(CamelModel):
    tenants: list[TenantRead]
    pagination: PaginationMeta


class TenantSettingUpsert(CamelModel):
    """Per-tenant integration credential override (Lokalise/Figma/etc.),
    stored in `system_settings` with `tenant_id` set. See
    `app/services/tenant_service.py`.
    """

    setting_key: str = Field(max_length=100)
    setting_value: str
    is_encrypted: bool = False
    description: str | None = None
