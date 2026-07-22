"""Sync persistence helpers for the pipeline executor (runs inside Celery
workers, which are synchronous — see `app/db/session.py`'s sync engine).

Design ref: `Database_Schema.md` §5, §6 (`artifact_stages`, `artifact_subtasks`).
Stories 2.2, 2.3, 2.5.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact_subtasks import ArtifactSubtask
from app.models.artifacts import ProjectArtifact
from app.models.projects import Project
from app.models.stages import ArtifactStage
from app.pipeline.constants import STAGE_ORDER


def get_or_create_stage(db: Session, artifact_id: uuid.UUID, stage_name: str) -> ArtifactStage:
    stage = db.execute(
        select(ArtifactStage).where(
            ArtifactStage.artifact_id == artifact_id, ArtifactStage.stage_name == stage_name
        )
    ).scalar_one_or_none()
    if stage is None:
        stage = ArtifactStage(artifact_id=artifact_id, stage_name=stage_name)
        db.add(stage)
        db.flush()
    return stage


def start_stage(db: Session, stage: ArtifactStage) -> ArtifactStage:
    stage.status = "in_progress"
    stage.started_at = datetime.now(timezone.utc)
    db.flush()
    return stage


def complete_stage(db: Session, stage: ArtifactStage, *, progress_percent: int = 100) -> ArtifactStage:
    stage.status = "complete"
    stage.progress_percent = progress_percent
    stage.completed_at = datetime.now(timezone.utc)
    db.flush()
    return stage


def fail_stage(db: Session, stage: ArtifactStage, error_message: str) -> ArtifactStage:
    stage.status = "failed"
    stage.error_message = error_message[:2000]
    stage.retry_count += 1
    db.flush()
    return stage


def skip_stage(db: Session, stage: ArtifactStage) -> ArtifactStage:
    stage.status = "skipped"
    stage.completed_at = datetime.now(timezone.utc)
    db.flush()
    return stage


def get_completed_stage_names(db: Session, artifact_id: uuid.UUID) -> set[str]:
    rows = db.execute(
        select(ArtifactStage.stage_name).where(
            ArtifactStage.artifact_id == artifact_id, ArtifactStage.status == "complete"
        )
    ).all()
    return {r[0] for r in rows}


def get_resume_stage(db: Session, artifact_id: uuid.UUID) -> str:
    """Checkpointing (LOCKED §7): resume from the first stage not yet
    `complete`, rather than restarting from `process`. Story 2.3.
    """
    completed = get_completed_stage_names(db, artifact_id)
    for stage_name in STAGE_ORDER:
        if stage_name not in completed:
            return stage_name
    return STAGE_ORDER[-1]


def create_subtasks(
    db: Session,
    artifact_id: uuid.UUID,
    parent_stage_id: uuid.UUID,
    task_types: list[str],
) -> list[ArtifactSubtask]:
    subtasks = [
        ArtifactSubtask(
            artifact_id=artifact_id,
            parent_stage_id=parent_stage_id,
            task_type=task_type,
            task_name=task_type,
        )
        for task_type in task_types
    ]
    db.add_all(subtasks)
    db.flush()
    return subtasks


def get_artifact(db: Session, artifact_id: uuid.UUID) -> ProjectArtifact | None:
    return db.get(ProjectArtifact, artifact_id)


def recompute_project_status_sync(db: Session, project_id: uuid.UUID) -> Project | None:
    """Sync counterpart of `app.services.project_service.recompute_project_status`
    (that module is async, for the API; the pipeline executor is sync). Derives
    project status from its artifacts (Architecture_Diagrams §5). Story 6.3.
    """
    project = db.get(Project, project_id)
    if project is None:
        return None

    artifacts = (
        db.execute(select(ProjectArtifact).where(ProjectArtifact.project_id == project_id))
        .scalars()
        .all()
    )
    if not artifacts:
        return project

    statuses = {a.status for a in artifacts}
    if statuses == {"cancelled"}:
        project.status = "cancelled"
    elif statuses <= {"complete", "cancelled"}:
        project.status = "complete"
    elif "complete" in statuses and statuses - {"complete"}:
        project.status = "partial_complete"
    elif statuses == {"pending"}:
        project.status = "pending"
    else:
        project.status = "in_progress"

    project.progress_percent = round(sum(a.progress_percent for a in artifacts) / len(artifacts))
    if project.status == "complete" and project.completed_at is None:
        project.completed_at = datetime.now(timezone.utc)

    db.flush()
    return project
