"""Strategy base class — Design ref: `LOCKED_Design_v1.0.md` §3, §13;
`Technical_Design_Document.md` §2.0. Story 2.1.

Each stage method receives the sync DB session, the `ProjectArtifact` row,
and a mutable `ctx` dict threaded through the pipeline run (per-run state —
not persisted directly; stages persist what they need onto the artifact/
stage/subtask rows themselves). Raise `PipelineSuspended` from a stage
(typically `orchestrate` or `signoff`) to fan out async work and stop the
executor without failing the artifact.
"""
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.models.artifacts import ProjectArtifact


class BaseStrategy(ABC):
    """Per-artifact-type behavior for each of the six universal stages."""

    @abstractmethod
    def process(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def orchestrate(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def assemble(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def review(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def signoff(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def download(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]: ...


class NoOpStrategy(BaseStrategy):
    """Trivially completes every stage — used to prove the executor advances
    through all six stages end-to-end (Story 2.1 acceptance).
    """

    def process(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def orchestrate(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def assemble(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def review(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def signoff(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def download(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx
