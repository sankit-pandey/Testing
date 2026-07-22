"""UI Resource strategy — Design ref: `LOCKED_Design_v1.0.md` §4.3;
`Architecture_Diagrams.md` §9; `Requirements_Document.md` §3.3. Story 5.3.

```
Process:     parse JSON/XML/YAML/Properties/RESX -> extract strings
Orchestrate: send strings -> Lokalise (single branch; still suspends/resumes
             via the same webhook+poll+join-barrier machinery as IFU)
Assemble:    reconstruct resource file with translations
Review:      AI review -> human review
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
from app.pipeline.state_machine import StateMachine
from app.pipeline.strategy import BaseStrategy
from app.services import review_service
from app.services.ai_reviewer import Finding
from app.services.approval_service import get_latest_approval
from app.services.event_bus import publish_event
from app.services.lokalise_service import (
    LokaliseService,
    create_lokalise_task,
    fetch_translation_bundle,
)
from app.services.notification_service import notify_review_required
from app.services.resource_parser import detect_format, extract_strings, reconstruct
from app.services.storage_service import StorageService

logger = get_logger(__name__)


class UIResourceStrategy(BaseStrategy):
    def process(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        storage = StorageService()
        source_bytes = storage.get_bytes(artifact.source_path)
        fmt = detect_format(artifact.source_filename or artifact.artifact_name)
        strings = extract_strings(source_bytes, fmt)

        artifact.metadata_ = {**(artifact.metadata_ or {}), "format": fmt, "string_count": len(strings)}
        db.flush()

        ctx["strings"] = strings
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
            raise PipelineSuspended("orchestrate: awaiting Lokalise ui_strings translation")

        stage = pers.get_or_create_stage(db, artifact.artifact_id, "orchestrate")
        (subtask,) = pers.create_subtasks(db, artifact.artifact_id, stage.stage_id, ["document_lokalise"])
        db.commit()

        strings: dict[str, str] = ctx.get("strings", {})
        key_prefix = f"ui.{artifact.artifact_id}."
        items = [
            {"key": f"{key_prefix}{path}", "sourceText": text, "context": path}
            for path, text in strings.items()
        ]

        lokalise = LokaliseService(tenant_id=artifact.project.product.tenant_id)
        source_language = (artifact.project.metadata_ or {}).get("source_language", "en")
        result = lokalise.upload_content(items, source_language=source_language) if items else {}
        external_id = result.get("keys", [{}])[0].get("task_id") if result.get("keys") else None

        lokalise_task = create_lokalise_task(
            db,
            artifact_id=artifact.artifact_id,
            subtask_id=subtask.subtask_id,
            task_type="ui_strings",
            source_language=source_language,
            target_language=artifact.project.target_language,
            lokalise_task_external_id=external_id,
        )
        lokalise_task.metadata_ = {"key_prefix": key_prefix}
        db.commit()

        if not items:
            # Nothing translatable — complete immediately, no Lokalise wait.
            from app.pipeline.join_barrier import complete_subtask_and_maybe_resume

            subtask.status = "complete"
            db.commit()
            complete_subtask_and_maybe_resume(artifact.artifact_id, subtask.task_type)
            return ctx

        publish_event(artifact.artifact_id, "subtask_progress", stage="orchestrate", data={"branch": "ui_strings"})
        raise PipelineSuspended("orchestrate: fanned out to Lokalise (ui_strings)")

    def assemble(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        storage = StorageService()
        source_bytes = storage.get_bytes(artifact.source_path)
        fmt = (artifact.metadata_ or {}).get("format")
        translations = (artifact.metadata_ or {}).get("translations", {})

        reconstructed = reconstruct(source_bytes, fmt, translations)

        filename = artifact.source_filename or artifact.artifact_name
        base, _, ext = filename.rpartition(".")
        output_filename = f"{base or filename}_{artifact.project.target_language}.{ext or fmt}"
        output_key = storage.new_output_key(artifact.project_id, artifact.artifact_id, output_filename)
        storage.put_bytes(output_key, reconstructed, storage.guess_content_type(output_filename))
        artifact.output_path = output_key
        db.flush()

        expected = (artifact.metadata_ or {}).get("string_count", 0)
        translated = len(translations)
        findings: list[Finding] = []
        if translated < expected:
            findings.append(
                Finding(
                    "major",
                    "completeness",
                    f"Only {translated}/{expected} strings were translated",
                )
            )
        ctx["assemble_findings"] = findings
        return ctx

    def review(self, db: Session, artifact: ProjectArtifact, ctx: dict[str, Any]) -> dict[str, Any]:
        # See IFUStrategy.review — entry type is distinguished by whether
        # findings were already persisted, not by `artifact.status` (the
        # executor already transitions status to "reviewing" before this runs).
        if review_service.has_findings(db, artifact.artifact_id):
            if review_service.has_open_blocking_findings(db, artifact.artifact_id):
                raise PipelineSuspended("review: waiting on human resolution of blocking findings")
            return ctx

        findings = ctx.get("assemble_findings", [])
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
        from datetime import datetime, timedelta, timezone

        storage = StorageService()
        artifact.download_url = storage.presign_download(artifact.output_path)
        artifact.download_url_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=storage.settings.storage_presign_expiry_seconds
        )
        artifact.progress_percent = 100
        artifact.completed_at = datetime.now(timezone.utc)
        db.flush()

        pers.recompute_project_status_sync(db, artifact.project_id)
        return ctx


def on_ui_strings_ready(db: Session, lokalise_task: LokaliseTask) -> None:
    """Completion handler dispatched from `lokalise_service._dispatch_completion`
    once the batched `ui_strings` Lokalise task completes.
    """
    artifact = db.get(ProjectArtifact, lokalise_task.artifact_id)
    lokalise = LokaliseService(tenant_id=artifact.project.product.tenant_id)
    bundle_url = lokalise.download_translations(lokalise_task.target_language)
    flat = fetch_translation_bundle(bundle_url)

    prefix = (lokalise_task.metadata_ or {}).get("key_prefix", "")
    translations = {k[len(prefix):]: v for k, v in flat.items() if k.startswith(prefix)}

    artifact.metadata_ = {**(artifact.metadata_ or {}), "translations": translations}
    db.flush()
    db.commit()

    subtask = db.get(ArtifactSubtask, lokalise_task.subtask_id)
    if subtask is not None:
        from app.pipeline.join_barrier import complete_subtask_and_maybe_resume

        complete_subtask_and_maybe_resume(lokalise_task.artifact_id, subtask.task_type)
