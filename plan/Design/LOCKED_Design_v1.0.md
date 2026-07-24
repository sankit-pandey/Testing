# 🔒 LOCKED Design — AI Localization Platform

**Project:** Knewron AI Localization Platform
**Client:** DeepHealth
**Prepared by:** CitiusTech
**Date:** July 20, 2026
**Version:** 1.1
**Status:** ✅ **APPROVED & LOCKED**

> **Change log**
> - **v1.1 (Jul 20, 2026):** IFU flow corrected — no in-app text extraction; the original DOCX is sent as-is to Lokalise's document upload API (Lokalise extracts + translates text, asynchronously, including human review inside Lokalise). Assembly now replaces the original images in Lokalise's translated DOCX with the localized images. See §4.1.

---

## 1. Purpose

This document is the **authoritative, locked architecture** for Phase 1 of the AI Localization Platform. All implementation must conform to this design. It supersedes any conflicting content in earlier drafts of `Technical_Design_Document.md` (v1.0).

---

## 2. Design Summary

### Architecture Pattern
- **Monolithic Python backend** (Phase 1) — decompose into microservices later if needed
- **Pipeline + Strategy pattern** — universal stages, artifact-specific strategies
- **Event-driven** — real-time UI updates via Redis Pub/Sub + WebSocket
- **Background processing** — Celery + Redis

### Technology Stack
| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (async Python) |
| **Task Queue** | Celery + Redis |
| **Relational DB** | PostgreSQL 15+ + SQLAlchemy |
| **Vector DB** | ChromaDB (client-server mode) |
| **Cache / Broker / Pub-Sub** | Redis |
| **File Storage** | AWS S3 / GCP Cloud Storage |
| **Real-time** | FastAPI WebSocket |
| **Deployment** | Docker Compose → small Kubernetes (later) |

---

## 3. Core Concept: Universal Pipeline

Every artifact flows through the **same six stages**:

```
Process/Extract → Orchestrate → Assemble → Review → Sign-off → Download
```

What changes per artifact type is the **strategy** for each stage (extraction, orchestration, assembly, review). **Orchestrate** is where localization *starts* (fan-out to Lokalise + the image sub-pipeline); **Assemble** combines the translated results into the final artifact.

```python
class Pipeline:
    async def execute(self):
        processed    = await self.strategy.process(artifact)
        orchestrated = await self.strategy.orchestrate(artifact, processed)
        assembled    = await self.strategy.assemble(artifact, orchestrated)
        reviewed     = await self.strategy.review(artifact, assembled)
        approved     = await self.strategy.signoff(artifact, reviewed)
        final        = await self.strategy.download(artifact)
        return final
```

---

## 4. Supported Artifact Types (Locked)

### 4.1 IFU Documents
```
Process:     Extract embedded IMAGES only (NO text extraction). Capture image
             positions/metadata for assembly. Keep the ORIGINAL DOCX intact.
Orchestrate: (parallel)
               Document: send the ORIGINAL DOCX as-is to the Lokalise document
                         upload API. Lokalise extracts + translates the text.
                         This is ASYNC — Lokalise includes human review of the
                         text; completion is signalled via webhook + polling.
               Images:   Image localization sub-pipeline (see §5)
Assemble:    Take the Lokalise-translated DOCX and REPLACE the
             original images with the localized images.
Review:      AI review → Human review (if issues)  [on the assembled document]
Sign-off:    Human approval
Download:    Presigned URL
```
> **Text handling:** The platform never parses/extracts IFU text itself. Text
> extraction, translation, and translator/reviewer workflow all happen **inside
> Lokalise** via the document upload API. Our pipeline only orchestrates images
> and re-assembles the final document.

### 4.2 Training Videos
```
Process:     Extract audio + subtitles + image frames
Orchestrate: (parallel)
               Audio:     Whisper (STT) → Lokalise → TTS
               Subtitles: Lokalise
               Images:    Image localization pipeline (reused)
Assemble:    Video assembly (FFmpeg)
Review:      AI review → Human review
Sign-off:    Human approval
Download:    Presigned URL
```

### 4.3 UI Resource Files
```
Process:     Parse JSON / XML / YAML / Properties / RESX → extract translatable strings
Orchestrate: Send strings → Lokalise
Assemble:    Reconstruct resource file with translations
Review:      AI review → Human review
Sign-off:    Human approval
Download:    Presigned URL
```
> Exact formats confirmed after UI resource analysis (Requirements §3.3).

> **Note:** IFU generation is **out of scope** for this design.

---

## 5. Image Localization Sub-Pipeline (Reused by IFU + Video)

```
For each image:
  1. Classify (UI screenshot vs non-UI)
  2. ChromaDB match → get Figma frame/coordinates (≥ 90% similarity)
  3. Check translation cache (hash + target language)
       → hit: reuse cached translated image
  4. Get text nodes from Figma
  5. Send text + image to Lokalise
  6. Wait for Lokalise completion
  7. Render translated image from Figma
  8. AI review of rendered image → auto-fix issues
  9. Human review (if flagged)
 10. Cache translated image for reuse
 11. Mark ready for assembly
Non-UI images → flagged for manual handling
```

---

## 6. Reusability Matrix

| Component | IFU | Video | UI Resource |
|-----------|:---:|:-----:|:-----------:|
| Pipeline framework | ✅ | ✅ | ✅ |
| State machine | ✅ | ✅ | ✅ |
| Event bus / WebSocket updates | ✅ | ✅ | ✅ |
| Lokalise service | ✅ | ✅ | ✅ |
| Image localization pipeline | ✅ | ✅ | — |
| Figma service | ✅ | ✅ | — |
| ChromaDB service | ✅ | ✅ | — |
| Translation cache | ✅ | ✅ | — |
| AI reviewer | ✅ | ✅ | ✅ |
| Whisper (STT) | — | ✅ | — |
| TTS | — | ✅ | — |
| FFmpeg assembler | — | ✅ | — |
| Resource parser (JSON/XML/YAML) | — | — | ✅ |

---

## 7. Reliability Patterns (Locked)

| Pattern | Purpose |
|---------|---------|
| **State Machine** | Enforce valid stage transitions; clear audit trail |
| **Saga / Compensation** | Roll back partial orchestration on failure |
| **Circuit Breaker** | Protect against Lokalise / Figma / Whisper / TTS failures |
| **Idempotency** | Safe retries; webhook deduplication (Redis keys) |
| **Checkpointing** | Resume from last successful stage, not from scratch |
| **Webhook + Polling hybrid** | Lokalise completion via webhook, 15-min polling fallback |

---

## 8. Concurrency & Sizing (Locked)

- **Expected load:** 2–3 concurrent localization requests (max)
- **Not latency-critical** (long-running jobs, hours acceptable)
- **Workers:** 1 Celery worker, `concurrency=3` (single queue)
- **Celery Beat:** 1 instance for polling / cleanup schedules

**Deployment path:**
| Environment | Setup |
|-------------|-------|
| Development | Docker Compose (all services on one machine) |
| Staging (CitiusTech) | Single VM + managed Redis/PostgreSQL |
| Production (Customer) | Single VM (Docker Compose) or small K8s cluster |

**Estimated infra cost:** ~$150/month.

**Scaling path (future):** increase concurrency → add workers → move to K8s with specialized queues (image/video) only if volume grows significantly.

---

## 9. Data Stores (Locked)

| Store | Type | Role | Persistence |
|-------|------|------|-------------|
| **PostgreSQL** | Relational | Primary data (projects, artifacts, stages, tasks, audit) | Permanent |
| **ChromaDB** | Vector | Image similarity matching (embeddings) | Permanent |
| **Redis** | In-memory | Celery broker/results, cache, Pub/Sub, idempotency | Ephemeral |
| **S3 / GCS** | Object storage | Source files, extracted/translated images, final artifacts | Permanent |

> Full schema in `Database_Schema.md`.
> Project model: **one project per product per target language**; a project contains **one or more artifacts**.

---

## 10. High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Application                     │
│   REST API   │   WebSocket   │   Webhook receivers        │
└──────┬──────────────┬──────────────────┬─────────────────┘
       │ queue tasks   │ real-time         │ external events
       ▼               │ updates           ▼
┌──────────────────────────────────────────────────────────┐
│                         Redis                             │
│  Celery broker/results │ Cache │ Pub/Sub │ Idempotency    │
└──────┬───────────────────────────────────────────────────┘
       │ pull tasks
       ▼
┌──────────────────────────────────────────────────────────┐
│           Celery Worker (1 worker, concurrency=3)         │
│                + Celery Beat (scheduler)                  │
└──────┬───────────────────────────────────────────────────┘
       ▼
┌──────────────────────────────────────────────────────────┐
│         Pipeline Framework (Process→…→Download)           │
│         State Machine │ Saga │ Checkpointing              │
└──────┬───────────────────────────────────────────────────┘
       ▼
┌──────────────────────────────────────────────────────────┐
│      Strategies:   IFU   │   Video   │   UI Resource      │
└──────┬───────────────────────────────────────────────────┘
       ▼
┌──────────────────────────────────────────────────────────┐
│  Integration Services (Circuit Breakers)                  │
│  Lokalise │ Figma │ ChromaDB │ Whisper │ TTS │ SSO        │
└──────┬───────────────────────────────────────────────────┘
       ▼
┌──────────────────────────────────────────────────────────┐
│  Data:  PostgreSQL │ ChromaDB │ Redis │ S3/GCS            │
└──────────────────────────────────────────────────────────┘
```

---

## 11. Project Structure (Locked)

```
knewron-localization/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/v1/                  # REST routes, WebSocket, webhooks
│   ├── core/                    # config, security, events
│   ├── pipeline/                # base, executor, state_machine, saga, checkpoint
│   ├── strategies/              # factory + ifu/ video/ ui_resource/
│   ├── services/                # lokalise, figma, chromadb, whisper, tts,
│   │                            #   document_processor, image_processor,
│   │                            #   assembler, storage, notification
│   ├── tasks/                   # Celery tasks
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # Pydantic schemas
│   ├── db/                      # session, migrations (Alembic)
│   └── utils/                   # circuit_breaker, retry, idempotency, tracing
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 12. Non-Functional Requirements (Locked)

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| API response | < 1 s | FastAPI async |
| Image classification | < 2 s/image | AI model (GPU optional) |
| ChromaDB match | < 500 ms/image | Client-server mode |
| Concurrent jobs | 2–3 (Phase 1) | Celery concurrency=3 |
| Availability | 99% | Single VM sufficient |
| Encryption in transit | TLS/HTTPS | Required |
| Encryption at rest | Not required | Customer responsibility |
| Audit logging | All actions | PostgreSQL, 1-year retention |
| Application logs | 30 days default | Configurable |
| RTO | < 4 hours | Restore from backup |
| RPO | < 24 hours | Daily backups |

---

## 13. Key Design Decisions (Locked)

1. **Monolith first** — faster delivery; clear boundaries for later extraction.
2. **Celery + Redis** — long-running tasks, retries, scheduling, persistence.
3. **Pipeline + Strategy** — universal stages, reusable services, easy extension.
4. **Event-driven UI** — Redis Pub/Sub → WebSocket for live progress.
5. **State machine** — valid transitions only.
6. **Saga** — transactional orchestration with compensation.
7. **Circuit breakers** — resilience against external services.
8. **Idempotency** — safe retries + webhook dedup.
9. **Checkpointing** — resume from last successful stage.
10. **Simple deployment** — Docker Compose / single VM for expected volume.

---

## 14. Out of Scope (Phase 1)

- IFU document **generation**
- Public API access (UI only)
- GitLab integration
- Encryption at rest

---

**Status:** ✅ **LOCKED** — Ready for implementation planning.
