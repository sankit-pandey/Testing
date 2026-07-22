"""Figma metadata ingestion endpoint — Design ref: `Figma_Integration.md`
§3 step 8, §4. Story 4.4. Admin-only: this is a system/integration
configuration action (`Requirements_Document.md` §2.2 — Admin: "Integration
configuration"), run once per Figma frame after the design team's
"Build & Export Metadata" plugin run. Tenant-scoped (multi-tenancy
extension): `productId` must belong to the caller's tenant.
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_roles, require_tenant_id
from app.core.roles import Role
from app.schemas.figma import FigmaIngestRequest, FigmaIngestResponse
from app.services.figma_service import FigmaError

router = APIRouter(prefix="/figma", tags=["figma"])


@router.post("/ingest", response_model=FigmaIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_figma_metadata(
    body: FigmaIngestRequest,
    current_user=Depends(require_roles(Role.ADMIN)),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> FigmaIngestResponse:
    try:
        figma_image = await asyncio.to_thread(_ingest_sync, tenant_id, body)
    except (KeyError, FigmaError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FigmaIngestResponse(figma_image_id=figma_image.figma_image_id, chromadb_id=figma_image.chromadb_id)


def _ingest_sync(tenant_id: uuid.UUID, body: FigmaIngestRequest):
    from app.db.session import SessionLocal
    from app.models.products import Product
    from app.services.figma_ingestion_service import ingest_figma_metadata

    with SessionLocal() as db:
        product = db.get(Product, body.product_id)
        if product is None or product.tenant_id != tenant_id:
            raise ValueError(f"Product {body.product_id} not found")
        return ingest_figma_metadata(db, tenant_id, body.product_id, body.metadata)
