"""Lokalise integration — Design ref: `Technical_Design_Document.md` §2.1.6,
§5.1; `LOCKED_Design_v1.0.md` §4.1, §7; `Architecture_Diagrams.md` §11, §17;
`Database_Schema.md` (`lokalise_tasks`). Story 4.2.

The Technical Design's Lokalise code sample is explicitly **illustrative
pseudocode** (see its header note); this module is a faithful Python
translation of the same operations (`uploadContent`/`downloadTranslations`/
`pollStatus`/`handleWebhook`) against Lokalise's real REST API v2, wrapped in
a circuit breaker + retry-with-backoff (LOCKED §7). Exact webhook event
payloads/signing are an Open Item per `Requirements/Open_Items_Tracker.md`
("Webhook specifications — TBD"); signature verification here uses
HMAC-SHA256 over the raw body with `LOKALISE_WEBHOOK_SECRET`, Lokalise's
documented webhook-signing scheme.
"""
import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.artifact_subtasks import ArtifactSubtask
from app.models.lokalise_tasks import LokaliseTask
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.retry import LOKALISE_MAX_ATTEMPTS, with_retry

logger = get_logger(__name__)


class LokaliseError(Exception):
    """Raised when a Lokalise API call fails after retries."""


class LokaliseService:
    """Sync client (runs inside Celery workers) for the Lokalise API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.token = settings.lokalise_api_token
        self.project_id = settings.lokalise_project_id
        self.base_url = settings.lokalise_base_url
        self.breaker = CircuitBreaker("lokalise")

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Token": self.token or "", "Content-Type": "application/json"}

    def _post(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}{path}", json=json_body, headers=self._headers())
                response.raise_for_status()
                return response.json()

        try:
            return self.breaker.call(
                lambda: with_retry(_call, max_attempts=LOKALISE_MAX_ATTEMPTS, exceptions=(httpx.HTTPError,))
            )
        except httpx.HTTPError as exc:
            raise LokaliseError(f"Lokalise API call to {path} failed: {exc}") from exc

    def _get(self, path: str) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{self.base_url}{path}", headers=self._headers())
                response.raise_for_status()
                return response.json()

        try:
            return self.breaker.call(
                lambda: with_retry(_call, max_attempts=LOKALISE_MAX_ATTEMPTS, exceptions=(httpx.HTTPError,))
            )
        except httpx.HTTPError as exc:
            raise LokaliseError(f"Lokalise API call to {path} failed: {exc}") from exc

    def upload_document(
        self, filename: str, file_bytes: bytes, source_language: str, target_language: str
    ) -> dict[str, Any]:
        """Upload the ORIGINAL document as-is (LOCKED §4.1 — IFU DOCX is never
        parsed by the platform; Lokalise extracts + translates the text).
        """
        payload = {
            "data": base64.b64encode(file_bytes).decode("ascii"),
            "filename": filename,
            "lang_iso": source_language,
            "target_langs": [target_language],
        }
        return self._post(f"/projects/{self.project_id}/files/upload", payload)

    def upload_content(self, items: list[dict[str, Any]], source_language: str = "en") -> dict[str, Any]:
        """Upload structured content (UI strings, image text) as keys —
        Technical_Design §2.1.6 `uploadContent`.
        """
        keys = [
            {
                "key_name": item["key"],
                "platforms": ["web"],
                "translations": [{"language_iso": source_language, "translation": item["sourceText"]}],
                "context": item.get("context"),
                "screenshots": item.get("screenshots", []),
            }
            for item in items
        ]
        return self._post(f"/projects/{self.project_id}/keys", {"keys": keys})

    def get_task_status(self, task_external_id: str) -> str:
        """Poll a Lokalise task's status. Technical_Design §2.1.6 `pollStatus`/`getTaskStatus`."""
        data = self._get(f"/projects/{self.project_id}/tasks/{task_external_id}")
        return data.get("task", {}).get("status", "unknown")

    def download_translations(self, target_language_iso: str) -> str:
        """Returns the downloadable bundle URL. Technical_Design §2.1.6 `downloadTranslations`."""
        data = self._post(
            f"/projects/{self.project_id}/files/download",
            {"format": "json", "original_filenames": False, "filter_langs": [target_language_iso]},
        )
        return data["bundle_url"]

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
        settings = get_settings()
        if not settings.lokalise_webhook_secret or not signature:
            return False
        computed = hmac.new(
            settings.lokalise_webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature)


def fetch_translation_bundle(bundle_url: str) -> dict[str, Any]:
    """Download and flatten a Lokalise JSON bundle to `{dotted.key: text}` —
    shared by the image sub-pipeline (Story 5.1) and UI Resource strategy
    (Story 5.3), both of which upload flat keys via `upload_content`.
    """
    with httpx.Client(timeout=30.0) as client:
        response = client.get(bundle_url)
        response.raise_for_status()
        data = response.json()

    flat: dict[str, Any] = {}

    def _walk(prefix: str, node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                _walk(f"{prefix}.{key}" if prefix else key, value)
        else:
            flat[prefix] = node

    _walk("", data)
    return flat


def create_lokalise_task(
    db: Session,
    *,
    artifact_id: uuid.UUID,
    subtask_id: uuid.UUID | None,
    task_type: str,
    source_language: str,
    target_language: str,
    lokalise_task_external_id: str | None = None,
) -> LokaliseTask:
    settings = get_settings()
    task = LokaliseTask(
        artifact_id=artifact_id,
        subtask_id=subtask_id,
        lokalise_project_id=settings.lokalise_project_id or "",
        lokalise_task_external_id=lokalise_task_external_id,
        task_type=task_type,
        source_language=source_language,
        target_language=target_language,
        status="uploaded" if lokalise_task_external_id else "pending",
        uploaded_at=datetime.now(timezone.utc) if lokalise_task_external_id else None,
    )
    db.add(task)
    db.flush()
    return task


def _dispatch_completion(db: Session, lokalise_task: LokaliseTask) -> None:
    """Route a completed Lokalise task to whatever else must happen before its
    sub-task can be marked done. `document`/default just trip the join
    barrier directly; `image_text` must render images via Figma first
    (Story 5.1); `ui_strings` must reconstruct the resource file first
    (Story 5.3).
    """
    if not lokalise_task.subtask_id:
        return
    subtask = db.get(ArtifactSubtask, lokalise_task.subtask_id)
    if subtask is None:
        return

    if lokalise_task.task_type == "image_text":
        from app.pipeline.image_pipeline import on_image_translations_ready

        on_image_translations_ready(db, lokalise_task)
        return

    if lokalise_task.task_type == "ui_strings":
        from app.strategies.ui_resource.strategy import on_ui_strings_ready

        on_ui_strings_ready(db, lokalise_task)
        return

    from app.pipeline.join_barrier import complete_subtask_and_maybe_resume

    complete_subtask_and_maybe_resume(lokalise_task.artifact_id, subtask.task_type)


def mark_lokalise_task_completed(
    db: Session, lokalise_task: LokaliseTask, *, source: str
) -> bool:
    """Mark completion (idempotent) and trip the parallel-branch join barrier
    (Story 2.5) for the associated sub-task, if any. Returns True iff this
    call actually transitioned the task (False for an already-completed task).
    """
    if lokalise_task.status == "completed":
        return False

    lokalise_task.status = "completed"
    lokalise_task.completed_at = datetime.now(timezone.utc)
    if source == "webhook":
        lokalise_task.webhook_received_at = datetime.now(timezone.utc)
    db.flush()
    db.commit()

    _dispatch_completion(db, lokalise_task)

    logger.info(
        "lokalise_task_completed",
        lokalise_task_id=str(lokalise_task.lokalise_task_id),
        artifact_id=str(lokalise_task.artifact_id),
        source=source,
    )
    return True


def poll_and_resume_pending_tasks() -> dict[str, int]:
    """Celery Beat entrypoint (every `LOKALISE_POLL_INTERVAL_MINUTES`):
    poll every non-terminal `lokalise_tasks` row; resume the pipeline for any
    that have completed since the last poll. Fallback for missed webhooks
    (LOCKED §7; Architecture_Diagrams §11, §17).
    """
    service = LokaliseService()
    polled = 0
    completed = 0

    with SessionLocal() as db:
        pending = (
            db.execute(
                select(LokaliseTask).where(
                    LokaliseTask.status.in_(("pending", "uploaded", "translating", "reviewing"))
                )
            )
            .scalars()
            .all()
        )

        for task in pending:
            if not task.lokalise_task_external_id:
                continue
            polled += 1
            task.polling_count += 1
            try:
                remote_status = service.get_task_status(task.lokalise_task_external_id)
            except LokaliseError as exc:
                logger.error("lokalise_poll_failed", lokalise_task_id=str(task.lokalise_task_id), error=str(exc))
                db.commit()
                continue

            if remote_status == "completed":
                if mark_lokalise_task_completed(db, task, source="poll"):
                    completed += 1
            else:
                task.status = remote_status if remote_status != "unknown" else task.status
                db.commit()

    logger.info("lokalise_poll_cycle", polled=polled, completed=completed)
    return {"polled": polled, "completed": completed}
