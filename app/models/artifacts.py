"""`project_artifacts` — Design ref: `Database_Schema.md` §4."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.projects import Project


class ProjectArtifact(Base, TimestampMixin):
    """Artifacts to be localized within a project."""

    __tablename__ = "project_artifacts"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_project_artifacts_progress_percent",
        ),
        Index("idx_artifacts_project_id", "project_id"),
        Index("idx_artifacts_type", "artifact_type"),
        Index("idx_artifacts_status", "status"),
        Index("idx_artifacts_created_at", "created_at"),
        {"comment": "Artifacts to be localized within a project"},
    )

    artifact_id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="IFU, VIDEO, UI_RESOURCE"
    )
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(500), comment="S3/GCS path to source file")
    source_filename: Mapped[str | None] = mapped_column(String(255))
    source_file_size: Mapped[int | None] = mapped_column(BigInteger, comment="bytes")
    source_file_hash: Mapped[str | None] = mapped_column(String(64), comment="SHA-256 hash")
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        comment="pending, processing, in_progress, complete, failed, cancelled",
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_path: Mapped[str | None] = mapped_column(String(500), comment="S3/GCS path to localized file")
    download_url: Mapped[str | None] = mapped_column(String(1000), comment="Presigned URL for download")
    download_url_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Artifact-specific data (e.g., page count, duration, etc.)",
    )

    project: Mapped["Project"] = relationship(back_populates="artifacts")
