"""Pydantic schemas for `projects` — Design ref: `Database_Schema.md` §3;
`Technical_Design_Document.md` §4.1.1. Story 1.1.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.artifact import ArtifactSummary
from app.schemas.base import CamelModel, PaginationMeta


class ProjectCreate(CamelModel):
    product_id: uuid.UUID
    project_name: str = Field(max_length=255)
    target_language: str = Field(max_length=10, description="ISO 639-1 code, e.g. 'de'")
    target_market: str | None = Field(default=None, max_length=10, description="ISO 3166-1 alpha-2")
    source_language: str | None = Field(
        default=None,
        max_length=10,
        description=(
            "Not a persisted `projects` column per Database_Schema.md (higher authority than "
            "Technical_Design_Document's example payload); stored in `metadata.source_language`."
        ),
    )


class ProjectCreateResponse(CamelModel):
    project_id: uuid.UUID
    status: str
    created_at: datetime


class ProjectRead(CamelModel):
    project_id: uuid.UUID
    product_id: uuid.UUID
    project_name: str
    target_language: str
    target_market: str | None
    status: str
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    metadata: dict[str, Any]

    @classmethod
    def from_orm_model(cls, project: Any) -> "ProjectRead":
        return cls(
            project_id=project.project_id,
            product_id=project.product_id,
            project_name=project.project_name,
            target_language=project.target_language,
            target_market=project.target_market,
            status=project.status,
            progress_percent=project.progress_percent,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
            metadata=project.metadata_,
        )


class ProjectDetail(ProjectRead):
    artifacts: list[ArtifactSummary] = Field(default_factory=list)


class ProjectList(CamelModel):
    projects: list[ProjectRead]
    pagination: PaginationMeta
