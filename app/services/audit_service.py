"""Audit logging service — Design ref: `Database_Schema.md` §13;
`LOCKED_Design_v1.0.md` §12 (all actions logged, 1-year retention, immutable).
Story 7.1.
"""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog


async def record_audit_log(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    changes: dict[str, Any] | None = None,
    tenant_id: uuid.UUID | None = None,
) -> AuditLog:
    """Append an immutable audit record. Never update or delete audit rows.

    `tenant_id` (multi-tenancy extension) is `None` for platform-level
    actions (e.g. a superuser creating a tenant); tenant-scoped callers
    should pass `current_user.tenant_id`.
    """
    log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        changes=changes,
    )
    db.add(log)
    await db.flush()
    return log
