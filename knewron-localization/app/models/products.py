"""`products` — Design ref: `Database_Schema.md` §2."""
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
        Index("idx_products_created_by", "created_by"),
        Index("idx_products_active", "is_active"),
        {"comment": "Products that require localization"},
    )

    product_id: Mapped[uuid.UUID] = uuid_pk()
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str | None] = mapped_column(
        String(100), unique=True, comment="Unique product identifier/SKU"
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
