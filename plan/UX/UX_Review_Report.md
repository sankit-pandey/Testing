# 🎨 UX Review Report — Localization Platform (First Draft)

**Reviewed:** `UX/UX.pdf` (single-page mockup board, ~14 screens showing the end-to-end "Localize" flow)
**Reviewed against:** `Design/LOCKED_Design_v1.0.md`, `Requirements/Requirements_Document.md`, `Design/Database_Schema.md`
**Date:** July 21, 2026 · **Reviewer:** Cascade · **Status:** 📋 Draft review

---

## 1. Overall Impression

Strong, clean first draft. The core mental model — **Product → Project (single language) → Assets → Start → Track/Download** — is clear and maps well to the locked domain model. Progressive disclosure and empty states are handled thoughtfully. The main issues are **missing workflow states/screens** (human review/sign-off, failures, image handling) and a few **design/requirements mismatches** (asset types, file formats, stage visibility).

---

## 2. What Works Well

- **Correct domain model.** One project = one product + **single target language** (`DE German`), with **multiple assets** under it — exactly matches the locked design.
- **Partial completion** is represented: each asset has independent progress + its own **Download** (enabled only at 100%). Matches `Requirements §5.7.5`.
- **Progressive disclosure:** product → project → asset → start is intuitive; good empty states ("No translation jobs yet").
- **Expectation-setting:** Video asset type shown as **"Coming Soon"** (correctly out of scope).
- **Live feel:** progress bars + "Just now" timestamps imply real-time updates (WebSocket).
- **Filtering:** All / Active / Complete tabs on the jobs list.

---

## 3. Alignment Issues vs Locked Design & Requirements (highest priority)

| # | Severity | Finding | Authority |
|---|----------|---------|-----------|
| 3.1 | **P0** | **Missing asset type: UI Resource.** Add Asset offers only Document / Video, but the design supports **UI Resource files** (JSON/XML/YAML/Properties/RESX). Add it or mark "Coming Soon" like Video. | LOCKED §4.3 |
| 3.2 | **P0** | **File formats mismatch.** Upload says "PDF · DOCX · TXT", but the IFU pipeline is **DOCX-based** (sent to Lokalise doc API; `python-docx`). Sample asset is even named `ifu-document-v3.pdf`. Clarify whether PDF is a supported IFU input; add UI-resource formats. | LOCKED §4.1; Technical_Design §2.1.2 |
| 3.3 | **P0** | **No stage-level status.** UI shows a single % + In Progress/Complete. Requirements define granular states — In Translation (Lokalise) → In Review (Lokalise) → In Approval (Lokalise) → Assembly (Knewron) → Complete. Surface the current stage. | Requirements §5.6.1 |
| 3.4 | **P1** | **No human review / sign-off UI.** Pipeline has AI review → human review → approval. Mockups show a "Review Findings" button but no **approve/reject / sign-off** screen. | Requirements §5.8; Database_Schema (review_findings, approvals) |
| 3.5 | **P1** | **Language data inconsistency.** Project is German (DE), but asset cards show **ES** (Spanish) badges. Likely placeholder noise; confirm one-language-per-project is enforced in the UI. | LOCKED §9; Requirements §5.6.2 |

---

## 4. Missing Screens / States

- **[P1] Failure / error state** — asset failed, **Lokalise rejection → correct & resubmit**. No failed-state or retry UI. (`Requirements §5.7.1`)
- **[P1] Cancel asset/project** — API supports canceling an artifact; no cancel/confirm UI. (`Technical_Design §2.1.1`)
- **[P2] Image localization / flagged images** — non-UI or no-match images are retained + flagged for manual handling; no surface to review/handle them (could live under Review Findings). (`LOCKED §5`; `Figma_Integration §8`)
- **[P2] Notifications** — in-app notifications specified; no notification center/bell. (`Requirements §5.6.4`)
- **[P2] Admin / settings** — integration config (Lokalise/Figma/ChromaDB, `system_settings`) and **RBAC personas** (admin/localization_manager/**viewer** read-only) not represented. (`Requirements §2.2`, §6)
- **[P2] Auth / SSO** entry screen (may be intentionally out of scope). (`Requirements §6`)
- **[P2] "Review Findings" detail** — the destination view isn't in the board.

---

## 5. UX / IA Heuristics

- **[P1] IA crowding on the left rail.** "Create Localization Request" (really *product select*), inline "New Localization Project", live project cards, **and** a "Localization Projects (3)" list all stack in one column. Consider a clearer hierarchy: **Products → Projects (list) → Project detail (assets)**.
- **[P2] Duplicate entry points.** Two "New Localization Project" affordances (inline form + `+` button) — unify or clarify.
- **[P2] Label clarity.** "Create Localization Request" mostly = "Select a product". Rename to reduce confusion (e.g., "Select Product" / "New Request").
- **[P2] Scale.** Jobs list has no search/pagination; a product with many assets/languages will overflow.
- **[P2] Wasted space** in early steps — the large empty right panel could host guidance/onboarding.

---

## 6. Accessibility (caveated — inferred from render; verify in Figma)

- **[P1] Low-contrast text:** muted grey helper/subtitle text and disabled buttons (light-purple **Create Project**, grey **Download/Review Findings**) look **below WCAG AA (4.5:1)**.
- **[P2] Status by color:** yellow=in-progress, green=complete — a dot+label is present (good); keep the text label so status is not color-only.
- **[P2] Verify** keyboard navigation & visible focus states for dropdowns/toggles; ensure truncated asset names have tooltips/full text.

---

## 7. Prioritized Recommendations

**P0 (blockers / design alignment)**
- Add **UI Resource** asset type.
- Fix **file-format list** to match the pipeline (DOCX + UI-resource formats; clarify PDF).
- Add **stage-level status** to asset cards.

**P1 (core workflow / usability)**
- Add **human review & sign-off** screen (approve/reject).
- Add **failure/rejection + resubmit** and **cancel** states.
- Resolve **IA crowding** in the left rail.
- Fix **language placeholder inconsistency**.
- Raise **text/disabled contrast** to WCAG AA.

**P2 (completeness / scale)**
- Notifications center; admin/settings + RBAC (viewer read-only); image-flag handling; list search/pagination; label cleanups; onboarding in empty space.

---

## 8. Screens Observed (board walkthrough)

1. Empty dashboard — header (CitiusTech/Knewron, user menu), "Create Localization Request" (product select), "No translation jobs yet".
2. Product dropdown open (search + product list).
3. Product selected → "New Localization Project" form (Project Name, Target Language, Create Project).
4. Target Language dropdown open (search + language list).
5. Project card created (`test / German · 0 assets · Pending`) with "Add Asset".
6. Add Asset panel — Asset Type Document / Video (Coming Soon); Browse/drag-drop (PDF · DOCX · TXT, up to 50 MB).
7. Asset added → "New Localization Project" + **Start Localization**.
8. Jobs list — asset cards with progress (58% / 32% / 71%), In Progress, Download + Review Findings (disabled).
9. Complete state — 100% green, Download + Review Findings enabled.
10. Left sidebar — "Localization Projects (3)": German IFU Translation (2 assets), French User Manual (1 asset).

---

**Next step:** Confirm the P0 design-alignment items (asset types, formats, stage status) so the UX and the locked design stay in sync before high-fidelity/build.
