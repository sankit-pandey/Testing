"""Pydantic schemas for `audit_logs` — Design ref: `Database_Schema.md` §13;
`Requirements_Document.md` §6.4.5 (immutable, exportable, searchable). Story 7.1.
"""
import uuid
from datetime import datetime
from typing import Any

from app.schemas.base import CamelModel, PaginationMeta


class AuditLogRead(CamelModel):
    log_id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    ip_address: str | None
    changes: dict[str, Any] | None
    created_at: datetime


class AuditLogList(CamelModel):
    logs: list[AuditLogRead]
    pagination: PaginationMeta
