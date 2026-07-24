"""Pydantic schemas for `products` — Design ref: `Database_Schema.md` §2."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel, PaginationMeta


class ProductCreate(CamelModel):
    product_name: str = Field(max_length=255)
    product_code: str | None = Field(default=None, max_length=100)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(CamelModel):
    product_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class ProductRead(CamelModel):
    product_id: uuid.UUID
    product_name: str
    product_code: str | None
    description: str | None
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]

    @classmethod
    def from_orm_model(cls, product: Any) -> "ProductRead":
        """Build from a `Product` ORM row (whose JSONB column is `metadata_`,
        since `metadata` is reserved on the declarative base)."""
        return cls(
            product_id=product.product_id,
            product_name=product.product_name,
            product_code=product.product_code,
            description=product.description,
            is_active=product.is_active,
            created_by=product.created_by,
            created_at=product.created_at,
            updated_at=product.updated_at,
            metadata=product.metadata_,
        )


class ProductList(CamelModel):
    products: list[ProductRead]
    pagination: PaginationMeta
