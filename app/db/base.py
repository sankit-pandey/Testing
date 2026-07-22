"""Declarative base and shared mixins (UUID PK, timestamps).

Design ref: `Database_Schema.md` — every table uses a UUID primary key
(`gen_random_uuid()`), and `created_at`/`updated_at` timestamp columns. Story 0.2.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def uuid_pk() -> Mapped[uuid.UUID]:
    """Return a UUID primary-key column matching `<table>_id UUID PRIMARY KEY
    DEFAULT gen_random_uuid()`. Each model assigns this to its own
    schema-exact PK attribute name (e.g. `user_id`, `project_id`) — no
    generic `id` mixin, so column names match `Database_Schema.md` exactly.
    """
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns, both `DEFAULT CURRENT_TIMESTAMP`."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
