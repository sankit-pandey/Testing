# 🚧 Phased Implementation Plan — AI Localization Platform

**Project:** Knewron AI Localization Platform
**Client:** DeepHealth
**Date:** July 24, 2026
**Version:** 1.1
**Status:** ✅ Implemented — all stories `0.1`–`8.5` done at `knewron-localization/`
**Governing design:** `Design/LOCKED_Design_v1.0.md` (architecture) + `Design/Database_Schema.md` (schema) + `Design/Technical_Design_Document.md` §11 (post-implementation extensions)

> **Implementation scope note:** **Video localization is OUT OF SCOPE for implementation** (deferred to a future phase). Whisper/TTS/FFmpeg services and the Video strategy are not built now. The design docs still describe video; this plan simply does not implement it yet.
> **Artifact order:** **IFU first, then UI Resource files.**

---

## 1. Working Agreement (per-story workflow)

We implement **one story at a time**. No story starts until the previous one is checked in.

```
For each story:
  1. Plan      → confirm scope + acceptance criteria (this doc)
  2. Implement → code the story only (no scope creep)
  3. Validate  → run tests / demo commands; you review the diff
  4. Approve   → you confirm it is correct
  5. Check-in  → commit with a clear message
  6. Next      → move to the next story
```

**Definition of Done (every story)**
- Code matches the **cited design sections** (see each story's `Design Refs`) and coding standards.
- Unit tests for new logic; all tests pass.
- Runnable/verifiable via a documented command or endpoint.
- No breakage of previously completed stories.
- Diff reviewed and approved by you before commit.
- Traceability row(s) flipped to ✅ in `Design_Traceability_Matrix.md`.

**Design governance (source of truth)**
- Authority order & coverage: `Implementation/Design_Traceability_Matrix.md`.
- Always-on guardrails (Windsurf): `rules/rules/design-source-of-truth.md`.
- **GitHub Copilot developers:** repo-wide rules in `.github/copilot-instructions.md`; run the `/implement-story` prompt (`.github/prompts/implement-story.prompt.md`); onboarding in `.github/COPILOT_WORKFLOW.md`.
- Each story below carries a `Design Refs` line — read those design sections **before** coding. Deviations require a design-doc change (version bump + approval) **first**, then code.

---

## 2. Milestones

| Milestone | Stories | Outcome |
|-----------|---------|---------|
| **M0 — Foundations** | 0.1–0.3 | App boots, DB migrates, Celery runs (all via Docker Compose) |
| **M1 — Core Domain & API** | 1.1–1.3 | Create products/projects/artifacts, upload files, auth/RBAC |
| **M2 — Pipeline Framework** | 2.1–2.5 | Universal pipeline executes a no-op strategy with state, resilience, and parallel sub-task join |
| **M3 — Real-time** | 3.1 | Live progress via WebSocket |
| **M4 — Integrations** | 4.1–4.4 | Storage, Lokalise, ChromaDB, Figma clients (circuit-breakered) |
| **M5 — Image sub-pipeline** | 5.1 | Reusable image localization ready (needed by IFU) |
| **M6 — IFU (first vertical slice)** | 5.2 | **IFU** localized end-to-end (text + images) |
| **M7 — UI Resource** | 5.3 | **UI Resource** localized end-to-end |
| **M8 — Review/Sign-off/Download** | 6.1–6.3 | AI+human review, approval, per-artifact download |
| **M9 — Cross-cutting** | 7.1–7.4 | Audit, notifications, observability, CI |
| **M10 — Post-implementation extensions** | 8.1–8.5 | Multi-cloud storage/embeddings, ChromaDB tenant partition key, Poetry, externalized Redis |

> **IFU is the first vertical feature** (per your priority). Because IFU depends on the image sub-pipeline (ChromaDB + Figma), those integrations (M4) and the image sub-pipeline (5.1) come first. UI Resource follows as a simpler second slice.
> **Video (former M7) is out of scope for implementation** and removed from this plan.

---

## 3. Story Backlog

Each story: **Goal · Scope · Depends on · Acceptance criteria · Validation**.

### Phase 0 — Foundations

#### Story 0.1 — Project scaffold & Docker Compose
- **Design Refs:** LOCKED §2, §8, §11; Technical_Design (deployment)
- **Goal:** Boot the app skeleton and all services locally.
- **Scope:** Repo structure per locked §11; FastAPI app with `/health`; `docker-compose.yml` (api, celery_worker, celery_beat, redis, postgres, chromadb, flower); `requirements.txt`; `.env.example`; README.
- **Depends on:** —
- **Acceptance:** `docker compose up` starts all services; `GET /health` returns 200; Flower reachable.
- **Validation:** `curl /health`; open Flower :5555.

#### Story 0.2 — Database foundation (models + migrations)
- **Design Refs:** Database_Schema.md (all tables/indexes); LOCKED §9
- **Goal:** Schema in place with migrations.
- **Scope:** SQLAlchemy + Alembic; core tables (`products`, `projects`, `project_artifacts`, `artifact_stages`); session/engine; base mixins (timestamps, uuid).
- **Depends on:** 0.1
- **Acceptance:** `alembic upgrade head` creates tables matching `Database_Schema.md`.
- **Validation:** migration runs clean; tables visible in psql.

#### Story 0.3 — Celery + Redis wiring
- **Design Refs:** LOCKED §2, §8
- **Goal:** Async task execution proven.
- **Scope:** Celery app, broker/result backend (Redis), one sample task, Beat schedule stub, Flower.
- **Depends on:** 0.1
- **Acceptance:** enqueue sample task → executes in worker → result visible in Flower.
- **Validation:** trigger endpoint that enqueues a task; observe in Flower.

### Phase 1 — Core Domain & API

#### Story 1.1 — Product & Project APIs
- **Design Refs:** Database_Schema (products, projects); Requirements §1.5; LOCKED §9
- **Goal:** Manage products and single-language projects.
- **Scope:** CRUD for `products`; CRUD for `projects` (one product + one target language); Pydantic schemas; validation.
- **Depends on:** 0.2
- **Acceptance:** create/list/get product & project; project enforces single `target_language`.
- **Validation:** API tests + example requests.

#### Story 1.2 — Artifact submission & upload
- **Design Refs:** Database_Schema (project_artifacts); LOCKED §4; Requirements §2.2
- **Goal:** Add artifacts to a project and upload source files.
- **Scope:** `project_artifacts` CRUD; presigned upload URL (storage abstraction); `POST /artifacts/{id}/start` (enqueues pipeline stub); artifact status lifecycle fields.
- **Depends on:** 1.1, 0.3
- **Acceptance:** create artifact → get upload URL → upload → start → status=processing.
- **Validation:** end-to-end request sequence; file present in storage.

#### Story 1.3 — Auth (SSO/JWT/RBAC)
- **Design Refs:** Requirements §2.2, §6; LOCKED §12; Database_Schema (users)
- **Goal:** Protect APIs with roles.
- **Scope:** JWT validation (SSO-ready), roles `admin`/`localization_manager`/`viewer`, dependency guards; viewer = read-only.
- **Depends on:** 1.1
- **Acceptance:** unauthorized blocked; viewer cannot mutate; manager can.
- **Validation:** auth tests per role.

### Phase 2 — Pipeline Framework

#### Story 2.1 — Pipeline executor + Strategy base + factory
- **Design Refs:** LOCKED §3, §13
- **Goal:** Universal 6-stage executor.
- **Scope:** `Pipeline` base (process→orchestrate→assemble→review→signoff→download), `Strategy` ABC, `StrategyFactory`; a `NoOpStrategy` for testing.
- **Depends on:** 0.3
- **Acceptance:** running pipeline with NoOp advances through all stages.
- **Validation:** unit test asserting stage order and completion.

#### Story 2.2 — State machine + status persistence
- **Design Refs:** LOCKED §7; Arch §5; Database_Schema (artifact_stages)
- **Goal:** Enforce valid transitions; persist stage status.
- **Scope:** state machine (statuses per Architecture §5), write to `artifact_stages`; derive project status from artifacts.
- **Depends on:** 2.1, 0.2
- **Acceptance:** invalid transitions rejected; stage rows created/updated.
- **Validation:** unit tests for transitions; DB reflects progress.

#### Story 2.3 — Checkpointing & resume
- **Design Refs:** LOCKED §7
- **Goal:** Resume from last successful stage.
- **Scope:** checkpoint after each stage; re-run skips completed stages.
- **Depends on:** 2.2
- **Acceptance:** simulate failure mid-pipeline → re-run resumes, not restarts.
- **Validation:** test injecting failure then resuming.

#### Story 2.4 — Resilience utils (saga, circuit breaker, idempotency, retry)
- **Design Refs:** LOCKED §7
- **Goal:** Shared reliability primitives.
- **Scope:** circuit breaker wrapper, retry w/ backoff, idempotency keys (Redis), saga/compensation hook.
- **Depends on:** 2.1
- **Acceptance:** breaker opens after N failures; idempotent op runs once.
- **Validation:** unit tests for each primitive.

#### Story 2.5 — Parallel sub-task orchestration + join barrier
- **Design Refs:** LOCKED §7; Arch §6.1; Database_Schema (artifact_subtasks)
- **Goal:** Fan-out parallel branches within a stage and join them so the next stage triggers **exactly once**.
- **Scope:** create `artifact_subtasks` table + migration; sub-task dispatch (fan-out); DB-backed **join barrier** with atomic check (`SELECT ... FOR UPDATE`) + idempotency guard so assembly fires once; resume-on-external-completion hook (called by webhook/polling handlers).
- **Depends on:** 2.2, 2.4
- **Acceptance:** two branches marked complete in any order (incl. simultaneously/duplicates) trigger the next stage exactly once; barrier state survives worker restart.
- **Validation:** unit tests for race (both complete together), duplicate completion, and crash/resume.

### Phase 3 — Real-time

#### Story 3.1 — Event bus + WebSocket progress
- **Design Refs:** LOCKED §2; Arch §10; Technical_Design (WebSocket)
- **Goal:** Live progress to UI.
- **Scope:** Redis Pub/Sub publisher in pipeline; WebSocket endpoint; event schema (stage_started/progress/completed/failed/download_ready).
- **Depends on:** 2.2, 0.3
- **Acceptance:** running pipeline pushes events to a connected WS client.
- **Validation:** WS test client receives ordered events.

### Phase 4 — Integrations (each circuit-breakered)

#### Story 4.1 — Storage service
- **Design Refs:** LOCKED §9; Technical_Design (storage)
- **Goal:** Abstract S3/GCS operations.
- **Scope:** put/get/presign/delete; local/dev fallback (MinIO or filesystem).
- **Depends on:** 2.4
- **Acceptance:** upload/download/presign works against dev backend.
- **Validation:** integration test.

#### Story 4.2 — Lokalise service (webhook + polling)
- **Design Refs:** LOCKED §7; Arch §11, §17; Database_Schema (lokalise_tasks)
- **Goal:** Text translation integration.
- **Scope:** upload content, create task, status API, webhook receiver (signature + idempotency), 15-min polling fallback (Beat).
- **Depends on:** 2.4, 3.1
- **Acceptance:** upload → completion via webhook OR polling → pipeline resumes; duplicates ignored.
- **Validation:** mocked Lokalise; simulate webhook + polling.

#### Story 4.3 — ChromaDB service
- **Design Refs:** LOCKED §5; Technical_Design §3; Database_Schema (image_processing)
- **Goal:** Image similarity matching.
- **Scope:** client-server connection; embed + query; 90% threshold; metadata retrieval.
- **Depends on:** 2.4
- **Acceptance:** known image returns match ≥ 90% with metadata.
- **Validation:** seed vectors; query test.

#### Story 4.4 — Figma service
- **Design Refs:** Figma_Integration (all); Database_Schema (figma_images, translation_cache)
- **Goal:** Render translated images.
- **Scope:** load metadata; set variable values per target-language mode; render frame; export PNG (bbox/scale/format). See `Design/Figma_Integration.md`.
- **Depends on:** 2.4, 4.1
- **Acceptance:** given metadata + translations → PNG produced & stored.
- **Validation:** mocked Figma API; asset stored.

### Phase 5 — Strategies (vertical features)

#### Story 5.1 — Image localization sub-pipeline
- **Design Refs:** LOCKED §5; Figma_Integration §6, §8; Requirements §4
- **Goal:** Reusable image localization (dependency for IFU).
- **Scope:** classify (UI vs non-UI) → ChromaDB match → cache lookup → Figma render → AI review → cache store; non-UI/no-match → retain + flag (per `Figma_Integration.md` §8).
- **Depends on:** 4.3, 4.4
- **Acceptance:** UI image localized or reused; non-UI flagged; original retained on no-match.
- **Validation:** tests across scenarios.

#### Story 5.2 — IFU strategy (first full slice) ⭐
- **Design Refs:** LOCKED §4.1; Arch §6, §6.1; Requirements §3
- **Goal:** IFU document end-to-end.
- **Scope:** DOCX **image extractor** (extract embedded images + positions/hash; **no text parsing** — original DOCX kept intact) → fan-out via **join barrier (2.5)**: (a) **upload original DOCX to Lokalise doc API**, (b) run **image sub-pipeline** → on join, **assemble** = take Lokalise-translated DOCX and **re-inject localized images** (by position/hash) → review → download.
- **Depends on:** 5.1, 4.2, 2.5
- **Acceptance:** upload IFU DOCX → download localized DOCX (Lokalise-translated text + localized images); layout preserved.
- **Validation:** sample IFU round-trip; images correctly replaced; formatting preserved.

#### Story 5.3 — UI Resource strategy
- **Design Refs:** LOCKED §4.3; Arch §9; Requirements §3.3
- **Goal:** Localize a resource file end-to-end.
- **Scope:** parse JSON/XML/YAML/Properties/RESX → extract strings → Lokalise → reconstruct → review stub → download.
- **Depends on:** 2.x, 4.2, 3.1
- **Acceptance:** upload resource file → download translated file with same structure.
- **Validation:** round-trip test on sample files.

> ~~Story 5.4 — Video strategy~~ **— OUT OF SCOPE (deferred).** Whisper/TTS/FFmpeg not implemented in this phase.

### Phase 6 — Review / Sign-off / Download

#### Story 6.1 — AI reviewer + findings
- **Design Refs:** Requirements §4–§5; Database_Schema (review_findings)
- **Goal:** Automated quality checks.
- **Scope:** AI review of outputs; write `review_findings`; flag `needs_human_review`.
- **Depends on:** 5.2 (applies to all strategies)
- **Acceptance:** issues produce findings + status change.
- **Validation:** tests with good/bad samples.

#### Story 6.2 — Human review & sign-off
- **Design Refs:** LOCKED §4; Database_Schema (approvals); Requirements §5
- **Goal:** Approval workflow.
- **Scope:** review queue endpoints; approve/reject; `approvals` table; transitions.
- **Depends on:** 6.1
- **Acceptance:** reject → back to reviewing; approve → complete.
- **Validation:** workflow tests.

#### Story 6.3 — Download & partial completion
- **Design Refs:** LOCKED §4; Requirements §1.5; Database_Schema (artifact status)
- **Goal:** Per-artifact delivery.
- **Scope:** presigned download; project partial-complete status; independent artifact downloads.
- **Depends on:** 5.x, 6.2
- **Acceptance:** completed artifacts downloadable while others still processing.
- **Validation:** mixed-status project test.

### Phase 7 — Cross-cutting

#### Story 7.1 — Audit logging
- **Design Refs:** LOCKED §12; Database_Schema (audit_logs); Requirements §6
- **Scope:** log all user/system actions; immutable; exportable; 1-yr retention. **Validation:** actions produce audit rows.

#### Story 7.2 — Notifications
- **Design Refs:** Requirements; Arch §2
- **Scope:** notify on completion/failure/review-needed. **Validation:** notification emitted on events.

#### Story 7.3 — Observability & error handling
- **Design Refs:** LOCKED §12; Requirements §6
- **Scope:** structured logging (30-day default), tracing/correlation ids, global error handlers. **Validation:** logs/correlation present.

#### Story 7.4 — Test suite & CI
- **Design Refs:** LOCKED §11; all story acceptance criteria
- **Scope:** unit/integration/e2e coverage; CI pipeline. **Validation:** CI green.

### Phase 8 — Post-Implementation Extensions

> Added by direct client instruction after the initial locked build (M0–M9).
> Each story is additive/config-driven: no functional behavior, API contract,
> or `Database_Schema.md` table changes as a result. Design first, per the
> golden rule — all four are documented in `Technical_Design_Document.md`
> §11 before being listed here.

#### Story 8.1 — Multi-cloud object storage
- **Design Refs:** Technical_Design §11.1; Requirements §6.2.1
- **Goal:** Swap the object storage provider without touching any caller.
- **Scope:** `StorageBackend` interface with `local`/`s3`/`gcs` implementations; `STORAGE_BACKEND` env selection; `gcp` Poetry extra for the GCS client.
- **Depends on:** 4.1
- **Acceptance:** artifact upload/presign/download flow (Story 1.2, 6.3) works unchanged regardless of `STORAGE_BACKEND` value.
- **Validation:** unit tests constructing each backend; existing artifact upload/download tests pass against the `local` backend in CI.

#### Story 8.2 — Multi-cloud image embeddings
- **Design Refs:** Technical_Design §11.2; Appendix B §1 (open question this closes)
- **Goal:** Swap the image-embedding provider without touching ChromaDB matching/threshold logic.
- **Scope:** `ImageEmbedder` interface with `clip`/`phash`/`aws`/`gcp` implementations; `AI_EMBEDDING_BACKEND` env selection; `ml`/`gcp` Poetry extras.
- **Depends on:** 4.3
- **Acceptance:** `ChromaDBService` produces vectors via any configured backend; the ≥ 90% match threshold (LOCKED §5) is unaffected by backend choice.
- **Validation:** unit tests per embedder; `phash` used as the dependency-light default in CI/tests.

#### Story 8.3 — ChromaDB tenant partition key
- **Design Refs:** Technical_Design §11.3; Requirements §6.3.2
- **Goal:** Let multiple environments/deployments share one ChromaDB instance without cross-contamination.
- **Scope:** `CHROMADB_TENANT_ID` env setting (default `"default"`); stamped into vector metadata on `add_image`; applied as an `$and` query filter alongside `product_id` on `find_matches`. **Not** relational multi-tenancy — no `tenants` table, no `tenant_id` on any PostgreSQL table.
- **Depends on:** 4.3
- **Acceptance:** vectors written under one `CHROMADB_TENANT_ID` are never returned by a query run under a different one; existing per-product scoping (Story 4.3) still applies on top.
- **Validation:** `test_chromadb_tenant_scoping.py` (mocked chromadb client).

#### Story 8.4 — Poetry dependency management
- **Design Refs:** Technical_Design §11.4
- **Goal:** Replace `pip -r requirements.txt` with Poetry; keep heavy/optional deps out of the default install.
- **Scope:** `pyproject.toml` (`[tool.poetry]` deps, `gcp`/`ml` extras); `Dockerfile` installs via Poetry (`--build-arg POETRY_EXTRAS="gcp ml"`); `requirements.txt` removed.
- **Depends on:** 0.1
- **Acceptance:** `poetry install` (with/without extras) reproduces a working environment; `docker build` succeeds with and without `POETRY_EXTRAS`.
- **Validation:** `poetry check`; CI installs via Poetry and runs the suite.

#### Story 8.5 — Redis externalized from Docker Compose
- **Design Refs:** Technical_Design §11.4, §7.1
- **Goal:** Redis is never a Docker Compose service; it's always an external instance (self-run in dev, managed in staging/prod).
- **Scope:** `redis` service removed from `docker-compose.yml`; `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` sourced from `.env`, pointing off-host.
- **Depends on:** 0.1, 0.3
- **Acceptance:** `docker compose config` has no `redis` service; `api`/`celery_worker`/`celery_beat`/`flower` connect to whatever `REDIS_URL` (etc.) resolves to.
- **Validation:** local run against a manually-started Redis container; CI runs Redis as a GitHub Actions service container (not compose).

---

## 4. Dependency Overview

```
0.1 → 0.2 → 1.1 → 1.2
0.1 → 0.3 → 2.1 → 2.2 → 2.3
                  2.1 → 2.4
2.2 + 2.4 → 2.5 (parallel sub-task join barrier)
2.2 → 3.1
2.4 → 4.1 → 4.4
2.4 → 4.2 (needs 3.1)
2.4 → 4.3 → 5.1 ← 4.4
4.3 + 4.4 → 5.1 (image sub-pipeline)
5.1 + 4.2 + 2.5 → 5.2 (IFU, first slice)
4.2 + 2.x + 3.1 → 5.3 (UI Resource)
5.2 → 6.1 → 6.2 → 6.3
(Video 5.4 — out of scope)
(anytime after M2) → 7.x
4.1 → 8.1 (multi-cloud storage)
4.3 → 8.2 (multi-cloud embeddings)
4.3 → 8.3 (ChromaDB tenant partition key)
0.1 → 8.4 (Poetry)
0.1 + 0.3 → 8.5 (Redis externalized)
```

---

## 5. Progress Tracker

| Story | Title | Status | Commit |
|-------|-------|--------|--------|
| 0.1 | Project scaffold & Docker Compose | ✅ | knewron-localization/ initial build |
| 0.2 | Database foundation | ✅ | knewron-localization/ initial build |
| 0.3 | Celery + Redis wiring | ✅ | knewron-localization/ initial build |
| 1.1 | Product & Project APIs | ✅ | knewron-localization/ initial build |
| 1.2 | Artifact submission & upload | ✅ | knewron-localization/ initial build |
| 1.3 | Auth (SSO/JWT/RBAC) | ✅ | knewron-localization/ initial build |
| 2.1 | Pipeline executor + strategy | ✅ | knewron-localization/ initial build |
| 2.2 | State machine + persistence | ✅ | knewron-localization/ initial build |
| 2.3 | Checkpointing & resume | ✅ | knewron-localization/ initial build |
| 2.4 | Resilience utils | ✅ | knewron-localization/ initial build |
| 2.5 | Parallel sub-task join barrier | ✅ | knewron-localization/ initial build |
| 3.1 | Event bus + WebSocket | ✅ | knewron-localization/ initial build |
| 4.1 | Storage service | ✅ | knewron-localization/ initial build |
| 4.2 | Lokalise service | ✅ | knewron-localization/ initial build |
| 4.3 | ChromaDB service | ✅ | knewron-localization/ initial build |
| 4.4 | Figma service | ✅ | knewron-localization/ initial build |
| 5.1 | Image sub-pipeline | ✅ | knewron-localization/ initial build |
| 5.2 | IFU strategy (first slice) | ✅ | knewron-localization/ initial build |
| 5.3 | UI Resource strategy | ✅ | knewron-localization/ initial build |
| ~~5.4~~ | ~~Video strategy~~ | ⛔ Out of scope | — |
| 6.1 | AI reviewer | ✅ | knewron-localization/ initial build |
| 6.2 | Human review & sign-off | ✅ | knewron-localization/ initial build |
| 6.3 | Download & partial completion | ✅ | knewron-localization/ initial build |
| 7.1 | Audit logging | ✅ | knewron-localization/ initial build |
| 7.2 | Notifications | ✅ | knewron-localization/ initial build |
| 7.3 | Observability | ✅ | knewron-localization/ initial build |
| 7.4 | Tests & CI | ✅ | knewron-localization/ initial build |
| 8.1 | Multi-cloud object storage | ✅ | knewron-localization/ extensions |
| 8.2 | Multi-cloud image embeddings | ✅ | knewron-localization/ extensions |
| 8.3 | ChromaDB tenant partition key | ✅ | knewron-localization/ extensions |
| 8.4 | Poetry dependency management | ✅ | knewron-localization/ extensions |
| 8.5 | Redis externalized from Docker Compose | ✅ | knewron-localization/ extensions |

Legend: ⬜ Not started · 🟨 In progress · ✅ Done

---

**Status:** ✅ Implemented. All stories `0.1`–`8.5` done — see `knewron-localization/README.md` for how to run/test. New work: pick up maintenance/extension work the same way (one story at a time, design first).
