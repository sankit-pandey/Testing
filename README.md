# Knewron AI Localization Platform — Backend

Monolithic **Python + FastAPI** backend implementing the AI Localization Platform
for DeepHealth, per the locked design in `../plan/Design/` (this repo's
authoritative source of truth — see `../plan/README.md` and
`../.github/copilot-instructions.md`), extended with **multi-tenancy**,
**multi-cloud storage/embeddings**, and **Poetry** dependency management
per direct follow-up instruction (beyond the original single-tenant locked
design — see §6 below for what changed and why).

**Implements:** foundations, core domain/API, pipeline framework (state
machine, checkpointing, resilience, parallel join barrier), real-time
WebSocket progress, Lokalise/ChromaDB/Figma/Storage integrations, the image
localization sub-pipeline, the **IFU** and **UI Resource** strategies
end-to-end, AI + human review/sign-off, per-artifact download, audit
logging, notifications, observability, and multi-tenancy.

**Out of scope (per `Implementation_Plan.md`):** Video localization
(Whisper/TTS/FFmpeg), IFU document generation, public API access, GitLab
integration, encryption at rest (for infrastructure — application-level
secrets in `system_settings` are encrypted; see §6).

---

## 1. Stack

Python 3.11+ · FastAPI · Celery + Redis (managed, not containerized — see §6) ·
PostgreSQL 15 + SQLAlchemy 2 + Alembic · ChromaDB (client-server) ·
AWS S3 / Google Cloud Storage / local filesystem (dev) · Poetry · Docker Compose.

## 2. Local setup

```bash
cp .env.example .env        # fill in Lokalise/Figma/SSO secrets as available
docker compose up --build   # api, celery_worker, celery_beat, db, chromadb, flower
```

Redis is **not** part of docker-compose (see §6) — run one yourself for local
dev (`docker run -d --name dev-redis -p 6379:6379 redis:7-alpine`) or point
`REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` in `.env` at a managed
instance.

- API: http://localhost:8000/docs (OpenAPI, auto-generated)
- Flower (Celery monitoring): http://localhost:5555
- Health: `curl http://localhost:8000/health` and `/health/ready` (DB+Redis check)

### Database migrations

```bash
alembic upgrade head          # apply the schema (0001 locked schema + 0002 multi-tenant)
alembic revision -m "..."     # new migration (hand-write DDL or autogenerate against a live DB)
```

### Dependency management (Poetry)

```bash
poetry install                        # core deps only
poetry install -E gcp -E ml           # + GCS storage/Vertex AI embeddings + local CLIP
poetry run uvicorn app.main:app --reload
poetry run celery -A app.tasks.celery_app worker --concurrency=3 --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
```

`Dockerfile` accepts `--build-arg POETRY_EXTRAS="gcp ml"` to bake extras into
an image.

## 3. Tests

Requires a disposable PostgreSQL database and Redis (the schema uses
Postgres-only types — UUID/JSONB/INET — so SQLite is not viable). Point
`DATABASE_URL`/`DATABASE_URL_SYNC`/`REDIS_URL` at them (see
`tests/conftest.py` for defaults), then:

```bash
poetry run pytest --cov=app --cov-report=term-missing
```

CI (`.github/workflows/ci.yml`) runs Postgres + Redis as service containers,
applies migrations, lints with `ruff`, and runs the suite.

## 4. Project structure

```
app/
├── main.py                  # FastAPI entry point
├── api/v1/                  # REST routes, WebSocket, webhooks, tenant admin
├── core/                    # config, security, logging, RBAC, crypto
├── pipeline/                # executor, state machine, checkpointing, join barrier
├── strategies/               # ifu/, ui_resource/ (video deferred)
├── services/                 # lokalise, figma, chromadb, storage, embeddings,
│                             #   document_processor, image pipeline, assembler,
│                             #   review, notifications, tenant
├── tasks/                    # Celery tasks + beat schedule
├── models/                   # SQLAlchemy models (Database_Schema.md's 14 tables
│                             #   + tenants + tenant_id extensions)
├── schemas/                  # Pydantic request/response schemas
├── db/                       # session, Alembic migrations
└── utils/                    # circuit breaker, retry, idempotency, saga
tests/                        # pytest — one file per story where practical
```

## 5. Design conformance notes

Table/column names, enums, thresholds, and flows follow `../plan/Design/`
exactly (see each module's docstring for the specific section cited). Two
explicitly-flagged, minimal deviations were necessary and are documented
inline where they occur:

- `projects.metadata.source_language` — `Technical_Design_Document.md`'s
  example request body includes `sourceLanguage`, but `Database_Schema.md`
  (higher authority) has no such column; it's stored in the JSONB
  `metadata` column rather than dropped or added as an unauthorized column.
- Artifact-level status values follow the granular state machine in
  `Architecture_Diagrams.md` §5 (as Story 2.2's own Design Refs direct),
  which is richer than the summary value list in `Database_Schema.md`'s
  column comment — that column has no CHECK constraint, so both are
  consistent with the schema itself.

Known placeholders pending real ML assets (clearly marked in code, swappable
behind stable interfaces): the UI-screenshot classifier (heuristic pending a
trained model — none exists yet, per `Technical_Design_Document.md` §2.1.3),
the default (`clip`) image embedding backend needs a model download, and the
AI image reviewer implements the structural/completeness checks that don't
require a vision-QA model.

## 6. Extensions beyond the locked design

Four capabilities were added by direct follow-up instruction, **beyond**
`Database_Schema.md`/`LOCKED_Design_v1.0.md` (which assumed one customer
deployment, S3-only storage, `pip`, and a containerized Redis). Each is
additive/config-driven — none change any of the stories in §5 above.

1. **Multi-cloud storage** (`STORAGE_BACKEND=local|s3|gcs` in `.env`) — see
   `app/services/storage_service.py`. GCS needs `poetry install -E gcp`.
2. **Multi-cloud embeddings** (`AI_EMBEDDING_BACKEND=clip|phash|aws|gcp`) —
   see `app/services/embeddings.py`. `aws` uses Bedrock Titan Multimodal
   Embeddings (no extra dep — `boto3` is core); `gcp` uses Vertex AI
   multimodal embeddings (needs `poetry install -E gcp`).
3. **Multi-tenancy** — a `tenants` table plus `tenant_id` on `users`,
   `products`, `figma_images`, `translation_cache`, `audit_logs`, and
   `system_settings` (migration `0002_multi_tenant`); everything else
   (`projects`, `project_artifacts`, ...) is scoped transitively via
   `product_id -> products.tenant_id`. See `app/models/tenants.py` for the
   rationale on each table. Highlights:
   - Login is tenant-scoped (`tenantSlug` on `/auth/sso/login-url` and
     `/auth/sso/callback`); a platform `is_superuser` flag (orthogonal to
     `role`) manages tenants via `/api/v1/tenants` (`app/api/v1/endpoints/tenants.py`).
   - Each tenant can override Lokalise/Figma credentials
     (`PUT /tenants/{id}/settings`, stored in `system_settings` with
     `is_encrypted` support via `app/core/crypto.py`); `LokaliseService`/
     `FigmaService` resolve the artifact's tenant override first, falling
     back to the platform-wide `.env` default (`app/services/tenant_service.py`).
   - Every product/project/artifact/finding/approval lookup 404s (never 403s)
     across tenants, so cross-tenant UUID guessing can't confirm existence.
4. **Poetry** replaces `requirements.txt` (`pyproject.toml`); `sentence-transformers`
   (CLIP) and the GCP SDKs are optional extras (`ml`, `gcp`) so a minimal
   install stays light.

Redis was removed from `docker-compose.yml` — it now always points at an
external instance via `.env` (a managed one in staging/prod, a locally-run
container in dev), matching `LOCKED_Design_v1.0.md` §7.3's own future-scaling
note about managed Redis; the design's Docker Compose topology otherwise
included it as a convenience for local dev only.
