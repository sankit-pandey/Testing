# AI Localization Platform - Requirements Documentation

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Last Updated:** July 24, 2026  
**Status:** Draft - Sections 1-6 Complete, Section 7 On Hold. **Implemented**
at `../../app/` — see `../LLM_BUILD_GUIDE.md` for the technical summary.

---

## 📁 Folder Contents

This folder contains all requirements documentation for the AI Localization Platform project.

### **Main Documents:**

1. **Requirements_Document.md**
   - **Primary requirements document**
   - Comprehensive coverage of Sections 1-6
   - Version 1.3 (synced to locked design + implementation notes for the
     post-implementation extensions — Sec 6.2.1, 6.3.2)
   - **Start here for complete requirements**

2. **Requirements_Summary.md** (v1.2)
   - **Executive summary**
   - High-level overview for stakeholders
   - Quick reference guide
   - **Start here for overview**

3. **Open_Items_Tracker.md**
   - **Action items and pending decisions**
   - Status tracking with priorities
   - Dependencies and blockers
   - **Check here for what's pending**

> There is no separate `Requirements_Review_Report.md` in this folder (an
> earlier version of this index referenced one that was never added). The
> quality-review outcome — approved, 3 discrepancies fixed — is folded into
> `Requirements_Document.md`'s own Document Control table (v1.1 row).

---

## 📖 Document Guide

### **For Stakeholders/Executives:**
→ Start with **Requirements_Summary.md**

### **For Technical Team:**
→ Read **Requirements_Document.md**

### **For Project Managers:**
→ Track progress with **Open_Items_Tracker.md**

### **For QA / testing this implementation:**
→ See `../../tests/` and `../Implementation/Design_Traceability_Matrix.md`
(design element → implementing story/test)

---

## 📊 Requirements Coverage

### ✅ **Complete Sections (6 of 7):**

1. **Section 1: Project Scope & Objectives**
   - Business goals and success metrics
   - Target markets and languages
   - In-scope and out-of-scope content types

2. **Section 2: User Roles & Permissions**
   - Knewron roles (Admin, Localization Manager, Viewer)
   - Lokalise users (Translators, Reviewers, SMEs)
   - Role assignment rules

3. **Section 3: Document & Content Types**
   - IFU documents (DOCX format)
   - UI resource files (analysis pending)
   - Training videos (analysis pending)

4. **Section 4: Image Localization Requirements**
   - Hybrid approach (UI screenshots automated, others manual)
   - AI classification (70% confidence threshold)
   - ChromaDB matching (90% similarity threshold)
   - Figma integration

5. **Section 5: Translation & Review Workflow**
   - Lokalise Enterprise integration
   - Workflow stages (Translation → Review → SME → Approval)
   - Webhook + polling mechanisms
   - Quality assurance

6. **Section 6: System Integration & Deployment**
   - Cloud deployment (AWS/GCP)
   - Security and compliance
   - Monitoring and logging
   - Backup and disaster recovery

### ⏸️ **On Hold (1 of 7):**

7. **Section 7: Non-Functional Requirements**
   - SLA requirements
   - Support model
   - Documentation and training
   - User acceptance criteria

---

## 🎯 Key Requirements Highlights

### **Platform Scope:**
- **Knewron:** Orchestration, image/video localization
- **Lokalise:** Text translation, linguistic workflows

### **Phase 1 Content Types:**
- IFU Documents (DOCX only)
- UI Resource Files (formats TBD)
- Training Videos (MP4/MPEG)

### **Image Localization:**
- **Automated:** UI screenshots via Figma
- **Manual:** Diagrams, flowcharts, symbols (offline)

### **Technology Stack:**
- ChromaDB (image matching)
- Lokalise Enterprise (translation)
- Figma (UI screenshot localization)
- OpenAI Whisper (speech-to-text)
- Google Cloud TTS (text-to-speech)

### **Deployment:**
- Customer environment (AWS or GCP)
- Dev/QA/Staging in CitiusTech environment
- Shared responsibility model

---

## 📋 Open Items (High Priority)

1. **Lokalise API POC** - In progress
2. **Webhook specifications** - TBD
3. **UI Resource Files Analysis** - Starting this week
4. **Training Video Analysis** - Pending samples

See **Open_Items_Tracker.md** for complete list.

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | July 19, 2026 | Initial requirements gathering (Sections 1-6) |
| 1.1 | July 19, 2026 | Fixed 3 discrepancies, quality review complete |
| 1.2 | July 20, 2026 | Synced to locked design: one-project-per-language + multi-artifact model, `viewer` role naming, concurrency note |
| 1.3 | July 24, 2026 | Implementation notes added for the post-implementation extensions (Sec 6.2.1 cloud storage/embedding providers, Sec 6.3.2 ChromaDB partition key) — no functional requirement changed |

---

## 👥 Document Ownership

**Requirements Analyst:** [Name]  
**CitiusTech Project Manager:** [Name]  
**DeepHealth Stakeholder:** [Name]  
**Technical Lead:** [Name]

---

## 🔄 Status

1. ✅ Requirements gathering complete (Sections 1-6)
2. ✅ Quality review complete (v1.1 approved)
3. ✅ Technical design complete (`../Design/Technical_Design_Document.md`)
4. ✅ **Implementation complete** (`../../app/`) — see `../LLM_BUILD_GUIDE.md`
5. ⏳ Finalize Section 7 (Non-Functional Requirements) — still on hold
6. ⏳ Resolve remaining open items (see `Open_Items_Tracker.md`) — mostly
   external (Lokalise API confirmation, video samples), not blocking
7. ⏳ UAT / production rollout to DeepHealth

---

## 📞 Contact

For questions or updates to these requirements, contact:
- **Requirements Team:** [Email]
- **Project Manager:** [Email]

---

**Last Updated:** July 24, 2026  
**Document Status:** APPROVED (v1.3) — implemented
