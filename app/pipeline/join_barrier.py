"""DB-backed parallel sub-task join barrier.

Design ref: `LOCKED_Design_v1.0.md` §7; `Architecture_Diagrams.md` §6.1, §16
("both branches complete, barrier trips, resume"); `Database_Schema.md` §6
(`artifact_subtasks`). Story 2.5.

Guarantees, per Arch §6.1:
- two branches marked complete in any order (incl. simultaneously/duplicates)
  trigger the next stage exactly once
- barrier state survives worker restart (it's a Postgres row, not memory)

`SELECT ... FOR UPDATE` on the artifact's subtask rows serializes concurrent
completions; an idempotency key belt-and-suspenders-guards the *resume
dispatch* itself (the Celery enqueue happens after the DB transaction commits,
so it needs its own dedup).
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.artifact_subtasks import ArtifactSubtask
from app.utils.idempotency import acquire_idempotency_key

logger = get_logger(__name__)


def complete_subtask_and_maybe_resume(
    artifact_id: uuid.UUID | str, task_type: str, result: dict[str, Any] | None = None
) -> bool:
    """Mark the `task_type` sub-task for `artifact_id` complete; if it is the
    last sibling to finish, enqueue `resume_pipeline` exactly once.

    Returns True iff this call tripped the barrier and enqueued the resume.
    """
    artifact_id = uuid.UUID(str(artifact_id))

    with SessionLocal() as db, db.begin():
        siblings = (
            db.execute(
                select(ArtifactSubtask)
                .where(ArtifactSubtask.artifact_id == artifact_id)
                .with_for_update()
            )
            .scalars()
            .all()
        )

        target = next((s for s in siblings if s.task_type == task_type), None)
        if target is None:
            raise ValueError(f"No subtask of type '{task_type}' for artifact {artifact_id}")

        if target.status == "complete":
            logger.info(
                "join_barrier_duplicate_completion", artifact_id=str(artifact_id), task_type=task_type
            )
            return False  # already processed — duplicate webhook/poll/retry

        target.status = "complete"
        target.completed_at = datetime.now(timezone.utc)
        target.progress_percent = 100
        if result:
            target.result = result

        db.flush()
        all_complete = all(s.status == "complete" for s in siblings)

    if not all_complete:
        return False

    if not acquire_idempotency_key(f"join-barrier:{artifact_id}"):
        logger.info("join_barrier_already_tripped", artifact_id=str(artifact_id))
        return False

    from app.tasks.pipeline_tasks import resume_pipeline

    resume_pipeline.delay(str(artifact_id), reason=f"join_barrier:{task_type}")
    logger.info("join_barrier_tripped", artifact_id=str(artifact_id), task_type=task_type)
    return True
