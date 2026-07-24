"""`system_settings` — Design ref: `Database_Schema.md` §14."""
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class SystemSetting(Base, TimestampMixin):
    """Application-wide configuration settings."""

    __tablename__ = "system_settings"
    __table_args__ = (
        Index("idx_settings_key", "setting_key"),
        {"comment": "Application-wide configuration settings"},
    )

    setting_id: Mapped[uuid.UUID] = uuid_pk()
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    setting_type: Mapped[str] = mapped_column(
        String(20),
        default="string",
        server_default="string",
        comment="string, number, boolean, json",
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", comment="Whether value is encrypted (e.g., API keys)"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
