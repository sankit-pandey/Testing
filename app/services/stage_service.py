"""Business logic for `artifact_stages` — Design ref: `Database_Schema.md`
§5; `Architecture_Diagrams.md` §5. Story 2.2.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stages import ArtifactStage
from app.pipeline.constants import STAGE_ORDER


async def list_stages(db: AsyncSession, artifact_id: uuid.UUID) -> list[ArtifactStage]:
    query = (
        select(ArtifactStage)
        .where(ArtifactStage.artifact_id == artifact_id)
        .order_by(ArtifactStage.created_at.asc())
    )
    stages = list((await db.execute(query)).scalars().all())
    stages.sort(key=lambda s: STAGE_ORDER.index(s.stage_name) if s.stage_name in STAGE_ORDER else 99)
    return stages


async def get_or_create_stage(
    db: AsyncSession, artifact_id: uuid.UUID, stage_name: str
) -> ArtifactStage:
    query = select(ArtifactStage).where(
        ArtifactStage.artifact_id == artifact_id, ArtifactStage.stage_name == stage_name
    )
    stage = (await db.execute(query)).scalar_one_or_none()
    if stage is None:
        stage = ArtifactStage(artifact_id=artifact_id, stage_name=stage_name)
        db.add(stage)
        await db.flush()
    return stage


async def start_stage(db: AsyncSession, stage: ArtifactStage) -> ArtifactStage:
    stage.status = "in_progress"
    stage.started_at = datetime.now(timezone.utc)
    await db.flush()
    return stage


async def complete_stage(
    db: AsyncSession, stage: ArtifactStage, *, progress_percent: int = 100
) -> ArtifactStage:
    stage.status = "complete"
    stage.progress_percent = progress_percent
    stage.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return stage


async def fail_stage(db: AsyncSession, stage: ArtifactStage, error_message: str) -> ArtifactStage:
    stage.status = "failed"
    stage.error_message = error_message
    stage.retry_count += 1
    await db.flush()
    return stage
