"""Scheduled cleanup jobs — Design ref: `Database_Schema.md` "Maintenance
Scripts" section; `LOCKED_Design_v1.0.md` §12 (1-year audit retention,
30-day default app log retention). Story 7.1 / Celery Beat (Story 0.3).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.artifacts import ProjectArtifact
from app.models.audit_logs import AuditLog
from app.models.translation_cache import TranslationCache
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_expired_translation_cache")
def cleanup_expired_translation_cache() -> int:
    """`DELETE FROM translation_cache WHERE expires_at < now()` — run daily."""
    with _sync_session() as db:
        result = db.execute(
            delete(TranslationCache).where(TranslationCache.expires_at < datetime.now(timezone.utc))
        )
        db.commit()
        deleted = result.rowcount or 0
    logger.info("cleanup_expired_translation_cache", deleted=deleted)
    return deleted


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_expired_download_urls")
def cleanup_expired_download_urls() -> int:
    """Clear expired presigned download URLs on `project_artifacts` — run daily."""
    with _sync_session() as db:
        result = db.execute(
            update(ProjectArtifact)
            .where(ProjectArtifact.download_url_expires_at < datetime.now(timezone.utc))
            .values(download_url=None, download_url_expires_at=None)
        )
        db.commit()
        updated = result.rowcount or 0
    logger.info("cleanup_expired_download_urls", updated=updated)
    return updated


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_old_audit_logs")
def cleanup_old_audit_logs() -> int:
    """`DELETE FROM audit_logs WHERE created_at < now() - retention` — run monthly."""
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_log_retention_days)
    with _sync_session() as db:
        result = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        db.commit()
        deleted = result.rowcount or 0
    logger.info("cleanup_old_audit_logs", deleted=deleted, retention_days=settings.audit_log_retention_days)
    return deleted


def _sync_session():
    from app.db.session import SessionLocal

    return SessionLocal()
