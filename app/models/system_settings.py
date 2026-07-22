"""`system_settings` — Design ref: `Database_Schema.md` §14.

`tenant_id` is a multi-tenancy extension (see `app/models/tenants.py`):
`NULL` = a platform-wide default (e.g. `.env`-sourced fallback recorded for
visibility); a tenant-scoped row overrides it for that tenant only — used
for per-tenant Lokalise/Figma credentials (`app/services/tenant_service.py`).
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class SystemSetting(Base, TimestampMixin):
    """Application-wide (or per-tenant override) configuration settings."""

    __tablename__ = "system_settings"
    __table_args__ = (
        Index("idx_settings_key", "setting_key"),
        Index("idx_settings_tenant_id", "tenant_id"),
        # Two partial unique indexes (not one plain composite): Postgres
        # treats NULL as distinct in a unique index, so a plain UNIQUE
        # (tenant_id, setting_key) would let multiple *global* (tenant_id
        # NULL) rows share the same key.
        Index(
            "idx_settings_key_global_unique",
            "setting_key",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        ),
        Index(
            "idx_settings_key_tenant_unique",
            "tenant_id",
            "setting_key",
            unique=True,
            postgresql_where=text("tenant_id IS NOT NULL"),
        ),
        {"comment": "Application-wide configuration settings"},
    )

    setting_id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        comment="NULL = platform-wide default; set = per-tenant override",
    )
    setting_key: Mapped[str] = mapped_column(String(100), nullable=False)
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
