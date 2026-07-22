"""`tenants` — multi-tenancy extension (user-directed; not part of the
original `Database_Schema.md` 14-table locked schema, which assumed a
single customer deployment per `LOCKED_Design_v1.0.md` §1). Each tenant is
an isolated customer organization; `users.tenant_id` and `products.tenant_id`
are the isolation boundary — everything else (projects, artifacts, stages,
...) is scoped transitively through `product_id`.
"""
import uuid

from sqlalchemy import Boolean, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class Tenant(Base, TimestampMixin):
    """A customer organization. Isolation boundary for all tenant-owned data."""

    __tablename__ = "tenants"
    __table_args__ = (
        Index("idx_tenants_slug", "slug"),
        Index("idx_tenants_active", "is_active"),
        {"comment": "Customer organizations (multi-tenant isolation boundary)"},
    )

    tenant_id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="URL/subdomain-safe unique identifier"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", comment="Tenant-specific configuration"
    )
