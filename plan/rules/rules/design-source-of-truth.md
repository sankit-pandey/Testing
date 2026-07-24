---
trigger: always_on
description: Enforce the Design/ folder as the authoritative source of truth for all AI Localization Platform implementation work.
---

# Design Is the Source of Truth (AI Localization Platform)

These rules apply to ALL implementation work in `C:\Projects\AI Localization`.

## Status: implemented
The backend is fully implemented at `knewron-localization/` (all stories in
`Implementation/Implementation_Plan.md`, including `8.x` post-implementation
extensions). Check the Progress Tracker there before starting new work — most
things you'd think to build already exist. New work extends or fixes what's
there, following the same one-story-at-a-time workflow below.

Four infrastructure extensions were added **beyond** this design by direct
client instruction, documented as an addendum in
`Design/Technical_Design_Document.md` §11 (not a silent code deviation — the
design docs were updated first, per the workflow below): multi-cloud object
storage (§11.1), multi-cloud image embeddings (§11.2), a ChromaDB-only
`tenant_id` partition key (§11.3 — **not** relational multi-tenancy; no
`tenants` table, no `tenant_id` on any PostgreSQL table), and Poetry +
externalized Redis (§11.4).

## Authority order (higher wins on conflict)
1. `Design/LOCKED_Design_v1.0.md` — architecture, patterns, scope, NFRs
2. `Design/Database_Schema.md` — data model (tables, columns, indexes)
3. `Design/Figma_Integration.md` — Figma metadata, variables/modes, rendering
4. `Design/Technical_Design_Document.md` — detailed APIs/services reference
5. `Design/Architecture_Diagrams.md` — behavioral/structural views
6. `Requirements/Requirements_Document.md` — functional what/why, compliance

## Mandatory workflow for every implementation task/story
1. **Load design first.** Before writing code, open and read the story's **Design Refs**
   (see `Implementation/Implementation_Plan.md`) and the matching rows in
   `Implementation/Design_Traceability_Matrix.md`.
2. **Conform exactly.** Table/column names, field names, thresholds, enums, flows,
   and roles MUST match the cited design. Do not invent anything outside it.
3. **No silent deviations.** If the design seems wrong or insufficient, STOP and ask.
   Update the design doc first (version bump + user approval), THEN write code.
4. **One story at a time.** Implement only the current story's scope. No scope creep.
5. **Validate against design.** The story's validation/DoD includes: "output conforms
   to cited design sections."
6. **Update traceability.** After a story is approved, flip its row(s) in
   `Design_Traceability_Matrix.md` (and the plan tracker) to ✅ and record the commit.
7. **Check in before next.** Commit only after the user reviews and approves the diff.

## Fixed values that must be honored (from design)
- Architecture: monolithic Python + FastAPI; Pipeline + Strategy; event-driven.
- Async: Celery + Redis (Redis is external/managed, never a Docker Compose
  service — Technical_Design §11.4); 1 worker, `concurrency=3`; Celery Beat
  for schedules.
- Data: PostgreSQL + SQLAlchemy + Alembic; ChromaDB (client-server); Redis;
  object storage is S3/GCS/local, config-selected (Technical_Design §11.1).
- Project model: ONE project per product per SINGLE target language; a project has
  one or more artifacts, processed and downloaded independently (partial completion).
- Thresholds: ChromaDB image match >= 90%; AI image detection confidence 70%.
- Roles: `admin`, `localization_manager`, `viewer` (viewer = read-only).
- Reliability: state machine, saga/compensation, circuit breaker, idempotency,
  checkpointing, webhook + 15-min polling fallback.
- Security: SSO auth, TLS in transit, no PHI/PII, audit all actions (1-yr retention).

## Out of scope (do NOT implement now)
- Video localization (Whisper / TTS / FFmpeg / Video strategy).
- IFU document generation.
- Public API access (UI only), GitLab integration, encryption at rest.

## Implementation order
- Story 0.1 → foundations → core/API → pipeline framework → real-time →
  integrations → **5.1 image sub-pipeline → 5.2 IFU (first slice) → 5.3 UI Resource**
  → review/sign-off/download → cross-cutting → **8.x post-implementation
  extensions**. See `Implementation/Implementation_Plan.md`. All stories are
  ✅ done — read the Progress Tracker there first.

## Python coding standards
- Backend conventions: `.github/instructions/python-code.instructions.md`.
- Production-grade async code (FastAPI async vs. Celery sync boundaries,
  timeouts, structured concurrency, session lifecycle): `.github/instructions/python-async.instructions.md`.
