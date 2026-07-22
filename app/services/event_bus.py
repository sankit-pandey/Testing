"""Redis Pub/Sub event bus — pipeline progress → WebSocket.

Design ref: `LOCKED_Design_v1.0.md` §2; `Architecture_Diagrams.md` §3.1, §10;
`Technical_Design_Document.md` §4.2. Story 3.1.

Event types (Technical_Design §4.2): `stage_started`, `stage_progress`,
`stage_completed`, `stage_failed`, `subtask_progress`, `review_required`,
`download_ready`.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis
import redis.asyncio as aioredis

from app.core.config import get_settings

EVENT_TYPES = (
    "stage_started",
    "stage_progress",
    "stage_completed",
    "stage_failed",
    "subtask_progress",
    "review_required",
    "download_ready",
)


def _channel(artifact_id: uuid.UUID | str) -> str:
    return f"artifact:{artifact_id}:events"


def publish_event(
    artifact_id: uuid.UUID | str,
    event: str,
    *,
    stage: str | None = None,
    progress_percent: int | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Publish a pipeline event (sync — called from the Celery worker)."""
    if event not in EVENT_TYPES:
        raise ValueError(f"Unknown event type '{event}'; expected one of {EVENT_TYPES}")

    payload = {
        "event": event,
        "artifactId": str(artifact_id),
        "stage": stage,
        "progressPercent": progress_percent,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    client.publish(_channel(artifact_id), json.dumps(payload))


class ArtifactEventSubscriber:
    """Async subscriber used by the WebSocket endpoint to forward one
    artifact's events to a connected client.
    """

    def __init__(self, artifact_id: uuid.UUID | str) -> None:
        self.artifact_id = artifact_id
        self._redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()

    async def __aenter__(self) -> "ArtifactEventSubscriber":
        await self._pubsub.subscribe(_channel(self.artifact_id))
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._pubsub.unsubscribe(_channel(self.artifact_id))
        await self._pubsub.aclose()
        await self._redis.aclose()

    async def listen(self):
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
