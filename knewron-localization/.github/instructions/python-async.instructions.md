---
applyTo: "**/*.py"
description: Production-grade async Python conventions for the AI Localization Platform.
---

# Production-grade async Python

Applies on top of `.github/copilot-instructions.md` and
`python-code.instructions.md`. This codebase deliberately runs **two**
concurrency models side by side — know which one you're in before writing a
line of async code:

- **FastAPI request path** — `async def`, `AsyncSession` (SQLAlchemy asyncio),
  runs on the event loop. Optimizes for I/O concurrency across many
  concurrent requests.
- **Celery worker (pipeline execution)** — plain **sync** `def`, `Session`
  (SQLAlchemy sync engine). Celery tasks are not coroutines; there is no
  event loop inside a worker process. See `app/pipeline/executor.py`,
  `app/pipeline/persistence.py`, every `app/services/*` client used from
  strategies (`LokaliseService`, `FigmaService`, `ChromaDBService`).

**Never mix them.** Do not `await` inside a Celery task; do not call a
blocking sync client from inside an `async def` route without offloading it.

## Rule 1 — Never block the event loop

Inside any `async def` (routes, dependencies, WebSocket handlers):
- Never call blocking I/O directly: `requests`, `psycopg2`, `time.sleep`,
  `open()/read()` on a real filesystem, `boto3` client calls, `smtplib`.
- If you must call sync/blocking code from an async context, offload it:
  `await asyncio.to_thread(blocking_fn, *args)`. This codebase already does
  this at every async/sync boundary — e.g. `app/api/v1/endpoints/artifacts.py`
  (`storage.get_bytes` via `asyncio.to_thread`), `app/api/v1/endpoints/webhooks.py`
  (`_process_completion`), `app/api/v1/endpoints/reviews.py`
  (`_submit_approval_sync`). Follow that exact pattern for new sync-service
  calls from routes.
- `httpx` calls from async code must use `httpx.AsyncClient`, not `httpx.Client`.
  (Sync service clients used by Celery tasks correctly use `httpx.Client` —
  don't "fix" that; it's the correct choice for a sync worker.)

## Rule 2 — Never mix AsyncSession and Session on the same code path

- A function taking `db: AsyncSession` must stay async end-to-end (`await
  db.execute(...)`, `await db.commit()`, `await db.get(...)`).
- A function taking `db: Session` (from `app/db/session.py`'s sync
  `SessionLocal`) must stay sync end-to-end. This is every pipeline/strategy/
  service function reachable from `app/pipeline/executor.py`.
- If a Celery task needs to trigger something the API layer owns (or vice
  versa), cross the boundary with a **new session of the right kind**, not by
  passing one session across an async/sync call. See `_dispatch_completion`
  in `app/services/lokalise_service.py` for the pattern: sync all the way
  through, opening `SessionLocal()` fresh where needed.

## Rule 3 — Structured concurrency, not fire-and-forget

- Don't launch untracked background work with `asyncio.create_task(...)` and
  drop the reference — a silently-dying task is invisible. If you need
  concurrent async work with a lifetime tied to a request/connection (e.g.
  the WebSocket per-artifact subscriptions in
  `app/api/v1/endpoints/websocket.py`), keep the task handles, and cancel them
  explicitly on teardown (`finally: for task in subscriptions.values():
  task.cancel()`).
- Prefer `asyncio.gather(*coros)` (or `asyncio.TaskGroup` on 3.11+) over
  manual task bookkeeping when you need "run N things concurrently, wait for
  all". Always decide up front whether one failure should cancel the rest
  (`gather(..., return_exceptions=True)` vs. propagate).
- Long-running work (anything that isn't a quick request/response) belongs in
  a Celery task, not an `async def` route doing `await asyncio.sleep()` loops
  or unbounded polling. The pipeline's suspend/resume model
  (`PipelineSuspended`, webhook + Beat polling) exists specifically so nothing
  ever blocks waiting on an external system — follow that pattern rather than
  inventing an in-process wait loop.

## Rule 4 — Timeouts and cancellation are mandatory, not optional

- Every external call (Lokalise, Figma, ChromaDB, SSO, storage) must have an
  explicit timeout. `httpx.Client()`/`AsyncClient()` calls in this repo always
  pass `timeout=...` — match that, don't rely on the library default.
- Wrap external calls in the existing circuit breaker + retry utilities
  (`app/utils/circuit_breaker.py`, `app/utils/retry.py`) rather than adding ad
  hoc `try/except` retry loops. A new integration client should look like
  `LokaliseService`/`FigmaService`: breaker-wrapped, retried with backoff,
  timeout on every request.
- FastAPI cancels the request task if the client disconnects; don't swallow
  `asyncio.CancelledError` — let it propagate so cleanup (`finally` blocks)
  still runs, but don't convert it into a generic exception handler response.

## Rule 5 — Session/connection lifecycle

- Always use dependency-injected sessions (`Depends(get_db)` for async,
  `SessionLocal()` context manager for sync) — never construct a session at
  module import time or hold one open across requests/tasks.
- One `AsyncSession`/`Session` per request or per task, closed (or exited via
  `async with`/`with`) before the function returns. Don't share a session
  across `asyncio.gather` branches — each concurrent DB-touching coroutine
  needs its own session, since SQLAlchemy sessions are not safe for
  concurrent use from multiple coroutines/threads at once.
- Async engine pool sizing and sync engine pool sizing are configured
  separately (`app/db/session.py`); don't assume they share a pool.

## Rule 6 — Testing async code

- Use `pytest-asyncio` (`@pytest.mark.asyncio`, already configured via
  `asyncio_mode` in `pytest.ini`/`pyproject.toml`). Don't call `asyncio.run()`
  inside a test — let the plugin manage the loop.
- Test the async/sync boundary explicitly: a test exercising an API route
  that calls `asyncio.to_thread(sync_fn, ...)` should assert the sync path's
  side effects (DB rows, files written), not just mock it away.
- For WebSocket tests, drive the actual `websockets`/`httpx-ws` client against
  the ASGI app rather than unit-testing the handler function in isolation —
  the interesting bugs live in the subscribe/unsubscribe/cancel lifecycle.

## Rule 7 — Errors in async code must be observable

- Never `except Exception: pass` in an async task or background coroutine —
  a swallowed exception in a detached task disappears with no trace. Log it
  (`app/core/logging.py`'s `get_logger`) with enough context to act on, per
  the existing pattern in `app/services/notification_service.py` and
  `app/pipeline/executor.py`'s stage failure handling.
- Correlation IDs (`app/core/logging.py`, `app/core/middleware.py`,
  `app/tasks/celery_app.py`'s Celery signal handlers) must survive
  async/sync and API/worker boundaries — don't introduce a new entry point
  (route, task, webhook) without confirming a correlation ID gets bound.

## Anti-patterns to reject in review

- `async def` function with no `await` in its body and no genuine reason to
  be async (e.g. it's only ever called from sync code) — should be sync.
- A sync function called directly (not via `asyncio.to_thread`) from inside
  an `async def` route body when that function does blocking I/O.
- `time.sleep()` anywhere in request-serving code (API or Celery task) as a
  substitute for proper backoff/retry or the checkpoint/resume model.
- Creating a new `httpx.Client`/`AsyncClient` (or DB session) per loop
  iteration instead of once per logical operation/request.
- Broad `except:`/`except Exception:` around an `await` that hides
  `asyncio.CancelledError` or genuine programming errors alongside the
  expected failure modes.
