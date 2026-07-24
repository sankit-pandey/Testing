"""Business logic for `project_artifacts` — Design ref: `Database_Schema.md`
§4; `LOCKED_Design_v1.0.md` §4; `Requirements_Document.md` §2.2. Story 1.2.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifacts import ProjectArtifact
from app.schemas.artifact import ARTIFACT_TYPES, ArtifactCreate
from app.services.storage_service import StorageService


class InvalidArtifactTypeError(Exception):
    """Raised for an `artifact_type` outside the currently implemented set."""


class ArtifactNotStartableError(Exception):
    """Raised when `/start` is called on an artifact not in `pending` status."""


async def create_artifact(
    db: AsyncSession, project_id: uuid.UUID, body: ArtifactCreate
) -> tuple[ProjectArtifact, str]:
    if body.artifact_type not in ARTIFACT_TYPES:
        raise InvalidArtifactTypeError(
            f"artifact_type must be one of {ARTIFACT_TYPES} "
            "(VIDEO is design-locked but deferred — out of scope for this phase)"
        )

    artifact = ProjectArtifact(
        project_id=project_id,
        artifact_type=body.artifact_type,
        artifact_name=body.artifact_name,
        source_filename=body.source_filename,
    )
    db.add(artifact)
    await db.flush()

    storage = StorageService()
    filename = body.source_filename or body.artifact_name
    key = storage.new_source_key(project_id, artifact.artifact_id, filename)
    artifact.source_path = key
    upload_url = storage.presign_upload(key, storage.guess_content_type(filename))
    await db.flush()

    return artifact, upload_url


async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> ProjectArtifact | None:
    return await db.get(ProjectArtifact, artifact_id)


async def list_artifacts_for_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[ProjectArtifact]:
    query = select(ProjectArtifact).where(ProjectArtifact.project_id == project_id)
    return list((await db.execute(query)).scalars().all())


async def start_artifact(db: AsyncSession, artifact: ProjectArtifact) -> ProjectArtifact:
    if artifact.status != "pending":
        raise ArtifactNotStartableError(
            f"Artifact {artifact.artifact_id} is '{artifact.status}', not 'pending'"
        )
    artifact.status = "processing"
    artifact.started_at = datetime.now(timezone.utc)
    await db.flush()
    return artifact


async def cancel_artifact(db: AsyncSession, artifact: ProjectArtifact) -> ProjectArtifact:
    artifact.status = "cancelled"
    await db.flush()
    return artifact
