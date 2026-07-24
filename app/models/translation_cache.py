"""`translation_cache` — Design ref: `Database_Schema.md` §9."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class TranslationCache(Base):
    """Cache of translated images for reuse across projects."""

    __tablename__ = "translation_cache"
    __table_args__ = (
        Index("idx_cache_source_hash", "source_image_hash"),
        Index("idx_cache_target_lang", "target_language"),
        Index("idx_cache_figma_frame", "figma_frame_id"),
        Index("idx_cache_expires_at", "expires_at"),
        Index("idx_cache_unique", "source_image_hash", "target_language", unique=True),
        {"comment": "Cache of translated images for reuse across projects"},
    )

    cache_id: Mapped[uuid.UUID] = uuid_pk()
    source_image_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    figma_frame_id: Mapped[str | None] = mapped_column(String(255))
    translated_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    translation_quality_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="Number of times this cached translation was reused"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
