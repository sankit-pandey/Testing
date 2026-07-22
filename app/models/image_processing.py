"""`image_processing` — Design ref: `Database_Schema.md` §7."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class ImageProcessing(Base, TimestampMixin):
    """Individual image processing tracking."""

    __tablename__ = "image_processing"
    __table_args__ = (
        Index("idx_image_proc_artifact_id", "artifact_id"),
        Index("idx_image_proc_hash", "image_hash"),
        Index("idx_image_proc_status", "status"),
        Index("idx_image_proc_classification", "classification"),
        Index("idx_image_proc_chromadb_match", "chromadb_match_id"),
        {"comment": "Individual image processing tracking"},
    )

    processing_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Internal image identifier"
    )
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="SHA-256 hash")
    image_path: Mapped[str | None] = mapped_column(String(500), comment="Original image path")
    image_position: Mapped[dict | None] = mapped_column(
        JSONB, comment="Position in document (page, coordinates)"
    )
    classification: Mapped[str | None] = mapped_column(
        String(50), comment="AI classification: ui_screenshot, diagram, photo, chart, other"
    )
    classification_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    chromadb_match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), comment="ChromaDB match identifier"
    )
    chromadb_similarity: Mapped[float | None] = mapped_column(Numeric(5, 4))
    figma_frame_id: Mapped[str | None] = mapped_column(String(255))
    figma_file_key: Mapped[str | None] = mapped_column(String(255))
    lokalise_task_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        comment="pending, classified, matched, translating, translated, cached, manual, failed",
    )
    translated_image_path: Mapped[str | None] = mapped_column(
        String(500), comment="Path to translated image"
    )
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    requires_manual_translation: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
