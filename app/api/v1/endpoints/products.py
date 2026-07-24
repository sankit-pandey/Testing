"""Product CRUD — Design ref: `Database_Schema.md` §2. Story 1.1."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.roles import WRITE_ROLES
from app.db.session import get_db
from app.models.users import User
from app.schemas.product import ProductCreate, ProductList, ProductRead, ProductUpdate
from app.services import product_service
from app.services.audit_service import record_audit_log
from app.utils.pagination import build_pagination_meta

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
) -> ProductRead:
    try:
        product = await product_service.create_product(db, body, current_user.user_id)
    except product_service.DuplicateProductCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="create_product",
        entity_type="product",
        entity_id=product.product_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ProductRead.from_orm_model(product)


@router.get("", response_model=ProductList)
async def list_products(
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductList:
    products, total = await product_service.list_products(
        db, is_active=is_active, page=page, limit=limit
    )
    return ProductList(
        products=[ProductRead.from_orm_model(p) for p in products],
        pagination=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductRead:
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductRead.from_orm_model(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
) -> ProductRead:
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await product_service.update_product(db, product, body)
    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="update_product",
        entity_type="product",
        entity_id=product.product_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        changes=body.model_dump(exclude_unset=True, by_alias=True),
    )
    await db.commit()
    return ProductRead.from_orm_model(product)
