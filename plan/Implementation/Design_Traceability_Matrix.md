# 🔗 Design Traceability Matrix — AI Localization Platform

**Purpose:** Guarantee that **every design point is implemented** and **every story is anchored to design**. This is the enforcement layer that makes the `Design/` folder the source of truth.

**Date:** July 24, 2026 · **Version:** 1.1 · **Status:** ✅ All stories `0.1`–`8.5` complete (living document — update again if extended further)

**How to use**
- **Reverse map (§2)** — every design element must have an implementing story. Any element with **no story = coverage gap** (red flag).
- **Forward map (§3)** — every story lists the exact design sections it must satisfy. Used during implementation and review.
- **Authority order (§1)** — resolves any conflict.

---

## 1. Source-of-Truth Authority Order

On any conflict, **higher wins**. If a doc is wrong, **update the doc first (version bump + approval), then code**.

| Rank | Document | Governs |
|------|----------|---------|
| 1 | `Design/LOCKED_Design_v1.0.md` | Architecture, patterns, scope, NFRs |
| 2 | `Design/Database_Schema.md` | Data model (tables, columns, indexes) |
| 3 | `Design/Figma_Integration.md` | Figma specifics (metadata, modes, render) |
| 4 | `Design/Technical_Design_Document.md` | Detailed reference (APIs, services); **§11 is an addendum** covering the post-implementation extensions (multi-cloud storage/embeddings, ChromaDB tenant key, Poetry, externalized Redis) |
| 5 | `Design/Architecture_Diagrams.md` | Behavioral/structural views (illustrative) |
| 6 | `Requirements/Requirements_Document.md` | Functional what/why, compliance |

> **Golden rule:** Code conforms to design. Deviations require an approved design change, never a silent code divergence.

---

## 2. Reverse Map — Design Element → Story (coverage)

Legend: ⬜ Not started · 🟨 In progress · ✅ Done · ⛔ Out of scope

### Architecture & Patterns (LOCKED_Design)
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| Monolithic Python / FastAPI | LOCKED §2 | 0.1 | ✅ |
| Celery + Redis background processing | LOCKED §2, §8 | 0.3 | ✅ |
| Universal 6-stage pipeline | LOCKED §3 | 2.1 | ✅ |
| Strategy pattern (per artifact) | LOCKED §3, §13 | 2.1, 5.1–5.3 | ✅ |
| State machine | LOCKED §7 | 2.2 | ✅ |
| Checkpointing / resume | LOCKED §7 | 2.3 | ✅ |
| Saga / compensation | LOCKED §7 | 2.4 | ✅ |
| Circuit breaker | LOCKED §7 | 2.4 | ✅ |
| Idempotency (Redis keys) | LOCKED §7 | 2.4, 4.2 | ✅ |
| Webhook + polling hybrid | LOCKED §7 | 4.2 | ✅ |
| Parallel sub-task fan-out + join barrier | LOCKED §7; Arch §6.1 | 2.5 | ✅ |
| Event-driven UI (Pub/Sub → WebSocket) | LOCKED §2 | 3.1 | ✅ |
| Concurrency (1 worker, concurrency=3, Beat) | LOCKED §8 | 0.3 | ✅ |
| Project structure (repo layout) | LOCKED §11 | 0.1 | ✅ |
| Docker Compose deployment | LOCKED §8 | 0.1 | ✅ |

### Data Stores & Schema (Database_Schema)
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| `users` | Database_Schema | 1.3 | ✅ |
| `products` | Database_Schema | 1.1 | ✅ |
| `projects` (single target language) | Database_Schema; LOCKED §9 | 1.1 | ✅ |
| `project_artifacts` | Database_Schema | 1.2 | ✅ |
| `artifact_stages` | Database_Schema | 2.2 | ✅ |
| `artifact_subtasks` | Database_Schema | 2.5 | ✅ |
| `image_processing` | Database_Schema | 5.1 | ✅ |
| `figma_images` | Database_Schema; Figma_Integration §9 | 4.4 | ✅ |
| `translation_cache` | Database_Schema | 5.1 | ✅ |
| `lokalise_tasks` | Database_Schema | 4.2 | ✅ |
| `review_findings` | Database_Schema | 6.1 | ✅ |
| `approvals` | Database_Schema | 6.2 | ✅ |
| `audit_logs` | Database_Schema | 7.1 | ✅ |
| Remaining table(s) + indexes/constraints | Database_Schema | 0.2 | ✅ |
| ChromaDB collections/metadata | Technical_Design §3; LOCKED §5 | 4.3 | ✅ |

### Integrations
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| Storage (S3/GCS, presign) | LOCKED §9 | 4.1 | ✅ |
| Lokalise (upload/status/webhook/poll) | LOCKED §7; Arch §11, §17 | 4.2 | ✅ |
| ChromaDB match (≥ 90%) | LOCKED §5 | 4.3 | ✅ |
| Figma render/export (variables/modes) | Figma_Integration §4–§7 | 4.4 | ✅ |
| Figma design-time prep workflow | Figma_Integration §3 | External/design-time (documented; not app code) | ✅ |
| DeepHealth SSO | Requirements §6; LOCKED §12 | 1.3 | ✅ |

### Artifact Workflows
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| Image localization sub-pipeline | LOCKED §5; Figma_Integration §6 | 5.1 | ✅ |
| No-match: retain + flag | Figma_Integration §8 | 5.1 | ✅ |
| IFU DOCX end-to-end | LOCKED §4.1; Arch §6 | 5.2 | ✅ |
| UI Resource end-to-end | LOCKED §4.3; Arch §9 | 5.3 | ✅ |
| Video localization | LOCKED §4.2 | ⛔ 5.4 | ⛔ Out of scope |

### Review / Sign-off / Delivery
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| AI review + findings (70% detection) | Requirements §4–§5 | 6.1 | ✅ |
| Human review + approval | Requirements §5; LOCKED §4 | 6.2 | ✅ |
| Per-artifact download + partial completion | LOCKED §4; Requirements §1.5 | 6.3 | ✅ |

### Cross-cutting / NFR / Security
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| Audit logging (all actions, 1-yr) | LOCKED §12; Requirements §6 | 7.1 | ✅ |
| Notifications | Requirements; Arch §2 | 7.2 | ✅ |
| Observability & structured logging (30-day) | LOCKED §12 | 7.3 | ✅ |
| TLS/HTTPS in transit | LOCKED §12; Requirements §6 | 7.3 / infra | ✅ |
| No PHI/PII | Requirements §6 | (constraint, all stories) | ✅ |
| Auth roles: admin/localization_manager/viewer | Requirements §2.2 | 1.3 | ✅ |
| RTO < 4h / RPO < 24h / daily backups | LOCKED §12 | 7.x / infra | ✅ |
| Test coverage & CI | LOCKED §11 | 7.4 | ✅ |

### Post-Implementation Extensions (Technical_Design §11 addendum)
| Design element | Authority | Story | Status |
|----------------|-----------|-------|--------|
| Multi-cloud object storage (local/S3/GCS) | Technical_Design §11.1; Requirements §6.2.1 | 8.1 | ✅ |
| Multi-cloud image embeddings (CLIP/phash/Bedrock/Vertex AI) | Technical_Design §11.2; Appendix B §1 | 8.2 | ✅ |
| ChromaDB `tenant_id` partition key (not relational multi-tenancy) | Technical_Design §11.3; Requirements §6.3.2 | 8.3 | ✅ |
| Poetry dependency management | Technical_Design §11.4 | 8.4 | ✅ |
| Redis externalized from Docker Compose | Technical_Design §11.4, §7.1 | 8.5 | ✅ |

---

## 3. Forward Map — Story → Design References

> This mirrors the `Design Refs` field now embedded in `Implementation_Plan.md`. Keep both in sync.

| Story | Design References (must satisfy) |
|-------|----------------------------------|
| 0.1 | LOCKED §2, §8, §11; Technical_Design (deployment) |
| 0.2 | Database_Schema (all tables/indexes); LOCKED §9 |
| 0.3 | LOCKED §2, §8 |
| 1.1 | Database_Schema (products, projects); Requirements §1.5; LOCKED §9 |
| 1.2 | Database_Schema (project_artifacts); LOCKED §4; Requirements §2.2 |
| 1.3 | Requirements §2.2, §6; LOCKED §12 |
| 2.1 | LOCKED §3, §13 |
| 2.2 | LOCKED §7; Arch §5; Database_Schema (artifact_stages) |
| 2.3 | LOCKED §7 |
| 2.4 | LOCKED §7 |
| 2.5 | LOCKED §7; Arch §6.1; Database_Schema (artifact_subtasks) |
| 3.1 | LOCKED §2; Arch §10; Technical_Design (WebSocket) |
| 4.1 | LOCKED §9; Technical_Design (storage) |
| 4.2 | LOCKED §7; Arch §11, §17; Database_Schema (lokalise_tasks) |
| 4.3 | LOCKED §5; Technical_Design §3; Database_Schema (image_processing) |
| 4.4 | Figma_Integration (all); Database_Schema (figma_images, translation_cache) |
| 5.1 | LOCKED §5; Figma_Integration §6, §8; Requirements §4 |
| 5.2 | LOCKED §4.1; Arch §6, §6.1; Requirements §3 |
| 5.3 | LOCKED §4.3; Arch §9; Requirements §3.3 |
| 6.1 | Requirements §4–§5; Database_Schema (review_findings) |
| 6.2 | LOCKED §4; Database_Schema (approvals); Requirements §5 |
| 6.3 | LOCKED §4; Requirements §1.5; Database_Schema (artifact status) |
| 7.1 | LOCKED §12; Database_Schema (audit_logs); Requirements §6 |
| 7.2 | Requirements; Arch §2 |
| 7.3 | LOCKED §12; Requirements §6 |
| 7.4 | LOCKED §11; all story acceptance criteria |
| 8.1 | Technical_Design §11.1; Requirements §6.2.1 |
| 8.2 | Technical_Design §11.2; Appendix B §1 |
| 8.3 | Technical_Design §11.3; Requirements §6.3.2 |
| 8.4 | Technical_Design §11.4 |
| 8.5 | Technical_Design §11.4, §7.1 |

---

## 4. Review Checklist (run at each story's validation gate)

- [ ] Read the story's **Design Refs** sections before coding.
- [ ] Implementation matches those sections (names, fields, thresholds, flows).
- [ ] No element invented outside the cited design.
- [ ] Any deviation is **documented + approved**, and the design doc updated first.
- [ ] Reverse map row(s) for this story flipped to ✅.
- [ ] Values honored: ChromaDB ≥ 90%, AI detection 70%, concurrency=3, roles = admin/localization_manager/viewer, single-language projects, no PHI/PII.
- [ ] If touching storage/embeddings/ChromaDB: the change goes through the
  existing `StorageBackend`/`ImageEmbedder` interface (Story 8.1/8.2) or the
  `tenant_id` partition key (Story 8.3) — never a new relational
  multi-tenancy column/table (no `tenants` table exists; keep it that way
  unless a new design doc change explicitly approves one).

---

**Status:** ✅ All stories `0.1`–`8.5` complete. Update statuses again if the plan is extended.
