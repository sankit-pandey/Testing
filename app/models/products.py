"""`products` — Design ref: `Database_Schema.md` §2.

`tenant_id` is a multi-tenancy extension (see `app/models/tenants.py`);
`product_code` uniqueness is scoped per-tenant rather than global.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class Product(Base, TimestampMixin):
    """Products that require localization."""

    __tablename__ = "products"
    __table_args__ = (
        Index("idx_products_code", "product_code"),
        Index("idx_products_code_tenant_unique", "tenant_id", "product_code", unique=True),
        Index("idx_products_created_by", "created_by"),
        Index("idx_products_active", "is_active"),
        Index("idx_products_tenant_id", "tenant_id"),
        {"comment": "Products that require localization"},
    )

    product_id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str | None] = mapped_column(
        String(100), comment="Unique product identifier/SKU (unique per tenant)"
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Product-specific configuration and settings",
    )
