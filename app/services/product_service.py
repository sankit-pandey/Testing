"""Business logic for `products`. Story 1.1."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product
from app.schemas.product import ProductCreate, ProductUpdate


class DuplicateProductCodeError(Exception):
    """Raised when `product_code` is not unique (`products.product_code` UNIQUE)."""


async def create_product(
    db: AsyncSession, body: ProductCreate, created_by: uuid.UUID
) -> Product:
    product = Product(
        product_name=body.product_name,
        product_code=body.product_code,
        description=body.description,
        created_by=created_by,
        metadata_=body.metadata,
    )
    db.add(product)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateProductCodeError(f"product_code '{body.product_code}' already exists") from exc
    return product


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Product | None:
    return await db.get(Product, product_id)


async def update_product(db: AsyncSession, product: Product, body: ProductUpdate) -> Product:
    if body.product_name is not None:
        product.product_name = body.product_name
    if body.description is not None:
        product.description = body.description
    if body.is_active is not None:
        product.is_active = body.is_active
    if body.metadata is not None:
        product.metadata_ = body.metadata
    await db.flush()
    return product


async def list_products(
    db: AsyncSession, *, is_active: bool | None, page: int, limit: int
) -> tuple[list[Product], int]:
    query = select(Product)
    count_query = select(func.count()).select_from(Product)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
        count_query = count_query.where(Product.is_active == is_active)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit)
    products = (await db.execute(query)).scalars().all()
    return list(products), total
