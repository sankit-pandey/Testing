"""Webhook receivers — Design ref: `Technical_Design_Document.md` §4.3;
`Architecture_Diagrams.md` §11, §17. Story 4.2.

Multi-tenancy extension: the payload's `project.id` (Lokalise's project,
not ours) is reverse-looked-up against each tenant's configured
`lokalise_project_id` override so the signature is verified against that
tenant's webhook secret rather than only the platform-wide default.
"""
import asyncio
import json

from fastapi import APIRouter, Header, Request, status
from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.lokalise_tasks import LokaliseTask
from app.services.lokalise_service import LokaliseService, mark_lokalise_task_completed
from app.services.tenant_service import find_tenant_id_by_lokalise_project_id, get_tenant_setting_sync
from app.utils.idempotency import acquire_idempotency_key

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/lokalise", status_code=status.HTTP_200_OK)
async def lokalise_webhook(
    request: Request, x_lokalise_signature: str | None = Header(default=None)
) -> dict:
    """Receive Lokalise task-completion events. Always ack 200 (per
    Technical_Design §4.3 contract) — unknown/duplicate/unsigned events are
    logged and ignored rather than surfaced as client errors, since Lokalise
    has no way to act on a non-200 beyond its own retry policy.
    """
    raw_body = await request.body()

    try:
        payload = json.loads(raw_body)
    except ValueError:
        logger.warning("lokalise_webhook_invalid_json")
        return {"received": False}

    lokalise_project_id = payload.get("project", {}).get("id")
    tenant_id, secret = await asyncio.to_thread(_resolve_webhook_secret, lokalise_project_id)

    if not LokaliseService.verify_webhook_signature(raw_body, x_lokalise_signature, secret):
        logger.warning("lokalise_webhook_invalid_signature")
        return {"received": False}

    task_external_id = payload.get("task", {}).get("id")
    task_status = payload.get("task", {}).get("status")

    if not task_external_id or task_status != "completed":
        return {"received": True}

    if not acquire_idempotency_key(f"lokalise-webhook:{task_external_id}:{task_status}"):
        logger.info("lokalise_webhook_duplicate", task_external_id=task_external_id)
        return {"received": True}

    job_id = await asyncio.to_thread(_process_completion, task_external_id)
    return {"received": True, "jobId": job_id}


def _resolve_webhook_secret(lokalise_project_id: str | None) -> tuple[object, str | None]:
    if not lokalise_project_id:
        return None, None
    tenant_id = find_tenant_id_by_lokalise_project_id(lokalise_project_id)
    secret = get_tenant_setting_sync(tenant_id, "lokalise_webhook_secret") if tenant_id else None
    return tenant_id, secret


def _process_completion(task_external_id: str) -> str | None:
    with SessionLocal() as db:
        lokalise_task = (
            db.execute(
                select(LokaliseTask).where(LokaliseTask.lokalise_task_external_id == task_external_id)
            )
            .scalars()
            .first()
        )
        if lokalise_task is None:
            logger.warning("lokalise_webhook_unknown_task", task_external_id=task_external_id)
            return None

        mark_lokalise_task_completed(db, lokalise_task, source="webhook")
        return str(lokalise_task.artifact_id) if lokalise_task.artifact_id else None
