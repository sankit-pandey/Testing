"""Celery application — broker/result backend on Redis.

Design ref: `LOCKED_Design_v1.0.md` §2, §8 — Celery + Redis, **1 worker,
`concurrency=3`**, plus Celery Beat for polling/cleanup schedules. Story 0.3.

Structured logging + a per-task correlation ID (Story 7.3, mirroring the
API's `CorrelationIdMiddleware`) are wired via Celery signals so worker logs
are traceable the same way request logs are.
"""
import uuid

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_postrun, task_prerun, worker_process_init

from app.core.config import get_settings
from app.core.logging import configure_logging, correlation_id_var

settings = get_settings()


@worker_process_init.connect
def _init_worker_logging(**kwargs: object) -> None:
    configure_logging(settings.log_level)


@task_prerun.connect
def _bind_correlation_id(task_id: str | None = None, **kwargs: object) -> None:
    correlation_id_var.set(task_id or str(uuid.uuid4()))


@task_postrun.connect
def _clear_correlation_id(**kwargs: object) -> None:
    correlation_id_var.set(None)

celery_app = Celery(
    "knewron_localization",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.sample_task",
        "app.tasks.pipeline_tasks",
        "app.tasks.lokalise_tasks",
        "app.tasks.maintenance_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

# Celery Beat schedule — polling fallback (Story 4.2) + cleanup jobs
# (Database_Schema.md maintenance scripts) + audit retention (Story 7.1).
celery_app.conf.beat_schedule = {
    "poll-pending-lokalise-tasks": {
        "task": "app.tasks.lokalise_tasks.poll_pending_lokalise_tasks",
        "schedule": settings.lokalise_poll_interval_minutes * 60.0,
    },
    "cleanup-expired-translation-cache": {
        "task": "app.tasks.maintenance_tasks.cleanup_expired_translation_cache",
        "schedule": crontab(hour=2, minute=0),
    },
    "cleanup-expired-download-urls": {
        "task": "app.tasks.maintenance_tasks.cleanup_expired_download_urls",
        "schedule": crontab(hour=2, minute=15),
    },
    "cleanup-old-audit-logs": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_audit_logs",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),
    },
}
