---
mode: agent
description: Implement exactly ONE story from the Implementation Plan, strictly conforming to the cited Design docs.
---

# Implement one story (design-governed)

You are implementing **one** story from `Implementation/Implementation_Plan.md` for the
AI Localization Platform. The `Design/` folder is the **source of truth**. Follow the
repo instructions in `.github/copilot-instructions.md` at all times.

## Input
The developer will give a **story id** (e.g. `2.5`) — this may be provided as `${input:storyId}`.
If no story id is provided, ask for it before doing anything else.

## Steps (do them in this order, and show your work)

1. **Locate the story.** Read the story block for the given id in
   `Implementation/Implementation_Plan.md`. Restate its **Goal, Scope, Depends on,
   Acceptance, Validation** back to the developer.

2. **Load the design.** Open every reference in the story's **`Design Refs`** line and
   the matching rows in `Implementation/Design_Traceability_Matrix.md`. List the exact
   design sections you read and the key rules/values they impose (table/column names,
   enums, thresholds, flows, roles).

3. **Dependency check.** Confirm the story's `Depends on` items exist in the codebase.
   If a dependency is missing, STOP and tell the developer which prerequisite story
   must be done first. Do **not** re-implement dependencies.

4. **Design-conformance check.** Before coding, confirm your plan matches the cited
   design **exactly**. If the design is wrong, insufficient, or contradictory, **STOP
   and ask** — do not diverge in code. The design doc must be updated (version bump +
   approval) first.

5. **Implement — this story's scope ONLY.** No scope creep, no work from other stories.
   Follow the coding conventions in `.github/copilot-instructions.md`. All DB changes go
   through **Alembic migrations**.

6. **Tests & validation.** Add unit tests for new logic. Provide the exact command(s)
   or endpoint(s) from the story's **Validation** so the reviewer can verify locally.

7. **Summary for review.** End with:
   - Files created/changed (bullet list).
   - Which `Design Refs` each change satisfies.
   - How to run/verify (copy-pastable commands).
   - The **Definition of Done** checklist with each item checked or flagged.

## Hard stops
- Do **not** commit. The human reviews the diff and approves first.
- Do **not** start the next story.
- Do **not** implement anything marked **out of scope** (Video/Whisper/TTS/FFmpeg,
  IFU generation, public API, GitLab, encryption at rest).
- Do **not** invent table/column names, enums, thresholds, or roles not in the design.
