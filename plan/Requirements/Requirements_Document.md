# AI Localization Platform - Requirements Document

**Project:** Knewron AI Localization Platform  
**Client:** DeepHealth  
**Prepared by:** CitiusTech (Requirements Analysis)  
**Date:** July 19, 2026  
**Version:** 1.3  
**Status:** Draft - Section 7 Pending (Sections 1-6 + implementation notes below are current)

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | July 19, 2026 | Requirements Analyst | Initial requirements gathering (Sections 1-6) |
| 1.1 | July 19, 2026 | Requirements Analyst | Fixed 3 discrepancies: clarified image sources (Sec 1.3.1, 3.2.1), ChromaDB scope (Sec 6.3.2) |
| 1.2 | July 20, 2026 | Requirements Analyst | Synced to locked design: adopted **one project per target language + multiple artifacts** model (Sec 1.5, 2.2, 5.6, 5.7); role naming `viewer`; concurrency note (Sec 6.9). |
| 1.3 | July 24, 2026 | Technical Architect | Implementation complete (`knewron-localization/`). Added implementation notes to Sec 6.2.1 (cloud storage/embedding provider choice, both now concrete and config-driven) and Sec 6.3.2 (ChromaDB partition key). No functional requirement changed — see `Technical_Design_Document.md` §11 for full detail. |

---

## Table of Contents

1. [Project Scope & Objectives](#1-project-scope--objectives)
2. [User Roles & Permissions](#2-user-roles--permissions)
3. [Document & Content Types](#3-document--content-types)
4. [Image Localization Requirements](#4-image-localization-requirements)
5. [Translation & Review Workflow](#5-translation--review-workflow)
6. [System Integration & Deployment](#6-system-integration--deployment)
7. [Non-Functional Requirements](#7-non-functional-requirements) *(On Hold)*
8. [Open Items & Pending Decisions](#8-open-items--pending-decisions)

---

## Executive Summary

The **Knewron AI Localization Platform** is an orchestration and image/video localization platform designed to accelerate global product launches for DeepHealth's healthcare products. The platform automates the localization of complex technical documentation (IFUs), UI resource files, and training videos while integrating with Lokalise for text translation and Figma for image localization.

### Key Objectives:
- **Reduce time-to-market** for global product launches
- **Reduce localization costs** through automation and reuse
- **Improve translation quality** through AI-assisted workflows
- **Ensure regulatory compliance** for medical device documentation

### Phase 1 Scope:
- **IFU Documents** (DOCX format)
- **UI Resource Files** (common web app formats)
- **Training Videos** (MP4/MPEG)
- **Target Market:** Hungary (Hungarian language) with EU expansion
- **Platform:** Language-agnostic design supporting any target language

---

## 1. Project Scope & Objectives

### 1.1 Business Goals

**Primary Objective:**  
Reduce time-to-market for global product launches

**Success Metrics:**
- Localization turnaround time reduction
- Cost per language reduction
- Translation accuracy/quality scores
- *(Specific target numbers to be defined during implementation)*

### 1.2 Target Market & Languages

**Requirements Principle:**  
✓ Platform must be **language-agnostic** and support any target language/market  
✓ No hard-coded language dependencies  
✓ Configurable for any language supported by Lokalise and TTS/Speech services

**Phase 1 Business Context:**
- **Initial deployment market:** Hungary (Hungarian language)
- **Planned expansion:** All major EU languages (DE, FR, ES, IT, NL, PT, PL, SV, DA, FI, CS, HU)

**Design Requirements:**
- Support dynamic language selection
- Allow adding new languages without code changes
- Handle right-to-left (RTL) languages if needed in future
- Support Unicode and special characters for all languages

### 1.3 In-Scope Content Types (Phase 1)

#### 1.3.1 IFU Documents
- **Format:** DOCX only
- **Characteristics:** Variable size (10-300+ pages), complex formatting, regulatory content
- **Embedded Images:**
  - **UI screenshots:** Figma sources only (automated localization)
  - **Non-UI images:** Manual process offline (diagrams, flowcharts, symbols, logos)
  - **No OCR fallback** in Phase 1
  - *(See Section 4 for detailed image localization strategy)*

#### 1.3.2 UI Resource Files
- **Status:** Analysis starting this week
- **Expected Formats:** JSON, XML, Properties, YAML, RESX (common web app formats)
- **Requirements:** TBD after analysis

#### 1.3.3 Training Videos
- **Formats:** MP4/MPEG
- **Localization Scope:**
  - Audio narration (voice-over replacement)
  - Subtitles/captions
  - On-screen text/graphics replacement (Figma-based only)
- **Requirements:** TBD (samples not yet available)

### 1.4 Out of Scope (Phase 1)

✗ PDF documents (IFU or User Guides)  
✗ User Guides (any format)  
✗ PowerPoint presentations  
✗ Marketing materials  
✗ Advanced video editing  
✗ Images from non-Figma sources  
✗ OCR-based image localization  
✗ IFU document **generation** (future phase)  

### 1.5 Localization Project & Artifact Model

**Confirmed structure (aligns with locked design):**

✓ **One project per localization request** = one **product** + one **target language/market**  
  - To localize a product into multiple languages, create **multiple projects** (one per language)  
✓ **A project contains one or more artifacts** to be localized (IFU, UI resource file, video)  
✓ **Artifacts are the unit of processing and delivery:**  
  - Artifacts can be **added after the project starts**  
  - Each artifact is processed **independently** and can be **downloaded as it completes** (partial completion)  
  - A failed artifact does **not** block others in the same project  
✓ **Same source file** may be used across different projects (e.g., same IFU in a German project and a French project), each producing an independent translation  

**Project status:** `pending → in_progress → partial_complete → complete` (or `cancelled`).  
**Artifact status:** `pending → processing → complete` (or `failed` / `cancelled`).

---

## 2. User Roles & Permissions

### 2.1 Platform Scope Clarification

**Knewron Platform Responsibilities:**
1. Orchestration - Workflow management and coordination
2. Image Localization - Figma-based image translation
3. Video Localization - Audio/subtitle/graphics replacement
4. Integration - Connect source systems with Lokalise

**Lokalise Platform Responsibilities:**
1. Text Translation - All document text translation
2. Translation Workflow - Translator assignment, review, approval
3. Linguistic Team Management - Translators, reviewers, Clinical SMEs
4. Regulatory Review - Clinical SMEs work within Lokalise

### 2.2 Knewron Platform Roles

#### Role 1: Admin
**Who:** CitiusTech users only

**Permissions:**
- User management
- System configuration
- Product and project setup
- Integration configuration (GitLab, Figma, Lokalise)
- Can perform Localization Manager tasks (but as separate action)
- Access to all features

#### Role 2: Localization Manager
**Who:** CitiusTech users

**Permissions (Full rights on localization projects):**
- Create localization projects (one project per product per target language/market)
- Add one or more artifacts (IFU, UI resource, video) to a project — including after it has started
- Upload source artifacts
- Monitor project and per-artifact status
- Cancel/retry individual artifacts; cancel projects
- Download completed artifacts individually (partial completion)
- View reports and dashboards

#### Role 3: Viewer
**Who:** DeepHealth users

**Permissions (Read-only):**
- View job status
- View progress/dashboard
- Download completed artifacts (if permitted)

**Cannot:**
- Create or modify jobs
- Upload artifacts
- Change configurations

### 2.3 Lokalise Users (Not in Knewron)

- Translators (LSP or in-house)
- Linguistic reviewers
- Clinical SMEs (have Lokalise accounts)
- Project managers
- CitiusTech coordinators/Localization managers

### 2.4 Role Assignment Rules

✓ **Per user** (global across all products)  
✓ Admin and Localization Manager are **separate roles**  
✓ Admin **can perform** Localization Manager actions when needed  
✓ One user cannot have both Admin and Localization Manager roles simultaneously  

### 2.5 User Access Summary

| User Type | Knewron Access | Lokalise Access | Primary Activities |
|-----------|----------------|-----------------|-------------------|
| **CitiusTech Admins** | Full admin rights | Admin/Config | System management |
| **CitiusTech Loc Managers** | Full job management | Monitor status | Orchestrate localization |
| **CitiusTech Linguistic Team** | None | Translator/Reviewer/SME | Translation & review |
| **DeepHealth Users** | Viewer (status only) | None or limited | Monitor progress |

---

## 3. Document & Content Types

### 3.1 IFU Document Specifications

#### 3.1.1 Format & Structure
✓ **DOCX format only** for Phase 1  
✓ **Standard template structure** with consistent sections:
  - Cover page, TOC, Terminology, Symbols, Regulatory, Content, Appendix

#### 3.1.2 Content Complexity (Based on Sample Analysis)

**Sample IFU Analyzed:** DH_Diagnostic_Suite_IFU_US.pdf
- **Total Pages:** 306 pages
- **File Size:** 17.5 MB
- **Images:** ~300+ images
- **Document ID:** IFU-024.001
- **Version:** 1.3.0

**Content Features:**
✓ **Tables:** Yes - must preserve structure exactly  
✓ **Hyperlinks:** Yes - internal and external, must maintain  
✓ **Footnotes/Endnotes:** Not observed in sample  
✓ **Headers/Footers:** Yes - need translation (product name, dates)  
✓ **Special Formatting:** Yes - bold, colors, WARNING/NOTICE boxes  
✓ **Lists:** Yes - numbered, bulleted, multi-level  

#### 3.1.3 File Specifications
- **IFU size:** **Variable** - depends on product nature
  - Sample analyzed: 306 pages, 17.5 MB, 300+ images
  - Could be smaller or larger depending on product
- **Maximum file size:** **100 MB** (recommended to handle large IFUs)
- **Must preserve:** Exact layout, formatting, regulatory symbols

#### 3.1.4 Regulatory Compliance
**Standards Referenced in Sample IFU:**
- FDA 21 CFR Part 820 (Quality Management System)
- ISO 13485 (Medical devices - Quality management)
- IEC 62304 (Medical device software lifecycle)
- IEC 82304-1 (Health software - Product safety)
- ISO 14971 (Risk management for medical devices)
- ISO 15223-1 (Medical device symbols)
- IEC 62366-1 (Usability engineering)

**Implication:** All formatting, warnings, symbols must be preserved exactly

### 3.2 Embedded Image Specifications

#### 3.2.1 Image Sources
✓ **UI screenshots from Figma** (confirmed)  
✓ **Non-UI images NOT in Figma** (diagrams, flowcharts, symbols, logos, photos)  
✓ **If UI screenshot not in Figma:** Flag for manual handling  

**IMPORTANT:** Only product UI screens are available in Figma. All other image types require manual offline translation process. *(See Section 4.1 for detailed hybrid approach)*  

#### 3.2.2 Image Types (From Sample Analysis)
- Logos and regulatory symbols
- UI screenshots with annotations
- Flowcharts and diagrams
- Warning/caution graphics
- ISO symbols

#### 3.2.3 Image Characteristics
- **Formats:** PNG/JPG (standard for document embedding)
- **Resolution:** Print quality required (300 DPI for regulatory docs)
- **Text elements per image:** Highly variable (1 to 20+ labels)
- **Quantity:** Variable - sample had ~1 image per page average

### 3.3 UI Resource File Specifications

**Status:** ⏳ **Analysis Not Started**
- **UI localization analysis:** Starting this week
- **Sample files:** Not available yet
- **Formats:** To be determined during analysis
- **Expected formats:** JSON, XML, Properties, YAML (common web app formats)

**Action Item:** Wait for UI localization analysis to complete

### 3.4 Video Specifications

**Status:** ⏳ **Analysis Not Started**
- **Sample videos:** Not available yet
- **Specifications:** To be determined

**Confirmed Requirements:**
✓ **Video localization includes:**
  - Audio narration (voice-over replacement)
  - Subtitles/captions
  - On-screen text/graphics replacement

**Action Item:** Wait for video samples

### 3.5 Content Volume & Complexity

**Volume Projections:**
- **Target:** Multiple products, multiple markets by end of year
- **Specific numbers:** Unknown at this time
- **IFU size:** Variable depending on product nature

**Planning Assumptions:**
- Platform must handle **variable document sizes** (10 pages to 300+ pages)
- Platform must handle **variable image counts** (few to hundreds)
- Platform must be **scalable** for unknown volume

---

## 4. Image Localization Requirements

### 4.1 Image Localization Strategy

**CRITICAL CLARIFICATION:**  
Only **product UI screens** will be available in Figma. All other image types (diagrams, flowcharts, symbols, logos, etc.) will NOT be in Figma.

#### 4.1.1 Hybrid Approach

**Type 1: UI Screenshots (Automated)**
- **Source:** Figma
- **Process:** Automated via Knewron platform
  1. Extract UI screenshots from IFU
  2. Match in ChromaDB (90% threshold)
  3. Translate via Figma variables
  4. Generate localized images
  5. Replace in document

**Type 2: Other Images (Manual/Out of Scope)**
- **Types:** Diagrams, flowcharts, symbols, logos, photos, etc.
- **Process:** Manual translation outside Knewron platform
- **Platform responsibility:** Identify and flag these images
- **Knewron action:** Leave in source language OR accept manually translated versions

**Type 3: Regulatory Symbols (TBD)**
- **Decision pending:** Regulatory team to determine
- **Likely:** No translation needed (ISO universal symbols)

### 4.2 Image Type Detection & Classification

#### 4.2.1 AI-Based Detection
✓ **Confidence threshold:** 70% (configurable)
  - ≥ 70% confidence → Auto-classify
  - < 70% confidence → Flag for manual review

✓ **User interface:**
  - Show all images with filters
  - User can filter by:
    - All images
    - UI screenshots only
    - Non-UI images only
    - Uncertain images only (< 70% confidence)
    - By AI confidence score
  - User can override any classification

#### 4.2.2 Image Categories
1. **UI Screenshots** → Automated via Figma
2. **Non-UI Images** (diagrams, flowcharts, photos) → Offline manual process
3. **Regulatory Symbols** → TBD by regulatory team

#### 4.2.3 Non-UI Image Handling
✓ **Offline manual process**
  - Platform identifies and flags non-UI images
  - Manual translation happens outside Knewron
  - Platform leaves non-UI images in source language

### 4.3 UI Screenshot Matching (ChromaDB)

#### 4.3.1 Matching Strategy
✓ **Per product** (not global)
  - UI screenshots matched only within same product
  - Prevents cross-product false matches
  - Better accuracy and context

#### 4.3.2 Similarity Threshold
- **≥ 90%** → Match found, reuse/translate
- **< 90%** → New image, flag for manual translation

#### 4.3.3 Version Handling
✓ **Overwrite old version** when UI screenshot updated  
✓ **Keep translation history:**
  - Which languages were translated
  - When translations were created
  - Enables reuse of existing translations for new version

#### 4.3.4 Metadata Stored in ChromaDB
✓ Figma frame ID  
✓ Figma file key  
✓ Product name/version  
✓ Screen name (Login, Dashboard, etc.)  
✓ Text elements extracted  
✓ Available translations (language codes)  
✓ Last updated timestamp  
✓ Image hash/fingerprint  
✓ Translation history  

### 4.4 Figma Integration

#### 4.4.1 Workspace Organization
✓ **One Figma file per product**
  - Each product has dedicated Figma file
  - Organized by screens within file

#### 4.4.2 Maintenance
✓ **DeepHealth design team** creates/maintains Figma frames
  - CitiusTech team consumes via API
  - DeepHealth responsible for keeping Figma updated

#### 4.4.3 API Configuration
✓ **Authentication:** Personal Access Token  
✓ **Rate limits:** Minimum 1 API call per UI screenshot  
  - Need rate limiting/throttling capability
  - Handle Figma API quotas

✓ **API Operations Needed:**
  - Read Figma file metadata
  - Read frame/node data
  - Update variable values (translations)
  - Export frame as PNG
  - Get frame by ID

### 4.5 Translation Workflow

#### 4.5.1 Sending to Lokalise
✓ **Send whatever Lokalise needs for human text translation:**
  - UI text strings
  - Context information
  - Reference screenshots (if helpful for translators)
  - Screen/product context
  - Grouping of related strings

#### 4.5.2 Image Export
✓ **Format:** PNG
  - Resolution: TBD (likely 300 DPI for print quality)
  - Maintain source image dimensions

#### 4.5.3 Quality Validation
✓ **Text readable** (not cut off, not overlapping)  
✓ **Translation quality/accuracy** comparing with source image  
✓ **Both AI and human validation:**
  - AI performs automated checks:
    - Text completeness (all elements translated)
    - Text readability (not cut off)
    - Visual comparison with source
    - Layout preservation
  - AI flags potential issues
  - Human reviewer validates flagged items

### 4.6 Reuse & Storage

✓ **Reuse existing translations whenever possible**
  - If matched UI screenshot has translation for target language → Reuse
  - Avoids redundant translation work
  - Faster processing

✓ **Permanent storage** for translated images
  - Enables reuse across versions
  - Builds translation memory over time

### 4.7 Error Handling & Fallbacks

#### 4.7.1 UI Screenshot Not in Figma
✓ **Treat as non-UI image (manual process)**
  - Flag for offline manual translation
  - Don't fail the job
  - Continue processing other images

#### 4.7.2 Figma API Unavailable
✓ **Queue and retry** (max retries: TBD - recommend 3-5)  
✓ **Then fail the job** if retries exhausted
  - Log error details
  - Notify user/admin
  - Allow manual retry later

#### 4.7.3 ChromaDB Unavailable
✓ **Fail the job**
  - Critical dependency
  - Cannot proceed without matching capability
  - Notify user/admin immediately

### 4.8 Performance & Scalability

✓ **Parallel processing**
  - Max concurrent: **TBD** (recommend 5-10 based on Figma API limits)
  - Configurable based on:
    - Figma API rate limits
    - System resources
    - Job priority

### 4.9 Reporting & Visibility

✓ **Image Summary Report:**
  - Total images found
  - UI screenshots (automated)
  - Non-UI images (manual/offline)
  - Regulatory symbols
  - Successfully localized
  - Failed/skipped
  - AI confidence scores

✓ **Preview Capability:**
  - Side-by-side comparison (source vs translated)
  - Visual validation before finalizing
  - User can approve/reject translations

---

## 5. Translation & Review Workflow

### 5.1 Lokalise Integration Architecture

#### 5.1.1 Lokalise Configuration
✓ **Plan:** Lokalise Enterprise  
✓ **Project Structure:**
  - **One main project per organization** (DeepHealth)
  - **Sub-projects per localization request per product**

✓ **Project Creation:** Pre-created by admin (manual setup)

### 5.2 Data Exchange: Knewron → Lokalise

#### 5.2.1 Document Upload Format
✓ **Multiple formats sent:**
  - **DOCX** (full document with source screenshots)
  - **Extracted text** (for translation)
  - **JSON/XML** (structured content)

#### 5.2.2 Processing Flow
✓ **Parallel processing:**
  1. Full document sent to Lokalise with source screenshots
  2. Image localization happens in parallel (Figma workflow)
  3. Translated images assembled back into translated document

#### 5.2.3 UI Screenshot Text
✓ **Sent with reference images attached**
  - Individual text strings
  - Reference screenshot for context
  - Helps translators understand UI context

#### 5.2.4 Metadata
✓ **Project configured in Lokalise for target language**
  - Language pairs pre-configured
  - Workflow stages defined
  - Translator assignments set up

#### 5.2.5 Content Organization
✓ **Controlled by Lokalise**
  - Lokalise manages file organization
  - Knewron follows Lokalise structure

### 5.3 Translation Keys & Reuse

✓ **Structured keys for reuse:**
  - **UI strings:** Use consistent keys across products
  - **Image text:** Use same keys when text repeats
  - **Purpose:** Enable Lokalise to reuse approved translations
  - **Benefit:** Avoid duplication of translation effort

**Example:**
```
ui.login.username → "Username"
ui.login.password → "Password"
image.warning.general → "Warning: Do not operate without training"
```

### 5.4 Translation Workflow in Lokalise

#### 5.4.1 Workflow Stages
✓ **Translation → Linguistic Review → Clinical SME Review → Approval**

1. **Translation:** LSP or in-house translators
2. **Linguistic Review:** Language quality, grammar, style
3. **Clinical SME Review:** Medical accuracy, regulatory compliance (always required for IFUs)
4. **Approval:** Final sign-off

#### 5.4.2 Lokalise Users
✓ Translators (LSP or in-house)  
✓ Linguistic reviewers  
✓ Clinical SMEs (have Lokalise accounts)  
✓ Project managers  
✓ CitiusTech coordinators/Localization managers  

#### 5.4.3 Translator Assignment
✓ **Automatic (as per Lokalise configuration)**
  - Mostly auto-assigned by language pair
  - Some manual assignment possible

#### 5.4.4 Translation Memory & Glossaries
✓ **TM:** Shared across all products  
✓ **Glossaries:** Maintained by DeepHealth team
  - Medical/regulatory terms
  - Product-specific terminology
  - UI terminology

### 5.5 Data Exchange: Lokalise → Knewron

#### 5.5.1 Webhook Notifications
✓ **TBD** - specific events to be determined  
✓ **Primary purpose:** Monitor workflow status from Knewron UI  
✓ **Payload:** As per Lokalise specifications  
✓ **Authentication:** TBD  

#### 5.5.2 Polling Mechanism (Fallback)
✓ **Frequency:** Every 15 minutes  
✓ **Trigger:** When webhook delivery fails  
✓ **API Endpoints:** TBD (Lokalise API POC pending)  

#### 5.5.3 Downloaded Translation Format
✓ **DOCX** (translated document)  
✓ **XML/JSON** (structured content)  

#### 5.5.4 UI Screenshot Text Return
✓ **Individual strings with keys**
  - Key-value pairs
  - Enables assembly back into Figma

#### 5.5.5 Translation Validation
✓ **No validation by Knewron** - Trust Lokalise output
  - Lokalise handles QA internally
  - Knewron accepts translations as-is from Lokalise

### 5.6 Status Tracking & Monitoring

#### 5.6.1 Job Statuses
✓ **Statuses:**
  - Created/Submitted
  - Image Processing (UI screenshots)
  - Sent to Lokalise
  - In Translation (Lokalise)
  - In Review (Lokalise)
  - In Approval (Lokalise)
  - Translation Complete
  - Assembly in Progress (Knewron)
  - Completed
  - Failed
  - Cancelled

#### 5.6.2 Per-Artifact Tracking
✓ **A project targets a single language; each artifact is tracked independently**
  - Each artifact has its own status and progress
  - Artifacts can complete at different times (partial completion)
  - Multiple languages are handled via **separate projects** (each independently tracked)

#### 5.6.3 Progress Indicators
✓ **TBD** - Not determined yet

#### 5.6.4 Notifications
✓ **Who:** Localization Manager  
✓ **Channel:** In-app notifications (Knewron UI)  
✓ **Events:** All major stage transitions  

### 5.7 Error Handling & Recovery

#### 5.7.1 Lokalise Rejection
✓ **Yes** - If Lokalise rejects uploaded content
  - Knewron handles rejection
  - Notifies user
  - Allows correction and resubmission

#### 5.7.2 Translation Failure
✓ **Manual intervention required**
  - Translator error or system error in Lokalise
  - CitiusTech team coordinates resolution
  - Job remains in "waiting" state

#### 5.7.3 Webhook Failure
✓ **Knewron polling detects completion**
  - Fallback to 15-minute polling
  - No manual intervention needed

#### 5.7.4 Timeout
✓ **No timeout** - Wait indefinitely
  - Translation can take as long as needed
  - No automatic job failure due to time

#### 5.7.5 Partial Completion
✓ **Each artifact has its own delivery cycle within a project**
  - Artifacts complete independently
  - Deliver/download each artifact as it completes
  - No need to wait for all artifacts in the project
  - Across languages: each language is a separate project, delivered independently

### 5.8 Review & Approval Workflow

#### 5.8.1 Review Types
✓ **All review types performed:**
  - Linguistic review (grammar, style, accuracy)
  - Technical review (terminology, context)
  - Clinical/regulatory review (medical accuracy, compliance)

#### 5.8.2 Reviewer Capabilities
✓ **Reviewers can edit translations directly in Lokalise**
  - Edit and approve in one step
  - Or reject with comments

#### 5.8.3 Rejection Handling
✓ **Goes back to translator in Lokalise**
  - Lokalise manages internal workflow
  - Knewron monitors status changes
  - No Knewron intervention needed

#### 5.8.4 Clinical SME Review
✓ **Always required for regulatory content (IFUs)**  
✓ **Happens in Lokalise** (SMEs have Lokalise accounts)
  - Part of standard workflow
  - No external review process

### 5.9 Quality Assurance

#### 5.9.1 Lokalise QA
✓ **Yes, but not in Knewron's control**
  - Lokalise performs automated QA
  - Spelling, grammar, terminology, placeholders, etc.
  - Knewron trusts Lokalise QA

#### 5.9.2 Knewron QA (Post-Lokalise)
✓ **Yes - validate completeness**  
✓ **Yes - check formatting**  
✓ **Yes - compare with source (no missing content)**  

**QA Checks:**
- All sections translated
- Document structure preserved
- Images properly assembled
- No missing content
- Formatting intact (tables, lists, headers/footers)

### 5.10 Manual Trigger & Override

#### 5.10.1 Manual Triggers
✓ **All manual triggers supported:**
  - Manually send to Lokalise (if auto-send fails)
  - Manually pull from Lokalise (if webhook/polling fails)
  - Manually retry failed steps

#### 5.10.2 Overrides
✓ **No overrides allowed**
  - Cannot upload pre-translated content (bypass Lokalise)
  - Cannot edit translations in Knewron (after Lokalise)
  - Cannot skip Lokalise for specific content
  - All translations must go through Lokalise workflow

**Rationale:** Maintain quality control, ensure regulatory compliance, preserve audit trail

### 5.11 Open Items

**Pending POC/Decisions:**
1. **Lokalise API POC** - In progress
2. **Webhook specifications** - TBD
3. **Progress indicators** - TBD

---

## 6. System Integration & Deployment

### 6.1 GitLab Integration

**Phase 1: No GitLab Integration**  
✓ **All manual processes:**
  - Users manually upload source documents to Knewron
  - Users manually download localized documents from Knewron
  - No automated pull/push to GitLab
  - GitLab integration deferred to future phase

### 6.2 Deployment Environment

#### 6.2.1 Cloud Platform
✓ **AWS or GCP** (customer choice)
  - Knewron supports both platforms
  - Deployed in customer's cloud environment

**Implementation note (July 24, 2026):** realized as `STORAGE_BACKEND=s3|gcs|local`
and `AI_EMBEDDING_BACKEND=aws|gcp|clip|phash` in `.env` — the customer's cloud
choice is a runtime config selection, not a code branch; both object storage
and image-embedding generation are provider-swappable independently. See
`Technical_Design_Document.md` §11.1–§11.2.

#### 6.2.2 Region
✓ **Customer environment** (customer's choice)
  - No specific region requirement
  - Customer decides based on their infrastructure

#### 6.2.3 Data Residency
✓ **No data residency requirements**
  - Only product documentation and UI strings
  - No PHI/PII data
  - No regulatory restrictions on data location

#### 6.2.4 Environment Setup
✓ **Four environments:**
  1. **Development** - CitiusTech environment
  2. **QA/Testing** - CitiusTech environment
  3. **Staging** - CitiusTech environment
  4. **Production** - Customer environment (with production release)

#### 6.2.5 Infrastructure Management
✓ **Shared responsibility:**
  - **CitiusTech:** Application deployment, configuration, monitoring, support
  - **Customer:** Infrastructure provisioning, network, security policies, backup infrastructure

### 6.3 Infrastructure Requirements

#### 6.3.1 Knewron Platform
✓ **Existing Knewron platform with DevOps:**
  - AI Localization service deployed on Knewron platform
  - Leverages existing Knewron infrastructure

#### 6.3.2 Dependencies
✓ **ChromaDB** - Persistent volume, shared across all products  
  - Single database instance (shared infrastructure)
  - Image matching scoped per product (not global)
  - Prevents cross-product false matches
  - **Implementation note (July 24, 2026):** also partitioned by a
    `tenant_id` metadata key (`CHROMADB_TENANT_ID`, default `"default"`) —
    a namespace for deployments/environments sharing one ChromaDB instance,
    layered on top of (not replacing) the per-product scoping above. Not a
    relational multi-tenancy model; see `Technical_Design_Document.md` §11.3.
✓ **SQL Database** - Metadata storage  
✓ **Object Storage** (S3/GCS) - Document storage  

### 6.4 Security & Compliance

#### 6.4.1 Authentication
✓ **Integration with DeepHealth identity provider**
  - SSO integration
  - No separate user database

#### 6.4.2 API Access
✓ **UI only** (no API access in Phase 1)

#### 6.4.3 Data Encryption
✓ **At rest:** Not required (customer environment)  
✓ **In transit:** Yes - TLS/HTTPS for all connections  

#### 6.4.4 PHI/PII
✓ **No PHI data involved**

#### 6.4.5 Audit Logging
✓ **All audit logging:**
  - User actions
  - System actions
  - Data access
  - Configuration changes

✓ **Retention:** 1 year

✓ **Capabilities:**
  - Immutable (cannot be modified/deleted)
  - Exportable (for compliance reporting)
  - Searchable (for investigations)

#### 6.4.6 Regulatory Compliance
✓ **None specific** - No regulatory compliance requirements for Phase 1

### 6.5 Monitoring & Logging

#### 6.5.1 Monitoring
✓ **Tools:** Existing Knewron monitoring (leverage platform)

✓ **Metrics tracked:**
  - Job success/failure rates
  - Processing times (per stage)
  - API response times (Lokalise, Figma, ChromaDB)
  - Error rates
  - Resource utilization (CPU, memory, disk)
  - Queue depths

#### 6.5.2 Alerting
✓ **Alert on:** Critical errors (job failures, API down)  
✓ **Recipients:** CitiusTech Localization Manager  

#### 6.5.3 Application Logging
✓ **Log levels:** All levels captured (ERROR, WARN, INFO, DEBUG)  
✓ **Storage:** Existing Knewron logging infrastructure  
✓ **Retention:** Configurable (default: 30 days)  

### 6.6 Backup & Disaster Recovery

#### 6.6.1 Backup Strategy
✓ **What:** All data backed up
  - SQL Database
  - ChromaDB data
  - Source documents
  - Translated documents
  - Configuration files

✓ **Frequency:** Daily backups  
✓ **Storage:** Customer's backup infrastructure  

#### 6.6.2 Disaster Recovery
✓ **RTO (Recovery Time Objective):** < 4 hours  
✓ **RPO (Recovery Point Objective):** < 24 hours  

### 6.7 Storage

#### 6.7.1 Source Documents
✓ **Object storage (S3, GCS)**  
✓ **Temporary** - Deleted after processing  

#### 6.7.2 Translated Documents
✓ **Same as source documents** (Object storage)  
✓ **Retention:** Same as source  

#### 6.7.3 Translated Images
✓ **Permanent (never delete)**
  - Enables reuse across versions
  - Builds translation memory
  - Critical for ChromaDB matching

#### 6.7.4 Overall Retention Policy
- **Source documents:** Temporary (deleted after processing)
- **Translated documents:** Temporary (deleted after download or retention period)
- **Translated images:** Permanent (stored in ChromaDB + object storage)
- **Audit logs:** 1 year
- **Application logs:** 30 days (configurable)

### 6.8 CI/CD & DevOps

#### 6.8.1 CI/CD Pipeline
✓ **New pipeline needed** for AI Localization  
✓ **Deployment strategy:** Follow existing Knewron deployment process  

#### 6.8.2 Automated Testing
✓ **All testing levels:**
  - Unit tests
  - Integration tests (Lokalise, Figma, ChromaDB)
  - End-to-end tests (full localization workflow)

### 6.9 Performance & Scalability

#### 6.9.1 Expected Load
✓ **Concurrent users:** < 10 (CitiusTech team only)  
✓ **Concurrent localization requests:** typically **2–3** in parallel (design sizing); upper bound **< 10**  
  - Not latency-critical; long-running jobs (hours) are acceptable  
  - Design sized for 2–3 concurrent (Celery worker concurrency=3) with a clear scaling path to handle bursts up to <10  

#### 6.9.2 Performance Targets
✓ **UI response time:** < 1 second (good)

### 6.10 Cost Management

✓ **Cost tracking:** Not required  
✓ **Cost optimization:** Yes - minimize cloud costs
  - Delete temporary source documents after processing
  - Configurable log retention (default 30 days)
  - Efficient storage usage
  - Optimize compute resources for low concurrency

---

## 7. Non-Functional Requirements

**Status:** ⏸️ **On Hold**

This section will cover:
- SLA requirements
- Support model
- Documentation requirements
- Training requirements
- User acceptance criteria
- Go-live readiness
- Future enhancements

---

## 8. Open Items & Pending Decisions

### 8.1 High Priority

1. **Lokalise API POC** - In progress
   - Specific API endpoints
   - Authentication methods
   - Rate limits
   - Error responses

2. **Webhook specifications** - TBD
   - Specific events to subscribe to
   - Payload structure
   - Authentication/validation method

3. **UI Resource Files Analysis** - Starting this week
   - Specific formats
   - Sample files
   - Requirements

4. **Training Video Analysis** - Pending
   - Sample videos
   - Technical specifications
   - Requirements

### 8.2 Medium Priority

5. **Progress indicators** - TBD (UI/UX design decision)

6. **Figma API rate limits** - Need to determine max concurrent calls (recommend 5-10)

7. **Figma retry count** - Recommend 3-5 retries with exponential backoff

8. **PNG resolution/DPI** - Recommend 300 DPI for print quality

9. **Processing time targets** - Need to define acceptable times for:
   - 1 UI screenshot
   - 50 UI screenshots
   - Entire IFU (300 pages)

### 8.3 Low Priority / Future Phases

10. **GitLab integration** - Deferred to future phase

11. **API access** - Deferred to future phase

12. **Regulatory symbols handling** - Pending regulatory team decision

13. **Section 7: Non-Functional Requirements** - On hold

---

## Appendix A: Workflow Diagrams

### A.1 IFU Document Localization Workflow

```
Phase 1: Image Localization (Knewron)
1. User uploads source IFU document (DOCX)
2. Knewron extracts embedded images
3. AI classifies images (UI screenshots vs other)
4. Knewron matches UI screenshots in ChromaDB (90% threshold)
5. For matched UI screenshots:
   - Extract source text from image metadata
   - Translate text OR reuse existing translation
   - Generate translated images via Figma
6. Create image-localized document

Phase 2: Text Translation (Lokalise)
7. Knewron → Lokalise: Push document + reference images + image text
8. Lokalise: Linguistic team translates:
   - Document body text
   - Image text (with reference images for context)
9. Lokalise: Reviewers validate translation
10. Lokalise: Clinical SMEs approve (for regulatory content)

Phase 3: Assembly & Delivery (Knewron)
11. Lokalise → Knewron: Webhook notification when translation complete
12. Knewron pulls completed translation from Lokalise API
13. Knewron assembles final localized document
14. User downloads completed artifact
```

### A.2 Video Localization Workflow

```
Phase 1: Video Processing (Knewron)
1. User uploads source video (MP4/MPEG)
2. Knewron extracts:
   - Audio (speech-to-text via OpenAI Whisper)
   - On-screen text/graphics
   - Subtitle timing information

Phase 2: Text Translation (Lokalise)
3. Knewron → Lokalise: Push extracted text:
   - Audio script/transcript
   - On-screen text
   - Subtitle text
4. Lokalise: Linguistic team translates all text
5. Lokalise: Reviewers validate

Phase 3: Video Assembly (Knewron)
6. Lokalise → Knewron: Webhook notification + translated text
7. Knewron generates:
   - Translated audio (text-to-speech via Google Cloud TTS)
   - Translated on-screen graphics (via Figma)
   - Translated subtitles (with timing sync)
8. Knewron assembles final localized video
9. User downloads completed video
```

---

## Appendix B: Technology Stack

### B.1 Core Platform
- **Knewron Platform** - Existing orchestration platform
- **SQL Database** - Metadata storage (jobs, users, status)
- **Object Storage** - S3/GCS for document storage

### B.2 AI & Machine Learning
- **ChromaDB** - Vector database for image matching
- **AI Image Classification** - Detect UI screenshots vs other images (70% confidence threshold)
- **OpenAI Whisper** - Speech-to-text for video audio
- **Google Cloud TTS** - Text-to-speech for video narration

### B.3 Integrations
- **Lokalise Enterprise** - Translation management system
- **Figma** - Design tool for UI screenshot localization
- **DeepHealth Identity Provider** - SSO authentication

### B.4 Cloud Infrastructure
- **AWS or GCP** - Customer choice
- **Deployment:** Customer environment (production), CitiusTech environment (dev/QA/staging)

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **IFU** | Instructions for Use - Regulatory documentation for medical devices |
| **Lokalise** | Third-party translation management system (TMS) |
| **Figma** | Design tool used for UI screenshot localization |
| **ChromaDB** | Vector database for image similarity matching |
| **UI Screenshot** | Product user interface screen capture |
| **Non-UI Image** | Diagrams, flowcharts, symbols, logos (not UI screenshots) |
| **LSP** | Language Service Provider - Translation vendor |
| **Clinical SME** | Clinical Subject Matter Expert - Reviews medical/regulatory content |
| **TM** | Translation Memory - Database of previously translated content |
| **RTO** | Recovery Time Objective - Maximum acceptable downtime |
| **RPO** | Recovery Point Objective - Maximum acceptable data loss |
| **SSO** | Single Sign-On - Centralized authentication |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **Requirements Analyst** | | | |
| **CitiusTech Project Manager** | | | |
| **DeepHealth Stakeholder** | | | |
| **Technical Lead** | | | |

---

**End of Requirements Document**
