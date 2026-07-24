"""Pydantic schemas for `project_artifacts` — Design ref: `Database_Schema.md`
§4; `Technical_Design_Document.md` §4.1.1, §4.1.2. Stories 1.2, 6.3.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel, PaginationMeta

ARTIFACT_TYPES = ("IFU", "UI_RESOURCE")  # VIDEO is design-locked but out of scope (deferred)


class ArtifactCreate(CamelModel):
    artifact_type: str = Field(description="IFU | UI_RESOURCE")
    artifact_name: str = Field(max_length=255)
    source_filename: str | None = Field(default=None, max_length=255)


class ArtifactCreateResponse(CamelModel):
    artifact_id: uuid.UUID
    status: str
    created_at: datetime
    upload_url: str
    upload_fields: dict[str, str] = Field(default_factory=dict)


class ArtifactSummary(CamelModel):
    """Nested summary used inside `GET /projects/{id}` (Technical_Design §4.1.1)."""

    artifact_id: uuid.UUID
    artifact_type: str
    artifact_name: str
    status: str
    progress_percent: int


class StageSummary(CamelModel):
    stage: str
    status: str


class ArtifactRead(CamelModel):
    artifact_id: uuid.UUID
    project_id: uuid.UUID
    artifact_type: str
    artifact_name: str
    source_filename: str | None
    status: str
    progress_percent: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    metadata: dict[str, Any]

    @classmethod
    def from_orm_model(cls, artifact: Any) -> "ArtifactRead":
        return cls(
            artifact_id=artifact.artifact_id,
            project_id=artifact.project_id,
            artifact_type=artifact.artifact_type,
            artifact_name=artifact.artifact_name,
            source_filename=artifact.source_filename,
            status=artifact.status,
            progress_percent=artifact.progress_percent,
            error_message=artifact.error_message,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            started_at=artifact.started_at,
            completed_at=artifact.completed_at,
            metadata=artifact.metadata_,
        )


class ArtifactDetail(ArtifactRead):
    stages: list[StageSummary] = Field(default_factory=list)


class ArtifactCancelResponse(CamelModel):
    artifact_id: uuid.UUID
    status: str
    cancelled_at: datetime
