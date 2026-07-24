# AI Localization Platform - Executive Summary

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Date:** July 19, 2026  
**Version:** 1.0  

---

## Project Overview

The **Knewron AI Localization Platform** automates the localization of complex healthcare product documentation, UI resources, and training videos for DeepHealth's global market expansion.

### Primary Objective
**Reduce time-to-market** for global product launches through automated localization workflows.

### Phase 1 Target Market
- **Primary:** Hungary (Hungarian language)
- **Expansion:** All major EU languages

---

## Key Features

### 1. Orchestration & Workflow Management
- Centralized platform for managing localization projects
- One project per product per target language; each project holds one or more artifacts
- Per-artifact status tracking and independent delivery (partial completion)
- Integration with Lokalise for text translation

### 2. AI-Powered Image Localization
- **AI image classification** (70% confidence threshold)
- **ChromaDB vector matching** for UI screenshots (90% similarity)
- **Figma integration** for automated image generation
- **Translation reuse** to reduce costs and time

### 3. Hybrid Approach
- **Automated:** UI screenshots via Figma
- **Manual:** Diagrams, flowcharts, symbols (offline process)
- **Quality validation:** AI flags issues, humans review

### 4. Enterprise Translation Workflow
- **Lokalise Enterprise** integration
- **Multi-stage review:** Translation → Linguistic Review → Clinical SME → Approval
- **Translation Memory** shared across products
- **Glossary management** by DeepHealth team

---

## Scope

### In Scope (Phase 1)
✓ IFU Documents (DOCX format)  
✓ UI Resource Files (formats TBD)  
✓ Training Videos (MP4/MPEG)  
✓ UI Screenshot localization (Figma-based)  
✓ Text translation (Lokalise-based)  

### Out of Scope (Phase 1)
✗ PDF documents  
✗ User Guides  
✗ GitLab integration (manual upload/download)  
✗ Non-UI image localization (manual offline process)  
✗ API access (UI only)  
✗ IFU document generation (future phase)  

---

## User Roles

| Role | Who | Access Level |
|------|-----|--------------|
| **Admin** | CitiusTech | Full system access, configuration |
| **Localization Manager** | CitiusTech | Full job management |
| **Viewer** | DeepHealth | Read-only status monitoring |
| **Translators/Reviewers/SMEs** | LSP/CitiusTech | Lokalise only (not Knewron) |

---

## Technology Stack

### Core Platform
- **Knewron Platform** - Orchestration
- **ChromaDB** - Image matching (vector database); partitioned by an optional
  `tenant_id` metadata key for shared deployments (config-driven, not a
  relational multi-tenancy model — see Technical Design §11.3)
- **SQL Database** - Metadata storage
- **Object Storage** - S3, GCS, or local filesystem (dev), selected at
  runtime via config (Technical Design §11.1)

### AI & ML
- **AI Image Classification** - Detect UI screenshots
- **Image Embeddings** - CLIP (local), Amazon Bedrock Titan, or Google Vertex
  AI, selected at runtime via config (Technical Design §11.2)
- **OpenAI Whisper** - Speech-to-text (videos)
- **Google Cloud TTS** - Text-to-speech (videos)

### Integrations
- **Lokalise Enterprise** - Translation management
- **Figma** - UI screenshot localization
- **DeepHealth SSO** - Authentication

### Infrastructure
- **Cloud:** AWS or GCP (customer choice)
- **Deployment:** Customer environment (production)
- **Dev/QA/Staging:** CitiusTech environment

---

## Workflow Summary

### IFU Document Localization

```
1. Upload DOCX → 2. Extract Images → 3. AI Classify Images
                                           ↓
                              ┌────────────┴────────────┐
                              ↓                         ↓
                    UI Screenshots              Non-UI Images
                    (Automated)                 (Manual/Offline)
                         ↓
                    4. ChromaDB Match (90%)
                         ↓
                    5. Figma Generate
                         ↓
                    6. Image-Localized Doc
                         ↓
                    7. Send to Lokalise
                         ↓
        8. Translation → Review → SME → Approval
                         ↓
                    9. Assemble Final Doc
                         ↓
                    10. Download
```

---

## Key Metrics & Targets

### Performance
- **Concurrent users:** < 10 (CitiusTech team)
- **Concurrent requests:** typically 2–3 (design sizing); upper bound < 10
- **UI response time:** < 1 second

### Reliability
- **RTO:** < 4 hours
- **RPO:** < 24 hours
- **Backup frequency:** Daily

### Data Retention
- **Source documents:** Temporary (deleted after processing)
- **Translated documents:** Temporary
- **Translated images:** Permanent (for reuse)
- **Audit logs:** 1 year
- **Application logs:** 30 days (configurable)

---

## Security & Compliance

### Authentication
✓ DeepHealth SSO integration  
✓ No separate user database  

### Encryption
✓ In transit: TLS/HTTPS (all connections)  
✓ At rest: Not required (customer environment)  

### Data Classification
✓ No PHI/PII data  
✓ Product documentation and UI strings only  

### Audit
✓ All user and system actions logged  
✓ Immutable, exportable, searchable  
✓ 1-year retention  

---

## Success Criteria

### Business Goals
- Reduce time-to-market for global launches
- Reduce cost per language
- Improve translation quality/accuracy

### Technical Goals
- Automated UI screenshot localization
- Reuse translations across products
- Seamless Lokalise integration
- Scalable for unknown volume

### Quality Goals
- Preserve exact formatting (regulatory compliance)
- AI-assisted quality validation
- Human review for critical content
- Side-by-side preview before delivery

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| **Figma API unavailable** | Queue and retry, then fail job with notification |
| **ChromaDB unavailable** | Fail job immediately, critical dependency |
| **Lokalise delays** | No timeout, wait indefinitely, per-artifact delivery |
| **Image not in Figma** | Treat as manual process, don't fail job |
| **Unknown volume** | Scalable architecture, configurable concurrency |

---

## Open Items

### High Priority
1. Lokalise API POC (in progress)
2. Webhook specifications (TBD)
3. UI resource files analysis (starting this week)
4. Training video analysis (pending samples)

### Medium Priority
5. Progress indicators (UI/UX design)
6. Figma API rate limits (recommend 5-10 concurrent)
7. Processing time targets (TBD)

### Deferred to Future Phases
8. GitLab integration
9. API access
10. Section 7: Non-Functional Requirements

---

## Next Steps

1. **Complete open items** (Lokalise POC, UI/video analysis)
2. **Finalize Section 7** (SLAs, support, training)
3. **Create technical design** based on requirements
4. **Develop CI/CD pipeline** (new pipeline needed)
5. **Build and test** (unit, integration, E2E)
6. **Deploy to customer environment** (production)

---

## Contact

**CitiusTech Team:**
- Project Manager: [TBD]
- Technical Lead: [TBD]
- Localization Manager: [TBD]

**DeepHealth Team:**
- Product Owner: [TBD]
- Design Team: [TBD] (Figma maintenance)
- Glossary Manager: [TBD]

---

**Document Version:** 1.2  
**Last Updated:** July 24, 2026  
**Status:** Draft - Sections 1-6 Complete, Section 7 On Hold (synced to locked design).
Implementation complete at `knewron-localization/`; see `Requirements_Document.md`
v1.3 and `Technical_Design_Document.md` §11 for the post-implementation
infrastructure extensions (multi-cloud storage/embeddings, ChromaDB tenant
partition key, Poetry, externalized Redis).
