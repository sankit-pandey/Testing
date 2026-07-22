"""Artifact submission & upload — Design ref: `Database_Schema.md` §4;
`Technical_Design_Document.md` §4.1.1. Story 1.2. Tenant-scoped throughout
(multi-tenancy extension) via `artifact_service.get_artifact_for_tenant`.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles, require_tenant_id
from app.core.roles import WRITE_ROLES
from app.db.session import get_db
from app.models.users import User
from app.schemas.artifact import (
    ArtifactCancelResponse,
    ArtifactCreate,
    ArtifactCreateResponse,
    ArtifactDetail,
    StageSummary,
)
from app.services import artifact_service, project_service
from app.services.audit_service import record_audit_log
from app.services.storage_service import StorageService

router = APIRouter(tags=["artifacts"])


@router.post(
    "/projects/{project_id}/artifacts",
    response_model=ArtifactCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_artifact(
    project_id: uuid.UUID,
    body: ArtifactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ArtifactCreateResponse:
    """Add an artifact to a project and return a presigned upload URL.
    Artifacts may be added at any time, including after the project has started
    (`Requirements_Document.md` §1.5).
    """
    project = await project_service.get_project(db, project_id, tenant_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        artifact, upload_url = await artifact_service.create_artifact(db, project_id, body)
    except artifact_service.InvalidArtifactTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        action="add_artifact",
        entity_type="artifact",
        entity_id=artifact.artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return ArtifactCreateResponse(
        artifact_id=artifact.artifact_id,
        status=artifact.status,
        created_at=artifact.created_at,
        upload_url=upload_url,
    )


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetail)
async def get_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ArtifactDetail:
    """Artifact status/progress, including per-stage detail (Technical_Design §4.1.1)."""
    artifact = await artifact_service.get_artifact_for_tenant(db, artifact_id, tenant_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    from app.services import stage_service

    stages = await stage_service.list_stages(db, artifact_id)
    base = ArtifactDetail.from_orm_model(artifact)
    base.stages = [StageSummary(stage=s.stage_name, status=s.status) for s in stages]
    return base


@router.post("/artifacts/{artifact_id}/start", status_code=status.HTTP_202_ACCEPTED)
async def start_artifact(
    artifact_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> dict:
    """Enqueue the artifact's pipeline (`execute_pipeline` Celery task)."""
    artifact = await artifact_service.get_artifact_for_tenant(db, artifact_id, tenant_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    try:
        artifact = await artifact_service.start_artifact(db, artifact)
    except artifact_service.ArtifactNotStartableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        action="start_artifact",
        entity_type="artifact",
        entity_id=artifact.artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    from app.tasks.pipeline_tasks import execute_pipeline

    execute_pipeline.delay(str(artifact.artifact_id))

    return {"artifactId": str(artifact.artifact_id), "status": artifact.status}


@router.delete("/artifacts/{artifact_id}", response_model=ArtifactCancelResponse)
async def cancel_artifact(
    artifact_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> ArtifactCancelResponse:
    """Cancel a single artifact; does not affect other artifacts in the project
    (`Requirements_Document.md` §1.5 — a failed/cancelled artifact never blocks others).
    """
    artifact = await artifact_service.get_artifact_for_tenant(db, artifact_id, tenant_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    artifact = await artifact_service.cancel_artifact(db, artifact)
    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        action="cancel_artifact",
        entity_type="artifact",
        entity_id=artifact.artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return ArtifactCancelResponse(
        artifact_id=artifact.artifact_id,
        status=artifact.status,
        cancelled_at=datetime.now(timezone.utc),
    )


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(require_tenant_id),
) -> Response:
    """Each artifact downloads independently as soon as it completes —
    partial completion (`Requirements_Document.md` §1.5, §5.7.5); Story 6.3.
    """
    artifact = await artifact_service.get_artifact_for_tenant(db, artifact_id, tenant_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    if artifact.status != "complete" or not artifact.output_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Artifact is '{artifact.status}', not yet complete/downloadable",
        )

    storage = StorageService()
    content = await asyncio.to_thread(storage.get_bytes, artifact.output_path)
    filename = artifact.output_path.rsplit("/", 1)[-1]
    content_type = storage.guess_content_type(filename) or "application/octet-stream"

    await record_audit_log(
        db,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        action="download_artifact",
        entity_type="artifact",
        entity_id=artifact.artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
