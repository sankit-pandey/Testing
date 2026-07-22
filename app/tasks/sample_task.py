"""Sample task proving Celery + Redis wiring end-to-end. Story 0.3."""
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sample_task.ping")
def ping(message: str = "pong") -> dict:
    """Trivial task used to verify enqueue → worker execution → Flower visibility."""
    logger.info("sample_task_executed", message=message)
    return {"message": message}
