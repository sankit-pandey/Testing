"""Project CRUD — Design ref: `Database_Schema.md` §3; `Technical_Design_Document.md`
§4.1.1. Story 1.1. Tenant-scoped throughout (multi-tenancy extension).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles, require_tenant_id
from app.core.roles import WRITE_ROLES
from app.db.session import get_db
from app.models.users import User
from app.schemas.artifact import ArtifactSummary
from app.schemas.project import ProjectCreate, ProjectCreateResponse, ProjectDetail, ProjectList, ProjectRead
from app.services import project_service
from app.services.audit_service import record_audit_log
from app.utils.pagination import build_pagination_meta

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ProjectCreateResponse:
    try:
        project = await project_service.create_project(db, body, current_user.user_id, tenant_id)
    except project_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except project_service.DuplicateProjectError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        action="create_project",
        entity_type="project",
        entity_id=project.project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ProjectCreateResponse(
        project_id=project.project_id, status=project.status, created_at=project.created_at
    )


@router.get("", response_model=ProjectList)
async def list_projects(
    status_filter: str | None = Query(default=None, alias="status"),
    product_id: uuid.UUID | None = Query(default=None, alias="productId"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ProjectList:
    projects, total = await project_service.list_projects(
        db, tenant_id=tenant_id, status=status_filter, product_id=product_id, page=page, limit=limit
    )
    return ProjectList(
        projects=[ProjectRead.from_orm_model(p) for p in projects],
        pagination=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ProjectDetail:
    project = await project_service.get_project_with_artifacts(db, project_id, tenant_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    base = ProjectRead.from_orm_model(project)
    return ProjectDetail(
        **base.model_dump(by_alias=False),
        artifacts=[
            ArtifactSummary(
                artifact_id=a.artifact_id,
                artifact_type=a.artifact_type,
                artifact_name=a.artifact_name,
                status=a.status,
                progress_percent=a.progress_percent,
            )
            for a in project.artifacts
        ],
    )
