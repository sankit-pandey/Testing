"""Health check + Celery smoke-test endpoint. Stories 0.1, 0.3, 7.3."""
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import async_engine
from app.tasks.sample_task import ping

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 if the API process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict:
    """Readiness probe — checks the DB and Redis dependencies. Story 7.3."""
    checks: dict[str, str] = {}

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(get_settings().redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if response.status_code == 200 else "degraded", "checks": checks}


@router.post("/health/enqueue-sample")
async def enqueue_sample(message: str = "pong") -> dict:
    """Enqueue the sample Celery task; verify execution in Flower (:5555)."""
    result = ping.delay(message)
    return {"task_id": result.id, "status": "queued"}
