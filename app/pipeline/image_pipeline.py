"""Image localization sub-pipeline — reused by IFU (and, when built, Video).

Design ref: `LOCKED_Design_v1.0.md` §5; `Figma_Integration.md` §6, §8;
`Requirements_Document.md` §4; `Architecture_Diagrams.md` §16.
Story 5.1.

Per-image flow: classify -> ChromaDB match (per product, >= 90%) -> cache
check -> (cache hit: reuse) or (cache miss: batch for Lokalise, then Figma
render + AI review) -> cache store -> ready. Non-UI / low-confidence /
no-match images are **retained unchanged and flagged** for manual handling
(never fail the artifact) per `Figma_Integration.md` §8.

Because each image's translation may need Lokalise's async human-review
workflow, all cache-miss images in one artifact are batched into a single
Lokalise upload; the `image_pipeline` sub-task suspends until that batch
completes (webhook/poll — Story 4.2), then `on_image_translations_ready`
renders every pending image and trips the join barrier (Story 2.5).
"""
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.artifact_subtasks import ArtifactSubtask
from app.models.artifacts import ProjectArtifact
from app.models.figma_images import FigmaImage
from app.models.image_processing import ImageProcessing
from app.models.lokalise_tasks import LokaliseTask
from app.models.translation_cache import TranslationCache
from app.pipeline.exceptions import PipelineSuspended
from app.services.ai_reviewer import review_rendered_image
from app.services.chromadb_service import ChromaDBService, ChromaDBUnavailableError
from app.services.figma_service import FigmaService, get_text_elements
from app.services.image_classifier import get_image_classifier, is_confident
from app.services.lokalise_service import LokaliseService, create_lokalise_task, fetch_translation_bundle
from app.services.storage_service import StorageService

logger = get_logger(__name__)


@dataclass
class ExtractedImage:
    image_id: uuid.UUID
    image_hash: str
    image_bytes: bytes
    position: dict[str, Any]
    filename: str


def run_image_pipeline(
    db: Session,
    artifact: ProjectArtifact,
    subtask: ArtifactSubtask,
    images: list[ExtractedImage],
) -> None:
    """Classify/match/cache every extracted image; batch cache-misses to
    Lokalise. Raises `PipelineSuspended` if any image needs an async
    translation wait; otherwise completes the sub-task synchronously.
    """
    classifier = get_image_classifier()
    storage = StorageService()
    product_id = _get_product_id(db, artifact)

    try:
        chroma = ChromaDBService()
    except ChromaDBUnavailableError:
        # Requirements §4.7.3: ChromaDB is a critical dependency — fail the job.
        raise

    pending_lokalise_batch: list[dict[str, Any]] = []

    for image in images:
        proc = ImageProcessing(
            artifact_id=artifact.artifact_id,
            image_id=image.image_id,
            image_hash=image.image_hash,
            image_path=storage.new_source_key(artifact.project_id, artifact.artifact_id, image.filename),
            image_position=image.position,
        )
        db.add(proc)
        storage.put_bytes(proc.image_path, image.image_bytes, storage.guess_content_type(image.filename))

        classification, confidence = classifier.classify(image.image_bytes)
        proc.classification = classification
        proc.classification_confidence = confidence

        if classification != "ui_screenshot" or not is_confident(confidence):
            proc.status = "manual"
            proc.requires_manual_translation = True
            db.flush()
            continue

        proc.status = "classified"

        try:
            matches = chroma.find_matches(image.image_bytes, product_id=product_id)
        except ChromaDBUnavailableError:
            raise

        if not matches:
            proc.status = "manual"
            proc.requires_manual_translation = True
            db.flush()
            continue

        best = matches[0]
        proc.chromadb_match_id = uuid.UUID(best.chromadb_id) if _is_uuid(best.chromadb_id) else None
        proc.chromadb_similarity = round(best.similarity, 4)
        proc.figma_file_key = best.metadata.get("figma_file_key")
        proc.figma_frame_id = best.metadata.get("figma_frame_id")
        proc.status = "matched"
        db.flush()

        cache_row = _lookup_cache(db, image.image_hash, artifact.project.target_language)
        if cache_row is not None:
            proc.translated_image_path = cache_row.translated_image_path
            proc.status = "cached"
            proc.cache_hit = True
            cache_row.usage_count += 1
            cache_row.last_used_at = datetime.now(timezone.utc)
            db.flush()
            continue

        figma_image = _lookup_figma_image(db, proc.figma_file_key, proc.figma_frame_id)
        if figma_image is None:
            proc.status = "manual"
            proc.requires_manual_translation = True
            db.flush()
            continue

        proc.status = "translating"
        db.flush()
        pending_lokalise_batch.append(
            {
                "processing_id": proc.processing_id,
                "figma_image_id": figma_image.figma_image_id,
                "variables": get_text_elements(figma_image),
            }
        )

    db.commit()

    if not pending_lokalise_batch:
        _finish_subtask(db, artifact, subtask)
        return

    _upload_image_text_batch(db, artifact, subtask, pending_lokalise_batch)
    raise PipelineSuspended("image_pipeline: awaiting Lokalise image-text translation")


def _upload_image_text_batch(
    db: Session,
    artifact: ProjectArtifact,
    subtask: ArtifactSubtask,
    batch: list[dict[str, Any]],
) -> None:
    lokalise = LokaliseService()
    items = []
    for entry in batch:
        for variable in entry["variables"]:
            items.append(
                {
                    "key": f"image.{entry['processing_id']}.{variable['name']}",
                    "sourceText": next(iter(variable.get("values", {}).values()), ""),
                    "context": f"UI screenshot text ({variable['name']})",
                }
            )

    source_language = (artifact.project.metadata_ or {}).get("source_language", "en")
    result = lokalise.upload_content(items, source_language=source_language)
    external_id = result.get("keys", [{}])[0].get("task_id") if result.get("keys") else None

    lokalise_task = create_lokalise_task(
        db,
        artifact_id=artifact.artifact_id,
        subtask_id=subtask.subtask_id,
        task_type="image_text",
        source_language=source_language,
        target_language=artifact.project.target_language,
        lokalise_task_external_id=external_id,
    )
    lokalise_task.metadata_ = {"batch": [{"processingId": str(e["processing_id"])} for e in batch]}
    db.commit()


def on_image_translations_ready(db: Session, lokalise_task: LokaliseTask) -> None:
    """Called (via `lokalise_service`'s completion dispatch) once the batched
    `image_text` Lokalise task completes — render every pending image via
    Figma, AI-review it, cache it, then trip the join barrier.
    """
    subtask = db.get(ArtifactSubtask, lokalise_task.subtask_id)
    artifact = db.get(ProjectArtifact, lokalise_task.artifact_id)
    figma = FigmaService()
    lokalise = LokaliseService()

    bundle_url = lokalise.download_translations(lokalise_task.target_language)
    translations_by_key = fetch_translation_bundle(bundle_url)

    processing_ids = [
        uuid.UUID(e["processingId"]) for e in (lokalise_task.metadata_ or {}).get("batch", [])
    ]
    for processing_id in processing_ids:
        proc = db.get(ImageProcessing, processing_id)
        if proc is None or proc.status != "translating":
            continue

        figma_image = _lookup_figma_image(db, proc.figma_file_key, proc.figma_frame_id)
        if figma_image is None:
            proc.status = "manual"
            proc.requires_manual_translation = True
            db.flush()
            continue

        variables = get_text_elements(figma_image)
        translations = {
            v["name"]: translations_by_key.get(f"image.{proc.processing_id}.{v['name']}", "")
            for v in variables
        }

        try:
            rendered = figma.render_localized_frame(figma_image, lokalise_task.target_language, translations)
        except Exception as exc:  # noqa: BLE001 — flagged for manual handling, not a hard failure
            logger.error("figma_render_failed", processing_id=str(processing_id), error=str(exc))
            proc.status = "manual"
            proc.requires_manual_translation = True
            proc.error_message = str(exc)
            db.flush()
            continue

        findings = review_rendered_image(rendered, expected_variable_count=len(variables))
        needs_review = any(f.severity in ("critical", "major") for f in findings)

        storage = StorageService()
        output_key = storage.new_output_key(
            artifact.project_id, artifact.artifact_id, f"images/{processing_id}_{lokalise_task.target_language}.png"
        )
        storage.put_bytes(output_key, rendered, "image/png")

        proc.translated_image_path = output_key
        proc.status = "manual" if needs_review else "translated"
        proc.requires_manual_translation = needs_review
        db.flush()

        if not needs_review:
            _store_cache(db, proc.image_hash, lokalise_task.target_language, figma_image.figma_frame_id, output_key)

    db.commit()
    _finish_subtask(db, artifact, subtask)


def _finish_subtask(db: Session, artifact: ProjectArtifact, subtask: ArtifactSubtask) -> None:
    subtask.status = "complete"
    subtask.progress_percent = 100
    subtask.completed_at = datetime.now(timezone.utc)
    db.commit()

    from app.pipeline.join_barrier import complete_subtask_and_maybe_resume

    complete_subtask_and_maybe_resume(artifact.artifact_id, subtask.task_type)


def _lookup_cache(db: Session, image_hash: str, target_language: str) -> TranslationCache | None:
    return (
        db.execute(
            select(TranslationCache).where(
                TranslationCache.source_image_hash == image_hash,
                TranslationCache.target_language == target_language,
            )
        )
        .scalars()
        .first()
    )


def _store_cache(
    db: Session, image_hash: str, target_language: str, figma_frame_id: str | None, path: str
) -> None:
    cache = TranslationCache(
        source_image_hash=image_hash,
        target_language=target_language,
        figma_frame_id=figma_frame_id,
        translated_image_path=path,
    )
    db.add(cache)
    db.flush()


def _lookup_figma_image(db: Session, file_key: str | None, frame_id: str | None) -> FigmaImage | None:
    if not file_key or not frame_id:
        return None
    return (
        db.execute(
            select(FigmaImage).where(
                FigmaImage.figma_file_key == file_key, FigmaImage.figma_frame_id == frame_id
            )
        )
        .scalars()
        .first()
    )


def _get_product_id(db: Session, artifact: ProjectArtifact) -> uuid.UUID:
    return artifact.project.product_id


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def compute_image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()
