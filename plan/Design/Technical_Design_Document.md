# AI Localization Platform - Technical Design Document

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Prepared by:** CitiusTech (Technical Design)  
**Date:** July 24, 2026  
**Version:** 2.1  
**Status:** Locked (§1–§10) + Addendum (§11, post-implementation extensions)

> **Authoritative design:** This document reflects the **LOCKED architecture** (see `LOCKED_Design_v1.0.md`). It supersedes the v1.0 draft. Illustrative code snippets are pseudocode; the canonical backend implementation language is **Python (FastAPI)**. §1–§10 remain locked as approved; **§11 is an addendum** documenting infrastructure extensions implemented by direct client instruction after the initial build — see §11 for scope and rationale.

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | July 19, 2026 | Technical Architect | Initial technical design based on Requirements v1.1 |
| 2.0 | July 20, 2026 | Technical Architect | Aligned to LOCKED design: monolithic Python/FastAPI, Pipeline + Strategy pattern, Celery + Redis, one-project-per-language model, simplified deployment. DB section now references `Database_Schema.md`. |
| 2.1 | July 24, 2026 | Technical Architect | Full implementation delivered at `knewron-localization/` (all stories, `Implementation_Plan.md`). Added §11 addendum: multi-cloud storage/embedding provider abstraction, Poetry dependency management, Redis externalized from Docker Compose, and a ChromaDB-only `tenant_id` partition key (not relational multi-tenancy — no schema change to `Database_Schema.md`'s 14 tables). §3.2 ChromaDB metadata schema updated to include `tenant_id`; §7 deployment table updated to drop the `redis` compose service. |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Design](#2-component-design)
3. [Database Design](#3-database-design)
4. [API Design](#4-api-design)
5. [Integration Design](#5-integration-design)
6. [Security Design](#6-security-design)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Data Flow Design](#8-data-flow-design)
11. [Post-Implementation Extensions (Addendum)](#11-post-implementation-extensions-addendum)

---

## Executive Summary

This document provides the technical design for the **Knewron AI Localization Platform**, translating business requirements into a detailed technical architecture. The platform is a **monolithic Python backend** (Phase 1) built around a **universal Pipeline + Strategy** engine that automates localization workflows for IFU documents, UI resource files, and training videos. It is structured with clear internal boundaries so it can be decomposed into microservices in a later phase if volume requires it.

### Key Design Principles:
- **Simplicity first:** Monolithic Phase 1, sized for 2–3 concurrent jobs
- **Reusability:** Shared services and a common pipeline across all artifact types
- **Extensibility:** Strategy pattern for adding new artifact types
- **Reliability:** State machine, saga/compensation, circuit breakers, idempotency, checkpointing
- **Real-time:** Event-driven UI updates via Redis Pub/Sub + WebSocket
- **Security:** SSO, RBAC, TLS in transit

### Technology Stack:
- **Backend:** Python + FastAPI (async)
- **Task Queue:** Celery + Redis
- **Database:** PostgreSQL (metadata), ChromaDB (vectors)
- **Cache / Broker / Pub-Sub:** Redis
- **Storage:** AWS S3 / GCP Cloud Storage
- **Deployment:** Docker Compose → small Kubernetes (later)
- **Monitoring:** Flower (Celery) + optional Prometheus/Grafana

---

## 1. System Architecture

### 1.1 High-Level Architecture

The platform is a **single deployable Python application** (FastAPI) with **Celery workers** for background processing. Internal modules have clear boundaries (pipeline, strategies, services) to enable future decomposition.

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

### 1.2 Architectural Patterns

#### 1.2.1 Monolithic (Phase 1)
- **Single codebase & deployable:** Faster to build, test, and operate at low volume (2–3 concurrent jobs)
- **Clear internal boundaries:** `pipeline/`, `strategies/`, `services/` modules map cleanly to future services
- **Decomposition-ready:** Extract to microservices later only if volume demands

#### 1.2.2 Pipeline + Strategy Pattern
- **Universal pipeline:** Process → Orchestrate → Assemble → Review → Sign-off → Download
- **Artifact strategies:** IFU, Video, UI Resource implement each stage differently
- **High reuse:** Shared services (Lokalise, Figma, ChromaDB, image pipeline) used across strategies

#### 1.2.3 Event-Driven Updates
- **Asynchronous processing:** Celery tasks; non-blocking API
- **Redis Pub/Sub → WebSocket:** Real-time progress to the UI
- **Audit trail:** All state changes persisted in PostgreSQL

#### 1.2.4 Reliability Patterns
- **State machine:** Enforce valid stage transitions
- **Saga/compensation:** Roll back partial orchestration on failure
- **Circuit breaker:** Protect external services (Lokalise, Figma, Whisper, TTS)
- **Idempotency:** Safe retries + webhook deduplication
- **Checkpointing:** Resume from last successful stage

#### 1.2.5 API-First Design
- **RESTful APIs:** Standard HTTP methods, versioned (`/api/v1`)
- **OpenAPI:** Auto-generated by FastAPI
- **UI-only in Phase 1:** No public/external API access

---

## 2. Component Design

> All components run **inside the single Python/FastAPI application**. "Service" below denotes an internal module/class, not a separate deployable. Code samples are illustrative pseudocode.

### 2.0 Pipeline Framework & Strategy Pattern

**Responsibility:** Provide a universal execution engine shared by all artifact types.

**Universal stages:** `Process → Orchestrate → Assemble → Review → Sign-off → Download`

```python
class BaseStrategy(ABC):
    async def process(self, artifact): ...
    async def orchestrate(self, artifact, processed): ...
    async def assemble(self, artifact, orchestrated): ...
    async def review(self, artifact, assembled): ...
    async def signoff(self, artifact, reviewed): ...
    async def download(self, artifact): ...

class Pipeline:
    def __init__(self, artifact, strategy):
        self.artifact = artifact
        self.strategy = strategy
        self.state_machine = StateMachine()
        self.event_bus = EventBus()

    async def execute(self):
        ctx = await self.load_checkpoint(self.artifact["id"]) or {}
        for stage in STAGES_FROM(ctx.get("last_stage")):
            await self._run(stage, ctx)          # emits events, updates state
            await self.save_checkpoint(self.artifact["id"], stage, ctx)
        return ctx
```

**Strategy factory:**
```python
class StrategyFactory:
    @staticmethod
    def create(artifact_type):
        return {
            "IFU": IFUStrategy,
            "VIDEO": VideoStrategy,
            "UI_RESOURCE": UIResourceStrategy,
        }[artifact_type]()
```

**Cross-cutting:** State machine, saga/compensation, circuit breakers, idempotency, and checkpointing wrap every stage (see §1.2.4).

---

### 2.1 Core Components

#### 2.1.1 Job Orchestration (API + Tasks)

**Responsibility:** Manage project/artifact lifecycle and dispatch pipelines.

**Technology:** Python + FastAPI (API) + Celery (background execution)

**Model:** A **project** targets **one** language/market and contains **one or more artifacts**. Each artifact runs its own pipeline and can complete/download independently (partial completion supported).

**Key endpoints (see §4 for full contracts):**
```
POST   /api/v1/projects                 # create project (single target language)
POST   /api/v1/projects/{id}/artifacts  # add artifact(s); can add after start
GET    /api/v1/artifacts/{id}           # artifact status/progress
DELETE /api/v1/artifacts/{id}           # cancel a single artifact
```

**Dispatch:**
```python
@router.post("/projects/{project_id}/artifacts")
async def add_artifact(project_id: str, body: ArtifactCreate):
    artifact = create_artifact(project_id, body)
    execute_pipeline.delay(str(artifact.id))   # Celery
    return artifact
```

**Database tables:** `projects`, `project_artifacts`, `artifact_stages`, `artifact_subtasks` (see `Database_Schema.md`).

**Artifact state machine:**
```
pending → processing → orchestrating → assembling
  → reviewing → (needs_human_review) → signoff
  → complete / failed / cancelled
(failed → processing on retry; checkpoint resumes last good stage)
```

---

#### 2.1.2 Document Processor Service

**Responsibility:** Extract **embedded images** from IFU documents for the image
sub-pipeline, and re-assemble the final document. **Text is never extracted** by
the platform — the original DOCX is sent as-is to Lokalise's document upload API,
which performs text extraction, translation, and human review internally (async).

**Technology:** Python + python-docx

**Key Functions:**
- Extract embedded images + their positions (for later re-insertion)
- Generate lightweight image metadata (hash, position) — **no text parsing**
- Keep the original DOCX intact for upload to Lokalise
- Assemble: replace original images in the Lokalise-translated DOCX with localized images

**Processing Pipeline:**
```python
class DocumentProcessor:
    def process_ifu(self, docx_file):
        # NOTE: no text extraction — the original DOCX goes to Lokalise as-is.
        # 1. Extract embedded images + positions (for the image sub-pipeline)
        images = self.extract_images(docx_file)   # includes position + hash

        # 2. Lightweight manifest (images only; original DOCX preserved)
        manifest = {
            "metadata": self.extract_metadata(docx_file),  # doc-level only
            "images": images,
            "source_docx": docx_file,   # sent as-is to Lokalise
        }
        return manifest

    def assemble(self, translated_docx, localized_images):
        # Replace the original images in Lokalise's translated DOCX
        # with the localized versions, matched by position/hash.
        return self.replace_images(translated_docx, localized_images)
```

**Output Format:**
```json
{
  "documentId": "uuid",
  "metadata": {
    "title": "IFU Document",
    "pages": 306,
    "imageCount": 300
  },
  "sections": [
    {
      "sectionId": "1",
      "title": "Introduction",
      "content": "...",
      "images": ["img_001.png", "img_002.png"]
    }
  ],
  "images": [
    {
      "imageId": "img_001",
      "filename": "screenshot_login.png",
      "position": "section_1_para_3",
      "hash": "sha256_hash"
    }
  ]
}
```
> **Note:** `sections`/`text` above are illustrative doc-level metadata only. The
> platform does **not** extract or store translatable text — that is handled
> entirely by Lokalise via the document upload API.

---

#### 2.1.3 AI Image Classifier Service

**Responsibility:** Classify images as UI screenshots vs non-UI

**Technology:** Python + TensorFlow/PyTorch

**Model Architecture:**
```python
class ImageClassifier:
    def __init__(self):
        self.model = self.load_model()
        self.confidence_threshold = 0.70  # Configurable
    
    def classify_image(self, image_path):
        # Load and preprocess image
        image = self.preprocess(image_path)
        
        # Run inference
        prediction = self.model.predict(image)
        
        # Interpret results
        result = {
            "imageId": "img_001",
            "classification": "ui_screenshot",  # or "non_ui"
            "confidence": 0.85,
            "needsReview": False  # True if < threshold
        }
        
        return result
```

**Training Data:**
- UI screenshots (positive samples)
- Diagrams, flowcharts, logos (negative samples)
- Minimum 1000 samples per category

**Model Performance Targets:**
- Accuracy: > 90%
- Precision: > 85%
- Recall: > 85%

---

#### 2.1.4 ChromaDB Image Matching Service

**Responsibility:** Match UI screenshots using vector similarity

**Technology:** Python + ChromaDB

**Vector Embedding:**
```python
class ImageMatcher:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name="ui_screenshots",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_image(self, image_id, image_path, metadata):
        # Generate embedding
        embedding = self.generate_embedding(image_path)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[image_id],
            embeddings=[embedding],
            metadatas=[metadata]
        )
    
    def find_matches(self, image_path, product_id, threshold=0.90):
        # Generate embedding for query image
        query_embedding = self.generate_embedding(image_path)
        
        # Search with product filter
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"product_id": product_id}
        )
        
        # Filter by threshold
        matches = [
            r for r in results 
            if r['distance'] >= threshold
        ]
        
        return matches
```

**Metadata Schema:**
```json
{
  "imageId": "uuid",
  "productId": "product_a",
  "screenName": "login_screen",
  "figmaFrameId": "frame_123",
  "figmaFileKey": "file_abc",
  "textElements": ["Username", "Password", "Login"],
  "translations": {
    "hu": "translation_id_1",
    "de": "translation_id_2"
  },
  "lastUpdated": "2026-07-19T10:00:00Z",
  "version": "1.0"
}
```

---

#### 2.1.5 Figma Integration Service

**Responsibility:** Interface with Figma API for image generation

**Technology:** Python (httpx/requests) + Figma REST API. Wrapped by a circuit breaker and rate limiter.

**Key Operations (illustrative pseudocode):**
```javascript
class FigmaService {
  constructor(accessToken) {
    this.token = accessToken;
    this.baseUrl = 'https://api.figma.com/v1';
  }
  
  // Get Figma file metadata
  async getFile(fileKey) {
    const response = await fetch(
      `${this.baseUrl}/files/${fileKey}`,
      { headers: { 'X-Figma-Token': this.token } }
    );
    return response.json();
  }
  
  // Update variable values (translations)
  async updateVariables(fileKey, variables) {
    // variables = { "var_username": "Felhasználónév" }
    const response = await fetch(
      `${this.baseUrl}/files/${fileKey}/variables`,
      {
        method: 'POST',
        headers: { 'X-Figma-Token': this.token },
        body: JSON.stringify({ variables })
      }
    );
    return response.json();
  }
  
  // Export frame as PNG
  async exportFrame(fileKey, frameId, scale=3) {
    const response = await fetch(
      `${this.baseUrl}/images/${fileKey}?ids=${frameId}&scale=${scale}&format=png`,
      { headers: { 'X-Figma-Token': this.token } }
    );
    const data = await response.json();
    return data.images[frameId]; // Returns image URL
  }
  
  // Rate limiting
  async withRateLimit(fn) {
    // Implement exponential backoff
    // Max 5-10 concurrent requests
  }
}
```

**Rate Limiting Strategy:**
```javascript
class RateLimiter {
  constructor(maxConcurrent = 5, retryCount = 3) {
    this.maxConcurrent = maxConcurrent;
    this.retryCount = retryCount;
    this.queue = [];
    this.active = 0;
  }
  
  async execute(fn) {
    if (this.active >= this.maxConcurrent) {
      await this.waitForSlot();
    }
    
    this.active++;
    try {
      return await this.retry(fn);
    } finally {
      this.active--;
      this.processQueue();
    }
  }
  
  async retry(fn, attempt = 0) {
    try {
      return await fn();
    } catch (error) {
      if (attempt < this.retryCount) {
        await this.delay(Math.pow(2, attempt) * 1000);
        return this.retry(fn, attempt + 1);
      }
      throw error;
    }
  }
}
```

---

#### 2.1.6 Lokalise Integration Service

**Responsibility:** Interface with Lokalise API for translation

**Technology:** Python (httpx/requests) + Lokalise REST API. Wrapped by a circuit breaker; webhook + 15-min polling fallback with idempotency.

**Key Operations (illustrative pseudocode):**
```javascript
class LokaliseService {
  constructor(apiToken, projectId) {
    this.token = apiToken;
    this.projectId = projectId;
    this.baseUrl = 'https://api.lokalise.com/api2';
  }
  
  // Upload content for translation
  async uploadContent(content, targetLanguages) {
    const keys = content.map(item => ({
      key_name: item.key,
      platforms: ["web"],
      translations: [
        {
          language_iso: "en",
          translation: item.sourceText
        }
      ],
      context: item.context,
      screenshots: item.screenshots
    }));
    
    const response = await fetch(
      `${this.baseUrl}/projects/${this.projectId}/keys`,
      {
        method: 'POST',
        headers: { 
          'X-Api-Token': this.token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ keys })
      }
    );
    
    return response.json();
  }
  
  // Download translations
  async downloadTranslations(languageIso) {
    const response = await fetch(
      `${this.baseUrl}/projects/${this.projectId}/files/download`,
      {
        method: 'POST',
        headers: { 'X-Api-Token': this.token },
        body: JSON.stringify({
          format: 'json',
          original_filenames: false,
          filter_langs: [languageIso]
        })
      }
    );
    
    const data = await response.json();
    return data.bundle_url; // Download URL
  }
  
  // Poll for completion
  async pollStatus(taskId, interval = 15000) {
    while (true) {
      const status = await this.getTaskStatus(taskId);
      
      if (status === 'completed') {
        return { status: 'completed' };
      } else if (status === 'failed') {
        throw new Error('Translation failed');
      }
      
      await this.delay(interval);
    }
  }
  
  // Webhook handler
  handleWebhook(payload, signature) {
    // Verify webhook signature
    if (!this.verifySignature(payload, signature)) {
      throw new Error('Invalid webhook signature');
    }
    
    // Process webhook event
    const event = JSON.parse(payload);
    return {
      eventType: event.event,
      projectId: event.project.id,
      language: event.language.lang_iso,
      status: event.task.status
    };
  }
}
```

---

#### 2.1.7 Assembly Engine Service

**Responsibility:** Assemble final localized documents

**Technology:** Python + python-docx

**Assembly Process:**
```python
class AssemblyEngine:
    def assemble_document(self, manifest, translations, images):
        # 1. Load original document structure
        structure = manifest['structure']
        
        # 2. Create new document
        doc = Document()
        
        # 3. Apply translations
        for section in structure['sections']:
            # Replace text
            translated_text = translations[section['textKey']]
            doc.add_paragraph(translated_text)
            
            # Replace images
            for img_ref in section['images']:
                if img_ref in images:
                    doc.add_picture(images[img_ref])
        
        # 4. Preserve formatting
        self.apply_formatting(doc, structure['formatting'])
        
        # 5. Validate
        self.validate_document(doc, manifest)
        
        return doc
    
    def validate_document(self, doc, manifest):
        # Check completeness
        assert doc.paragraphs.count >= manifest['expectedParagraphs']
        
        # Check images
        assert len(doc.inline_shapes) >= manifest['expectedImages']
        
        # Check tables
        assert len(doc.tables) == manifest['expectedTables']
        
        # Check formatting
        self.validate_formatting(doc, manifest)
```

---

### 2.2 Supporting Services

#### 2.2.1 Notification Service
- Email notifications
- In-app notifications
- Webhook callbacks

#### 2.2.2 Audit Service
- Log all user actions
- Log all system events
- Immutable audit trail

#### 2.2.3 Monitoring Service
- Celery/task monitoring (Flower)
- Optional metrics (Prometheus) + dashboards (Grafana)
- Alerting on job failure rate / queue depth

---

### 2.3 Artifact-Specific Components

#### 2.3.1 Image Localization Pipeline (reused by IFU + Video)
Classify → ChromaDB match → cache check → Figma text → Lokalise → render → AI review → human review → cache. See `LOCKED_Design_v1.0.md` §5.

#### 2.3.2 Video Components
- **Whisper Service** — speech-to-text (Python)
- **TTS Service** — text-to-speech, e.g. Google Cloud TTS (Python)
- **Video Assembler** — combine tracks via FFmpeg (Python)

#### 2.3.3 UI Resource Components
- **Resource Parser** — JSON/XML/YAML/Properties/RESX parse + reconstruct (Python). Exact formats confirmed after UI resource analysis (Requirements §3.3).

---

## 3. Database Design

### 3.1 PostgreSQL Schema

> **Canonical schema:** The full, authoritative PostgreSQL schema (DDL, indexes, constraints, volumes, maintenance) lives in **`Database_Schema.md`**. The tables below are a summary only; `Database_Schema.md` prevails on any discrepancy.

**Project model:** One **project** per product per **single** target language/market; a project contains **one or more artifacts**. (This replaces the earlier multi-language `localization_jobs` / `job_languages` model.)

**Core tables (14):**

| Table | Purpose |
|-------|---------|
| `users` | Accounts (DeepHealth SSO) |
| `products` | Products requiring localization |
| `projects` | One per product per target language |
| `project_artifacts` | Artifacts (IFU, VIDEO, UI_RESOURCE) within a project |
| `artifact_stages` | Pipeline stage tracking per artifact |
| `artifact_subtasks` | Parallel sub-tasks (image/audio/subtitle/assembly) |
| `image_processing` | Per-image classification, match, translation status |
| `figma_images` | Figma frame metadata for ChromaDB matching/reuse |
| `translation_cache` | Cached translated images (hash + language) |
| `lokalise_tasks` | Lokalise task tracking (webhook + polling) |
| `review_findings` | AI & human review findings |
| `approvals` | Sign-off approvals |
| `audit_logs` | Comprehensive audit trail (1-year retention) |
| `system_settings` | Application configuration (encrypted secrets) |

**Key relationships:** `products → projects → project_artifacts → {artifact_stages, artifact_subtasks, image_processing, lokalise_tasks, review_findings, approvals}`.

---

### 3.2 ChromaDB Collections

**ui_screenshots Collection**
```python
collection_metadata = {
    "hnsw:space": "cosine",  # Similarity metric
    "hnsw:construction_ef": 200,
    "hnsw:M": 16
}

# Document metadata schema
metadata_schema = {
    "image_id": "uuid",
    "product_id": "uuid",
    "tenant_id": "string",  # §11.3 addendum — ChromaDB-only partition key,
                            # default "default"; NOT a relational tenant model
    "screen_name": "string",
    "figma_frame_id": "string",
    "figma_file_key": "string",
    "text_elements": ["array", "of", "strings"],
    "translations": {
        "hu": "translation_id",
        "de": "translation_id"
    },
    "last_updated": "timestamp",
    "version": "string"
}
```

> **§11.3 addendum:** every query filters on `product_id` **and** `tenant_id`
> together (`$and`); `tenant_id` is stamped on write from `CHROMADB_TENANT_ID`
> (`.env`, default `"default"`). See §11.3 for full rationale.

---

## 4. API Design

### 4.1 REST API Endpoints

#### 4.1.1 Project & Artifact APIs

> **Model:** A **project** targets a **single** language/market and holds **one or more artifacts**. Artifacts can be added after the project starts and complete/download independently (partial completion). This replaces the earlier multi-language `jobs` API.

**Create Project**
```http
POST /api/v1/projects
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "productId": "uuid",
  "projectName": "German IFU Translation",
  "sourceLanguage": "en",
  "targetLanguage": "de",
  "targetMarket": "DE"
}

Response: 201 Created
{
  "projectId": "uuid",
  "status": "pending",
  "createdAt": "2026-07-20T10:00:00Z"
}
```

**Add Artifact(s) to Project**
```http
POST /api/v1/projects/{projectId}/artifacts
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "artifactType": "IFU",              // IFU | VIDEO | UI_RESOURCE
  "artifactName": "IFU_Product_A.docx",
  "sourceUploadUrl": "presigned-url"
}

Response: 201 Created
{
  "artifactId": "uuid",
  "status": "pending",
  "createdAt": "2026-07-20T10:01:00Z"
}
```

**Get Project Status** (aggregates its artifacts)
```http
GET /api/v1/projects/{projectId}
Authorization: Bearer {token}

Response: 200 OK
{
  "projectId": "uuid",
  "productId": "uuid",
  "projectName": "German IFU Translation",
  "targetLanguage": "de",
  "status": "in_progress",            // pending | in_progress | partial_complete | complete | cancelled
  "progressPercent": 65,
  "artifacts": [
    { "artifactId": "uuid", "artifactType": "IFU", "status": "complete",    "progressPercent": 100 },
    { "artifactId": "uuid", "artifactType": "VIDEO", "status": "in_progress", "progressPercent": 58 },
    { "artifactId": "uuid", "artifactType": "UI_RESOURCE", "status": "pending", "progressPercent": 0 }
  ],
  "createdAt": "2026-07-20T10:00:00Z",
  "updatedAt": "2026-07-20T14:30:00Z"
}
```

**Get Artifact Status** (per-stage detail)
```http
GET /api/v1/artifacts/{artifactId}
Authorization: Bearer {token}

Response: 200 OK
{
  "artifactId": "uuid",
  "artifactType": "IFU",
  "status": "reviewing",
  "progressPercent": 71,
  "stages": [
    { "stage": "process",     "status": "complete" },
    { "stage": "orchestrate", "status": "complete" },
    { "stage": "assemble",    "status": "complete" },
    { "stage": "review",      "status": "in_progress" }
  ]
}
```

**List Projects**
```http
GET /api/v1/projects?status=in_progress&productId=uuid&page=1&limit=20
Authorization: Bearer {token}

Response: 200 OK
{
  "projects": [...],
  "pagination": { "page": 1, "limit": 20, "total": 45, "totalPages": 3 }
}
```

**Cancel a Single Artifact**
```http
DELETE /api/v1/artifacts/{artifactId}
Authorization: Bearer {token}

Response: 200 OK
{ "artifactId": "uuid", "status": "cancelled", "cancelledAt": "2026-07-20T15:00:00Z" }
```

---

#### 4.1.2 Image Management APIs

**Get Image Classification Results**
```http
GET /api/v1/artifacts/{artifactId}/images
Authorization: Bearer {token}

Response: 200 OK
{
  "jobId": "uuid",
  "totalImages": 300,
  "classified": {
    "ui_screenshots": 50,
    "non_ui": 250
  },
  "needsReview": 15,
  "images": [
    {
      "imageId": "uuid",
      "filename": "screenshot_001.png",
      "classification": "ui_screenshot",
      "confidence": 0.92,
      "needsReview": false,
      "chromadbMatch": {
        "matched": true,
        "similarity": 0.95,
        "matchedImageId": "uuid",
        "existingTranslations": ["hu", "de"]
      }
    }
  ]
}
```

**Update Image Classification**
```http
PATCH /api/v1/images/{imageId}/classification
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "classification": "ui_screenshot",
  "userOverride": true
}

Response: 200 OK
```

---

#### 4.1.3 Download APIs

**Download a Completed Artifact** (each artifact downloads independently)
```http
GET /api/v1/artifacts/{artifactId}/download
Authorization: Bearer {token}

Response: 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="IFU_Product_A_de.docx"

[Binary file — DOCX / MP4 / JSON depending on artifact type]
```

---

### 4.2 WebSocket (Real-time Updates)

Clients subscribe for live pipeline progress; the backend publishes stage/subtask events via Redis Pub/Sub.
```
WS /api/v1/ws/{client_id}

Server → client events:
  stage_started | stage_progress | stage_completed | stage_failed
  subtask_progress | review_required | download_ready
```

---

### 4.3 Webhook APIs

**Lokalise Webhook Receiver**
```http
POST /api/v1/webhooks/lokalise
X-Lokalise-Signature: {signature}
Content-Type: application/json

Request:
{
  "event": "project.translation.updated",
  "project": {
    "id": "123456",
    "name": "DeepHealth Localization"
  },
  "language": {
    "lang_iso": "hu"
  },
  "task": {
    "id": "task_789",
    "status": "completed"
  }
}

Response: 200 OK
{
  "received": true,
  "jobId": "uuid"
}
```

---

## 5. Integration Design

### 5.1 Lokalise Integration

**Integration Flow:**
```
1. Job Created in Knewron
2. Document processed, text extracted
3. Content uploaded to Lokalise
   - Create keys with structured naming
   - Attach reference images
   - Set target languages
4. Lokalise assigns to translators (auto)
5. Translation → Review → SME → Approval
6. Lokalise sends webhook on completion
7. Knewron polls as fallback (15 min)
8. Download translations from Lokalise
9. Assemble final document
```

**Error Handling:**
- Lokalise API errors → Retry 3 times with exponential backoff
- Upload failures → Log and notify Localization Manager
- Webhook failures → Polling fallback activates
- Translation failures → Manual intervention required

---

### 5.2 Figma Integration

**Integration Flow:**
```
1. UI screenshot identified
2. Match in ChromaDB
3. If matched:
   - Retrieve Figma frame ID
   - Update variable values with translations
   - Export frame as PNG (300 DPI)
4. If not matched:
   - Flag for manual Figma creation
   - Treat as non-UI image
```

**Rate Limiting:**
- Max 5-10 concurrent API calls
- Exponential backoff on 429 errors
- Queue requests if limit reached

---

### 5.3 DeepHealth SSO Integration

**Authentication Flow (OAuth 2.0):**
```
1. User clicks "Login"
2. Redirect to DeepHealth SSO
3. User authenticates
4. SSO returns authorization code
5. Exchange code for access token
6. Validate token with SSO
7. Create/update user session
8. Redirect to Knewron dashboard
```

**Token Management:**
- Access token: 1 hour expiry
- Refresh token: 30 days expiry
- Auto-refresh before expiry

---

## 6. Security Design

### 6.1 Authentication & Authorization

**Authentication:**
- SSO via DeepHealth identity provider
- OAuth 2.0 / SAML 2.0
- No local password storage

**Authorization:**
- Role-Based Access Control (RBAC)
- Roles: Admin, Localization Manager, Viewer
- Permissions checked at API gateway

**Session Management:**
- JWT tokens
- Secure, HTTP-only cookies
- CSRF protection

---

### 6.2 Data Security

**Encryption in Transit:**
- TLS 1.3 for all connections
- Certificate pinning for external APIs
- HTTPS only (no HTTP)

**Encryption at Rest:**
- Not required (customer environment)
- Customer responsible for encryption policies

**API Security:**
- API key rotation (90 days)
- Rate limiting per user/IP
- Input validation and sanitization

---

### 6.3 Audit & Compliance

**Audit Logging:**
- All user actions logged
- All system events logged
- Immutable audit trail (append-only)
- 1-year retention

**Compliance:**
- No PHI/PII data
- No specific regulatory requirements (Phase 1)
- Customer responsible for compliance

---

## 7. Deployment Architecture

> **Sizing:** Expected load is **2–3 concurrent localization requests**; the workload is not latency-critical. Deployment is intentionally simple. Kubernetes is a **future option**, not required for Phase 1.

### 7.1 Primary Deployment — Docker Compose (Single Host)

> **§11.4 addendum (as implemented):** Redis is **not** a Docker Compose
> service — `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` always
> point at an external instance (self-run container in dev, managed
> ElastiCache/Memorystore in staging/prod). This pulls forward what §7.2/§7.3
> already described as the staging/scaling posture; see §11.4 for rationale.
> All other services below are unchanged.

All services run on one host via Docker Compose:

| Service | Command | Notes |
|---------|---------|-------|
| `api` | `uvicorn app.main:app` | FastAPI (REST + WebSocket + webhooks) |
| `celery_worker` | `celery -A app.celery_worker worker --concurrency=3` | Single worker, single queue |
| `celery_beat` | `celery -A app.celery_worker beat` | Polling & cleanup schedules |
| `db` | `postgres:15-alpine` | Primary database |
| `chromadb` | `chromadb/chroma` | Vector DB (client-server) |
| `flower` | `celery -A app.celery_worker flower` | Task monitoring (optional) |
| *(external)* `redis` | managed or self-run, not compose | Broker + cache + Pub/Sub — see §11.4 |

```yaml
# docker-compose.yml (abridged; REDIS_URL etc. come from .env, pointing off-host)
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    env_file: [.env]
    environment:
      - DATABASE_URL=postgresql://localization:password@db:5432/localization
      - CHROMADB_HOST=chromadb
    depends_on: [db, chromadb]
  celery_worker:
    build: .
    command: celery -A app.celery_worker worker --loglevel=info --concurrency=3
    env_file: [.env]
    environment:
      - DATABASE_URL=postgresql://localization:password@db:5432/localization
    depends_on: [db, chromadb]
  celery_beat:
    build: .
    command: celery -A app.celery_worker beat --loglevel=info
    env_file: [.env]
  db:      { image: postgres:15-alpine, ports: ["5432:5432"] }
  chromadb:{ image: chromadb/chroma:latest, ports: ["8001:8000"] }
```

### 7.2 Environment Configuration

| Environment | Setup | Notes |
|-------------|-------|-------|
| **Development** | Docker Compose on laptop | All services local; debug logging |
| **Staging (CitiusTech)** | Single VM + managed Redis/PostgreSQL | Info logging |
| **Production (Customer)** | Single VM (Docker Compose) or small K8s | Warn/Error logging; daily backups |

**Indicative sizing:** 8 GB RAM / 4 vCPU (dev); 16 GB RAM / 8 vCPU (prod). Estimated infra cost ~$150/month.

### 7.3 Future Scaling (only if volume grows)

- Increase Celery `concurrency` (3 → 10), then add workers.
- Move to Kubernetes with separate queues (image/video) and HPA on queue depth.
- Managed Redis (ElastiCache/Memorystore) and PostgreSQL (RDS/Cloud SQL).

---

## 8. Data Flow Design

### 8.1 IFU Localization Flow

```
┌─────────────┐
│ User Upload │
│  IFU.docx   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Document Processor                      │
│ - Extract text                          │
│ - Extract images (300 images)           │
│ - Preserve structure                    │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ AI Image Classifier                     │
│ - Classify: 50 UI screenshots           │
│ - Classify: 250 non-UI images           │
│ - Flag: 15 for manual review            │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ ChromaDB Matcher (UI screenshots only)  │
│ - Match 40/50 (80% match rate)          │
│ - New: 10 screenshots                   │
└──────┬──────────────────────────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
  ┌─────────┐  ┌──────────┐  ┌──────────┐
  │ Matched │  │   New    │  │  Non-UI  │
  │ (Reuse) │  │ (Figma)  │  │ (Manual) │
  └────┬────┘  └─────┬────┘  └─────┬────┘
       │             │              │
       └─────────────┴──────────────┘
                     │
                     ▼
       ┌──────────────────────────┐
       │ Send to Lokalise         │
       │ - Document text          │
       │ - UI screenshot text     │
       │ - Reference images       │
       └──────┬───────────────────┘
              │
              ▼
       ┌──────────────────────────┐
       │ Lokalise Workflow        │
       │ Translation → Review     │
       │ → SME → Approval         │
       └──────┬───────────────────┘
              │
              ▼ (Webhook/Poll)
       ┌──────────────────────────┐
       │ Assembly Engine          │
       │ - Merge translations     │
       │ - Insert translated imgs │
       │ - Preserve formatting    │
       └──────┬───────────────────┘
              │
              ▼
       ┌──────────────────────────┐
       │ QA Validation            │
       │ - Completeness check     │
       │ - Format validation      │
       │ - Image quality check    │
       └──────┬───────────────────┘
              │
              ▼
       ┌──────────────────────────┐
       │ Localized IFU Ready      │
       │ IFU_Product_A_hu.docx    │
       └──────────────────────────┘
```

---

## 9. Performance & Scalability

### 9.1 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API Response Time | < 1 second | 95th percentile |
| Document Upload | < 30 seconds | For 100 MB file |
| Image Classification | < 2 seconds | Per image |
| ChromaDB Match | < 500 ms | Per image |
| Figma Export | < 5 seconds | Per image |
| Job Creation | < 3 seconds | End-to-end |

### 9.2 Scalability Strategy

**Horizontal Scaling:**
- Stateless services (scale easily)
- Load balancer distributes traffic
- Auto-scaling based on CPU/memory

**Vertical Scaling:**
- Database (PostgreSQL, ChromaDB)
- Increase resources as needed

**Caching:**
- Redis for frequently accessed data
- CDN for static assets
- API response caching

---

## 10. Monitoring & Observability

### 10.1 Metrics

**Application Metrics:**
- Request rate (requests/second)
- Error rate (errors/second)
- Response time (p50, p95, p99)
- Active jobs count
- Queue depth

**Business Metrics:**
- Jobs created per day
- Jobs completed per day
- Average job duration
- Success rate by content type
- Cost per language

### 10.2 Logging

**Log Levels:**
- ERROR: System errors, failures
- WARN: Recoverable issues
- INFO: Key events (job created, completed)
- DEBUG: Detailed debugging (dev/QA only)

**Log Aggregation:**
- Centralized logging (ELK stack or cloud native)
- Structured logging (JSON format)
- Correlation IDs for tracing

### 10.3 Alerting

**Critical Alerts:**
- Service down
- Database connection failure
- API error rate > 5%
- Job failure rate > 10%

**Warning Alerts:**
- High response time (> 3 seconds)
- Queue depth > 100
- Disk usage > 80%

---

## 11. Post-Implementation Extensions (Addendum)

> **Status:** Implemented at `knewron-localization/`, in addition to (not a
> replacement of) everything in §1–§10. Added by direct client instruction
> after the initial locked build; each is additive/config-driven and changes
> no story's functional behavior, no API contract, and no `Database_Schema.md`
> table. Full rationale and file references also live in
> `knewron-localization/README.md` §6.

### 11.1 Multi-cloud object storage

`STORAGE_BACKEND` (`.env`) selects the backend at runtime — `local` (dev,
filesystem-backed, signed URLs served by the app itself), `s3` (AWS, real
presigned URLs via `boto3`), or `gcs` (Google Cloud Storage, V4 signed URLs
via `google-cloud-storage`, optional `gcp` Poetry extra). All three implement
one interface (`app/services/storage_service.py`: `put_bytes`/`get_bytes`/
`delete`/`exists`/`presign_put`/`presign_get`), so §2.1.2 (Document Processor),
§2.1.7 (Assembly Engine), and every artifact upload/download path in §4 are
unaffected — they call the interface, never a backend directly.

### 11.2 Multi-cloud image embeddings

Appendix B §1 left the embedding model an **open question**, recommending
CLIP. `AI_EMBEDDING_BACKEND` (`.env`) now selects among four implementations
of one interface (`app/services/embeddings.py`):

| Value | Implementation | Notes |
|-------|-----------------|-------|
| `clip` | CLIP via `sentence-transformers` (local model) | Appendix B's own recommendation; needs the `ml` Poetry extra |
| `phash` | Perceptual hash (no model download) | Dependency-light fallback for tests/CI/minimal installs |
| `aws` | Amazon Bedrock Titan Multimodal Embeddings | `boto3` (already a core dependency for §11.1's S3 backend) |
| `gcp` | Vertex AI multimodal embeddings | Needs the `gcp` Poetry extra |

§2.1.4 (ChromaDB Image Matching Service) and §3.2 (ChromaDB Collections) are
otherwise unchanged — the embedding backend only changes how the vector is
produced, not the matching/threshold logic (still ≥ 90%, LOCKED §5).

### 11.3 ChromaDB-only tenant partition key

`CHROMADB_TENANT_ID` (`.env`, default `"default"`) is stamped into every
vector's metadata on write and applied as an additional query filter on
every read, alongside the existing per-product scoping (Requirements
§4.3.1). This is a **namespace for separating environments/deployments that
share one ChromaDB instance** — it is explicitly **not** a relational
multi-tenancy model. There is no `tenants` table, no `tenant_id` column on
any PostgreSQL table, no tenant-scoped authentication, and no per-tenant
credential overrides. `Database_Schema.md`'s 14 tables are unmodified. See
§3.2's metadata schema (updated above) and
`app/services/chromadb_service.py`.

### 11.4 Redis externalized; Poetry dependency management

- **Redis** is not a Docker Compose service (§7.1, updated above);
  `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` always point at an
  external instance. This is the deployment posture §7.2/§7.3 already
  described for staging/scale-up, pulled forward to apply from the first
  deployment rather than only "if volume grows."
- **Poetry** (`pyproject.toml`) replaces `pip -r requirements.txt` as the
  dependency manager, with `gcp` and `ml` as optional extras (§11.1, §11.2)
  so a minimal install doesn't pull in the GCP SDKs or the CLIP model stack
  unless needed. `Dockerfile` accepts `--build-arg POETRY_EXTRAS="gcp ml"`.

---

## Appendix A: Technology Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend** | Python (single monolith) | ML/document/image processing ecosystem; one language, simpler ops |
| **API Framework** | FastAPI | Async, typed (Pydantic), auto OpenAPI, native WebSocket |
| **Task Queue** | Celery + Redis | Long-running jobs, retries, scheduling (Beat), persistence |
| **Database** | PostgreSQL | ACID compliance, JSONB support, mature |
| **Vector DB** | ChromaDB (client-server) | Purpose-built for embeddings; shared across workers |
| **Cache/Broker/PubSub** | Redis | Broker + cache + real-time Pub/Sub in one |
| **Object Storage** | S3 / GCS | Scalable, durable, cost-effective |
| **Deployment** | Docker Compose (→ K8s later) | Right-sized for 2–3 concurrent jobs |
| **Monitoring** | Flower (+ optional Prometheus/Grafana) | Simple task visibility for low volume |
| **CI/CD** | GitLab CI / GitHub Actions | Integrated with version control |

---

## Appendix B: Open Design Questions

1. **Image Embedding Model:** Which pre-trained model for image embeddings?
   - Options: ResNet, EfficientNet, CLIP
   - Recommendation: CLIP (multimodal, good for UI screenshots)

2. **Broker/Queue:** **Decided** — Redis + Celery (single queue). Cloud-native queues deferred to future scaling.

3. **API Gateway:** Not required for Phase 1 (single FastAPI app). Revisit if decomposed into microservices.

4. **Logging:** Structured JSON logs; aggregation via customer-preferred stack (CloudWatch/Stackdriver/ELK) in their environment.

5. **TTS Provider (Video):** Google Cloud TTS vs alternatives — confirm during video phase.

---

**End of Technical Design Document**

---

**Next Steps:**
1. Review and approve technical design
2. Create detailed component specifications
3. Set up development environment
4. Begin implementation (Sprint 1)
