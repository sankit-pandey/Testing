# Developer Guide — Using GitHub Copilot on this repo

This repo is **design-governed**: the `Design/` folder is the source of truth. The files
in `.github/` make Copilot follow that automatically. Read this once before you start.

## What's in `.github/`
- **`copilot-instructions.md`** — auto-attached to **every** Copilot Chat request. Repo-wide
  rules: design is source of truth, one story at a time, fixed values, out-of-scope list.
- **`prompts/implement-story.prompt.md`** — the `/implement-story` command that generates a
  single story the right way.
- **`instructions/python-code.instructions.md`** — coding conventions auto-applied to `**/*.py`.

## One-time VS Code setup (each developer)
1. Use **VS Code** with the **GitHub Copilot** + **Copilot Chat** extensions (latest).
2. Open the **whole `AI Localization` folder** as your workspace (repo root). This is required
   so Copilot can see `copilot-instructions.md`, `Design/`, and `Implementation/`.
3. In Settings (JSON), enable instruction + prompt files:
   ```jsonc
   {
     "github.copilot.chat.codeGeneration.useInstructionFiles": true,
     "chat.promptFiles": true
   }
   ```
4. Confirm it's active: open Copilot Chat and check that `copilot-instructions.md` appears in
   the request's **References**.

## The per-story workflow (do this for every story)
1. Pick **one** story from `Implementation/Implementation_Plan.md` (respect `Depends on`).
2. In Copilot Chat (**Agent** mode), run:
   ```
   /implement-story 2.5
   ```
   (replace `2.5` with your story id).
3. Copilot will: restate the story → read its `Design Refs` → check dependencies →
   confirm design conformance → implement **only that story** → add tests → give you a
   run/verify command and a Definition-of-Done checklist.
4. **You review the diff.** If anything drifts from the design, reject and ask Copilot to fix.
5. Run the validation command; confirm acceptance criteria pass.
6. Flip the story's row to done in `Implementation/Design_Traceability_Matrix.md` and the
   tracker in `Implementation_Plan.md`.
7. **Commit** (only after review/approval). Then move to the next story.

## Guardrails Copilot must respect (it's told to)
- **No scope creep** — only the current story.
- **No silent deviations** — if the design is wrong, stop and change the design doc first
  (version bump + approval), then code.
- **No out-of-scope work** — Video/Whisper/TTS/FFmpeg, IFU generation, public API, GitLab,
  encryption at rest.
- **No invented identifiers** — table/column names, enums, thresholds, roles must match `Design/`.

## If Copilot ignores the design
- Make sure the workspace root is the `AI Localization` folder and the two settings above are on.
- Add explicit context to your chat with `#file:` (e.g. `#file:Database_Schema.md`) for the
  design sections the story cites.
- Re-run `/implement-story` — it forces the read-design-first steps.
