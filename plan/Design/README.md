# AI Localization Platform - Design Documentation

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Last Updated:** July 24, 2026  
**Status:** ✅ Design Locked (v1.0) — **and fully implemented** at `../../app/`.
`Technical_Design_Document.md` §11 is a later addendum covering four
post-implementation infrastructure extensions (multi-cloud storage/
embeddings, ChromaDB tenant partition key, Poetry, externalized Redis) —
see `../LLM_BUILD_GUIDE.md` §7 for the condensed version.

---

## 📁 Folder Contents

This folder contains all design documentation for the AI Localization Platform project.

### **Documents (read in this order):**

1. **LOCKED_Design_v1.0.md** ⭐ **Authoritative**
   - The locked architecture summary
   - Pipeline + Strategy pattern, artifact types, reliability patterns
   - Concurrency, sizing, deployment, data stores
   - **Start here**

2. **Technical_Design_Document.md** (v2.1)
   - Detailed system architecture & component design
   - API specifications (project/artifact model)
   - Integration, security, deployment, data flow
   - §11 (addendum): post-implementation extensions — multi-cloud storage/
     embeddings, ChromaDB tenant partition key, Poetry, externalized Redis

3. **Database_Schema.md**
   - Canonical PostgreSQL schema (14 tables), ChromaDB collections
   - Indexes, constraints, volumes, maintenance

4. **Architecture_Diagrams.md**
   - Visual views (Mermaid): system context, layered architecture, deployment,
     pipeline, state machine, sequences, sub-pipelines, ER, project model

5. **Figma_Integration.md**
   - Figma design-time prep (plugin), metadata JSON structure, variables/modes,
     runtime rendering/export params, no-match behavior, DB/ChromaDB mapping

> On any discrepancy: **LOCKED_Design_v1.0.md** governs architecture; **Database_Schema.md** governs the schema.

---

## 📖 Design Overview

### **Architecture Style:**
- **Monolithic Python backend** (Phase 1; decomposition-ready)
- **Pipeline + Strategy pattern** (universal stages, artifact strategies)
- **Event-driven** (Redis Pub/Sub → WebSocket)

### **Universal Pipeline:**
```
Process → Orchestrate → Localize → Review → Sign-off → Download
```

### **Key Components:**

1. **Pipeline Framework** — executor, state machine, saga, checkpointing
2. **Strategies** — IFU, Video, UI Resource
3. **Shared Services** — Lokalise, Figma, ChromaDB, image pipeline, Whisper/TTS (video), AI reviewer
4. **Background Processing** — Celery + Redis (1 worker, concurrency=3)
5. **Data Layer** — PostgreSQL, ChromaDB, Redis, S3/GCS

---

## 🛠️ Technology Stack

### **Backend:**
- Python + FastAPI (async) — single monolith
- Celery + Redis (background tasks)

### **Databases:**
- PostgreSQL (relational data)
- ChromaDB (vector similarity, client-server)
- Redis (broker, cache, Pub/Sub)

### **Storage:**
- AWS S3 / GCP Cloud Storage

### **Deployment:**
- Docker Compose (Phase 1) → small Kubernetes (future)

### **Monitoring:**
- Flower (Celery) + optional Prometheus/Grafana

---

## 📊 Design Decisions

### **Why Monolith first?**
- Faster to build/operate at low volume (2–3 concurrent jobs)
- Clear internal boundaries → decompose later if needed

### **Why Pipeline + Strategy?**
- Universal stages with artifact-specific strategies
- High reuse (Lokalise, Figma, ChromaDB, image pipeline)
- Easy to add new artifact types

### **Why Celery + Redis?**
- Long-running jobs, retries, scheduling (Beat), persistence

### **Why PostgreSQL / ChromaDB?**
- PostgreSQL: ACID, JSONB, mature
- ChromaDB: purpose-built vector similarity for image matching

---

## 🔄 Data Flow

### **Supported Artifact Types:**
- **IFU** — extract text + images → image pipeline + Lokalise (parallel) → assemble → review
- **Video** — audio (Whisper→Lokalise→TTS) + subtitles (Lokalise) + image pipeline → FFmpeg assemble
- **UI Resource** — parse JSON/XML/YAML → Lokalise → reconstruct

> IFU generation is **out of scope** for this design.

### **IFU Localization Flow:**
```
Upload → Extract → Classify → Match → Translate → Assemble → Deliver
```

### **Processing Stages:**
1. **Document Processing** (2-5 min)
2. **Image Classification** (5-10 min for 300 images)
3. **ChromaDB Matching** (1-2 min)
4. **Lokalise Upload** (2-3 min)
5. **Translation** (hours to days - external)
6. **Assembly** (5-10 min)
7. **QA Validation** (2-3 min)

**Total Platform Processing:** ~20-30 minutes  
**Total with Translation:** Days (depends on Lokalise)

---

## 🎯 Performance Targets

| Metric | Target |
|--------|--------|
| API Response | < 1 second |
| Image Classification | < 2 seconds/image |
| ChromaDB Match | < 500 ms/image |
| Document Upload | < 30 seconds (100 MB) |
| Job Creation | < 3 seconds |

---

## 🔐 Security Design

### **Authentication:**
- DeepHealth SSO (OAuth 2.0)
- JWT tokens
- No local passwords

### **Authorization:**
- Role-Based Access Control (RBAC)
- 3 roles: Admin, Localization Manager, Viewer

### **Encryption:**
- TLS 1.3 in transit
- Customer responsible for at-rest

### **Audit:**
- All actions logged
- Immutable audit trail
- 1-year retention

---

## 📈 Scalability

### **Current (Phase 1):**
- 1 Celery worker, `concurrency=3` (2–3 concurrent jobs)
- Single host via Docker Compose

### **Future (only if volume grows):**
- Increase Celery concurrency → add workers
- Move to Kubernetes with separate queues (image/video) + HPA
- Managed Redis and PostgreSQL

### **Caching:**
- Redis for hot data (Figma metadata, ChromaDB matches)
- Translation cache for reused images

---

## 🚀 Deployment

### **Environments:**
- **Development:** Docker Compose (laptop)
- **QA/Staging:** Single VM + managed Redis/PostgreSQL (CitiusTech)
- **Production:** Single VM (Docker Compose) or small K8s (Customer)

### **Cloud Platforms:**
- AWS or GCP (customer choice)

### **Estimated Infra Cost:** ~$150/month

---

## 📋 Status

1. ✅ Design locked (LOCKED_Design_v1.0.md)
2. ✅ Database schema (Database_Schema.md) — implemented verbatim
3. ✅ Technical design aligned (Technical_Design_Document.md v2.1, incl. §11 addendum)
4. ✅ Project scaffolding & Docker Compose setup — done
5. ✅ Pipeline framework + IFU/UI Resource strategies — implemented end-to-end

All design here is implemented at `../../app/`. See `../LLM_BUILD_GUIDE.md`
for the full story list and `../Implementation/Implementation_Plan.md` for
acceptance criteria per story.

---

## 👥 Design Team

**Technical Architect:** [Name]  
**Backend Lead:** [Name]  
**Frontend Lead:** [Name]  
**DevOps Lead:** [Name]  
**QA Lead:** [Name]

---

## 📞 Contact

For questions about the design, contact:
- **Technical Architect:** [Email]
- **Project Manager:** [Email]

---

**Last Updated:** July 24, 2026  
**Design Status:** ✅ Locked (v1.0) + §11 addendum — **Implemented**
