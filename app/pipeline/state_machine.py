"""Artifact state machine — Design ref: `Architecture_Diagrams.md` §5;
`LOCKED_Design_v1.0.md` §7 ("State Machine — enforce valid transitions").
Story 2.2.
"""
from app.models.artifacts import ProjectArtifact
from app.pipeline.exceptions import InvalidTransitionError

# Transitions drawn in Architecture_Diagrams.md §5, plus cancellation allowed
# from any non-terminal state (Requirements_Document.md §2.2 — Localization
# Managers can "cancel individual artifacts" without a stage qualifier; the
# diagram only draws `pending`/`processing` -> `cancelled` explicitly).
_NON_TERMINAL = (
    "pending",
    "processing",
    "orchestrating",
    "assembling",
    "reviewing",
    "needs_human_review",
    "signoff",
)

TRANSITIONS: dict[str, set[str]] = {
    "pending": {"processing", "cancelled"},
    "processing": {"orchestrating", "failed", "cancelled"},
    "orchestrating": {"assembling", "failed", "cancelled"},
    "assembling": {"reviewing", "failed", "cancelled"},
    "reviewing": {"needs_human_review", "signoff", "failed", "cancelled"},
    "needs_human_review": {"reviewing", "cancelled"},
    "signoff": {"complete", "reviewing", "cancelled"},
    "failed": {"processing"},
    "complete": set(),
    "cancelled": set(),
}


class StateMachine:
    """Validates and applies `project_artifacts.status` transitions."""

    def validate(self, current: str, target: str) -> None:
        allowed = TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Cannot transition artifact from '{current}' to '{target}'")

    def transition(self, artifact: ProjectArtifact, target: str) -> ProjectArtifact:
        self.validate(artifact.status, target)
        artifact.status = target
        return artifact
