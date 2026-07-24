# AI Localization Platform - Project Overview

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Last Updated:** July 24, 2026  
**Current Phase:** ✅ **Implemented** — see `LLM_BUILD_GUIDE.md` for the
condensed technical brief, or `../README.md` for how to run the code.

---

## 📁 Project Structure

This `plan/` folder is one part of the `knewron-localization/` repository;
the implemented backend lives alongside it at `../app/`.

```
knewron-localization/                 ← repo root
│
├── app/                              ← IMPLEMENTED BACKEND (Python/FastAPI)
├── tests/                            ← pytest suite
├── others/                           ← raw source materials (sample IFU PDF,
│                                        Figma metadata screenshots, extracted
│                                        text) — reference only
├── .github/                          ← coding-convention instruction files
├── pyproject.toml, docker-compose.yml, Dockerfile, alembic.ini, README.md
│
└── plan/                             ← THIS folder (design record)
    ├── LLM_BUILD_GUIDE.md            ← start here (any LLM/agent)
    ├── README.md                     ← narrative tour of this folder
    ├── PROJECT_OVERVIEW.md           ← this file
    │
    ├── Requirements/                 ← Requirements Documentation
    │   ├── README.md
    │   ├── Requirements_Document.md      (v1.3 - main requirements)
    │   ├── Requirements_Summary.md       (v1.2 - executive summary)
    │   └── Open_Items_Tracker.md         (action items)
    │
    ├── Design/                       ← Technical Design
    │   ├── README.md
    │   ├── LOCKED_Design_v1.0.md         (authoritative locked architecture)
    │   ├── Technical_Design_Document.md  (v2.1 - detailed design + §11 extensions addendum)
    │   ├── Database_Schema.md            (canonical DB schema - 14 tables)
    │   ├── Architecture_Diagrams.md      (v1.1 - Mermaid diagrams)
    │   └── Figma_Integration.md
    │
    ├── Implementation/               ← Story backlog + traceability (all ✅ done)
    │   ├── Implementation_Plan.md
    │   └── Design_Traceability_Matrix.md
    │
    ├── rules/                        ← governance rules (tool-agnostic)
    └── UX/                           ← UX mockups & review
```

---

## 🎯 Project Summary

### **What We're Building:**
An AI-powered localization platform that automates the translation of:
- IFU Documents (DOCX format)
- UI Resource Files (JSON, XML, etc.)
- Training Videos (MP4/MPEG)

### **Key Innovation:**
- **Hybrid image localization:** AI classifies images, automates UI screenshots via Figma, flags others for manual handling
- **ChromaDB matching:** Reuses existing translations (90% similarity threshold)
- **Lokalise integration:** Professional translation workflow with review and approval

### **Target Market:**
- **Phase 1:** Hungary (Hungarian language)
- **Expansion:** All major EU languages
- **Platform:** Language-agnostic design

---

## ✅ Completed Work

### **Phase 1: Requirements Gathering** ✅ COMPLETE
- **Duration:** July 19, 2026
- **Deliverables:**
  - Requirements Document v1.2 (6 sections complete)
  - Executive Summary
  - Quality Review Report (9/10 score)
  - Open Items Tracker
- **Status:** APPROVED

### **Phase 2: Technical Design** ✅ COMPLETE
- **Duration:** July 19-20, 2026
- **Deliverables:**
  - Technical Design Document
  - System Architecture
  - Database Schema
  - API Specifications
  - Integration Design
- **Status:** Locked (v1.0), superseded for detail by Technical_Design_Document.md v2.1

### **Phase 3: Implementation** ✅ COMPLETE
- **Duration:** through July 24, 2026
- **Deliverables:**
  - Full backend at `../app/` — all 26 original stories (`0.1`–`7.4`) plus
    5 post-implementation extension stories (`8.1`–`8.5`)
  - Test suite (`../tests/`), CI workflow (`../.github/workflows/ci.yml`)
  - Design_Traceability_Matrix.md fully green (every design element traced
    to an implemented story)
- **Status:** Done — see `LLM_BUILD_GUIDE.md` for the technical summary

---

## 📊 Key Requirements

### **Scope:**
✓ IFU Documents (DOCX only)  
✓ UI Resource Files (formats TBD)  
✓ Training Videos (MP4/MPEG)  
✓ Image Localization (UI screenshots automated)  
✓ Text Translation (via Lokalise)  

### **Out of Scope (Phase 1):**
✗ PDF documents  
✗ GitLab integration (manual upload/download)  
✗ Non-UI image localization (manual offline)  
✗ API access (UI only)  
✗ IFU document generation (future phase)  
✗ Encryption at rest (customer responsibility)  

### **User Roles:**
- **Admin** (CitiusTech) - Full system access
- **Localization Manager** (CitiusTech) - Job management
- **Viewer** (DeepHealth) - Read-only status

---

## 🏗️ Technical Architecture

### **Architecture Style:**
- Monolithic Python backend (Phase 1; decomposition-ready)
- Pipeline + Strategy pattern (universal stages, artifact strategies)
- Event-driven (Redis Pub/Sub → WebSocket)

### **Universal Pipeline:**
`Process → Orchestrate → Localize → Review → Sign-off → Download`

### **Core Components:**
1. **Pipeline Framework** - State machine, saga, checkpointing
2. **Strategies** - IFU, Video, UI Resource
3. **Document Processor** - Extract text and images from DOCX
4. **AI Classifier** - Classify images (70% confidence threshold)
5. **ChromaDB Matcher** - Match UI screenshots (90% similarity)
6. **Figma Connector** - Generate translated images
7. **Lokalise Connector** - Manage translation workflow
8. **Assembly Engine** - Build final localized artifacts

### **Technology Stack:**
- **Backend:** Python + FastAPI (single monolith)
- **Task Queue:** Celery + Redis
- **Database:** PostgreSQL + ChromaDB
- **Storage:** AWS S3 / GCP Cloud Storage
- **Deployment:** Docker Compose (→ small Kubernetes later)
- **Monitoring:** Flower (+ optional Prometheus/Grafana)

---

## 🔄 Workflow

### **IFU Localization Flow:**
```
1. User uploads IFU.docx
2. Extract text and images (300 images)
3. AI classifies images:
   - 50 UI screenshots → Automated
   - 250 non-UI images → Manual
4. ChromaDB matches UI screenshots:
   - 40 matched → Reuse translations
   - 10 new → Generate via Figma
5. Send to Lokalise:
   - Document text
   - UI screenshot text
   - Reference images
6. Lokalise workflow:
   - Translation → Review → SME → Approval
7. Webhook/polling detects completion
8. Assemble final document:
   - Merge translations
   - Insert translated images
   - Preserve formatting
9. QA validation
10. User downloads IFU_hu.docx
```

**Processing Time:**
- Platform: ~20-30 minutes
- Translation (Lokalise): Hours to days

---

## 📈 Success Metrics

### **Business Goals:**
- Reduce time-to-market for global launches
- Reduce cost per language
- Improve translation quality

### **Performance Targets:**
- API response: < 1 second
- Image classification: < 2 seconds/image
- ChromaDB match: < 500 ms/image
- Job creation: < 3 seconds

### **Quality Targets:**
- Translation accuracy: > 95%
- Image match accuracy: > 90%
- Job success rate: > 95%

---

## 🔐 Security & Compliance

### **Authentication:**
- DeepHealth SSO (OAuth 2.0)
- No local passwords

### **Authorization:**
- Role-Based Access Control (RBAC)

### **Data Security:**
- TLS 1.3 in transit
- No PHI/PII data
- Customer responsible for at-rest encryption

### **Audit:**
- All actions logged
- Immutable audit trail
- 1-year retention

---

## 🚀 Deployment

### **Environments:**
- **Dev/QA/Staging:** CitiusTech environment
- **Production:** Customer environment (AWS or GCP)

### **Deployment Model:**
- Docker Compose on a single host (Phase 1)
- 1 Celery worker (concurrency=3) sized for 2–3 concurrent requests
- Scaling path to Kubernetes only if volume grows
- Estimated infra cost ~$150/month

### **Shared Responsibility:**
- **CitiusTech:** Application, monitoring, support
- **Customer:** Infrastructure, network, backups

---

## 📋 Open Items

Still genuinely open (unresolved requirements-level questions, not blocking
what was built — see `Requirements/Open_Items_Tracker.md` for current
detail):
1. Webhook payload specifications from Lokalise (exact events/fields) — the
   implementation follows the illustrative shape in
   `Technical_Design_Document.md` §4.3 pending confirmation.
2. UI resource file format confirmation (implemented for
   JSON/XML/YAML/Properties/RESX per Requirements §3.3's expected list).
3. Training video samples/specs (Video remains out of scope — §9 of
   `LLM_BUILD_GUIDE.md`).
4. Regulatory-symbol translation policy (Requirements §4.1, "Type 3: TBD").
5. Section 7 (Non-Functional Requirements) — still on hold, per
   `Requirements_Document.md`.

Resolved since the last version of this document: cloud platform choice
(AWS/GCP) is now a concrete, config-driven implementation (`Technical_Design`
§11.1–§11.2), and GitLab integration / public API access remain deferred by
design (not accidentally missing).

---

## 🎯 Status & Next Steps

**Implementation is complete.** What used to be "next steps" here (review
design, set up dev environment, implement, test, deploy) has all happened —
see §"Completed Work" above and `LLM_BUILD_GUIDE.md` for the technical
summary. Remaining forward-looking items are genuinely open questions, not
build tasks:

1. Resolve the open items above (mostly external: Lokalise API details, UI
   resource/video samples from the client).
2. UAT with DeepHealth against the running backend.
3. Production deployment to the customer's cloud environment (AWS or GCP —
   both are supported per §11.1–§11.2; select via `.env`).
4. Post-launch support & monitoring.

If you are an LLM/agent picking this up: don't restart "Sprint 1" or
re-scaffold the project — the code already exists at `../app/`. Read
`LLM_BUILD_GUIDE.md` first.

---

## 👥 Team

### **CitiusTech:**
- **Project Manager:** [Name]
- **Technical Architect:** [Name]
- **Backend Lead:** [Name]
- **Frontend Lead:** [Name]
- **DevOps Lead:** [Name]
- **QA Lead:** [Name]
- **Localization Manager:** [Name]

### **DeepHealth:**
- **Product Owner:** [Name]
- **Design Team:** [Name] (Figma maintenance)
- **Glossary Manager:** [Name]

---

## 📞 Contact

**Project Inquiries:**
- CitiusTech PM: [Email]
- DeepHealth PO: [Email]

**Technical Questions:**
- Technical Architect: [Email]

**Requirements Updates:**
- Requirements Analyst: [Email]

---

## 📚 Documentation Index

### **Start here:**
- [LLM Build Guide](LLM_BUILD_GUIDE.md) - dense, self-contained technical brief (any LLM/agent)
- [Design & Planning README](README.md) - narrative tour of this folder

### **Requirements:**
- [Requirements Document](Requirements/Requirements_Document.md) - Complete requirements (v1.3)
- [Requirements Summary](Requirements/Requirements_Summary.md) - Executive overview (v1.2)
- [Open Items](Requirements/Open_Items_Tracker.md) - Pending decisions

### **Design:**
- [LOCKED Design](Design/LOCKED_Design_v1.0.md) - Authoritative locked architecture ⭐
- [Technical Design](Design/Technical_Design_Document.md) - Detailed system design (v2.1, §11 = post-implementation extensions)
- [Database Schema](Design/Database_Schema.md) - Canonical DB schema (14 tables)
- [Architecture Diagrams](Design/Architecture_Diagrams.md) - Mermaid diagrams (v1.1)
- [Figma Integration](Design/Figma_Integration.md) - Figma metadata/rendering contract
- [Design Overview](Design/README.md) - Design summary & index

### **Implementation status:**
- [Implementation Plan](Implementation/Implementation_Plan.md) - full story backlog, all ✅ done
- [Design Traceability Matrix](Implementation/Design_Traceability_Matrix.md) - design element → story mapping

### **Reference:**
- `../others/` - raw source materials (sample IFU PDF, Figma metadata
  screenshots, extracted text) — reference only, not authoritative
- Sample IFU: `../others/DH_Diagnostic_Suite_IFU_US.pdf`

---

## 🏆 Project Status

| Phase | Status | Completion |
|-------|--------|------------|
| **Requirements** | ✅ Complete | 100% (6 of 7 sections; Section 7 on hold) |
| **Design** | ✅ Complete | 100% (+ §11 post-implementation addendum) |
| **Development** | ✅ Complete | 100% (all stories `0.1`–`8.5`) |
| **Testing** | ✅ Complete | `../tests/`, CI green (`.github/workflows/ci.yml`) |
| **Deployment** | ⏳ Not started | 0% — UAT/production rollout to DeepHealth still pending |

**Overall Project:** ~95% Complete (Requirements + Design + Development + Testing done; UAT/production deployment remaining)

---

## 🎉 Achievements

✅ Comprehensive requirements gathered (114 pages)  
✅ Technical design completed and locked  
✅ Database schema defined (14 tables) and implemented verbatim  
✅ API specifications created and implemented (REST + WebSocket + webhooks)  
✅ Integration design completed and implemented (Lokalise, Figma, ChromaDB, SSO)  
✅ Security design finalized and implemented (SSO/JWT/RBAC, audit logging)  
✅ Deployment architecture defined and implemented (Docker Compose, Poetry, CI)  
✅ **Full backend built, tested, and running** — see `../app/` and `LLM_BUILD_GUIDE.md`  
✅ Four post-implementation infrastructure extensions delivered (§11 addendum)  

---

**Implementation phase is complete.** Remaining work is UAT and production
rollout, not further development, unless new requirements emerge.

---

**Last Updated:** July 24, 2026  
**Document Owner:** Project Manager  
**Next Review:** Upon UAT kickoff or new requirements
