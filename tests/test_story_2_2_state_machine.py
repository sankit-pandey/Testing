"""Story 2.2 acceptance: invalid transitions are rejected; valid ones apply."""
import pytest

from app.models.artifacts import ProjectArtifact
from app.pipeline.exceptions import InvalidTransitionError
from app.pipeline.state_machine import StateMachine


def _artifact(status: str) -> ProjectArtifact:
    return ProjectArtifact(artifact_type="IFU", artifact_name="a.docx", status=status)


def test_valid_transition_applies():
    artifact = _artifact("pending")
    StateMachine().transition(artifact, "processing")
    assert artifact.status == "processing"


def test_invalid_transition_rejected():
    artifact = _artifact("pending")
    with pytest.raises(InvalidTransitionError):
        StateMachine().transition(artifact, "complete")
    assert artifact.status == "pending"  # unchanged


def test_terminal_states_have_no_outgoing_transitions():
    artifact = _artifact("complete")
    with pytest.raises(InvalidTransitionError):
        StateMachine().transition(artifact, "processing")


def test_failed_can_retry_to_processing():
    artifact = _artifact("failed")
    StateMachine().transition(artifact, "processing")
    assert artifact.status == "processing"
