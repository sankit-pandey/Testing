"""Celery Beat polling fallback for Lokalise task completion.

Design ref: `LOCKED_Design_v1.0.md` §7 (webhook + 15-min polling hybrid);
`Architecture_Diagrams.md` §11, §17; `Database_Schema.md` (lokalise_tasks).
Story 4.2. (Placeholder here; full body added alongside the Lokalise
service client in Story 4.2 below.)
"""
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.lokalise_tasks.poll_pending_lokalise_tasks")
def poll_pending_lokalise_tasks() -> dict:
    """Poll every `lokalise_tasks` row still pending/uploaded/translating; resume
    the pipeline for any that have completed. Runs every
    `LOKALISE_POLL_INTERVAL_MINUTES` via Celery Beat.
    """
    from app.services.lokalise_service import poll_and_resume_pending_tasks

    return poll_and_resume_pending_tasks()
