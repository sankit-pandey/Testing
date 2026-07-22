"""`review_findings` — Design ref: `Database_Schema.md` §11."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk
from sqlalchemy import func


class ReviewFinding(Base):
    """AI and human review findings."""

    __tablename__ = "review_findings"
    __table_args__ = (
        Index("idx_findings_artifact_id", "artifact_id"),
        Index("idx_findings_type", "finding_type"),
        Index("idx_findings_severity", "severity"),
        Index("idx_findings_status", "status"),
        Index("idx_findings_reviewed_by", "reviewed_by"),
        {"comment": "AI and human review findings"},
    )

    finding_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE"), nullable=False
    )
    finding_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="ai_review, human_review"
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="critical, major, minor, info"
    )
    category: Mapped[str | None] = mapped_column(
        String(50), comment="completeness, formatting, quality, consistency, accuracy"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[dict | None] = mapped_column(
        JSONB, comment="Page number, image ID, timestamp, etc."
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", server_default="open", comment="open, resolved, ignored"
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
