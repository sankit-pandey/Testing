"""Review queue + sign-off endpoints — Design ref: `Database_Schema.md`
§11, §12; `LOCKED_Design_v1.0.md` §4. Stories 6.1, 6.2.
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.roles import WRITE_ROLES
from app.db.session import get_db
from app.models.review_findings import ReviewFinding
from app.models.users import User
from app.schemas.review import (
    ApprovalRead,
    ApprovalRequest,
    FindingRead,
    FindingResolveRequest,
    RejectionRequest,
)
from app.services import artifact_service
from app.services.audit_service import record_audit_log

router = APIRouter(tags=["reviews"])


@router.get("/artifacts/{artifact_id}/findings", response_model=list[FindingRead])
async def list_findings(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FindingRead]:
    findings = (
        (await db.execute(select(ReviewFinding).where(ReviewFinding.artifact_id == artifact_id)))
        .scalars()
        .all()
    )
    return [FindingRead.model_validate(f) for f in findings]


@router.patch("/findings/{finding_id}/resolve", response_model=FindingRead)
async def resolve_finding(
    finding_id: uuid.UUID,
    body: FindingResolveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
) -> FindingRead:
    """Resolve/ignore a finding; if no blocking findings remain for the
    artifact, resume the pipeline out of `needs_human_review` (Story 5.2/5.3
    `review()` re-entry checks `has_open_blocking_findings`).
    """
    finding = await db.get(ReviewFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    if body.status not in ("resolved", "ignored"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be resolved|ignored")

    from datetime import datetime, timezone

    finding.status = body.status
    finding.resolved_by = current_user.user_id
    finding.resolved_at = datetime.now(timezone.utc)

    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="resolve_finding",
        entity_type="review_finding",
        entity_id=finding.finding_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    remaining = (
        (
            await db.execute(
                select(ReviewFinding).where(
                    ReviewFinding.artifact_id == finding.artifact_id,
                    ReviewFinding.status == "open",
                    ReviewFinding.severity.in_(("critical", "major")),
                )
            )
        )
        .scalars()
        .all()
    )

    if not remaining:
        artifact = await artifact_service.get_artifact(db, finding.artifact_id)
        if artifact is not None and artifact.status == "needs_human_review":
            from app.tasks.pipeline_tasks import resume_pipeline

            await asyncio.to_thread(resume_pipeline.delay, str(artifact.artifact_id), "findings_resolved")

    return FindingRead.model_validate(finding)


@router.post("/artifacts/{artifact_id}/approve", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def approve_artifact(
    artifact_id: uuid.UUID,
    body: ApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
) -> ApprovalRead:
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    approval = await asyncio.to_thread(_submit_approval_sync, artifact_id, current_user.user_id, "approved", body.comments, None)

    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="approve_artifact",
        entity_type="artifact",
        entity_id=artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ApprovalRead.model_validate(approval)


@router.post("/artifacts/{artifact_id}/reject", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def reject_artifact(
    artifact_id: uuid.UUID,
    body: RejectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
) -> ApprovalRead:
    artifact = await artifact_service.get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    approval = await asyncio.to_thread(
        _submit_approval_sync, artifact_id, current_user.user_id, "rejected", None, body.rejection_reason
    )

    await record_audit_log(
        db,
        user_id=current_user.user_id,
        action="reject_artifact",
        entity_type="artifact",
        entity_id=artifact_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        changes={"rejection_reason": body.rejection_reason},
    )
    await db.commit()
    return ApprovalRead.model_validate(approval)


def _submit_approval_sync(
    artifact_id: uuid.UUID,
    approved_by: uuid.UUID,
    approval_status: str,
    comments: str | None,
    rejection_reason: str | None,
):
    """`submit_approval` needs the sync DB session (it transitions state via
    the pipeline's sync `StateMachine` and may enqueue a Celery resume) — run
    off the async event loop via `asyncio.to_thread` in the route.
    """
    from app.db.session import SessionLocal
    from app.models.artifacts import ProjectArtifact
    from app.services.approval_service import submit_approval

    with SessionLocal() as sync_db:
        artifact = sync_db.get(ProjectArtifact, artifact_id)
        approval = submit_approval(
            sync_db, artifact, approved_by, approval_status, comments=comments, rejection_reason=rejection_reason
        )
        sync_db.refresh(approval)
        return approval
