# LLM Build Guide — Knewron AI Localization Platform

**Audience:** any LLM/agent (Claude, GPT, Llama, Gemini, or other) asked to
understand, run, extend, or rebuild this project. This document is
self-contained — read it first, before opening anything else. It is
deliberately dense and tool-agnostic (no assumption of any specific IDE,
Copilot, or vendor).

If you take away one sentence: **the backend described here is fully built
and working at the repository root (`app/`); this `plan/` folder is the
design record it was built from, and it governs any change you make.**

---

## 1. What this project is

Knewron AI Localization Platform, for client DeepHealth. A backend service
that automates translating three kinds of artifacts into a target language:
**IFU documents** (regulatory instructions-for-use, DOCX), **UI resource
files** (JSON/XML/YAML/Properties/RESX), and (design-locked but **not
implemented** — see §7) **training videos**. It orchestrates two external
systems: **Lokalise** (human/AI text translation workflow) and **Figma**
(source of UI-screenshot reference images), matches images via **ChromaDB**
vector similarity, and exposes a REST + WebSocket API.

## 2. Where things are, and how to run them

```
knewron-localization/          <- repo root (also the Poetry project root)
├── app/                       <- the implemented backend (Python)
├── tests/                     <- pytest suite
├── plan/                      <- THIS folder: design docs that govern app/
├── others/                    <- raw source materials (sample IFU, Figma
│                                  metadata screenshots, extracted text) —
│                                  reference only, not authoritative
├── .github/                   <- coding-convention instruction files
├── pyproject.toml             <- Poetry deps (not requirements.txt)
├── docker-compose.yml         <- api, celery_worker, celery_beat, db,
│                                  chromadb, flower (NOT redis — see §7)
├── Dockerfile, alembic.ini, pytest.ini, .env.example
└── README.md                  <- human-oriented setup/run/test instructions
```

**To actually run or test the code, read `README.md` at the repo root, not
this file** — it has the exact commands (`poetry install`, `docker compose
up`, `alembic upgrade head`, `pytest`). This guide is about the *design*,
not operational steps.

## 3. Document map and authority order

When two documents disagree, the **higher-ranked one wins**. Never invent an
identifier (table name, column, field, enum value, threshold) that isn't in
one of these:

| Rank | Document | Governs |
|------|----------|---------|
| 1 | `Design/LOCKED_Design_v1.0.md` | Architecture, patterns, scope, NFRs |
| 2 | `Design/Database_Schema.md` | PostgreSQL data model (14 tables, verbatim) |
| 3 | `Design/Figma_Integration.md` | Figma metadata JSON shape, variables/modes, render params |
| 4 | `Design/Technical_Design_Document.md` | Detailed API/service reference; **§11 is an addendum** — see §7 below |
| 5 | `Design/Architecture_Diagrams.md` | Diagrams (Mermaid) — illustrative, not normative on conflict |
| 6 | `Requirements/Requirements_Document.md` | Functional what/why |

Supporting, non-authoritative documents:
- `Implementation/Implementation_Plan.md` — the story backlog (what got built, in what order, with acceptance criteria). **All stories are done** — this is a historical/status record now, not a to-do list, unless you are told to add a new story.
- `Implementation/Design_Traceability_Matrix.md` — maps every design element to the story that implements it. Use it to find "what implements X" or "what design section governs file Y."
- `Requirements/Requirements_Summary.md` — one-page executive version of the requirements.
- `rules/rules/design-source-of-truth.md` — the enforcement rules (same content as `.github/copilot-instructions.md`, tool-agnostic phrasing).
- `.github/instructions/python-code.instructions.md`, `.github/instructions/python-async.instructions.md` — coding conventions for this specific codebase (async/sync boundaries, etc.).

## 4. Data model (PostgreSQL, 14 tables — `Design/Database_Schema.md`)

All UUID primary keys, `created_at`/`updated_at` timestamps, JSONB `metadata`
column, unless noted. Implemented verbatim in `app/models/` + migration
`app/db/migrations/versions/0001_initial_schema.py`.

| Table | Purpose |
|-------|---------|
| `users` | Accounts (DeepHealth SSO); `role` = admin/localization_manager/viewer |
| `products` | Products requiring localization |
| `projects` | **One per product per single target language** |
| `project_artifacts` | IFU / VIDEO / UI_RESOURCE files within a project; independent status/download |
| `artifact_stages` | Per-artifact pipeline stage tracking (one row per stage name) |
| `artifact_subtasks` | Parallel sub-tasks within `orchestrate` (the join-barrier rows) |
| `image_processing` | Per-image classification/match/translation status |
| `figma_images` | Cached Figma frame metadata for ChromaDB matching/reuse |
| `translation_cache` | Cached translated images, keyed by `(source_image_hash, target_language)` |
| `lokalise_tasks` | Lokalise task tracking (webhook + polling) |
| `review_findings` | AI/human review findings |
| `approvals` | Sign-off approve/reject records |
| `audit_logs` | Immutable audit trail, 1-year retention |
| `system_settings` | App-wide config (encrypted secrets flag) |

Relationship chain: `products → projects → project_artifacts →
{artifact_stages, artifact_subtasks, image_processing, lokalise_tasks,
review_findings, approvals}`.

## 5. Universal pipeline (every artifact type runs this)

Six stages, in order, enforced by a state machine:
```
process → orchestrate → assemble → review → signoff → download
```
Artifact-level status values (`project_artifacts.status`,
`Architecture_Diagrams.md` §5):
```
pending → processing → orchestrating → assembling → reviewing
  → (needs_human_review ↔ reviewing) → signoff → complete
any-non-terminal-state → failed | cancelled
failed → processing (retry, resumes from last checkpoint stage — never restarts)
```
Implemented in `app/pipeline/executor.py` (`Pipeline` class) +
`app/pipeline/state_machine.py`. A stage's strategy method
(`app/pipeline/strategy.py`'s `BaseStrategy`) can raise `PipelineSuspended`
to fan out async work (Lokalise upload, image sub-pipeline) without
blocking the worker; a webhook, a 15-min Celery Beat poll, or a
human-approval endpoint later calls `resume_pipeline`, which re-enters the
same stage. Per-artifact-type behavior lives in `app/strategies/ifu/` and
`app/strategies/ui_resource/` (Video is design-locked but **not
implemented** — see §7).

## 6. Stack (exact — `Technical_Design_Document.md` §Appendix A + this repo's `pyproject.toml`)

Python 3.11+ · FastAPI (async REST + WebSocket + webhooks) · Celery + Redis
(1 worker, `concurrency=3`, + Beat scheduler; Redis is **external/managed**,
not a Docker Compose service — §7) · PostgreSQL 15 + SQLAlchemy 2 + Alembic
· ChromaDB (client-server, cosine similarity, ≥ 90% match threshold) ·
object storage is S3 / GCS / local filesystem, config-selected (§7) ·
Poetry for dependency management (`pyproject.toml`, extras `gcp`/`ml`) ·
Docker Compose for local/staging deployment.

Two concurrency models coexist — know which one you're reading:
- **API routes** (`app/api/v1/endpoints/*.py`): `async def`, SQLAlchemy
  `AsyncSession`.
- **Pipeline/Celery** (`app/pipeline/*.py`, `app/strategies/*.py`,
  `app/services/*.py` when called from a strategy, `app/tasks/*.py`): plain
  sync `def`, SQLAlchemy `Session`. Celery tasks are not coroutines.
  Full rules: `.github/instructions/python-async.instructions.md`.

## 7. Post-implementation extensions (read this before touching storage, embeddings, ChromaDB, Redis, or dependency management)

Four things were added **after** the initial locked design was fully built,
by direct client instruction — documented as an addendum in
`Technical_Design_Document.md` §11, traced in `Design_Traceability_Matrix.md`
as stories `8.1`–`8.5`. None of them change the data model in §4, any API
contract, or any story's functional behavior:

1. **Multi-cloud object storage** — `STORAGE_BACKEND=local|s3|gcs` (`.env`).
   One interface (`app/services/storage_service.py`), three implementations.
2. **Multi-cloud image embeddings** — `AI_EMBEDDING_BACKEND=clip|phash|aws|gcp`
   (`.env`). One interface (`app/services/embeddings.py`), four
   implementations (local CLIP, dependency-light perceptual hash, AWS
   Bedrock Titan, GCP Vertex AI).
3. **ChromaDB-only `tenant_id` partition key** — `CHROMADB_TENANT_ID`
   (`.env`, default `"default"`), stamped on every vector and filtered on
   every query, **inside `app/services/chromadb_service.py` only**. This is
   a namespace for deployments/environments sharing one ChromaDB instance.
   **It is explicitly not relational multi-tenancy** — there is no
   `tenants` table and no `tenant_id` column on any PostgreSQL table in §4.
   If you are asked to "add multi-tenancy," re-read this paragraph and
   `Technical_Design_Document.md` §11.3 before touching any table in §4 —
   a full relational multi-tenant model was built once and then explicitly
   reverted back to this scoped-to-ChromaDB-only form by direct instruction.
4. **Poetry replaces `requirements.txt`; Redis is external, not
   containerized** — `pyproject.toml` (extras `gcp`, `ml`);
   `docker-compose.yml` has no `redis` service, `REDIS_URL` etc. always
   point off-host.

## 8. Story status (`Implementation/Implementation_Plan.md`)

All of the following are **done** (✅). This table is a compressed index —
read the linked story in `Implementation_Plan.md` for Design Refs/Scope/
Acceptance before modifying that area.

| Phase | Stories | What it covers |
|-------|---------|-----------------|
| 0 — Foundations | 0.1–0.3 | Repo scaffold, DB migrations, Celery+Redis wiring |
| 1 — Core domain & API | 1.1–1.3 | Products/Projects/Artifacts CRUD, upload, SSO/JWT/RBAC |
| 2 — Pipeline framework | 2.1–2.5 | Executor, state machine, checkpointing, circuit breaker/retry/idempotency/saga, parallel join barrier |
| 3 — Real-time | 3.1 | Redis Pub/Sub → WebSocket progress |
| 4 — Integrations | 4.1–4.4 | Storage, Lokalise (webhook+poll), ChromaDB, Figma |
| 5 — Strategies | 5.1–5.3 | Image sub-pipeline, **IFU** end-to-end, **UI Resource** end-to-end. `5.4` (Video) is **out of scope** |
| 6 — Review/sign-off/download | 6.1–6.3 | AI reviewer + findings, human approve/reject, per-artifact download (partial completion) |
| 7 — Cross-cutting | 7.1–7.4 | Audit logging, notifications, observability, tests/CI |
| 8 — Post-implementation extensions | 8.1–8.5 | The four items in §7 above |

## 9. Explicitly out of scope — do not implement unless told to

- Video localization (Whisper STT, Google TTS, FFmpeg assembly, `VideoStrategy`). The state machine, DB tables (`project_artifacts.artifact_type` allows `'VIDEO'`), and diagrams describe it, but `app/strategies/` has no video implementation and `app/pipeline/factory.py` raises `UnsupportedArtifactTypeError` for it on purpose.
- IFU document *generation* (only localization of an existing IFU is in scope).
- Public/external API access (UI-only, per Requirements §6.4.2).
- GitLab integration (manual upload/download only).
- Encryption at rest (customer's infrastructure responsibility).
- Relational multi-tenancy (see §7.3 — it was built once, then reverted).

## 10. Rules for extending this project

1. **Read the design first.** For any change, find the governing section via
   §3's authority order or `Design_Traceability_Matrix.md`, then match its
   table/column/field names, enums, and thresholds exactly.
2. **No silent deviations.** If the design looks wrong or is missing
   something, update the design doc first (version bump, note the change in
   its Document Control table), *then* write code. Doc and code move
   together — that's the pattern the §7 extensions followed (each got a
   `Technical_Design_Document.md` §11 subsection and an `8.x` story entry).
3. **One unit of work at a time.** Don't bundle unrelated changes.
4. **Fixed values that must not drift:** ChromaDB match ≥ 90%; AI image
   classification confidence 70%; Celery 1 worker `concurrency=3`; roles are
   exactly `admin`/`localization_manager`/`viewer` (`viewer` = read-only);
   one project per product per single target language; pipeline stage order
   `process, orchestrate, assemble, review, signoff, download`.
5. **Tests:** add/update `pytest` tests under `tests/`, named
   `test_story_<id>_<short-description>.py` for story-scoped work (see
   existing files for the pattern). Run via `poetry run pytest`.
6. **Migrations:** any schema change is a new Alembic migration in
   `app/db/migrations/versions/` — never hand-edit `0001_initial_schema.py`.

## 11. If you're asked to rebuild this from scratch

Read, in order: `Design/LOCKED_Design_v1.0.md` → `Design/Database_Schema.md`
→ `Design/Technical_Design_Document.md` (including §11) →
`Design/Architecture_Diagrams.md` → `Design/Figma_Integration.md` →
`Requirements/Requirements_Document.md` → `Implementation/Implementation_Plan.md`
(story by story, in the order listed there) →
`Implementation/Design_Traceability_Matrix.md` (to self-check nothing was
missed). Then compare your output against the existing `app/` tree in this
repo — it is the reference implementation and should match every one of
those documents.
