"""Pydantic schemas for review findings & approvals — Design ref:
`Database_Schema.md` §11, §12. Stories 6.1, 6.2.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class FindingRead(CamelModel):
    finding_id: uuid.UUID
    artifact_id: uuid.UUID
    finding_type: str
    severity: str
    category: str | None
    description: str
    location: dict[str, Any] | None
    status: str
    created_at: datetime
    resolved_at: datetime | None


class FindingResolveRequest(CamelModel):
    status: str = Field(default="resolved", description="resolved | ignored")


class ApprovalRequest(CamelModel):
    comments: str | None = None


class RejectionRequest(CamelModel):
    rejection_reason: str


class ApprovalRead(CamelModel):
    approval_id: uuid.UUID
    artifact_id: uuid.UUID
    approved_by: uuid.UUID
    approval_status: str
    comments: str | None
    rejection_reason: str | None
    created_at: datetime
