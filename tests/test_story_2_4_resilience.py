"""Story 2.4 acceptance: circuit breaker opens after N failures; idempotent
op runs once. Uses `fakeredis` so no live Redis is required for these
pure-logic unit tests.
"""
import fakeredis
import pytest

from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.utils.idempotency import acquire_idempotency_key


@pytest.fixture()
def fake_redis(monkeypatch):
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr("app.utils.circuit_breaker.redis.Redis.from_url", lambda *a, **k: client)
    monkeypatch.setattr("app.utils.idempotency.redis.Redis.from_url", lambda *a, **k: client)
    return client


def test_breaker_opens_after_threshold(fake_redis):
    breaker = CircuitBreaker("test-service", failure_threshold=3, recovery_seconds=60)

    def failing():
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            breaker.call(failing)

    with pytest.raises(CircuitBreakerOpenError):
        breaker.call(failing)


def test_breaker_closes_on_success(fake_redis):
    breaker = CircuitBreaker("test-service-2", failure_threshold=3, recovery_seconds=60)
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker._state() == "closed"


def test_idempotency_key_runs_once(fake_redis):
    first = acquire_idempotency_key("op-123")
    second = acquire_idempotency_key("op-123")
    assert first is True
    assert second is False
