"""Redis-backed idempotency keys — safe retries + webhook deduplication.

Design ref: `LOCKED_Design_v1.0.md` §7; `Architecture_Diagrams.md` §3.1, §11,
§17 (webhook idempotency), §6.1 (join-barrier idempotency guard). Story 2.4.
"""
import redis

from app.core.config import get_settings

DEFAULT_TTL_SECONDS = 24 * 60 * 60


def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def acquire_idempotency_key(key: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    """Atomically claim `key`. Returns True the first time (proceed), False if
    already claimed (duplicate — e.g. a re-delivered webhook or a retried task).
    """
    return bool(_client().set(f"idem:{key}", "1", nx=True, ex=ttl_seconds))


def release_idempotency_key(key: str) -> None:
    """Release a claimed key (e.g. to allow a legitimate manual retry)."""
    _client().delete(f"idem:{key}")
