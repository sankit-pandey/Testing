"""Retry-with-exponential-backoff helpers.

Design ref: `Technical_Design_Document.md` §5.1 (Lokalise: "retry 3 times with
exponential backoff"); §5.2 / `Requirements_Document.md` §4.7.2 (Figma: 3-5
retries, recommend 5). Story 2.4.
"""
from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

T = TypeVar("T")

LOKALISE_MAX_ATTEMPTS = 3
FIGMA_MAX_ATTEMPTS = 5


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call `fn()` with exponential backoff, retrying on `exceptions`."""

    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )
    def _call() -> T:
        return fn()

    return _call()
