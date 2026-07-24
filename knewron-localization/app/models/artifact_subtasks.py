"""`artifact_subtasks` — Design ref: `Database_Schema.md` §6.

Sub-tasks within orchestration stage (parallel processing); doubles as the
DB-backed join barrier for Story 2.5.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class ArtifactSubtask(Base, TimestampMixin):
    """Sub-tasks within orchestration (parallel processing)."""

    __tablename__ = "artifact_subtasks"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_artifact_subtasks_progress_percent",
        ),
        Index("idx_subtasks_artifact_id", "artifact_id"),
        Index("idx_subtasks_parent_stage", "parent_stage_id"),
        Index("idx_subtasks_status", "status"),
        Index("idx_subtasks_type", "task_type"),
        {"comment": "Sub-tasks within orchestration (parallel processing)"},
    )

    subtask_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE"), nullable=False
    )
    parent_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifact_stages.stage_id", ondelete="CASCADE")
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="image_pipeline, audio_pipeline, subtitle_pipeline, document_lokalise, assembly",
    )
    task_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        comment="pending, in_progress, complete, failed",
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    result: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}", comment="Task execution results"
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
