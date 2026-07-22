"""`lokalise_tasks` — Design ref: `Database_Schema.md` §10."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class LokaliseTask(Base, TimestampMixin):
    """Tracks Lokalise translation tasks."""

    __tablename__ = "lokalise_tasks"
    __table_args__ = (
        Index("idx_lokalise_artifact_id", "artifact_id"),
        Index("idx_lokalise_subtask_id", "subtask_id"),
        Index("idx_lokalise_status", "status"),
        Index("idx_lokalise_external_id", "lokalise_task_external_id"),
        {"comment": "Tracks Lokalise translation tasks"},
    )

    lokalise_task_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE")
    )
    subtask_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("artifact_subtasks.subtask_id", ondelete="CASCADE")
    )
    lokalise_project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    lokalise_task_external_id: Mapped[str | None] = mapped_column(
        String(255), comment="Lokalise's task ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="document, subtitles, transcript, ui_strings, image_text"
    )
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        comment="pending, uploaded, translating, reviewing, completed, failed",
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    download_url: Mapped[str | None] = mapped_column(String(1000))
    webhook_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    polling_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="Number of times status was polled"
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
