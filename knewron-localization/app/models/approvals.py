"""`approvals` — Design ref: `Database_Schema.md` §12."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class Approval(Base):
    """Artifact sign-off approvals."""

    __tablename__ = "approvals"
    __table_args__ = (
        Index("idx_approvals_artifact_id", "artifact_id"),
        Index("idx_approvals_approved_by", "approved_by"),
        Index("idx_approvals_status", "approval_status"),
        {"comment": "Artifact sign-off approvals"},
    )

    approval_id: Mapped[uuid.UUID] = uuid_pk()
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_artifacts.artifact_id", ondelete="CASCADE"), nullable=False
    )
    approved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="approved, rejected"
    )
    comments: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
