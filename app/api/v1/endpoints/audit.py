"""Audit log query/export — Design ref: `Database_Schema.md` §13;
`Requirements_Document.md` §6.4.5 (immutable, exportable, searchable, 1-yr
retention). Story 7.1. Admin-only: audit trail access is a system-management
capability (`Requirements_Document.md` §2.2 — Admin: "System configuration").
"""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.roles import Role
from app.db.session import get_db
from app.models.audit_logs import AuditLog
from app.schemas.audit import AuditLogList, AuditLogRead
from app.utils.pagination import build_pagination_meta

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def _filtered_query(
    user_id: uuid.UUID | None, action: str | None, entity_type: str | None, entity_id: uuid.UUID | None
):
    query = select(AuditLog)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    return query


@router.get("", response_model=AuditLogList)
async def list_audit_logs(
    user_id: uuid.UUID | None = Query(default=None, alias="userId"),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN)),
) -> AuditLogList:
    base_query = _filtered_query(user_id, action, entity_type, entity_id)
    total = (await db.execute(select(func.count()).select_from(base_query.subquery()))).scalar_one()

    query = base_query.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    logs = (await db.execute(query)).scalars().all()

    return AuditLogList(
        logs=[AuditLogRead.model_validate(log) for log in logs],
        pagination=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.get("/export")
async def export_audit_logs(
    user_id: uuid.UUID | None = Query(default=None, alias="userId"),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="entityType"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN)),
) -> Response:
    """CSV export for compliance reporting (Requirements §6.4.5)."""
    query = _filtered_query(user_id, action, entity_type, None).order_by(AuditLog.created_at.desc())
    logs = (await db.execute(query)).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["log_id", "user_id", "action", "entity_type", "entity_id", "ip_address", "created_at"])
    for log in logs:
        writer.writerow(
            [log.log_id, log.user_id, log.action, log.entity_type, log.entity_id, log.ip_address, log.created_at]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_logs_export.csv"'},
    )
