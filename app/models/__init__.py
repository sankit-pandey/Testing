"""SQLAlchemy ORM models — one module per table in `Design/Database_Schema.md`.

Importing this package registers every model on `Base.metadata`, which Alembic
autogenerate relies on.
"""
from app.models.approvals import Approval
from app.models.artifact_subtasks import ArtifactSubtask
from app.models.artifacts import ProjectArtifact
from app.models.audit_logs import AuditLog
from app.models.figma_images import FigmaImage
from app.models.image_processing import ImageProcessing
from app.models.lokalise_tasks import LokaliseTask
from app.models.products import Product
from app.models.projects import Project
from app.models.review_findings import ReviewFinding
from app.models.stages import ArtifactStage
from app.models.system_settings import SystemSetting
from app.models.translation_cache import TranslationCache
from app.models.users import User

__all__ = [
    "User",
    "Product",
    "Project",
    "ProjectArtifact",
    "ArtifactStage",
    "ArtifactSubtask",
    "ImageProcessing",
    "FigmaImage",
    "TranslationCache",
    "LokaliseTask",
    "ReviewFinding",
    "Approval",
    "AuditLog",
    "SystemSetting",
]
