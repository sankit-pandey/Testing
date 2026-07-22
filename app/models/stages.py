"""`artifact_stages` — Design ref: `Database_Schema.md` §5."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class ArtifactStage(Base, TimestampMixin):
    """Pipeline stages for each artifact."""

    __tablename__ = "artifact_stages"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_artifact_stages_progress_percent",
        ),
        Index("idx_stages_artifact_id", "artifact_id"),
        Index("idx_stages_status", "status"),
        Index("idx_stages_name", "stage_name"),
        Index("idx_stages_unique", "artifact_id", "stage_name", unique=True),
        {"comment": "Pipeline stages for each artifact"},
    )

    stage_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE"), nullable=False
    )
    stage_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="process, orchestrate, assemble, review, signoff, download",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        comment="pending, in_progress, complete, failed, skipped",
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", comment="Stage-specific data and results"
    )
