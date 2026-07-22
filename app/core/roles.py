"""User roles — Design ref: `Database_Schema.md` §1; `Requirements_Document.md` §2.2.

Fixed set: `admin`, `localization_manager`, `viewer` (viewer = read-only).
"""
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    LOCALIZATION_MANAGER = "localization_manager"
    VIEWER = "viewer"


WRITE_ROLES = (Role.ADMIN, Role.LOCALIZATION_MANAGER)
ALL_ROLES = (Role.ADMIN, Role.LOCALIZATION_MANAGER, Role.VIEWER)
