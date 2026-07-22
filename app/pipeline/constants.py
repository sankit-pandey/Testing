"""Universal pipeline stage order and artifact/stage status vocabularies.

Design ref: `LOCKED_Design_v1.0.md` §3 (six universal stages);
`Architecture_Diagrams.md` §5 (artifact state machine — the granular states
used for `project_artifacts.status`; `Database_Schema.md` §4's column
comment lists a coarser summary set, but the column has no CHECK constraint,
and Story 2.2's own Design Refs cite Arch §5 for these exact values).
"""

STAGE_ORDER: tuple[str, ...] = (
    "process",
    "orchestrate",
    "assemble",
    "review",
    "signoff",
    "download",
)

# artifact_stages.status (Database_Schema.md §5)
STAGE_STATUSES: tuple[str, ...] = ("pending", "in_progress", "complete", "failed", "skipped")

# project_artifacts.status (Architecture_Diagrams.md §5)
ARTIFACT_STATUSES: tuple[str, ...] = (
    "pending",
    "processing",
    "orchestrating",
    "assembling",
    "reviewing",
    "needs_human_review",
    "signoff",
    "complete",
    "failed",
    "cancelled",
)

# Maps the stage currently running to the artifact-level status it puts the
# artifact into while that stage executes (Architecture_Diagrams.md §5, §15).
STAGE_TO_ARTIFACT_STATUS: dict[str, str] = {
    "process": "processing",
    "orchestrate": "orchestrating",
    "assemble": "assembling",
    "review": "reviewing",
    "signoff": "signoff",
    "download": "complete",
}

# artifact_subtasks.task_type (Database_Schema.md §6)
SUBTASK_TYPES: tuple[str, ...] = (
    "image_pipeline",
    "audio_pipeline",
    "subtitle_pipeline",
    "document_lokalise",
    "assembly",
)
