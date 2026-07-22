"""`users` — Design ref: `Database_Schema.md` §1.

`tenant_id`/`is_superuser` are a multi-tenancy extension (user-directed,
beyond the original locked schema — see `app/models/tenants.py`). Email
uniqueness is scoped per-tenant (composite index) rather than global, since
different customer tenants may independently provision a user with the same
email; `sso_id` remains globally unique (single shared IdP integration
point per `Requirements_Document.md` §6.4.1).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class User(Base, TimestampMixin):
    """User accounts integrated with DeepHealth SSO."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_email_tenant_unique", "tenant_id", "email", unique=True),
        Index("idx_users_sso_id", "sso_id"),
        Index("idx_users_role", "role"),
        Index("idx_users_tenant_id", "tenant_id"),
        {"comment": "User accounts integrated with DeepHealth SSO"},
    )

    user_id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        comment="NULL only for platform superusers with no home tenant",
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="User role: admin, localization_manager, viewer"
    )
    sso_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="Platform-level superuser (manages tenants); orthogonal to `role`",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Additional user preferences and settings",
    )
