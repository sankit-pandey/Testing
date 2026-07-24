"""Saga / compensation helper — roll back partial orchestration on failure.

Design ref: `LOCKED_Design_v1.0.md` §7 ("Saga / Compensation — Roll back
partial orchestration on failure"); `Architecture_Diagrams.md` §18. Story 2.4.
"""
from collections.abc import Callable

from app.core.logging import get_logger

logger = get_logger(__name__)


class Saga:
    """Accumulates compensating actions as a stage performs side effects;
    `compensate()` runs them in reverse order if the stage subsequently fails.

    Usage:
        saga = Saga()
        lokalise.upload(...)
        saga.add_compensation(lambda: lokalise.cancel_upload(...))
        ...
        try:
            risky_step()
        except Exception:
            saga.compensate()
            raise
    """

    def __init__(self) -> None:
        self._compensations: list[tuple[str, Callable[[], None]]] = []

    def add_compensation(self, action: Callable[[], None], *, description: str = "") -> None:
        self._compensations.append((description, action))

    def compensate(self) -> None:
        for description, action in reversed(self._compensations):
            try:
                action()
            except Exception as exc:  # noqa: BLE001 — best-effort compensation
                logger.error("saga_compensation_failed", step=description, error=str(exc))
        self._compensations.clear()
