"""Universal pipeline executor.

Design ref: `LOCKED_Design_v1.0.md` §3 (`Pipeline.execute`);
`Architecture_Diagrams.md` §4, §15, §18. Stories 2.1, 2.2, 2.3.

Runs synchronously inside a Celery worker (see `app/tasks/pipeline_tasks.py`).
Checkpointing (2.3): each stage commits as soon as it completes, so a crash
mid-run resumes from the first non-`complete` stage rather than from scratch
(`get_resume_stage`). A stage may raise `PipelineSuspended` (e.g. `orchestrate`
fanning out to Lokalise + the image sub-pipeline, or `signoff` awaiting human
approval) — the executor stops advancing without failing anything; an
external event (webhook, poll, join-barrier trip, approval) later calls
`resume_pipeline`, which re-enters here and picks up at the same stage.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.artifacts import ProjectArtifact
from app.pipeline import persistence as pers
from app.pipeline.constants import STAGE_ORDER, STAGE_TO_ARTIFACT_STATUS
from app.pipeline.exceptions import PipelineSuspended
from app.pipeline.factory import StrategyFactory
from app.pipeline.state_machine import StateMachine
from app.pipeline.strategy import BaseStrategy
from app.services.event_bus import publish_event
from app.services.notification_service import notify_artifact_failed, notify_download_ready

logger = get_logger(__name__)


class Pipeline:
    """Executes `STAGE_ORDER` for one artifact via its `BaseStrategy`."""

    def __init__(self, db: Session, artifact: ProjectArtifact, strategy: BaseStrategy) -> None:
        self.db = db
        self.artifact = artifact
        self.strategy = strategy
        self.state_machine = StateMachine()

    def execute(self) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        resume_stage = pers.get_resume_stage(self.db, self.artifact.artifact_id)
        start_index = STAGE_ORDER.index(resume_stage)

        for stage_name in STAGE_ORDER[start_index:]:
            try:
                ctx = self._run_stage(stage_name, ctx)
            except PipelineSuspended as exc:
                logger.info(
                    "pipeline_suspended",
                    artifact_id=str(self.artifact.artifact_id),
                    stage=stage_name,
                    reason=exc.reason,
                )
                return {"status": "suspended", "stage": stage_name, "reason": exc.reason}

        return {"status": "complete"}

    def _run_stage(self, stage_name: str, ctx: dict[str, Any]) -> dict[str, Any]:
        stage = pers.get_or_create_stage(self.db, self.artifact.artifact_id, stage_name)
        if stage.status == "complete":
            return ctx  # already done (defensive — resume already filters these out)

        target_status = STAGE_TO_ARTIFACT_STATUS[stage_name]
        if self.artifact.status != target_status:
            self.state_machine.transition(self.artifact, target_status)

        pers.start_stage(self.db, stage)
        self.db.commit()
        publish_event(self.artifact.artifact_id, "stage_started", stage=stage_name)

        try:
            method = getattr(self.strategy, stage_name)
            result = method(self.db, self.artifact, ctx)
        except PipelineSuspended:
            self.db.commit()
            raise
        except Exception as exc:  # noqa: BLE001 — persisted, then re-raised for Celery retry
            pers.fail_stage(self.db, stage, str(exc))
            if self.artifact.status != "failed":
                self.state_machine.transition(self.artifact, "failed")
            self.db.commit()
            publish_event(
                self.artifact.artifact_id, "stage_failed", stage=stage_name, data={"error": str(exc)}
            )
            notify_artifact_failed(self.db, self.artifact, stage_name, str(exc))
            raise

        pers.complete_stage(self.db, stage)
        self.db.commit()
        publish_event(
            self.artifact.artifact_id,
            "stage_completed",
            stage=stage_name,
            progress_percent=self.artifact.progress_percent,
        )
        if stage_name == "download":
            publish_event(self.artifact.artifact_id, "download_ready", stage=stage_name)
            notify_download_ready(self.db, self.artifact)
        return result if result is not None else ctx


def run_pipeline_sync(artifact_id: str) -> dict[str, Any]:
    """Celery task entrypoint — opens its own sync session/transaction."""
    with SessionLocal() as db:
        artifact = pers.get_artifact(db, artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} not found")

        strategy = StrategyFactory.create(artifact.artifact_type)
        pipeline = Pipeline(db, artifact, strategy)
        return pipeline.execute()
