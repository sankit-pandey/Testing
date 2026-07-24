"""`figma_images` — Design ref: `Database_Schema.md` §8; `Figma_Integration.md` §9."""
import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class FigmaImage(Base, TimestampMixin):
    """Figma image metadata for ChromaDB matching and reuse."""

    __tablename__ = "figma_images"
    __table_args__ = (
        Index("idx_figma_images_product_id", "product_id"),
        Index("idx_figma_images_file_key", "figma_file_key"),
        Index("idx_figma_images_frame_id", "figma_frame_id"),
        Index("idx_figma_images_hash", "image_hash"),
        Index("idx_figma_images_chromadb", "chromadb_id"),
        Index("idx_figma_images_unique", "figma_file_key", "figma_frame_id", unique=True),
        {"comment": "Figma image metadata for ChromaDB matching and reuse"},
    )

    figma_image_id: Mapped[uuid.UUID] = uuid_pk()
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.product_id", ondelete="CASCADE")
    )
    figma_file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    figma_frame_id: Mapped[str] = mapped_column(String(255), nullable=False)
    frame_name: Mapped[str | None] = mapped_column(String(255))
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="SHA-256 hash of original image")
    chromadb_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), comment="ChromaDB vector ID"
    )
    text_elements: Mapped[dict | None] = mapped_column(
        JSONB, comment="Extracted text nodes from Figma frame"
    )
    variable_mapping: Mapped[dict | None] = mapped_column(
        JSONB, comment="Figma variable IDs mapped to text elements"
    )
    original_language: Mapped[str | None] = mapped_column(String(10), comment="Source language")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
