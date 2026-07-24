# AI Localization Platform - Open Items Tracker

**Last Updated:** July 19, 2026  
**Status:** Active Tracking  

---

## High Priority Items

### 1. Lokalise API POC
**Status:** 🟡 In Progress  
**Owner:** TBD  
**Due Date:** TBD  
**Description:** Proof of concept for Lokalise API integration

**Tasks:**
- [ ] Identify required API endpoints
- [ ] Test authentication methods
- [ ] Determine rate limits
- [ ] Document error responses
- [ ] Test webhook functionality
- [ ] Test file upload/download
- [ ] Test status polling

**Dependencies:** None  
**Blockers:** None  

---

### 2. Webhook Specifications
**Status:** 🔴 Not Started (TBD)  
**Owner:** TBD  
**Due Date:** TBD  
**Description:** Define webhook integration between Lokalise and Knewron

**Decisions Needed:**
- [ ] Which Lokalise events to subscribe to
- [ ] Webhook payload structure
- [ ] Authentication/validation method (HMAC, API key, etc.)
- [ ] Retry mechanism if webhook fails
- [ ] Webhook endpoint URL structure

**Dependencies:** Lokalise API POC (#1)  
**Blockers:** Waiting for Lokalise API POC completion  

---

### 3. UI Resource Files Analysis
**Status:** 🟡 Starting This Week  
**Owner:** TBD  
**Due Date:** TBD  
**Description:** Analyze UI resource file formats and requirements

**Tasks:**
- [ ] Collect sample UI resource files from DeepHealth products
- [ ] Identify file formats (JSON, XML, Properties, YAML, etc.)
- [ ] Analyze file structure (flat vs nested)
- [ ] Determine placeholders/variables handling
- [ ] Define extraction and assembly process
- [ ] Document requirements

**Dependencies:** DeepHealth to provide samples  
**Blockers:** Waiting for sample files  

---

### 4. Training Video Analysis
**Status:** 🔴 Not Started (Pending Samples)  
**Owner:** TBD  
**Due Date:** TBD  
**Description:** Analyze training video formats and requirements

**Tasks:**
- [ ] Collect sample training videos
- [ ] Analyze video specifications (format, resolution, duration)
- [ ] Analyze audio characteristics (format, sample rate, channels)
- [ ] Identify on-screen text/graphics
- [ ] Test speech-to-text (OpenAI Whisper)
- [ ] Test text-to-speech (Google Cloud TTS)
- [ ] Define subtitle format and requirements
- [ ] Document requirements

**Dependencies:** DeepHealth to provide samples  
**Blockers:** Waiting for sample videos  

---

## Medium Priority Items

### 5. Progress Indicators Design
**Status:** 🔴 Not Started (TBD)  
**Owner:** UX/UI Designer  
**Due Date:** TBD  
**Description:** Design progress indicators for localization jobs

**Options to Evaluate:**
- [ ] Percentage complete (0-100%)
- [ ] Stage-based (e.g., "3 of 5 stages complete")
- [ ] Per-language progress
- [ ] Estimated completion time
- [ ] Combination of above

**Dependencies:** None  
**Blockers:** None  

---

### 6. Figma API Rate Limits
**Status:** 🔴 Not Started  
**Owner:** Technical Lead  
**Due Date:** TBD  
**Description:** Determine optimal Figma API concurrency

**Tasks:**
- [ ] Research Figma API rate limits
- [ ] Test concurrent API calls
- [ ] Determine max concurrent calls (recommend 5-10)
- [ ] Implement rate limiting/throttling
- [ ] Configure retry mechanism (recommend 3-5 retries)

**Dependencies:** None  
**Blockers:** None  

---

### 7. PNG Resolution/DPI
**Status:** 🔴 Not Started  
**Owner:** Technical Lead  
**Due Date:** TBD  
**Description:** Define image export resolution

**Decision Needed:**
- [ ] Confirm 300 DPI for print quality (regulatory docs)
- [ ] Or match source image resolution
- [ ] Test Figma export quality at different DPIs
- [ ] Document standard

**Dependencies:** None  
**Blockers:** None  

---

### 8. Processing Time Targets
**Status:** 🔴 Not Started  
**Owner:** Technical Lead  
**Due Date:** TBD  
**Description:** Define acceptable processing times

**Targets to Define:**
- [ ] 1 UI screenshot: ___ seconds/minutes
- [ ] 50 UI screenshots: ___ minutes/hours
- [ ] Entire IFU (300 pages): ___ hours/days
- [ ] Overall job SLA: ___ days

**Dependencies:** Performance testing  
**Blockers:** Need to build prototype first  

---

## Low Priority / Future Phases

### 9. GitLab Integration
**Status:** ⏸️ Deferred to Future Phase  
**Owner:** TBD  
**Due Date:** Post Phase 1  
**Description:** Automated pull/push to GitLab

**Scope:**
- Pull source documents from GitLab
- Push localized documents back to GitLab
- Track GitLab versions/commits
- Create merge requests

**Dependencies:** Phase 1 completion  
**Blockers:** Not in Phase 1 scope  

---

### 10. API Access
**Status:** ⏸️ Deferred to Future Phase  
**Owner:** TBD  
**Due Date:** Post Phase 1  
**Description:** Programmatic API access to Knewron

**Scope:**
- REST API for job creation
- API authentication (OAuth, API keys)
- API documentation
- Rate limiting

**Dependencies:** Phase 1 completion  
**Blockers:** Not in Phase 1 scope  

---

### 11. Regulatory Symbols Handling
**Status:** 🔴 Pending Regulatory Team Decision  
**Owner:** DeepHealth Regulatory Team  
**Due Date:** TBD  
**Description:** Determine if ISO regulatory symbols need translation

**Decision Needed:**
- [ ] Do symbols need translation?
- [ ] Which symbols are universal (no translation)?
- [ ] Which symbols have text that needs translation?
- [ ] How to handle in platform?

**Dependencies:** Regulatory team input  
**Blockers:** Waiting for regulatory decision  

---

### 12. Section 7: Non-Functional Requirements
**Status:** ⏸️ On Hold  
**Owner:** Requirements Analyst  
**Due Date:** TBD  
**Description:** Complete final requirements section

**Topics to Cover:**
- SLA requirements
- Support model
- Documentation requirements
- Training requirements
- User acceptance criteria
- Go-live readiness
- Future enhancements

**Dependencies:** Stakeholder availability  
**Blockers:** On hold per stakeholder request  

---

## Completed Items

### ✅ Requirements Gathering (Sections 1-6)
**Completed:** July 19, 2026  
**Owner:** Requirements Analyst  

**Sections Completed:**
- Section 1: Project Scope & Objectives
- Section 2: User Roles & Permissions
- Section 3: Document & Content Types
- Section 4: Image Localization Requirements
- Section 5: Translation & Review Workflow
- Section 6: System Integration & Deployment

---

## Status Legend

- 🔴 **Not Started** - Work has not begun
- 🟡 **In Progress** - Work is underway
- 🟢 **Complete** - Work is finished
- ⏸️ **On Hold** - Paused or deferred
- 🔵 **Blocked** - Cannot proceed due to dependency

---

## Next Review Date

**Scheduled:** TBD  
**Attendees:** TBD  
**Agenda:**
- Review progress on high priority items
- Update blockers and dependencies
- Adjust priorities as needed
- Set new due dates

---

## Notes

- **Lokalise API POC** is critical path for Phase 1
- **UI and Video analysis** needed before design can be finalized
- **Section 7** can be completed in parallel with development
- **Future phase items** (#9-10) should not block Phase 1 delivery

---

**Document Owner:** Requirements Analyst  
**Last Updated:** July 19, 2026
