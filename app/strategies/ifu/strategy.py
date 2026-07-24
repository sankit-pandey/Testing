"""IFU strategy — Design ref: `LOCKED_Design_v1.0.md` §4.1; `Architecture_Diagrams.md`
§6, §6.1; `Requirements_Document.md` §3. Story 5.2.

```
Process:     extract embedded images + positions/hash (no text parsing)
Orchestrate: fan-out -> (a) upload ORIGINAL DOCX to Lokalise document API
                        (b) image sub-pipeline
             join barrier (Story 2.5) -> resume
Assemble:    Lokalise-translated DOCX + re-inject localized images (by position)
Review:      AI review -> human review (if issues)
Sign-off:    human approval
Download:    presigned URL
```
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.artifact_subtasks import ArtifactSubtask
from app.models.artifacts import ProjectArtifact
from app.models.lokalise_tasks import LokaliseTask
from app.pipeline import persistence as pers
from app.pipeline.exceptions import PipelineSuspended
from app.pipeline.image_pipeline import ExtractedImage, run_image_pipeline
from app.pipeline.state_machine import StateMachine
from app.pipeline.strategy import BaseStrategy
from app.services import review_service
from app.services.ai_reviewer import review_document_completeness
from app.services.approval_service import get_latest_approval
from app.services.assembler import assemble_ifu
from app.services.document_processor import extract_images
from app.services.event_bus import publish_event
from app.services.lokalise_service import LokaliseService, create_lokalise_task
from app.services.notification_service import notify_review_required
from app.services.storage_service import StorageService

logger = get_logger(__name__)

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class IFUStrategy(BaseStrategy):
    def process(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        storage = StorageService()
        docx_bytes = storage.get_bytes(artifact.source_path)
        manifest = extract_images(docx_bytes)

        artifact.metadata_ = {
            **(artifact.metadata_ or {}),
            "page_count_estimate": manifest.page_count_estimate,
            "image_count": manifest.image_count,
        }
        db.flush()

        ctx["docx_bytes"] = docx_bytes
        ctx["images"] = manifest.images
        return ctx

    def orchestrate(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        existing = (
            db.execute(
                select(ArtifactSubtask).where(ArtifactSubtask.artifact_id == artifact.artifact_id)
            )
            .scalars()
            .all()
        )
        if existing:
            if all(s.status == "complete" for s in existing):
                return ctx
            raise PipelineSuspended("orchestrate: sub-tasks still pending")

        stage = pers.get_or_create_stage(db, artifact.artifact_id, "orchestrate")
        doc_subtask, image_subtask = pers.create_subtasks(
            db, artifact.artifact_id, stage.stage_id, ["document_lokalise", "image_pipeline"]
        )
        db.commit()

        lokalise = LokaliseService()
        source_language = (artifact.project.metadata_ or {}).get("source_language", "en")
        target_language = artifact.project.target_language

        result = lokalise.upload_document(
            filename=artifact.source_filename or artifact.artifact_name,
            file_bytes=ctx["docx_bytes"],
            source_language=source_language,
            target_language=target_language,
        )
        external_id = result.get("process_id") or result.get("task_id")

        create_lokalise_task(
            db,
            artifact_id=artifact.artifact_id,
            subtask_id=doc_subtask.subtask_id,
            task_type="document",
            source_language=source_language,
            target_language=target_language,
            lokalise_task_external_id=external_id,
        )
        db.commit()
        publish_event(artifact.artifact_id, "subtask_progress", stage="orchestrate", data={"branch": "document"})

        images: list[ExtractedImage] = ctx.get("images", [])
        run_image_pipeline(db, artifact, image_subtask, images)
        # run_image_pipeline either raises PipelineSuspended (cache misses queued
        # to Lokalise) or returns having already completed+checked the barrier.
        raise PipelineSuspended("orchestrate: fanned out to Lokalise (document) + image sub-pipeline")

    def assemble(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        storage = StorageService()
        lokalise = LokaliseService()

        doc_task = (
            db.execute(
                select(LokaliseTask).where(
                    LokaliseTask.artifact_id == artifact.artifact_id, LokaliseTask.task_type == "document"
                )
            )
            .scalars()
            .first()
        )
        if doc_task is None:
            raise RuntimeError(
                f"No 'document' lokalise_tasks row for artifact {artifact.artifact_id}; "
                "orchestrate() must run before assemble()"
            )
        if not doc_task.download_url:
            doc_task.download_url = lokalise.download_translations(artifact.project.target_language)
            db.commit()

        import httpx

        with httpx.Client(timeout=60.0) as client:
            response = client.get(doc_task.download_url)
            response.raise_for_status()
            translated_docx_bytes = response.content

        from app.models.image_processing import ImageProcessing

        translated_rows = (
            db.execute(
                select(ImageProcessing).where(
                    ImageProcessing.artifact_id == artifact.artifact_id,
                    ImageProcessing.translated_image_path.is_not(None),
                )
            )
            .scalars()
            .all()
        )
        localized_images = {
            str(row.image_position.get("inline_shape_index")): storage.get_bytes(row.translated_image_path)
            for row in translated_rows
            if row.image_position
        }

        expected_image_count = (artifact.metadata_ or {}).get("image_count", 0)
        assembled_bytes, findings = assemble_ifu(
            translated_docx_bytes, localized_images, expected_image_count=expected_image_count
        )

        filename = f"{artifact.artifact_name.rsplit('.', 1)[0]}_{artifact.project.target_language}.docx"
        output_key = storage.new_output_key(artifact.project_id, artifact.artifact_id, filename)
        storage.put_bytes(output_key, assembled_bytes, DOCX_CONTENT_TYPE)
        artifact.output_path = output_key
        db.flush()

        ctx["assemble_findings"] = findings
        return ctx

    def review(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        # Note: by the time this runs, the executor has already transitioned
        # artifact.status to "reviewing" (it sets STAGE_TO_ARTIFACT_STATUS
        # before invoking the stage) even on a resume from
        # `needs_human_review` — so entry type is distinguished by whether
        # findings were already persisted, not by `artifact.status`.
        if review_service.has_findings(db, artifact.artifact_id):
            if review_service.has_open_blocking_findings(db, artifact.artifact_id):
                raise PipelineSuspended("review: waiting on human resolution of blocking findings")
            return ctx

        findings = ctx.get("assemble_findings") or review_document_completeness(
            expected_image_count=(artifact.metadata_ or {}).get("image_count", 0),
            assembled_image_count=(artifact.metadata_ or {}).get("image_count", 0),
            expected_tables=0,
            actual_tables=0,
        )
        has_blocking = review_service.persist_findings(db, artifact.artifact_id, findings)
        db.commit()

        if has_blocking:
            StateMachine().transition(artifact, "needs_human_review")
            db.commit()
            publish_event(artifact.artifact_id, "review_required", stage="review")
            notify_review_required(db, artifact)
            raise PipelineSuspended("review: blocking findings need human resolution")

        return ctx

    def signoff(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        latest = get_latest_approval(db, artifact.artifact_id)
        if latest is not None and latest.approval_status == "approved":
            return ctx
        raise PipelineSuspended("signoff: awaiting human approval")

    def download(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        storage = StorageService()
        from datetime import datetime, timedelta, timezone

        artifact.download_url = storage.presign_download(artifact.output_path)
        artifact.download_url_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=storage.settings.storage_presign_expiry_seconds
        )
        artifact.progress_percent = 100
        artifact.completed_at = datetime.now(timezone.utc)
        db.flush()

        pers.recompute_project_status_sync(db, artifact.project_id)
        return ctx
