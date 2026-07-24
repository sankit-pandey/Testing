# GitHub Copilot — Repository Instructions (AI Localization Platform)

> These instructions are **auto-attached to every Copilot Chat request** in this
> workspace. They mirror the always-on rule in `rules/rules/design-source-of-truth.md`.
> **The `Design/` folder is the single source of truth.** Do not invent anything
> outside it.

## Status: implemented
The full backend (all stories below) is implemented at `knewron-localization/`.
Its `README.md` is the authoritative "how to run/test this" reference — read
it alongside this file. **New work in this repo means either (a) extending
`knewron-localization/`, following the same one-story workflow, or (b)
maintaining/fixing existing stories** — not re-planning from scratch.

Three infrastructure extensions were added **beyond** the original locked
design, by direct user instruction (not a design deviation the assistant
invented — see `knewron-localization/README.md` §6 for the full rationale):
1. **Multi-cloud storage** — `STORAGE_BACKEND=local|s3|gcs` (`.env`-selected).
2. **Multi-cloud embeddings** — `AI_EMBEDDING_BACKEND=clip|phash|aws|gcp`.
3. **Poetry** replaces `requirements.txt`; Redis is external/managed (not a
   docker-compose service).

A `tenant_id` partition key exists **only** inside `app/services/chromadb_service.py`
(config-driven via `CHROMADB_TENANT_ID`) — this is a ChromaDB-level namespace,
**not** relational multi-tenancy. There is no `tenants` table and no
`tenant_id` column anywhere else; `users`/`products`/every other table match
`Database_Schema.md` exactly, unmodified.

## What we are building
Knewron **AI Localization Platform** for DeepHealth. Backend is a monolithic
**Python + FastAPI** app using the **Pipeline + Strategy** pattern with an
event-driven, async design.

## Golden rule: Design is the source of truth
Before writing any code for a story, **read the design first**:
1. Open the story in `Implementation/Implementation_Plan.md` and read its **`Design Refs`** line.
2. Open the matching rows in `Implementation/Design_Traceability_Matrix.md`.
3. Open and read the cited **`Design/`** sections.
4. Make table names, column names, field names, enums, thresholds, flows, and roles
   **match the cited design exactly**.

**No silent deviations.** If the design seems wrong or insufficient, **STOP and ask
the reviewer**. The design doc must be changed first (version bump + approval),
**then** code. Never "fix" a mismatch by diverging in code.

## Authority order (higher wins on conflict)
1. `Design/LOCKED_Design_v1.0.md` — architecture, patterns, scope, NFRs
2. `Design/Database_Schema.md` — data model (tables, columns, indexes, enums)
3. `Design/Figma_Integration.md` — Figma metadata, variables/modes, rendering
4. `Design/Technical_Design_Document.md` — detailed APIs/services reference
5. `Design/Architecture_Diagrams.md` — behavioral/structural views
6. `Requirements/Requirements_Document.md` — functional what/why, compliance

## One story at a time (mandatory workflow)
Developers pick **one story** from `Implementation/Implementation_Plan.md` and ask
Copilot to generate it. For that story only:
1. **Plan** — restate the story Goal, Scope, Depends-on, Acceptance, Validation.
2. **Load design** — read the story's `Design Refs` sections (list them back).
3. **Implement** — code **only** this story's scope. No scope creep. Respect
   `Depends on`; do not re-implement earlier stories.
4. **Validate** — add unit tests for new logic; provide the documented run/verify
   command or endpoint from the story's `Validation`.
5. **Stop for review** — do **not** move to the next story; the human reviews the diff.

Use the reusable prompt **`/implement-story`** (`.github/prompts/implement-story.prompt.md`)
to run this workflow.

## Definition of Done (every story)
- Code matches the **cited design sections** and coding standards.
- Unit tests for new logic; all tests pass.
- Runnable/verifiable via a documented command or endpoint.
- No breakage of previously completed stories.
- Reviewer approves the diff **before** commit.
- Traceability row(s) flipped to done in `Design_Traceability_Matrix.md` (after approval).

## Fixed values that must be honored (from design)
- **Architecture:** monolithic Python + FastAPI; Pipeline + Strategy; event-driven.
- **Pipeline stages (universal, in order):** `process → orchestrate → assemble → review → signoff → download`.
- **Async:** Celery + Redis (Redis is external/managed, not containerized —
  see extension #3 above); **1 worker, `concurrency=3`**; Celery Beat for schedules.
- **Data:** PostgreSQL + SQLAlchemy + **Alembic**; ChromaDB (client-server); Redis;
  object storage is S3/GCS/local (`STORAGE_BACKEND`, extension #1 above).
- **Project model:** ONE project per product per **SINGLE** target language; a project
  has one or more artifacts, processed and downloaded **independently** (partial completion).
- **Thresholds:** ChromaDB image match **≥ 90%**; AI image detection confidence **70%**.
- **Roles:** `admin`, `localization_manager`, `viewer` (viewer = read-only).
- **Reliability:** state machine, saga/compensation, circuit breaker, idempotency,
  checkpointing, **webhook + 15-min polling fallback**.
- **Security:** SSO auth, TLS in transit, **no PHI/PII**, audit all actions (1-yr retention).

## Out of scope — do NOT implement now
- **Video localization** (Whisper / TTS / FFmpeg / Video strategy).
- IFU document generation.
- Public API access (UI only), GitLab integration, encryption at rest.

## Implementation order
Story `0.1` → foundations → core/API → pipeline framework → real-time → integrations
→ **`5.1` image sub-pipeline → `5.2` IFU (first slice) → `5.3` UI Resource** →
review/sign-off/download → cross-cutting → **`8.x` post-implementation
extensions** (storage/embedding providers, Poetry, ChromaDB tenant key).
All stories `0.1`–`8.5` are ✅ done — see `Implementation/Implementation_Plan.md`
Progress Tracker before starting new work, so you don't re-implement something
that already exists.

## Coding conventions (backend)
- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Celery, **Poetry**
  (`pyproject.toml` — not `requirements.txt`; optional extras `gcp`, `ml`).
- Type hints on all public functions; docstrings for modules/classes/public methods.
- Use dependency injection via FastAPI `Depends`; keep routers thin, logic in services.
- All DB changes go through **Alembic migrations** — never hand-edit the DB.
- Never hardcode secrets; use env vars / settings. Do not log PHI/PII.
- Prefer `pytest`; name tests to reflect the story (e.g. `test_story_2_5_join_barrier.py`).
- **Async code:** see `.github/instructions/python-async.instructions.md` —
  this codebase runs async (FastAPI/`AsyncSession`) and sync (Celery/`Session`)
  concurrency models side by side; never mix them on the same call path.
