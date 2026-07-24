---
applyTo: "**/*.py"
description: Backend coding conventions for the AI Localization Platform (Python/FastAPI/Celery).
---

# Python backend conventions

Apply these on top of `.github/copilot-instructions.md`. Design in `Design/` always wins.

## Stack
- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery + Redis, pytest.

## Structure & style
- Keep routers thin; put business logic in `services/`, data access in `repositories/`
  or models, and long-running work in Celery tasks.
- Type hints on all public functions/methods. Docstrings on modules, classes, and
  public methods.
- Use FastAPI `Depends` for DI (db session, current user/role, settings).
- Pydantic models for all request/response schemas; never return raw ORM objects.

## Database
- Every schema change is an **Alembic migration**. Table/column names, types, indexes,
  and enums MUST match `Design/Database_Schema.md` exactly.
- Pipeline stage enum order is `process, orchestrate, assemble, review, signoff, download`.

## Async / reliability
- Celery: 1 worker, `concurrency=3`; scheduled jobs via Beat.
- External calls (Lokalise, ChromaDB, Figma, storage) go through circuit-breakered
  service clients with retry/backoff and idempotency keys (Redis).
- Use webhook + 15-min polling fallback where the design specifies it.

## Security & data
- Never hardcode secrets; read from settings/env. Never log PHI/PII.
- Enforce roles `admin`/`localization_manager`/`viewer` (viewer = read-only) via guards.

## Testing
- `pytest` for unit/integration. Name story tests clearly (e.g.
  `test_story_2_5_join_barrier.py`). Cover the story's Acceptance/Validation criteria.

## Do not
- Do not implement out-of-scope items (Video/Whisper/TTS/FFmpeg, IFU generation,
  public API, GitLab, encryption at rest).
- Do not invent identifiers not present in the design docs.
