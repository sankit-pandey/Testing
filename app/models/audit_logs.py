"""`audit_logs` — Design ref: `Database_Schema.md` §13.

`tenant_id` is a multi-tenancy extension (see `app/models/tenants.py`);
nullable because platform-level actions (e.g. a superuser creating a tenant)
have no tenant.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk


class AuditLog(Base):
    """Comprehensive audit trail for all user and system actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_tenant_id", "tenant_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_entity_type", "entity_type"),
        Index("idx_audit_entity_id", "entity_id"),
        Index("idx_audit_created_at", "created_at"),
        {"comment": "Comprehensive audit trail for all user and system actions"},
    )

    log_id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.tenant_id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="create_project, upload_artifact, approve, reject, etc."
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), comment="project, artifact, user, etc.")
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(
        JSONB, comment="Before/after values for update operations"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
