# AI Localization Platform — Developer Onboarding

Knewron **AI Localization Platform** for DeepHealth. This repo is **design-governed**:
the [`Design/`](Design/) folder is the **single source of truth**. Code is implemented
**one story at a time** from the [Implementation Plan](Implementation/Implementation_Plan.md),
using **GitHub Copilot** steered by the rules in [`.github/`](.github/).

> **Read this once, then follow the per-story loop below for every story.**

---

## 1. What's in this repo

| Folder | Purpose | Source of truth? |
|--------|---------|------------------|
| [`Design/`](Design/) | Architecture, DB schema, Figma, tech design, diagrams | ✅ **Authoritative** |
| [`Requirements/`](Requirements/) | Functional requirements & compliance | ✅ (cited by stories) |
| [`Implementation/`](Implementation/) | Story backlog + design→story traceability | Plan of record |
| [`.github/`](.github/) | Copilot instructions, `/implement-story` prompt, coding conventions | Governance |
| `rules/` | Windsurf always-on guardrails (optional; Windsurf users only) | Governance |
| `UX/` | UX mockups & review (reference) | Reference |

**Authority order (higher wins on conflict):**
`Design/LOCKED_Design_v1.0.md` → `Design/Database_Schema.md` → `Design/Figma_Integration.md`
→ `Design/Technical_Design_Document.md` → `Design/Architecture_Diagrams.md` →
`Requirements/Requirements_Document.md`.

---

## 2. One-time setup (each developer)

1. **Clone** the repo and open the **repo root** (this folder) as your VS Code workspace.
   This is required so Copilot can see `.github/copilot-instructions.md` and the `Design/` docs.
2. Install the **GitHub Copilot** + **Copilot Chat** VS Code extensions (latest).
3. In VS Code Settings (JSON), enable instruction + prompt files:
   ```jsonc
   {
     "github.copilot.chat.codeGeneration.useInstructionFiles": true,
     "chat.promptFiles": true
   }
   ```
4. Verify: open Copilot Chat and confirm `copilot-instructions.md` shows up in the request
   **References**.

Full details: [`.github/COPILOT_WORKFLOW.md`](.github/COPILOT_WORKFLOW.md).

---

## 3. The per-story loop (do this for EVERY story)

1. Pick **one** story from [`Implementation/Implementation_Plan.md`](Implementation/Implementation_Plan.md)
   (respect its `Depends on`). Start with **Story 0.1**.
2. In Copilot Chat (**Agent** mode) run:
   ```
   /implement-story 0.1
   ```
   (replace with your story id). Copilot will read the story's `Design Refs`, check
   dependencies, implement **only that story**, add tests, and give you a verify command.
3. **Review the diff.** If anything drifts from the design, reject and ask Copilot to fix.
4. Run the story's **Validation** command; confirm the **Acceptance** criteria pass.
5. Flip the story's row to done in
   [`Implementation/Design_Traceability_Matrix.md`](Implementation/Design_Traceability_Matrix.md)
   and the tracker in `Implementation_Plan.md`.
6. **Commit** (only after review/approval), then move to the next story.

---

## 4. Non-negotiable rules

- **Design is the source of truth.** Table/column names, enums, thresholds, flows, and
  roles MUST match the cited `Design/` sections. Never invent identifiers.
- **No silent deviations.** If the design is wrong or insufficient, **STOP and ask** — the
  design doc is changed first (version bump + approval), then code.
- **One story at a time.** No scope creep; respect dependencies; don't start the next story.
- **Out of scope (do NOT build now):** Video (Whisper/TTS/FFmpeg), IFU generation, public
  API access, GitLab integration, encryption at rest.

---

## 5. Fixed values (from design)

- **Stack:** Python 3.11+/FastAPI, Celery + Redis (1 worker, `concurrency=3`, Beat),
  PostgreSQL + SQLAlchemy + Alembic, ChromaDB (client-server), S3/GCS, WebSocket.
- **Pipeline stages:** `process → orchestrate → assemble → review → signoff → download`.
- **Thresholds:** ChromaDB image match **≥ 90%**; AI image detection confidence **70%**.
- **Roles:** `admin`, `localization_manager`, `viewer` (viewer = read-only).
- **Project model:** one project per product per **single** target language; artifacts
  processed & downloaded independently (partial completion).

---

## 6. Implementation order (high level)

`0.1` scaffold → foundations (`0.x`) → core/API (`1.x`) → pipeline framework (`2.x`) →
real-time (`3.1`) → integrations (`4.x`) → **`5.1` image sub-pipeline → `5.2` IFU (first
slice) → `5.3` UI Resource** → review/sign-off/download (`6.x`) → cross-cutting (`7.x`).

See [`Implementation/Implementation_Plan.md`](Implementation/Implementation_Plan.md) for the
full backlog with acceptance criteria.

---

## 7. Note on Copilot behavior

Auto-apply of `copilot-instructions.md` + prompt files works in **VS Code Copilot Chat**.
On JetBrains / CLI / web, reference the design docs manually (e.g. `#file:Database_Schema.md`).
Copilot follows instructions probabilistically — the **human diff review + traceability
update** is the real enforcement gate.
