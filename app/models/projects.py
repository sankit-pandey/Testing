"""`projects` — Design ref: `Database_Schema.md` §3.

One project per product per single target language (LOCKED §9).
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.artifacts import ProjectArtifact
    from app.models.products import Product


class Project(Base, TimestampMixin):
    """Localization projects - one per product per target language."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100", name="ck_projects_progress_percent"
        ),
        Index("idx_projects_product_id", "product_id"),
        Index("idx_projects_status", "status"),
        Index("idx_projects_target_language", "target_language"),
        Index("idx_projects_created_by", "created_by"),
        Index(
            "idx_projects_unique",
            "product_id",
            "target_language",
            unique=True,
            postgresql_where=text("status != 'cancelled'"),
        ),
        {"comment": "Localization projects - one per product per target language"},
    )

    project_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_language: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="ISO 639-1 language code"
    )
    target_market: Mapped[str | None] = mapped_column(
        String(10), comment="ISO 3166-1 alpha-2 country code"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        comment="pending, in_progress, partial_complete, complete, cancelled",
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    artifacts: Mapped[list["ProjectArtifact"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    product: Mapped["Product"] = relationship()
