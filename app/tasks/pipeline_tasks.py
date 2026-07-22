"""Celery entrypoint for running an artifact's pipeline.

Design ref: `Technical_Design_Document.md` §2.1.1 (`execute_pipeline.delay`);
`LOCKED_Design_v1.0.md` §3. Story 1.2 wires the enqueue call; the executor
body is completed in Story 2.1.
"""
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.pipeline_tasks.execute_pipeline", bind=True, max_retries=3)
def execute_pipeline(self, artifact_id: str) -> dict:
    """Run the universal pipeline (process→orchestrate→assemble→review→signoff→download)
    for the given artifact, using the strategy selected by its `artifact_type`.
    """
    from app.pipeline.executor import run_pipeline_sync

    logger.info("execute_pipeline_started", artifact_id=artifact_id)
    try:
        result = run_pipeline_sync(artifact_id)
    except Exception as exc:  # noqa: BLE001 — retried via Celery, then surfaced as failed
        logger.error("execute_pipeline_failed", artifact_id=artifact_id, error=str(exc))
        raise
    logger.info("execute_pipeline_finished", artifact_id=artifact_id, result=result)
    return result


@celery_app.task(name="app.tasks.pipeline_tasks.resume_pipeline")
def resume_pipeline(artifact_id: str, reason: str = "external_completion") -> dict:
    """Resume a suspended pipeline (e.g. after a join-barrier trip or webhook). Story 2.5."""
    from app.pipeline.executor import run_pipeline_sync

    logger.info("resume_pipeline", artifact_id=artifact_id, reason=reason)
    return run_pipeline_sync(artifact_id)
