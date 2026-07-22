"""Redis-backed circuit breaker for external service clients.

Design ref: `LOCKED_Design_v1.0.md` §7 ("Circuit Breaker — Protect against
Lokalise / Figma / Whisper / TTS failures"); `Architecture_Diagrams.md` §18.
Story 2.4.

State is kept in Redis (not per-process memory) so all Celery worker threads
(`concurrency=3`) and the API process share one breaker per external service.
"""
import time
from collections.abc import Callable
from typing import TypeVar

import redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised instead of calling the wrapped function while the breaker is open."""


class CircuitBreaker:
    """Per-service circuit breaker: opens after N consecutive failures, then
    fails fast for `recovery_seconds` before allowing one trial (half-open) call.
    """

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int | None = None,
        recovery_seconds: int | None = None,
        redis_client: redis.Redis | None = None,
    ) -> None:
        settings = get_settings()
        self.name = name
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.recovery_seconds = recovery_seconds or settings.circuit_breaker_recovery_seconds
        self._redis = redis_client or redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def _key(self, suffix: str) -> str:
        return f"cb:{self.name}:{suffix}"

    def _state(self) -> str:
        return self._redis.get(self._key("state")) or CLOSED

    def _failures(self) -> int:
        return int(self._redis.get(self._key("failures")) or 0)

    def _record_failure(self) -> None:
        failures = self._redis.incr(self._key("failures"))
        if failures >= self.failure_threshold:
            self._redis.set(self._key("state"), OPEN)
            self._redis.set(self._key("opened_at"), time.time())
            logger.warning("circuit_breaker_opened", breaker=self.name, failures=failures)

    def _record_success(self) -> None:
        self._redis.delete(self._key("failures"))
        self._redis.set(self._key("state"), CLOSED)

    def _can_attempt(self) -> bool:
        state = self._state()
        if state == CLOSED:
            return True
        if state == OPEN:
            opened_at = float(self._redis.get(self._key("opened_at")) or 0)
            if time.time() - opened_at >= self.recovery_seconds:
                self._redis.set(self._key("state"), HALF_OPEN)
                return True
            return False
        return True  # HALF_OPEN — allow one trial call

    def call(self, fn: Callable[[], T]) -> T:
        """Execute `fn()` through the breaker; raises `CircuitBreakerOpenError`
        without calling `fn` while open.
        """
        if not self._can_attempt():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
        try:
            result = fn()
        except Exception:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result
