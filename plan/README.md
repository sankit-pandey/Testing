# AI Localization Platform — Design & Planning Folder

Knewron **AI Localization Platform** for DeepHealth. This folder is the
**design record** for the backend implemented at the repository root
(`../app/`, `../README.md`). It is **design-governed**: the [`Design/`](Design/)
folder is the single source of truth, and everything in [`app/`](../app/)
must trace back to a section in it via
[`Implementation/Design_Traceability_Matrix.md`](Implementation/Design_Traceability_Matrix.md).

> **New here, human or LLM?** Read
> [`LLM_BUILD_GUIDE.md`](LLM_BUILD_GUIDE.md) first — one dense, self-contained
> page covering what this is, where the code lives, the full data model,
> story status, and the rules for extending it. This README is a lighter,
> narrative tour of the same territory.

---

## 1. Status

**Fully implemented.** Every story in
[`Implementation/Implementation_Plan.md`](Implementation/Implementation_Plan.md)
(`0.1` through `8.5`) is done, at `../app/`. This is not a pre-implementation
planning folder anymore — treat it as the **as-built design record**:
authoritative for what the code *should* do, and the place to update first
if you need the code to do something different.

## 2. What's in this repo

| Folder | Purpose | Source of truth? |
|--------|---------|-------------------|
| [`Design/`](Design/) | Architecture, DB schema, Figma, tech design, diagrams | ✅ **Authoritative** |
| [`Requirements/`](Requirements/) | Functional requirements & compliance | ✅ (cited by stories) |
| [`Implementation/`](Implementation/) | Story backlog + design→story traceability | Plan of record (all done) |
| [`rules/`](rules/) | Same governance rules, in a generic always-on-rule format | Governance (tool-agnostic) |
| [`UX/`](UX/) | UX mockups & review | Reference |
| `../app/` | The implemented backend | The code itself |
| `../.github/` | Coding-convention instruction files (async rules, story-test naming, etc.) | Governance, code-style |

**Authority order (higher wins on conflict)** — full detail in
[`LLM_BUILD_GUIDE.md`](LLM_BUILD_GUIDE.md) §3:
`Design/LOCKED_Design_v1.0.md` → `Design/Database_Schema.md` →
`Design/Figma_Integration.md` → `Design/Technical_Design_Document.md`
(§11 is a later addendum, see below) → `Design/Architecture_Diagrams.md` →
`Requirements/Requirements_Document.md`.

## 3. Post-implementation extensions

Four infrastructure extensions were added after the initial build, by
direct client instruction: multi-cloud object storage, multi-cloud image
embeddings, a ChromaDB-only `tenant_id` partition key (**not** relational
multi-tenancy — this was tried and explicitly reverted), and
Poetry + externalized Redis. Full detail: `Design/Technical_Design_Document.md`
§11, traced as stories `8.1`–`8.5` in `Implementation/Implementation_Plan.md`
and `Implementation/Design_Traceability_Matrix.md`.

## 4. Extending or fixing the implementation

This still follows the same design-governed loop the project was originally
built with — it doesn't stop applying just because the initial build is
done:

1. Find the governing design section (via the authority order above, or by
   searching `Implementation/Design_Traceability_Matrix.md` for the
   table/feature you're touching).
2. If the design needs to change to support what you're doing, **update the
   design doc first** (version bump, note it in that doc's Document Control
   table), *then* write code. Never let code silently diverge from what the
   design docs say.
3. Match table/column names, enums, thresholds, and roles **exactly** as
   written in the cited design section. Don't invent identifiers.
4. Add or update a new row in `Implementation/Implementation_Plan.md` /
   `Design_Traceability_Matrix.md` if you're adding a genuinely new
   capability (follow the `8.x` extensions as the template for how that
   looks in practice).
5. Add/update `pytest` tests under `../tests/`.

## 5. Non-negotiable rules

- **Design is the source of truth.** Table/column names, enums, thresholds,
  flows, and roles MUST match the cited `Design/` sections.
- **No silent deviations.** If the design is wrong or insufficient, update
  the design doc first, then code.
- **Out of scope (do not build unless explicitly asked):** Video
  (Whisper/TTS/FFmpeg), IFU generation, public API access, GitLab
  integration, encryption at rest, relational multi-tenancy.

## 6. Fixed values (from design)

- **Stack:** Python 3.11+/FastAPI, Celery + Redis (external/managed; 1
  worker, `concurrency=3`, Beat), PostgreSQL + SQLAlchemy + Alembic,
  ChromaDB (client-server), S3/GCS/local storage, WebSocket, Poetry.
- **Pipeline stages:** `process → orchestrate → assemble → review → signoff → download`.
- **Thresholds:** ChromaDB image match **≥ 90%**; AI image detection confidence **70%**.
- **Roles:** `admin`, `localization_manager`, `viewer` (viewer = read-only).
- **Project model:** one project per product per **single** target language;
  artifacts processed & downloaded independently (partial completion).

## 7. Running the actual code

Not here — see `../README.md` for setup, `docker compose up`, Alembic
migrations, and `poetry run pytest`. This folder is documentation, not code.
