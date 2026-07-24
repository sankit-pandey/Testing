"""Review findings persistence — Design ref: `Database_Schema.md` §11
(`review_findings`); `Requirements_Document.md` §4-5. Story 6.1.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review_findings import ReviewFinding
from app.services.ai_reviewer import Finding

BLOCKING_SEVERITIES = ("critical", "major")


def persist_findings(
    db: Session, artifact_id: uuid.UUID, findings: list[Finding], *, finding_type: str = "ai_review"
) -> bool:
    """Write findings (immutable creation; resolution handled separately by
    Story 6.2). Returns True if any finding is blocking (critical/major) —
    the caller should route the artifact to `needs_human_review`.
    """
    for finding in findings:
        db.add(
            ReviewFinding(
                artifact_id=artifact_id,
                finding_type=finding_type,
                severity=finding.severity,
                category=finding.category,
                description=finding.description,
                location=finding.location,
            )
        )
    db.flush()
    return any(f.severity in BLOCKING_SEVERITIES for f in findings)


def list_open_findings(db: Session, artifact_id: uuid.UUID) -> list[ReviewFinding]:
    return list(
        db.execute(
            select(ReviewFinding).where(
                ReviewFinding.artifact_id == artifact_id, ReviewFinding.status == "open"
            )
        )
        .scalars()
        .all()
    )


def has_open_blocking_findings(db: Session, artifact_id: uuid.UUID) -> bool:
    return any(f.severity in BLOCKING_SEVERITIES for f in list_open_findings(db, artifact_id))


def has_findings(db: Session, artifact_id: uuid.UUID) -> bool:
    """Whether any finding (of any status) was ever persisted for this
    artifact — used by the IFU/UI Resource `review()` stage to tell a fresh
    AI-review pass apart from a resume after `needs_human_review` (suspension
    only ever happens once findings exist, so this is an unambiguous signal).
    """
    return (
        db.execute(select(ReviewFinding.finding_id).where(ReviewFinding.artifact_id == artifact_id).limit(1))
        .first()
        is not None
    )


def resolve_finding(
    db: Session, finding: ReviewFinding, resolved_by: uuid.UUID, *, status: str = "resolved"
) -> ReviewFinding:
    from datetime import datetime, timezone

    finding.status = status
    finding.resolved_by = resolved_by
    finding.resolved_at = datetime.now(timezone.utc)
    db.flush()
    return finding
