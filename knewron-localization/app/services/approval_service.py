"""Sign-off / approval workflow — Design ref: `LOCKED_Design_v1.0.md` §4;
`Database_Schema.md` §12 (`approvals`); `Architecture_Diagrams.md` §5.
Story 6.2.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approvals import Approval
from app.models.artifacts import ProjectArtifact
from app.pipeline.state_machine import StateMachine


def get_latest_approval(db: Session, artifact_id: uuid.UUID) -> Approval | None:
    return (
        db.execute(
            select(Approval)
            .where(Approval.artifact_id == artifact_id)
            .order_by(Approval.created_at.desc())
        )
        .scalars()
        .first()
    )


def submit_approval(
    db: Session,
    artifact: ProjectArtifact,
    approved_by: uuid.UUID,
    approval_status: str,
    *,
    comments: str | None = None,
    rejection_reason: str | None = None,
) -> Approval:
    """Record an approve/reject decision (Architecture_Diagrams §5:
    `signoff -> complete: approved` / `signoff -> reviewing: rejected`).
    Approval resumes the suspended pipeline; rejection just re-opens review
    for a human to act on out-of-band (Requirements §5.8.3 — Knewron only
    monitors status changes it doesn't drive Lokalise's internal workflow).
    """
    if approval_status not in ("approved", "rejected"):
        raise ValueError(f"Invalid approval_status '{approval_status}'")

    approval = Approval(
        artifact_id=artifact.artifact_id,
        approved_by=approved_by,
        approval_status=approval_status,
        comments=comments,
        rejection_reason=rejection_reason,
    )
    db.add(approval)
    db.flush()

    state_machine = StateMachine()
    if approval_status == "approved":
        if artifact.status == "reviewing":
            state_machine.transition(artifact, "signoff")
        db.commit()

        from app.tasks.pipeline_tasks import resume_pipeline

        resume_pipeline.delay(str(artifact.artifact_id), reason="approval_granted")
    else:
        if artifact.status == "signoff":
            state_machine.transition(artifact, "reviewing")
        db.commit()

    return approval
